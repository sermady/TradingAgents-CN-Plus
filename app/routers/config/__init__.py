# -*- coding: utf-8 -*-
"""
配置管理API路由

该文件是配置路由的入口，通过 include_router 组合所有子路由模块。

子路由模块位于 app/routers/config/ 目录下：
- base.py: 基础脱敏函数
- system_config.py: 系统配置端点（/reload, /system, /settings, /export, /import, /migrate-legacy）
- llm_provider.py: LLM提供商端点（/llm/providers/*）
- llm_config.py: LLM配置端点（/llm, /models）
- datasource_config.py: 数据源配置端点（/datasource/*）
- database_config.py: 数据库配置端点（/database/*, /test）
- market_category.py: 市场分类端点（/market-categories/*）
- datasource_grouping.py: 数据源分组端点（/datasource-groupings/*, /market-categories/{id}/datasource-order）
- model_catalog.py: 模型目录端点（/model-catalog/*）
"""

from fastapi import APIRouter

# 导入所有子路由
from .system_config import router as system_config_router
from .llm_provider import router as llm_provider_router
from .llm_config import router as llm_config_router
from .datasource_config import router as datasource_config_router
from .database_config import router as database_config_router
from .market_category import router as market_category_router
from .datasource_grouping import router as datasource_grouping_router
from .model_catalog import router as model_catalog_router

# 创建主路由
router = APIRouter(prefix="/config", tags=["配置管理"])

# 包含所有子路由
# 注意：子路由中的路径是相对于 /config 的
router.include_router(system_config_router)
router.include_router(llm_provider_router)
router.include_router(llm_config_router)
router.include_router(datasource_config_router)
router.include_router(database_config_router)
router.include_router(market_category_router)
router.include_router(datasource_grouping_router)
router.include_router(model_catalog_router)

# 导出脱敏函数供其他模块使用
from .base import (
    sanitize_llm_configs,
    sanitize_datasource_configs,
    sanitize_database_configs,
    sanitize_kv,
)

__all__ = [
    "router",
    "sanitize_llm_configs",
    "sanitize_datasource_configs",
    "sanitize_database_configs",
    "sanitize_kv",
]
