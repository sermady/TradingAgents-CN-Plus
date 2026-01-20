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


class UnifiedConfigManager:
    """
    统一配置管理器

    整合所有配置源，提供统一的配置接口。
    配置优先级：环境变量 > MongoDB > 文件 > 默认值
    """

    _instance: Optional["UnifiedConfigManager"] = None
    _lock: Lock = Lock()

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

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
        self._db_cache_ttl = 60

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
        self, key: str, default: Any = None, force_refresh: bool = False
    ) -> Optional[Any]:
        """
        从MongoDB获取配置

        Args:
            key: 配置键
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
