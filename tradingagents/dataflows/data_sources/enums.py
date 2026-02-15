# -*- coding: utf-8 -*-
"""
数据源枚举定义
"""

from enum import Enum
from tradingagents.constants import DataSourceCode


class ChinaDataSource(Enum):
    """
    中国股票数据源枚举

    注意：这个枚举与 tradingagents.constants.DataSourceCode 保持同步
    值使用统一的数据源编码
    """

    MONGODB = DataSourceCode.MONGODB  # MongoDB数据库缓存（最高优先级）
    TUSHARE = DataSourceCode.TUSHARE
    AKSHARE = DataSourceCode.AKSHARE
    BAOSTOCK = DataSourceCode.BAOSTOCK


class USDataSource(Enum):
    """
    美股数据源枚举

    注意：这个枚举与 tradingagents.constants.DataSourceCode 保持同步
    值使用统一的数据源编码
    """

    MONGODB = DataSourceCode.MONGODB  # MongoDB数据库缓存（最高优先级）
    YFINANCE = DataSourceCode.YFINANCE  # Yahoo Finance（免费，股票价格和技术指标）
    ALPHA_VANTAGE = DataSourceCode.ALPHA_VANTAGE  # Alpha Vantage（基本面和新闻）
    FINNHUB = DataSourceCode.FINNHUB  # Finnhub（备用数据源）
