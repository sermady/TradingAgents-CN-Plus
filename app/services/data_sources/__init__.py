# -*- coding: utf-8 -*-
"""
Data sources subpackage.
Expose adapters and manager for backward-compatible imports.
"""
from .base import DataSourceAdapter
from .tushare_adapter import TushareAdapter
from .akshare_adapter import AKShareAdapter
from .baostock_adapter import BaoStockAdapter
from .manager import DataSourceManager

# 本地备份数据源（当网络数据源都失败时使用）
from .backup import LocalStockListBackup, DEFAULT_STOCKS

__all__ = [
    "DataSourceAdapter",
    "TushareAdapter",
    "AKShareAdapter",
    "BaoStockAdapter",
    "DataSourceManager",
    "LocalStockListBackup",
    "DEFAULT_STOCKS",
]

