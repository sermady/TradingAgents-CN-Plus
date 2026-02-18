# -*- coding: utf-8 -*-
"""
配置管理服务 - 门面类

提供统一的配置管理接口，组合各个子服务：
- MarketConfigService: 市场分类管理
- LLMConfigService: LLM 提供商配置
- DataSourceConfigService: 数据源配置
- DatabaseConfigService: 数据库配置
- ModelCatalogService: 模型目录管理

以及混入类提供的基础功能：
- SystemConfigMixin: 系统配置管理
- ImportExportMixin: 配置导入导出
- LLMTestMixin: LLM配置测试
"""

import logging
from typing import List, Optional, Dict, Any

from app.core.database import get_mongo_db
from app.models.config import (
    SystemConfig,
    DataSourceConfig,
    DatabaseConfig,
    MarketCategory,
    DataSourceGrouping,
    ModelCatalog,
    LLMProvider,
)

from .market_config_service import MarketConfigService
from .llm_config_service import LLMConfigService
from .datasource import DataSourceConfigService
from .database_config_service import DatabaseConfigService
from .catalog import ModelCatalogService
from .mixins import SystemConfigMixin, ImportExportMixin, LLMTestMixin

logger = logging.getLogger(__name__)


class ConfigService(
    SystemConfigMixin,
    ImportExportMixin,
    LLMTestMixin,
):
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
        from .base_config_service import BaseConfigService

        base_config = BaseConfigService(self.db_manager)
        return await base_config.set_default_config(
            config_field='default_llm',
            value=model_name,
            validation_func=lambda config: any(
                llm.model_name == model_name for llm in config.llm_configs
            )
        )

    async def set_default_data_source(self, source_name: str) -> bool:
        """设置默认数据源"""
        from .base_config_service import BaseConfigService

        base_config = BaseConfigService(self.db_manager)
        return await base_config.set_default_config(
            config_field='default_data_source',
            value=source_name,
            validation_func=lambda config: any(
                ds.name == source_name for ds in config.data_source_configs
            )
        )

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

    # ==================== 工具方法（委托给 LLMConfigService）====================

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
