# -*- coding: utf-8 -*-
"""
数据源管理模块

提供统一的数据源管理功能，支持中国股票和美股数据。

注意：为避免循环导入，DataSourceManager 需要直接从上层模块导入：
    from tradingagents.dataflows.data_source_manager import DataSourceManager
"""

# 导出主要类和函数
from .enums import ChinaDataSource, USDataSource
from .models import ValidatedDataResult

# 工厂函数（延迟导入避免循环导入）
from .factory import (
    get_data_source_manager,
    get_china_stock_data_unified,
    get_china_stock_info_unified,
    get_stock_data_service,
)

__all__ = [
    "ChinaDataSource",
    "USDataSource",
    "ValidatedDataResult",
    "get_data_source_manager",
    "get_china_stock_data_unified",
    "get_china_stock_info_unified",
    "get_stock_data_service",
]
