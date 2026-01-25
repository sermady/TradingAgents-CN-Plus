# -*- coding: utf-8 -*-
"""
DataFlows Schemas Package

统一数据Schema定义模块：
- stock_basic_schema.py: 股票基础信息Schema（基本面分析）
- stock_historical_schema.py: 股票历史数据Schema（技术分析）
"""

from tradingagents.dataflows.schemas.stock_basic_schema import (
    STOCK_BASIC_SCHEMA,
    STOCK_BASIC_REQUIRED_FIELDS,
    STOCK_BASIC_OPTIONAL_FIELDS,
    validate_stock_basic_data,
    StockBasicData,
)

from tradingagents.dataflows.schemas.stock_historical_schema import (
    StockDailyData,
    StockHistoricalData,
)

__all__ = [
    # 基础信息 Schema（基本面分析）
    "STOCK_BASIC_SCHEMA",
    "STOCK_BASIC_REQUIRED_FIELDS",
    "STOCK_BASIC_OPTIONAL_FIELDS",
    "validate_stock_basic_data",
    "StockBasicData",
    # 历史数据 Schema（技术分析）
    "StockDailyData",
    "StockHistoricalData",
]
