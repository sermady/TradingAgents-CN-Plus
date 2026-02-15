# -*- coding: utf-8 -*-
"""
配置管理服务模块

提供统一的配置管理功能，包括：
- 市场分类管理
- LLM 提供商配置
- 数据源配置
- 数据库配置
- 模型目录管理
"""

from .base_config_service import BaseConfigService
from .market_config_service import MarketConfigService
from .llm_config_service import LLMConfigService
from .datasource_config_service import DataSourceConfigService
from .database_config_service import DatabaseConfigService
from .model_catalog_service import ModelCatalogService
from .config_service import ConfigService

__all__ = [
    "BaseConfigService",
    "MarketConfigService",
    "LLMConfigService",
    "DataSourceConfigService",
    "DatabaseConfigService",
    "ModelCatalogService",
    "ConfigService",
]

# 全局实例
config_service = ConfigService()
