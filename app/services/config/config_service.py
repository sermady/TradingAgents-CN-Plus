# -*- coding: utf-8 -*-
"""
配置管理服务 - 门面类

提供统一的配置管理接口，组合各个子服务：
- MarketConfigService: 市场分类管理
- LLMConfigService: LLM 提供商配置
- DataSourceConfigService: 数据源配置
- DatabaseConfigService: 数据库配置
- ModelCatalogService: 模型目录管理
"""

import time
import logging
from typing import List, Optional, Dict, Any

from app.core.database import get_mongo_db
from app.core.unified_config_service import get_config_manager
from app.models.config import (
    SystemConfig,
    LLMConfig,
    DataSourceConfig,
    DatabaseConfig,
    MarketCategory,
    DataSourceGrouping,
    ModelCatalog,
    LLMProvider,
)
from app.utils.api_tester import LLMAPITester

from .market_config_service import MarketConfigService
from .llm_config_service import LLMConfigService
from .datasource_config_service import DataSourceConfigService
from .database_config_service import DatabaseConfigService
from .model_catalog_service import ModelCatalogService

logger = logging.getLogger(__name__)


class ConfigService:
    """配置管理服务类 - 门面模式

    组合各个子服务，提供统一的配置管理接口。
    所有方法保持与原 ConfigService 完全相同的签名，确保向后兼容。
    """

    def __init__(self, db_manager=None):
        self.db = None
        self.db_manager = db_manager

        # 初始化子服务
        self._market_service = MarketConfigService(db_manager)
        self._llm_service = LLMConfigService(db_manager)
        self._datasource_service = DataSourceConfigService(db_manager)
        self._database_service = DatabaseConfigService(db_manager)
        self._model_catalog_service = ModelCatalogService(db_manager)

    async def _get_db(self):
        """获取数据库连接"""
        if self.db is None:
            if self.db_manager and self.db_manager.mongo_db is not None:
                self.db = self.db_manager.mongo_db
            else:
                self.db = get_mongo_db()
        return self.db

    # ==================== 市场分类管理（委托给 MarketConfigService）====================

    async def get_market_categories(self) -> List[MarketCategory]:
        """获取所有市场分类"""
        return await self._market_service.get_market_categories()

    async def _create_default_market_categories(self) -> List[MarketCategory]:
        """创建默认市场分类"""
        return await self._market_service._create_default_market_categories()

    async def add_market_category(self, category: MarketCategory) -> bool:
        """添加市场分类"""
        return await self._market_service.add_market_category(category)

    async def update_market_category(
        self, category_id: str, updates: Dict[str, Any]
    ) -> bool:
        """更新市场分类"""
        return await self._market_service.update_market_category(category_id, updates)

    async def delete_market_category(self, category_id: str) -> bool:
        """删除市场分类"""
        return await self._market_service.delete_market_category(category_id)

    # ==================== 数据源分组管理（委托给 MarketConfigService）====================

    async def get_datasource_groupings(self) -> List[DataSourceGrouping]:
        """获取所有数据源分组关系"""
        return await self._market_service.get_datasource_groupings()

    async def add_datasource_to_category(self, grouping: DataSourceGrouping) -> bool:
        """将数据源添加到分类"""
        return await self._market_service.add_datasource_to_category(grouping)

    async def remove_datasource_from_category(
        self, data_source_name: str, category_id: str
    ) -> bool:
        """从分类中移除数据源"""
        return await self._market_service.remove_datasource_from_category(
            data_source_name, category_id
        )

    async def update_datasource_grouping(
        self, data_source_name: str, category_id: str, updates: Dict[str, Any]
    ) -> bool:
        """更新数据源分组关系"""
        return await self._market_service.update_datasource_grouping(
            data_source_name, category_id, updates
        )

    async def update_category_datasource_order(
        self, category_id: str, ordered_datasources: List[Dict[str, Any]]
    ) -> bool:
        """更新分类中数据源的排序"""
        return await self._market_service.update_category_datasource_order(
            category_id, ordered_datasources
        )

    # ==================== 系统配置管理 ====================

    async def get_system_config(self) -> Optional[SystemConfig]:
        """获取系统配置 - 优先从数据库获取最新数据"""
        try:
            # 直接从数据库获取最新配置，避免缓存问题
            db = await self._get_db()
            config_collection = db.system_configs

            config_data = await config_collection.find_one(
                {"is_active": True}, sort=[("version", -1)]
            )

            if config_data:
                print(
                    f"📊 从数据库获取配置，版本: {config_data.get('version', 0)}, LLM配置数量: {len(config_data.get('llm_configs', []))}"
                )
                return SystemConfig(**config_data)

            # 如果没有配置，创建默认配置
            print("⚠️ 数据库中没有配置，创建默认配置")
            return await self._create_default_config()

        except Exception as e:
            print(f"❌ 从数据库获取配置失败: {e}")

            # 作为最后的回退，尝试从统一配置管理器获取
            try:
                unified_system_config = (
                    await get_config_manager().get_unified_system_config()
                )
                if unified_system_config:
                    print("🔄 回退到统一配置管理器")
                    return unified_system_config
            except Exception as e2:
                print(f"从统一配置获取也失败: {e2}")

            return None

    async def _create_default_config(self) -> SystemConfig:
        """创建默认系统配置"""
        from app.models.config import ModelProvider, DataSourceType, DatabaseType

        default_config = SystemConfig(
            config_name="默认配置",
            config_type="system",
            llm_configs=[
                LLMConfig(
                    provider=ModelProvider.OPENAI,
                    model_name="gpt-3.5-turbo",
                    api_key="your-openai-api-key",
                    api_base="https://api.openai.com/v1",
                    max_tokens=4000,
                    temperature=0.7,
                    enabled=False,
                    description="OpenAI GPT-3.5 Turbo模型",
                ),
                LLMConfig(
                    provider=ModelProvider.ZHIPU,
                    model_name="glm-4",
                    api_key="your-zhipu-api-key",
                    api_base="https://open.bigmodel.cn/api/paas/v4",
                    max_tokens=4000,
                    temperature=0.7,
                    enabled=True,
                    description="智谱AI GLM-4模型（推荐）",
                ),
                LLMConfig(
                    provider=ModelProvider.QWEN,
                    model_name="qwen-turbo",
                    api_key="your-qwen-api-key",
                    api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
                    max_tokens=4000,
                    temperature=0.7,
                    enabled=False,
                    description="阿里云通义千问模型",
                ),
            ],
            default_llm="glm-4",
            data_source_configs=[
                DataSourceConfig(
                    name="AKShare",
                    type=DataSourceType.AKSHARE,
                    endpoint="https://akshare.akfamily.xyz",
                    timeout=30,
                    rate_limit=100,
                    enabled=True,
                    priority=1,
                    description="AKShare开源金融数据接口",
                ),
                DataSourceConfig(
                    name="Tushare",
                    type=DataSourceType.TUSHARE,
                    api_key="your-tushare-token",
                    endpoint="https://api.tushare.pro",
                    timeout=30,
                    rate_limit=200,
                    enabled=False,
                    priority=2,
                    description="Tushare专业金融数据接口",
                ),
            ],
            default_data_source="AKShare",
            database_configs=[
                DatabaseConfig(
                    name="MongoDB主库",
                    type=DatabaseType.MONGODB,
                    host="localhost",
                    port=27017,
                    database="tradingagents",
                    enabled=True,
                    description="MongoDB主数据库",
                ),
                DatabaseConfig(
                    name="Redis缓存",
                    type=DatabaseType.REDIS,
                    host="localhost",
                    port=6379,
                    database="0",
                    enabled=True,
                    description="Redis缓存数据库",
                ),
            ],
            system_settings={
                "max_concurrent_tasks": 3,
                "default_analysis_timeout": 300,
                "enable_cache": True,
                "cache_ttl": 3600,
                "log_level": "INFO",
                "enable_monitoring": True,
                # Worker/Queue intervals
                "worker_heartbeat_interval_seconds": 30,
                "queue_poll_interval_seconds": 1.0,
                "queue_cleanup_interval_seconds": 60.0,
                # SSE intervals
                "sse_poll_timeout_seconds": 1.0,
                "sse_heartbeat_interval_seconds": 10,
                "sse_task_max_idle_seconds": 300,
                "sse_batch_poll_interval_seconds": 2.0,
                "sse_batch_max_idle_seconds": 600,
                # TradingAgents runtime intervals (optional; DB-managed)
                "ta_hk_min_request_interval_seconds": 2.0,
                "ta_hk_timeout_seconds": 60,
                "ta_hk_max_retries": 3,
                "ta_hk_rate_limit_wait_seconds": 60,
                "ta_hk_cache_ttl_seconds": 86400,
                # 新增：TradingAgents 数据来源策略
                # 是否优先从 app 缓存(Mongo 集合 stock_basic_info / market_quotes) 读取
                "ta_use_app_cache": False,
                "ta_china_min_api_interval_seconds": 0.5,
                "ta_us_min_api_interval_seconds": 1.0,
                "ta_google_news_sleep_min_seconds": 2.0,
                "ta_google_news_sleep_max_seconds": 6.0,
                "app_timezone": "Asia/Shanghai",
            },
        )

        # 保存到数据库
        await self.save_system_config(default_config)
        return default_config

    async def save_system_config(self, config: SystemConfig) -> bool:
        """保存系统配置到数据库"""
        try:
            print(f"💾 开始保存配置，LLM配置数量: {len(config.llm_configs)}")

            # 保存到数据库
            db = await self._get_db()
            config_collection = db.system_configs

            # 更新时间戳和版本
            config.updated_at = now_tz()
            config.version += 1

            # 将当前激活的配置设为非激活
            update_result = await config_collection.update_many(
                {"is_active": True}, {"$set": {"is_active": False}}
            )
            print(f"📝 禁用旧配置数量: {update_result.modified_count}")

            # 插入新配置 - 移除_id字段让MongoDB自动生成新的
            config_dict = config.model_dump(by_alias=True)
            if "_id" in config_dict:
                del config_dict["_id"]  # 移除旧的_id，让MongoDB生成新的

            # 打印即将保存的 system_settings
            system_settings = config_dict.get("system_settings", {})
            print(f"📝 即将保存的 system_settings 包含 {len(system_settings)} 项")
            if "quick_analysis_model" in system_settings:
                print(
                    f"  ✓ 包含 quick_analysis_model: {system_settings['quick_analysis_model']}"
                )
            else:
                print(f"  ⚠️  不包含 quick_analysis_model")
            if "deep_analysis_model" in system_settings:
                print(
                    f"  ✓ 包含 deep_analysis_model: {system_settings['deep_analysis_model']}"
                )
            else:
                print(f"  ⚠️  不包含 deep_analysis_model")

            insert_result = await config_collection.insert_one(config_dict)
            print(f"📝 新配置ID: {insert_result.inserted_id}")

            # 验证保存结果
            saved_config = await config_collection.find_one(
                {"_id": insert_result.inserted_id}
            )
            if saved_config:
                print(
                    f"✅ 配置保存成功，验证LLM配置数量: {len(saved_config.get('llm_configs', []))}"
                )
                return True
            else:
                print("❌ 配置保存验证失败")
                return False

        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def delete_llm_config(self, provider: str, model_name: str) -> bool:
        """删除大模型配置"""
        try:
            print(f"🗑️ 删除大模型配置 - provider: {provider}, model_name: {model_name}")

            config = await self.get_system_config()
            if not config:
                print("❌ 系统配置为空")
                return False

            print(f"📊 当前大模型配置数量: {len(config.llm_configs)}")

            # 打印所有现有配置
            for i, llm in enumerate(config.llm_configs):
                provider_match = str(llm.provider).lower() == provider.lower()
                model_match = llm.model_name == model_name
                print(
                    f"   {i + 1}. provider: {llm.provider} (匹配: {provider_match}), "
                    f"model_name: {llm.model_name} (匹配: {model_match})"
                )

            # 查找并删除指定的LLM配置
            original_count = len(config.llm_configs)

            # 使用更宽松的匹配条件
            config.llm_configs = [
                llm
                for llm in config.llm_configs
                if not (
                    str(llm.provider).lower() == provider.lower()
                    and llm.model_name == model_name
                )
            ]

            new_count = len(config.llm_configs)
            print(f"🔄 删除后配置数量: {new_count} (原来: {original_count})")

            if new_count == original_count:
                print(f"❌ 没有找到匹配的配置: {provider}/{model_name}")
                return False  # 没有找到要删除的配置

            # 保存更新后的配置
            save_result = await self.save_system_config(config)
            print(f"💾 保存结果: {save_result}")

            return save_result

        except Exception as e:
            print(f"❌ 删除LLM配置失败: {e}")
            import traceback

            print("完整堆栈跟踪:")
            print(traceback.format_exc())
            return False

    async def update_system_settings(self, settings: Dict[str, Any]) -> bool:
        """更新系统设置"""
        try:
            config = await self.get_system_config()
            if not config:
                return False

            # 打印更新前的系统设置
            print(f"📝 更新前 system_settings 包含 {len(config.system_settings)} 项")
            if "quick_analysis_model" in config.system_settings:
                print(
                    f"  ✓ 更新前包含 quick_analysis_model: {config.system_settings['quick_analysis_model']}"
                )
            else:
                print(f"  ⚠️  更新前不包含 quick_analysis_model")

            # 更新系统设置
            config.system_settings.update(settings)

            # 打印更新后的系统设置
            print(f"📝 更新后 system_settings 包含 {len(config.system_settings)} 项")
            if "quick_analysis_model" in config.system_settings:
                print(
                    f"  ✓ 更新后包含 quick_analysis_model: {config.system_settings['quick_analysis_model']}"
                )
            else:
                print(f"  ⚠️  更新后不包含 quick_analysis_model")
            if "deep_analysis_model" in config.system_settings:
                print(
                    f"  ✓ 更新后包含 deep_analysis_model: {config.system_settings['deep_analysis_model']}"
                )
            else:
                print(f"  ⚠️  更新后不包含 deep_analysis_model")

            result = await self.save_system_config(config)

            # 同步到文件系统（供 unified_config 使用）
            if result:
                try:
                    from app.core.unified_config_service import get_config_manager

                    get_config_manager().sync_to_legacy_format(config)
                    print(f"✅ 系统设置已同步到文件系统")
                except Exception as e:
                    print(f"⚠️  同步系统设置到文件系统失败: {e}")

            return result

        except Exception as e:
            print(f"更新系统设置失败: {e}")
            return False

    async def get_system_settings(self) -> Dict[str, Any]:
        """获取系统设置"""
        try:
            config = await self.get_system_config()
            if not config:
                return {}
            return config.system_settings
        except Exception as e:
            print(f"获取系统设置失败: {e}")
            return {}

    async def export_config(self) -> Dict[str, Any]:
        """导出配置"""
        try:
            config = await self.get_system_config()
            if not config:
                return {}

            # 转换为可序列化的字典格式
            # 导出时对敏感字段脱敏/清空
            def _llm_sanitize(x: LLMConfig):
                d = x.model_dump()
                d["api_key"] = ""
                # 确保必填字段有默认值（防止导出 None 或空字符串）
                # 注意：max_tokens 在 system_configs 中已经有正确的值，直接使用
                if not d.get("max_tokens") or d.get("max_tokens") == "":
                    d["max_tokens"] = 4000
                if not d.get("temperature") and d.get("temperature") != 0:
                    d["temperature"] = 0.7
                if not d.get("timeout") or d.get("timeout") == "":
                    d["timeout"] = 180
                if not d.get("retry_times") or d.get("retry_times") == "":
                    d["retry_times"] = 3
                return d

            def _ds_sanitize(x: DataSourceConfig):
                d = x.model_dump()
                d["api_key"] = ""
                d["api_secret"] = ""
                return d

            def _db_sanitize(x: DatabaseConfig):
                d = x.model_dump()
                d["password"] = ""
                return d

            from app.utils.timezone import now_tz

            export_data = {
                "config_name": config.config_name,
                "config_type": config.config_type,
                "llm_configs": [_llm_sanitize(llm) for llm in config.llm_configs],
                "default_llm": config.default_llm,
                "data_source_configs": [
                    _ds_sanitize(ds) for ds in config.data_source_configs
                ],
                "default_data_source": config.default_data_source,
                "database_configs": [
                    _db_sanitize(db) for db in config.database_configs
                ],
                # 导出时对 system_settings 中的敏感键做脱敏
                "system_settings": {
                    k: (
                        None
                        if any(
                            p in k.lower()
                            for p in (
                                "key",
                                "secret",
                                "password",
                                "token",
                                "client_secret",
                            )
                        )
                        else v
                    )
                    for k, v in (config.system_settings or {}).items()
                },
                "exported_at": now_tz().isoformat(),
                "version": config.version,
            }

            return export_data

        except Exception as e:
            print(f"导出配置失败: {e}")
            return {}

    async def import_config(self, config_data: Dict[str, Any]) -> bool:
        """导入配置"""
        try:
            # 验证配置数据格式
            if not self._validate_config_data(config_data):
                return False

            # 创建新的系统配置（导入时忽略敏感字段）
            def _llm_sanitize_in(llm: Dict[str, Any]):
                d = dict(llm or {})
                d.pop("api_key", None)
                d["api_key"] = ""
                # 清理空字符串，让 Pydantic 使用默认值
                if d.get("max_tokens") == "" or d.get("max_tokens") is None:
                    d.pop("max_tokens", None)
                if d.get("temperature") == "" or d.get("temperature") is None:
                    d.pop("temperature", None)
                if d.get("timeout") == "" or d.get("timeout") is None:
                    d.pop("timeout", None)
                if d.get("retry_times") == "" or d.get("retry_times") is None:
                    d.pop("retry_times", None)
                return LLMConfig(**d)

            def _ds_sanitize_in(ds: Dict[str, Any]):
                d = dict(ds or {})
                d.pop("api_key", None)
                d.pop("api_secret", None)
                d["api_key"] = ""
                d["api_secret"] = ""
                return DataSourceConfig(**d)

            def _db_sanitize_in(db: Dict[str, Any]):
                d = dict(db or {})
                d.pop("password", None)
                d["password"] = ""
                return DatabaseConfig(**d)

            new_config = SystemConfig(
                config_name=config_data.get("config_name", "导入的配置"),
                config_type="imported",
                llm_configs=[
                    _llm_sanitize_in(llm) for llm in config_data.get("llm_configs", [])
                ],
                default_llm=config_data.get("default_llm"),
                data_source_configs=[
                    _ds_sanitize_in(ds)
                    for ds in config_data.get("data_source_configs", [])
                ],
                default_data_source=config_data.get("default_data_source"),
                database_configs=[
                    _db_sanitize_in(db)
                    for db in config_data.get("database_configs", [])
                ],
                system_settings=config_data.get("system_settings", {}),
            )

            return await self.save_system_config(new_config)

        except Exception as e:
            print(f"导入配置失败: {e}")
            return False

    def _validate_config_data(self, config_data: Dict[str, Any]) -> bool:
        """验证配置数据格式"""
        try:
            required_fields = [
                "llm_configs",
                "data_source_configs",
                "database_configs",
                "system_settings",
            ]
            for field in required_fields:
                if field not in config_data:
                    print(f"配置数据缺少必需字段: {field}")
                    return False

            return True

        except Exception as e:
            print(f"验证配置数据失败: {e}")
            return False

    async def migrate_legacy_config(self) -> bool:
        """迁移传统配置"""
        try:
            # 这里可以调用迁移脚本的逻辑
            # 或者直接在这里实现迁移逻辑
            from scripts.migrate_config_to_webapi import ConfigMigrator

            migrator = ConfigMigrator()
            return await migrator.migrate_all_configs()

        except Exception as e:
            print(f"迁移传统配置失败: {e}")
            return False

    async def update_llm_config(self, llm_config: LLMConfig) -> bool:
        """更新大模型配置"""
        try:
            # 直接保存到统一配置管理器
            success = get_config_manager().save_llm_config(llm_config)
            if not success:
                return False

            # 同时更新数据库配置
            config = await self.get_system_config()
            if not config:
                return False

            # 查找并更新对应的LLM配置
            for i, existing_config in enumerate(config.llm_configs):
                if existing_config.model_name == llm_config.model_name:
                    config.llm_configs[i] = llm_config
                    break
            else:
                # 如果不存在，添加新配置
                config.llm_configs.append(llm_config)

            return await self.save_system_config(config)
        except Exception as e:
            print(f"更新LLM配置失败: {e}")
            return False

    async def test_llm_config(self, llm_config: LLMConfig) -> Dict[str, Any]:
        """测试大模型配置 - 真实调用API进行验证"""
        start_time = time.time()
        try:
            import requests

            # 获取 provider 字符串值（兼容枚举和字符串）
            provider_str = (
                llm_config.provider.value
                if hasattr(llm_config.provider, "value")
                else str(llm_config.provider)
            )

            logger.info(f"🧪 测试大模型配置: {provider_str} - {llm_config.model_name}")
            logger.info(f"📍 API基础URL (模型配置): {llm_config.api_base}")

            # 获取厂家配置（用于获取 API Key 和 default_base_url）
            db = await self._get_db()
            providers_collection = db.llm_providers
            provider_data = await providers_collection.find_one({"name": provider_str})

            # 1. 确定 API 基础 URL
            api_base = llm_config.api_base
            if not api_base:
                # 如果模型配置没有 api_base，从厂家配置获取 default_base_url
                if provider_data and provider_data.get("default_base_url"):
                    api_base = provider_data["default_base_url"]
                    logger.info(f"✅ 从厂家配置获取 API 基础 URL: {api_base}")
                else:
                    return {
                        "success": False,
                        "message": f"模型配置和厂家配置都未设置 API 基础 URL",
                        "response_time": time.time() - start_time,
                        "details": None,
                    }

            # 2. 验证 API Key
            api_key = None
            if llm_config.api_key:
                api_key = llm_config.api_key
            else:
                # 从厂家配置获取 API Key
                if provider_data and provider_data.get("api_key"):
                    api_key = provider_data["api_key"]
                    logger.info(f"✅ 从厂家配置获取到API密钥")
                else:
                    # 尝试从环境变量获取
                    api_key = self._llm_service._get_env_api_key(provider_str)
                    if api_key:
                        logger.info(f"✅ 从环境变量获取到API密钥")

            if not api_key or not self._llm_service._is_valid_api_key(api_key):
                return {
                    "success": False,
                    "message": f"{provider_str} 未配置有效的API密钥",
                    "response_time": time.time() - start_time,
                    "details": None,
                }

            # 3. 根据厂家类型选择测试方法
            # 使用 LLMAPITester 统一测试框架
            logger.info(f"🔍 使用 LLMAPITester 测试框架")

            # 对于 OpenAI 兼容的厂家，使用 test_openai_compatible
            if provider_str in ["openai", "anthropic", "qianfan", "zhipu", "siliconflow", "openrouter", "302ai", "oneapi", "newapi", "custom_aggregator"]:
                result = LLMAPITester.test_openai_compatible(
                    api_key=api_key,
                    display_name=f"{provider_str} {llm_config.model_name}",
                    base_url=api_base,
                    provider_name=provider_str,
                    model=llm_config.model_name,
                )
            else:
                # 其他厂家使用标准测试
                result = LLMAPITester.test_provider(
                    provider=provider_str,
                    api_key=api_key,
                    display_name=f"{provider_str} {llm_config.model_name}",
                    model_name=llm_config.model_name,
                    base_url=api_base if provider_str == "google" else None,
                )

            result["response_time"] = time.time() - start_time

            # 添加详细信息到成功的响应
            if result.get("success"):
                result["details"] = {
                    "provider": provider_str,
                    "model": llm_config.model_name,
                    "api_base": api_base,
                    "response_preview": result.get("message", "")[:100],
                }

            return result

        except requests.exceptions.Timeout:
            response_time = time.time() - start_time
            return {
                "success": False,
                "message": "连接超时，请检查API基础URL是否正确或网络是否可达",
                "response_time": response_time,
                "details": None,
            }
        except requests.exceptions.ConnectionError as e:
            response_time = time.time() - start_time
            return {
                "success": False,
                "message": f"连接失败，请检查API基础URL是否正确: {str(e)}",
                "response_time": response_time,
                "details": None,
            }
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"❌ 测试大模型配置失败: {e}")
            return {
                "success": False,
                "message": f"连接失败: {str(e)}",
                "response_time": response_time,
                "details": None,
            }

    # ==================== 数据源配置测试（委托给 DataSourceConfigService）====================

    async def test_data_source_config(
        self, ds_config: DataSourceConfig
    ) -> Dict[str, Any]:
        """测试数据源配置 - 真实调用API进行验证"""
        return await self._datasource_service.test_data_source_config(ds_config)

    # ==================== 数据库配置测试（委托给 DatabaseConfigService）====================

    async def test_database_config(self, db_config: DatabaseConfig) -> Dict[str, Any]:
        """测试数据库配置 - 真实连接测试"""
        return await self._database_service.test_database_config(db_config)

    # ==================== 数据库配置管理（委托给 DatabaseConfigService）====================

    async def add_database_config(self, db_config: DatabaseConfig) -> bool:
        """添加数据库配置"""
        return await self._database_service.add_database_config(db_config)

    async def update_database_config(self, db_config: DatabaseConfig) -> bool:
        """更新数据库配置"""
        return await self._database_service.update_database_config(db_config)

    async def delete_database_config(self, db_name: str) -> bool:
        """删除数据库配置"""
        return await self._database_service.delete_database_config(db_name)

    async def get_database_config(self, db_name: str) -> Optional[DatabaseConfig]:
        """获取指定的数据库配置"""
        return await self._database_service.get_database_config(db_name)

    async def get_database_configs(self) -> List[DatabaseConfig]:
        """获取所有数据库配置"""
        return await self._database_service.get_database_configs()

    # ==================== 模型目录管理（委托给 ModelCatalogService）====================

    async def get_model_catalog(self) -> List[ModelCatalog]:
        """获取所有模型目录"""
        return await self._model_catalog_service.get_model_catalog()

    async def get_provider_models(self, provider: str) -> Optional[ModelCatalog]:
        """获取指定厂家的模型目录"""
        return await self._model_catalog_service.get_provider_models(provider)

    async def save_model_catalog(self, catalog: ModelCatalog) -> bool:
        """保存或更新模型目录"""
        return await self._model_catalog_service.save_model_catalog(catalog)

    async def delete_model_catalog(self, provider: str) -> bool:
        """删除模型目录"""
        return await self._model_catalog_service.delete_model_catalog(provider)

    async def init_default_model_catalog(self) -> bool:
        """初始化默认模型目录"""
        return await self._model_catalog_service.init_default_model_catalog()

    def _get_default_model_catalog(self) -> List[Dict[str, Any]]:
        """获取默认模型目录数据"""
        return self._model_catalog_service._get_default_model_catalog()

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用的模型列表（从数据库读取，如果为空则返回默认数据）"""
        return await self._model_catalog_service.get_available_models()

    async def set_default_llm(self, model_name: str) -> bool:
        """设置默认大模型"""
        try:
            config = await self.get_system_config()
            if not config:
                return False

            # 检查模型是否存在
            model_exists = any(
                llm.model_name == model_name for llm in config.llm_configs
            )

            if not model_exists:
                return False

            config.default_llm = model_name
            return await self.save_system_config(config)
        except Exception as e:
            print(f"设置默认LLM失败: {e}")
            return False

    async def set_default_data_source(self, source_name: str) -> bool:
        """设置默认数据源"""
        try:
            config = await self.get_system_config()
            if not config:
                return False

            # 检查数据源是否存在
            source_exists = any(
                ds.name == source_name for ds in config.data_source_configs
            )

            if not source_exists:
                return False

            config.default_data_source = source_name
            return await self.save_system_config(config)
        except Exception as e:
            print(f"设置默认数据源失败: {e}")
            return False

    # ==================== 大模型厂家管理（委托给 LLMConfigService）====================

    async def get_llm_providers(self) -> List[LLMProvider]:
        """获取所有大模型厂家（合并环境变量配置）"""
        return await self._llm_service.get_llm_providers()

    async def add_llm_provider(self, provider: LLMProvider) -> str:
        """添加大模型厂家"""
        return await self._llm_service.add_llm_provider(provider)

    async def update_llm_provider(
        self, provider_id: str, update_data: Dict[str, Any]
    ) -> bool:
        """更新大模型厂家"""
        return await self._llm_service.update_llm_provider(provider_id, update_data)

    async def delete_llm_provider(self, provider_id: str) -> bool:
        """删除大模型厂家"""
        return await self._llm_service.delete_llm_provider(provider_id)

    async def toggle_llm_provider(self, provider_id: str, is_active: bool) -> bool:
        """切换大模型厂家状态"""
        return await self._llm_service.toggle_llm_provider(provider_id, is_active)

    async def init_aggregator_providers(self) -> Dict[str, Any]:
        """初始化聚合渠道厂家配置"""
        return await self._llm_service.init_aggregator_providers()

    async def migrate_env_to_providers(self) -> Dict[str, Any]:
        """将环境变量配置迁移到厂家管理"""
        return await self._llm_service.migrate_env_to_providers()

    async def test_provider_api(self, provider_id: str) -> dict:
        """测试厂家API密钥"""
        return await self._llm_service.test_provider_api(provider_id)

    async def fetch_provider_models(self, provider_id: str) -> dict:
        """从厂家 API 获取模型列表"""
        return await self._model_catalog_service.fetch_provider_models(provider_id)

    def _filter_popular_models(self, models: list) -> list:
        """过滤模型列表，只保留主流大厂的常用模型"""
        return self._model_catalog_service._filter_popular_models(models)

    def _format_models_with_pricing(self, models: list) -> list:
        """格式化模型列表，包含价格信息"""
        return self._model_catalog_service._format_models_with_pricing(models)

    # ==================== 工具方法 ====================

    def _is_valid_api_key(self, api_key: Optional[str]) -> bool:
        """判断 API Key 是否有效"""
        return self._llm_service._is_valid_api_key(api_key)

    def _get_env_api_key(self, provider_name: str) -> Optional[str]:
        """从环境变量获取API密钥"""
        return self._llm_service._get_env_api_key(provider_name)

    def _truncate_api_key(
        self, api_key: str, prefix_len: int = 6, suffix_len: int = 6
    ) -> str:
        """截断 API Key 用于显示"""
        return self._llm_service._truncate_api_key(api_key, prefix_len, suffix_len)


# 创建全局实例
config_service = ConfigService()
