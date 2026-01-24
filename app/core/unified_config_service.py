# -*- coding: utf-8 -*-
"""
统一配置管理器 (Unified Config Manager)

整合三个配置管理器(config.py, config_manager.py, unified_config.py)的功能：
1. 环境变量配置 (config.py)
2. MongoDB配置 (config_manager.py)
3. 文件配置 (unified_config.py)

配置优先级：环境变量 > MongoDB > 文件 > 默认值
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from threading import Lock
import hashlib

from pydantic_settings import BaseSettings

# 导入现有的配置类
from app.core.config import Settings as EnvSettings
from app.core.database import get_mongo_db_sync
from app.models.config import LLMConfig, SystemConfig

logger = logging.getLogger(__name__)


@dataclass
class ConfigCacheEntry:
    """配置缓存条目"""

    value: Any
    timestamp: datetime
    ttl: int = 60  # 缓存过期时间（秒）
    source: str = ""  # 配置来源（env/mongodb/file/default）

    def is_expired(self) -> bool:
        """检查缓存是否过期"""
        return (datetime.now(timezone.utc) - self.timestamp).total_seconds() > self.ttl


# ==================== 统一配置管理器 ====================

# 类级别变量（线程安全单例模式）
_config_manager_instance: Optional["UnifiedConfigManager"] = None
_config_manager_lock = Lock()
_config_manager_initialized = False


class UnifiedConfigManager:
    """
    统一配置管理器

    整合所有配置源，提供统一的配置接口。
    配置优先级：环境变量 > MongoDB > 文件 > 默认值
    """

    def __new__(cls):
        """线程安全的单例模式"""
        global _config_manager_instance

        # 使用类级别锁确保线程安全
        with _config_manager_lock:
            if _config_manager_instance is None:
                _config_manager_instance = super().__new__(cls)
                _config_manager_instance._initialized = False

        return _config_manager_instance

    def __init__(self):
        if self._initialized:
            return

        # 配置缓存
        self._cache: Dict[str, ConfigCacheEntry] = {}
        self._db_config_cache: Optional[Dict[str, Any]] = None
        self._db_config_cache_timestamp: Optional[datetime] = None
        self._file_config_cache: Dict[str, Dict[str, Any]] = {}

        # 配置文件路径
        self._config_paths = {
            "models": Path("config/models.json"),
            "settings": Path("config/settings.json"),
            "pricing": Path("config/pricing.json"),
            "tradingagents": Path("tradingagents/config/settings.toml"),
        }

        # 环境变量配置（pydantic）
        self._env_settings = EnvSettings()

        # MongoDB配置缓存TTL（秒）
        # 生产环境建议300-600秒，开发环境60秒
        self._db_cache_ttl = 300  # 从60秒提升到300秒，减少数据库查询频率

        self._initialized = True
        logger.info("✅ 统一配置管理器初始化完成")

    # ==================== 配置源加载 ====================

    def _get_env_config(self, key: str, default: Any = None) -> Optional[Any]:
        """
        从环境变量获取配置

        Args:
            key: 配置键（大小写不敏感）
            default: 默认值

        Returns:
            配置值，如果不存在则返回默认值
        """
        env_key = key.upper()
        if env_key in os.environ:
            return os.environ[env_key]

        # 尝试从pydantic Settings获取
        if hasattr(self._env_settings, key):
            return getattr(self._env_settings, key)

        return default

    def _get_mongodb_config(
        self,
        key: Optional[str] = None,
        default: Any = None,
        force_refresh: bool = False,
    ) -> Optional[Any]:
        """
        从MongoDB获取配置

        Args:
            key: 配置键，如果为None则返回整个配置文档
            default: 默认值
            force_refresh: 强制刷新缓存

        Returns:
            配置值，如果不存在则返回默认值
        """
        try:
            # 检查缓存
            if not force_refresh and self._db_config_cache is not None:
                if self._db_config_cache_timestamp is not None:
                    cache_age = (
                        datetime.now(timezone.utc) - self._db_config_cache_timestamp
                    ).total_seconds()
                    if cache_age < self._db_cache_ttl:
                        # 如果key为None，返回整个配置文档
                        if key is None:
                            return self._db_config_cache
                        # 从缓存中获取
                        return self._db_config_cache.get(key, default)

            # 从MongoDB加载
            db = get_mongo_db_sync()
            if db is None:
                logger.warning("MongoDB连接失败，无法加载配置")
                return default

            # 获取最新的系统配置
            collection = db.system_configs
            doc = collection.find_one({"is_active": True}, sort=[("version", -1)])

            if doc:
                # 缓存整个配置文档
                self._db_config_cache = doc
                self._db_config_cache_timestamp = datetime.now(timezone.utc)

                # 如果key为None，返回整个配置文档
                if key is None:
                    return doc

                # 从system_settings或llm_configs中获取
                if key in doc:
                    return doc[key]

                # 尝试从system_settings中获取
                system_settings = doc.get("system_settings", {})
                if key in system_settings:
                    return system_settings[key]

            return default

        except Exception as e:
            logger.error(f"❌ 从MongoDB加载配置失败: {e}")
            return default

    def _get_file_config(
        self, file_key: str, config_key: Optional[str] = None, default: Any = None
    ) -> Optional[Any]:
        """
        从文件获取配置

        Args:
            file_key: 配置文件键（models/settings/pricing/tradingagents）
            config_key: 配置键，如果为None则返回整个文件内容
            default: 默认值

        Returns:
            配置值，如果不存在则返回默认值
        """
        try:
            file_path = self._config_paths.get(file_key)
            if file_path is None or not file_path.exists():
                return default

            # 检查缓存
            cache_key = f"{file_key}:{config_key or 'all'}"
            if cache_key in self._file_config_cache:
                cached_entry = self._file_config_cache[cache_key]
                if not cached_entry.is_expired():
                    return cached_entry.value

            # 加载文件
            with open(file_path, "r", encoding="utf-8") as f:
                if file_key == "tradingagents":
                    import toml

                    data = toml.load(f)
                else:
                    data = json.load(f)

            # 缓存文件内容
            self._file_config_cache[cache_key] = ConfigCacheEntry(
                value=data,
                timestamp=datetime.now(timezone.utc),
                ttl=300,  # 文件配置缓存5分钟
                source="file",
            )

            # 如果需要返回特定键
            if config_key is not None:
                if config_key in data:
                    return data[config_key]
                return default

            return data

        except Exception as e:
            logger.error(f"❌ 从文件加载配置失败 ({file_key}): {e}")
            return default

    # ==================== 统一配置接口 ====================

    def get(self, key: str, default: Any = None, category: str = "general") -> Any:
        """
        获取配置值（统一接口）

        配置优先级：环境变量 > MongoDB > 文件 > 默认值

        Args:
            key: 配置键
            default: 默认值
            category: 配置类别（general/llm/database/system）

        Returns:
            配置值，如果不存在则返回默认值
        """
        # 检查缓存
        cache_key = f"{category}:{key}"
        if cache_key in self._cache:
            cached_entry = self._cache[cache_key]
            if not cached_entry.is_expired():
                logger.debug(f"📦 从缓存获取配置: {cache_key}")
                return cached_entry.value

        # 按优先级查找配置
        value = None
        source = ""

        # 1. 环境变量
        env_value = self._get_env_config(key)
        if env_value is not None:
            value = env_value
            source = "env"
            logger.debug(f"🌍 从环境变量获取配置: {key} = {value}")

        # 2. MongoDB配置
        if value is None:
            mongo_value = self._get_mongodb_config(key)
            if mongo_value is not None:
                value = mongo_value
                source = "mongodb"
                logger.debug(f"💾 从MongoDB获取配置: {key} = {value}")

        # 3. 文件配置（针对特定类别）
        if value is None and category in ["llm", "database", "system"]:
            file_value = self._get_file_config("settings", key)
            if file_value is not None:
                value = file_value
                source = "file"
                logger.debug(f"📄 从文件获取配置: {key} = {value}")

        # 4. 使用默认值
        if value is None:
            value = default
            source = "default"
            logger.debug(f"🔧 使用默认值: {key} = {value}")

        # 缓存结果
        if value is not None:
            self._cache[cache_key] = ConfigCacheEntry(
                value=value,
                timestamp=datetime.now(timezone.utc),
                ttl=60,  # 默认缓存60秒
                source=source,
            )

        return value

    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """
        获取特定LLM模型的配置

        Args:
            model_name: 模型名称

        Returns:
            模型配置字典
        """
        # 默认配置
        config = {
            "model_name": model_name,
            "max_tokens": 4000,
            "temperature": 0.7,
            "timeout": 180,
            "retry_times": 3,
            "api_base": None,
            "provider": "dashscope",
            "input_price_per_1k": 0.0,
            "output_price_per_1k": 0.0,
            "currency": "CNY",
        }

        # 从MongoDB获取
        db_config = self._get_mongodb_config(force_refresh=False)
        if db_config and "llm_configs" in db_config:
            llm_configs = db_config["llm_configs"]
            for llm_cfg in llm_configs:
                cfg_name = (
                    llm_cfg.get("model_name")
                    if isinstance(llm_cfg, dict)
                    else getattr(llm_cfg, "model_name", "")
                )
                if cfg_name == model_name:
                    # 更新配置
                    if isinstance(llm_cfg, dict):
                        config.update(
                            {k: v for k, v in llm_cfg.items() if v is not None}
                        )
                    else:
                        # Pydantic模型
                        if hasattr(llm_cfg, "max_tokens") and llm_cfg.max_tokens:
                            config["max_tokens"] = llm_cfg.max_tokens
                        if hasattr(llm_cfg, "temperature") and llm_cfg.temperature:
                            config["temperature"] = llm_cfg.temperature
                        if hasattr(llm_cfg, "timeout") and llm_cfg.timeout:
                            config["timeout"] = llm_cfg.timeout
                        if hasattr(llm_cfg, "api_base") and llm_cfg.api_base:
                            config["api_base"] = llm_cfg.api_base
                        if hasattr(llm_cfg, "provider") and llm_cfg.provider:
                            config["provider"] = llm_cfg.provider
                        if (
                            hasattr(llm_cfg, "input_price_per_1k")
                            and llm_cfg.input_price_per_1k
                        ):
                            config["input_price_per_1k"] = llm_cfg.input_price_per_1k
                        if (
                            hasattr(llm_cfg, "output_price_per_1k")
                            and llm_cfg.output_price_per_1k
                        ):
                            config["output_price_per_1k"] = llm_cfg.output_price_per_1k
                    logger.info(f"✅ 从MongoDB加载模型配置: {model_name}")
                    break

        # 如果MongoDB没有配置，尝试从文件获取
        if config.get("api_base") is None:
            file_models = self._get_file_config("models")
            if file_models:
                for model in file_models:
                    if model.get("model_name") == model_name:
                        config["api_base"] = model.get("base_url")
                        config["max_tokens"] = model.get(
                            "max_tokens", config["max_tokens"]
                        )
                        config["temperature"] = model.get(
                            "temperature", config["temperature"]
                        )
                        logger.info(f"✅ 从文件加载模型配置: {model_name}")
                        break

        # 推断provider
        if config.get("provider") == "dashscope":
            config["provider"] = "dashscope"
        elif "gpt" in model_name:
            config["provider"] = "openai"
        elif "gemini" in model_name:
            config["provider"] = "google"
        elif "deepseek" in model_name:
            config["provider"] = "deepseek"

        return config

    def get_system_setting(self, key: str, default: Any = None) -> Any:
        """
        获取系统设置

        Args:
            key: 设置键
            default: 默认值

        Returns:
            设置值
        """
        return self.get(key, default, category="system")

    def get_quick_analysis_model(self) -> str:
        """获取快速分析模型名称"""
        return self.get_system_setting("quick_analysis_model", "qwen-turbo")

    def get_deep_analysis_model(self) -> str:
        """获取深度分析模型名称"""
        return self.get_system_setting("deep_analysis_model", "qwen-max")

    def get_provider_by_model(self, model_name: str) -> str:
        """
        根据模型名称获取provider

        Args:
            model_name: 模型名称

        Returns:
            provider名称
        """
        config = self.get_model_config(model_name)
        return config.get("provider", "dashscope")

    # ==================== 向后兼容方法 ====================

    def get_llm_configs(self) -> List[Any]:
        """
        获取所有LLM配置（向后兼容方法）

        Returns:
            LLM配置列表（从MongoDB或文件）
        """
        # 尝试从MongoDB获取
        db_config = self._get_mongodb_config(force_refresh=False)
        if db_config and "llm_configs" in db_config:
            llm_configs = db_config["llm_configs"]
            logger.info(f"📊 从MongoDB获取到 {len(llm_configs)} 个LLM配置")
            return llm_configs

        # 降级到文件配置
        file_models = self._get_file_config("models")
        if file_models:
            logger.info(f"📊 从文件获取到 {len(file_models)} 个LLM配置")
            return file_models

        return []

    def get_default_model(self) -> str:
        """
        获取默认模型名称（向后兼容方法）

        Returns:
            默认模型名称
        """
        # 优先使用系统设置中的default_model
        default_model = self.get_system_setting("default_model")
        if default_model:
            return default_model

        # 降级到快速分析模型
        return self.get_quick_analysis_model()

    def get_data_source_configs(self) -> List[Any]:
        """
        获取数据源配置（向后兼容方法）

        Returns:
            数据源配置列表（从MongoDB或文件）
        """
        # 尝试从MongoDB获取
        db_config = self._get_mongodb_config(force_refresh=False)
        if db_config and "data_source_configs" in db_config:
            ds_configs = db_config["data_source_configs"]
            logger.info(f"📊 从MongoDB获取到 {len(ds_configs)} 个数据源配置")
            return ds_configs

        # 降级到文件配置
        settings_data = self._get_file_config("settings")
        if settings_data and "data_sources" in settings_data:
            ds_configs = settings_data["data_sources"]
            logger.info(f"📊 从文件获取到 {len(ds_configs)} 个数据源配置")
            return ds_configs

        return []

    def save_system_settings(self, settings: Dict[str, Any]) -> bool:
        """
        保存系统设置到文件（向后兼容方法）

        Args:
            settings: 系统设置字典

        Returns:
            是否保存成功
        """
        try:
            settings_file = self._config_paths["settings"]
            settings_file.parent.mkdir(parents=True, exist_ok=True)

            # 读取现有文件
            existing_data = {}
            if settings_file.exists():
                try:
                    with open(settings_file, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                except Exception as e:
                    logger.warning(f"读取现有设置文件失败: {e}")

            # 更新system_settings
            existing_data["system_settings"] = settings

            # 保存文件
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ 系统设置已保存到文件: {settings_file}")
            return True

        except Exception as e:
            logger.error(f"❌ 保存系统设置失败: {e}")
            return False

    def save_llm_config(self, llm_config: Any) -> bool:
        """
        保存LLM配置到MongoDB（向后兼容方法）

        Args:
            llm_config: LLM配置（字典或LLMConfig对象）

        Returns:
            是否保存成功
        """
        try:
            # 转换为字典格式（兼容LLMConfig对象和字典）
            if hasattr(llm_config, "model_name"):
                # LLMConfig 对象
                config_dict = {
                    "model_name": getattr(llm_config, "model_name", None),
                    "model_display_name": getattr(
                        llm_config, "model_display_name", None
                    ),
                    "provider": getattr(llm_config, "provider", None),
                    "api_key": getattr(llm_config, "api_key", None),
                    "api_base": getattr(llm_config, "api_base", None),
                    "max_tokens": getattr(llm_config, "max_tokens", 4000),
                    "temperature": getattr(llm_config, "temperature", 0.7),
                    "timeout": getattr(llm_config, "timeout", 180),
                    "retry_times": getattr(llm_config, "retry_times", 3),
                    "enabled": getattr(llm_config, "enabled", True),
                    "description": getattr(llm_config, "description", None),
                    "enable_memory": getattr(llm_config, "enable_memory", False),
                    "enable_debug": getattr(llm_config, "enable_debug", False),
                    "priority": getattr(llm_config, "priority", 0),
                    "model_category": getattr(llm_config, "model_category", None),
                    "input_price_per_1k": getattr(
                        llm_config, "input_price_per_1k", None
                    ),
                    "output_price_per_1k": getattr(
                        llm_config, "output_price_per_1k", None
                    ),
                    "currency": getattr(llm_config, "currency", "CNY"),
                    "capability_level": getattr(llm_config, "capability_level", 2),
                    "suitable_roles": getattr(llm_config, "suitable_roles", ["both"]),
                    "features": getattr(llm_config, "features", []),
                    "recommended_depths": getattr(
                        llm_config, "recommended_depths", ["快速", "基础", "标准"]
                    ),
                    "performance_metrics": getattr(
                        llm_config, "performance_metrics", None
                    ),
                }
            else:
                # 已经是字典
                config_dict = llm_config

            model_name = (
                config_dict.get("model_name") if isinstance(config_dict, dict) else None
            )
            if not model_name:
                logger.error("❌ LLM配置缺少model_name字段")
                return False

            # 获取MongoDB连接
            db = get_mongo_db_sync()
            if db is None:
                logger.error("❌ MongoDB连接失败，无法保存LLM配置")
                return False

            # 获取或创建系统配置文档
            collection = db.system_configs
            doc = collection.find_one({"is_active": True}, sort=[("version", -1)])

            if not doc:
                # 创建新的配置文档
                doc = {
                    "version": 1,
                    "is_active": True,
                    "llm_configs": [],
                    "data_source_configs": [],
                    "system_settings": {},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }

            # 更新或添加LLM配置
            llm_configs = doc.get("llm_configs", [])

            # 查找是否已存在相同模型名的配置
            existing_index = None
            for i, config in enumerate(llm_configs):
                config_model_name = (
                    config.get("model_name")
                    if isinstance(config, dict)
                    else getattr(config, "model_name", None)
                )
                if config_model_name == model_name:
                    existing_index = i
                    break

            if existing_index is not None:
                # 更新现有配置
                llm_configs[existing_index] = config_dict
                logger.info(f"🔄 更新LLM配置: {model_name}")
            else:
                # 添加新配置
                llm_configs.append(config_dict)
                logger.info(f"➕ 添加LLM配置: {model_name}")

            doc["llm_configs"] = llm_configs
            doc["updated_at"] = datetime.now(timezone.utc).isoformat()

            # 保存到MongoDB
            if "_id" in doc:
                collection.replace_one({"_id": doc["_id"]}, doc)
            else:
                collection.insert_one(doc)

            # 清除缓存
            self._db_config_cache = None

            logger.info(f"✅ LLM配置已保存到MongoDB: {model_name}")
            return True

        except Exception as e:
            logger.error(f"❌ 保存LLM配置失败: {e}")
            return False

    # ==================== 缓存管理 ====================

    def clear_cache(self, pattern: Optional[str] = None):
        """
        清除配置缓存

        Args:
            pattern: 清除模式（可选），如果为None则清除所有缓存
        """
        if pattern is None:
            self._cache.clear()
            logger.info("🗑️ 清除所有配置缓存")
        else:
            keys_to_remove = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self._cache[key]
            logger.info(f"🗑️ 清除配置缓存: {pattern} ({len(keys_to_remove)}个)")

    def refresh_db_config(self):
        """强制刷新MongoDB配置缓存"""
        self._db_config_cache = None
        self._db_config_cache_timestamp = None
        logger.info("🔄 强制刷新MongoDB配置")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            缓存统计字典
        """
        total_entries = len(self._cache)
        expired_entries = sum(1 for entry in self._cache.values() if entry.is_expired())

        sources = {}
        for entry in self._cache.values():
            source = entry.source
            sources[source] = sources.get(source, 0) + 1

        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "sources": sources,
            "db_config_cached": self._db_config_cache is not None,
            "db_config_cache_age": (
                (
                    datetime.now(timezone.utc) - self._db_config_cache_timestamp
                ).total_seconds()
                if self._db_config_cache_timestamp
                else None
            ),
        }


# 全局配置管理器实例
_config_manager: Optional[UnifiedConfigManager] = None


def get_config_manager() -> UnifiedConfigManager:
    """
    获取全局统一配置管理器实例

    Returns:
        UnifiedConfigManager实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = UnifiedConfigManager()
    return _config_manager


# 为了向后兼容，保留UnifiedConfigManager类名
# 使用get_config_manager()获取实例
UnifiedConfigManager = UnifiedConfigManager  # 警告：这不是真正的类，只是函数别名
