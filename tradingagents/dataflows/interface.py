# -*- coding: utf-8 -*-
"""
数据流接口主模块

此模块已从原来的单一文件拆分为多个功能子模块，位于 interfaces/ 目录下。
本文件保留统一的对外接口，从子模块导入所有功能函数。

拆分后的模块结构：
- interfaces/base_interface.py: 基础接口定义、常量、工具函数
- interfaces/config_reader.py: 数据源配置读取
- interfaces/finnhub_interface.py: Finnhub API 接口
- interfaces/simfin_interface.py: SimFin API 接口
- interfaces/news_interface.py: 新闻获取接口
- interfaces/technical_interface.py: 技术指标接口
- interfaces/yfinance_interface.py: YFinance 数据接口
- interfaces/openai_interface.py: OpenAI 集成接口
- interfaces/fundamentals_interface.py: 基本面数据接口
- interfaces/china_stock_interface.py: A股数据接口
- interfaces/hk_stock_interface.py: 港股数据接口
"""

# 从子模块导入所有对外接口
from .interfaces import (
    # 配置读取
    _get_enabled_hk_data_sources,
    _get_enabled_us_data_sources,
    # Finnhub
    get_finnhub_news,
    get_finnhub_company_insider_sentiment,
    get_finnhub_company_insider_transactions,
    # SimFin
    get_simfin_balance_sheet,
    get_simfin_cashflow,
    get_simfin_income_statements,
    # 新闻
    get_google_news,
    get_reddit_global_news,
    get_reddit_company_news,
    # 技术指标
    get_stock_stats_indicators_window,
    get_stockstats_indicator,
    # YFinance
    get_YFin_data_window,
    get_YFin_data_online,
    get_YFin_data,
    # OpenAI
    get_stock_news_openai,
    get_global_news_openai,
    # 基本面数据
    get_fundamentals_finnhub,
    get_fundamentals_openai,
    # A股数据
    get_china_stock_data_tushare,
    get_china_stock_info_tushare,
    get_china_stock_fundamentals_tushare,
    get_china_stock_data_unified,
    get_china_stock_info_unified,
    switch_china_data_source,
    get_current_china_data_source,
    # 港股数据
    get_hk_stock_data_unified,
    get_hk_stock_info_unified,
)

# 从 news 模块导入中文社交情绪分析
from .news.chinese_finance import get_chinese_social_sentiment

# 额外导入：用于根据市场类型自动选择数据源的函数
from typing import Annotated
from .interfaces.base_interface import logger


def get_stock_data_by_market(
    symbol: str, start_date: str = None, end_date: str = None
) -> str:
    """
    根据股票市场类型自动选择数据源获取数据

    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        str: 格式化的股票数据
    """
    try:
        from tradingagents.utils.stock_utils import StockUtils

        market_info = StockUtils.get_market_info(symbol)

        if market_info["is_china"]:
            # 中国A股
            # 🔥 从 Toolkit._config 获取分析日期
            analysis_date = None
            try:
                from tradingagents.agents.utils.agent_utils import Toolkit

                analysis_date = Toolkit._config.get("analysis_date")
            except Exception as e:
                logger.debug(f"⚠️ 无法从 Toolkit._config 获取 analysis_date: {e}")
            return get_china_stock_data_unified(
                symbol, start_date, end_date, analysis_date=analysis_date
            )
        elif market_info["is_hk"]:
            # 港股
            return get_hk_stock_data_unified(symbol, start_date, end_date)
        else:
            # 美股或其他
            # 导入美股数据提供器（支持新旧路径）
            try:
                from .providers.us import OptimizedUSDataProvider

                provider = OptimizedUSDataProvider()
                return provider.get_stock_data(symbol, start_date, end_date)
            except ImportError:
                from tradingagents.dataflows.providers.us.optimized import (
                    get_us_stock_data_cached,
                )

                return get_us_stock_data_cached(symbol, start_date, end_date)

    except Exception as e:
        logger.error(f"❌ 获取股票数据失败: {e}")
        return f"❌ 获取股票{symbol}数据失败: {e}"


# 保持向后兼容：导出所有函数
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
    # 市场自动选择
    "get_stock_data_by_market",
]
