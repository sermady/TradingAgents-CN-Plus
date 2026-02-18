# -*- coding: utf-8 -*-
"""
本地股票列表备用数据源模块

当所有网络数据源都失败时使用，包含100只主要蓝筹股的静态数据。

示例:
    >>> from app.services.data_sources.backup import LocalStockListBackup
    >>> df = LocalStockListBackup.get_stock_list()
    >>> stock = LocalStockListBackup.get_stock_by_code("000001")
    >>> results = LocalStockListBackup.search_stocks("银行")
"""

from .core import LocalStockListBackup
from .search import (
    get_all_areas,
    get_all_industries,
    get_stocks_by_market,
    search_by_area,
    search_by_industry,
    search_stocks,
)
from .stock_data import (
    DEFAULT_STOCKS,
    get_stock_by_code,
    get_stock_name,
    is_stock_code_valid,
)

__all__ = [
    # 主类
    "LocalStockListBackup",
    # 数据
    "DEFAULT_STOCKS",
    # 核心函数
    "get_stock_by_code",
    "get_stock_name",
    "is_stock_code_valid",
    # 搜索函数
    "search_stocks",
    "search_by_industry",
    "search_by_area",
    "get_stocks_by_market",
    "get_all_industries",
    "get_all_areas",
]
