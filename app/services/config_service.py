# -*- coding: utf-8 -*-
"""
配置管理服务 - 向后兼容入口

此文件已重构，所有功能已迁移到 app/services/config/ 目录下的模块：
- base_config_service.py: 配置服务基类
- market_config_service.py: 市场分类管理
- llm_config_service.py: LLM 提供商配置
- datasource_config_service.py: 数据源配置
- database_config_service.py: 数据库配置
- model_catalog_service.py: 模型目录管理
- config_service.py: 门面类（组合各个子服务）

为了保持向后兼容，请从 app.services.config 导入：
    from app.services.config import ConfigService, config_service
"""

# 从新的模块位置重新导出所有内容
from app.services.config import (
    BaseConfigService,
    MarketConfigService,
    LLMConfigService,
    DataSourceConfigService,
    DatabaseConfigService,
    ModelCatalogService,
    ConfigService,
    config_service,
)

__all__ = [
    "BaseConfigService",
    "MarketConfigService",
    "LLMConfigService",
    "DataSourceConfigService",
    "DatabaseConfigService",
    "ModelCatalogService",
    "ConfigService",
    "config_service",
]
