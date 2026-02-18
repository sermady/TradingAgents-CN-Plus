# -*- coding: utf-8 -*-
"""配置导入导出混入类

提供配置的导入、导出、验证等功能
"""

import logging
from typing import Dict, Any

from app.models.config import SystemConfig, LLMConfig, DataSourceConfig, DatabaseConfig
from app.utils.timezone import now_tz

logger = logging.getLogger(__name__)


class ImportExportMixin:
    """配置导入导出混入类"""

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
