# -*- coding: utf-8 -*-
"""
数据流接口模块

将原 interface.py 拆分为多个功能模块，便于维护。
"""

# 配置读取
from .config_reader import _get_enabled_hk_data_sources, _get_enabled_us_data_sources

# Finnhub API
from .finnhub_interface import (
    get_finnhub_news,
    get_finnhub_company_insider_sentiment,
    get_finnhub_company_insider_transactions,
)

# SimFin API
from .simfin_interface import (
    get_simfin_balance_sheet,
    get_simfin_cashflow,
    get_simfin_income_statements,
)

# 新闻获取
from .news_interface import (
    get_google_news,
    get_reddit_global_news,
    get_reddit_company_news,
)

# 技术指标
from .technical_interface import (
    get_stock_stats_indicators_window,
    get_stockstats_indicator,
)

# YFinance 数据
from .yfinance_interface import (
    get_YFin_data_window,
    get_YFin_data_online,
    get_YFin_data,
)

# OpenAI 集成
from .openai_interface import (
    get_stock_news_openai,
    get_global_news_openai,
)

# 基本面数据
from .fundamentals_interface import (
    get_fundamentals_finnhub,
    get_fundamentals_openai,
)

# A股数据
from .china_stock_interface import (
    get_china_stock_data_tushare,
    get_china_stock_info_tushare,
    get_china_stock_fundamentals_tushare,
    get_china_stock_data_unified,
    get_china_stock_info_unified,
    switch_china_data_source,
    get_current_china_data_source,
)

# 港股数据
from .hk_stock_interface import (
    get_hk_stock_data_unified,
    get_hk_stock_info_unified,
)

__all__ = [
    # 配置读取
    "_get_enabled_hk_data_sources",
    "_get_enabled_us_data_sources",
    # Finnhub
    "get_finnhub_news",
    "get_finnhub_company_insider_sentiment",
    "get_finnhub_company_insider_transactions",
    # SimFin
    "get_simfin_balance_sheet",
    "get_simfin_cashflow",
    "get_simfin_income_statements",
    # 新闻
    "get_google_news",
    "get_reddit_global_news",
    "get_reddit_company_news",
    # 技术指标
    "get_stock_stats_indicators_window",
    "get_stockstats_indicator",
    # YFinance
    "get_YFin_data_window",
    "get_YFin_data_online",
    "get_YFin_data",
    # OpenAI
    "get_stock_news_openai",
    "get_global_news_openai",
    # 基本面数据
    "get_fundamentals_finnhub",
    "get_fundamentals_openai",
    # A股数据
    "get_china_stock_data_tushare",
    "get_china_stock_info_tushare",
    "get_china_stock_fundamentals_tushare",
    "get_china_stock_data_unified",
    "get_china_stock_info_unified",
    "switch_china_data_source",
    "get_current_china_data_source",
    # 港股数据
    "get_hk_stock_data_unified",
    "get_hk_stock_info_unified",
]
