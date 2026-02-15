# -*- coding: utf-8 -*-
"""Toolkit 基类 - 提供配置管理和工具门面"""
from typing import Annotated
from langchain_core.tools import tool

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.utils.logging_manager import get_logger
from tradingagents.utils.tool_logging import log_tool_call

# 导入各功能模块的静态方法
from .news_tools import (
    get_reddit_news,
    get_finnhub_news,
    get_google_news,
    get_realtime_stock_news,
    get_reddit_stock_info,
    get_chinese_social_sentiment,
    get_stock_news_openai,
    get_global_news_openai,
)
from .stock_data_tools import (
    get_china_stock_data,
    get_hk_stock_data_unified,
    get_YFin_data,
    get_YFin_data_online,
    get_china_market_overview,
)
from .technical_tools import (
    get_stockstats_indicators_report,
    get_stockstats_indicators_report_online,
)
from .fundamentals_tools import (
    get_finnhub_company_insider_sentiment,
    get_finnhub_company_insider_transactions,
    get_simfin_balance_sheet,
    get_simfin_cashflow,
    get_simfin_income_stmt,
    get_fundamentals_openai,
    get_china_fundamentals,
)
from .unified_tools import (
    get_stock_comprehensive_financials,
    get_stock_fundamentals_unified,
    get_stock_market_data_unified,
    get_stock_news_unified,
    get_stock_sentiment_unified,
)

logger = get_logger("agents")


class Toolkit:
    """工具包门面类 - 提供统一的数据获取工具接口

    该类作为门面(Facade)模式实现，将所有工具方法委托给各个功能模块。
    保持向后兼容性，原有代码可以继续使用 Toolkit.xxx() 的方式调用。
    """

    _config = DEFAULT_CONFIG.copy()

    @classmethod
    def update_config(cls, config):
        """Update the class-level configuration."""
        cls._config.update(config)

    @property
    def config(self):
        """Access the configuration."""
        return self._config

    def __init__(self, config=None):
        if config:
            self.update_config(config)

    # ==================== 新闻工具 ====================
    @staticmethod
    def get_reddit_news(
        curr_date: Annotated[str, "Date you want to get news for in yyyy-mm-dd format"],
    ) -> str:
        """获取 Reddit 全球新闻"""
        return get_reddit_news(curr_date)

    @staticmethod
    def get_finnhub_news(
        ticker: Annotated[str, "Search query of a company, e.g. 'AAPL, TSM, etc."],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ):
        """获取 Finnhub 股票新闻"""
        return get_finnhub_news(ticker, start_date, end_date)

    @staticmethod
    def get_reddit_stock_info(
        ticker: Annotated[str, "Ticker of a company. e.g. AAPL, TSM"],
        curr_date: Annotated[str, "Current date you want to get news for"],
    ) -> str:
        """获取 Reddit 股票信息"""
        return get_reddit_stock_info(ticker, curr_date)

    @staticmethod
    def get_chinese_social_sentiment(
        ticker: Annotated[str, "Ticker of a company. e.g. AAPL, TSM"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ) -> str:
        """获取中国社交媒体情绪"""
        return get_chinese_social_sentiment(ticker, curr_date)

    @staticmethod
    def get_google_news(
        query: Annotated[str, "Query to search with"],
        curr_date: Annotated[str, "Curr date in yyyy-mm-dd format"],
    ):
        """获取 Google 新闻"""
        return get_google_news(query, curr_date)

    @staticmethod
    def get_realtime_stock_news(
        ticker: Annotated[str, "Ticker of a company. e.g. AAPL, TSM"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ) -> str:
        """获取实时股票新闻"""
        return get_realtime_stock_news(ticker, curr_date)

    @staticmethod
    def get_stock_news_openai(
        ticker: Annotated[str, "the company's ticker"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """获取 OpenAI 股票新闻"""
        return get_stock_news_openai(ticker, curr_date)

    @staticmethod
    def get_global_news_openai(
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """获取 OpenAI 全球宏观经济新闻"""
        return get_global_news_openai(curr_date)

    # ==================== 股票数据工具 ====================
    @staticmethod
    def get_china_stock_data(
        stock_code: Annotated[str, "中国股票代码，如 000001(平安银行), 600519(贵州茅台)"],
        start_date: Annotated[str, "开始日期，格式 yyyy-mm-dd"],
        end_date: Annotated[str, "结束日期，格式 yyyy-mm-dd"],
    ) -> str:
        """获取中国A股实时和历史数据"""
        return get_china_stock_data(stock_code, start_date, end_date)

    @staticmethod
    def get_hk_stock_data_unified(
        symbol: Annotated[str, "港股代码，如：0700.HK、9988.HK等"],
        start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"],
        end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"],
    ) -> str:
        """获取港股数据的统一接口"""
        return get_hk_stock_data_unified(symbol, start_date, end_date)

    @staticmethod
    def get_YFin_data(
        symbol: Annotated[str, "ticker symbol of the company"],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ) -> str:
        """获取 Yahoo Finance 历史数据"""
        return get_YFin_data(symbol, start_date, end_date)

    @staticmethod
    def get_YFin_data_online(
        symbol: Annotated[str, "ticker symbol of the company"],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ) -> str:
        """获取 Yahoo Finance 在线数据"""
        return get_YFin_data_online(symbol, start_date, end_date)

    @staticmethod
    def get_china_market_overview(
        curr_date: Annotated[str, "当前日期，格式 yyyy-mm-dd"],
    ) -> str:
        """获取中国股市概览"""
        return get_china_market_overview(curr_date)

    # ==================== 技术指标工具 ====================
    @staticmethod
    def get_stockstats_indicators_report(
        symbol: Annotated[str, "ticker symbol of the company"],
        indicator: Annotated[str, "technical indicator to get the analysis and report of"],
        curr_date: Annotated[str, "The current trading date you are trading on, YYYY-mm-dd"],
        look_back_days: Annotated[int, "how many days to look back"] = 30,
    ) -> str:
        """获取技术指标报告离线"""
        return get_stockstats_indicators_report(symbol, indicator, curr_date, look_back_days)

    @staticmethod
    def get_stockstats_indicators_report_online(
        symbol: Annotated[str, "ticker symbol of the company"],
        indicator: Annotated[str, "technical indicator to get the analysis and report of"],
        curr_date: Annotated[str, "The current trading date you are trading on, YYYY-mm-dd"],
        look_back_days: Annotated[int, "how many days to look back"] = 30,
    ) -> str:
        """获取技术指标报告在线"""
        return get_stockstats_indicators_report_online(symbol, indicator, curr_date, look_back_days)

    # ==================== 基本面数据工具 ====================
    @staticmethod
    def get_finnhub_company_insider_sentiment(
        ticker: Annotated[str, "ticker symbol for the company"],
        curr_date: Annotated[str, "current date of you are trading at, yyyy-mm-dd"],
    ):
        """获取内部人士情绪"""
        return get_finnhub_company_insider_sentiment(ticker, curr_date)

    @staticmethod
    def get_finnhub_company_insider_transactions(
        ticker: Annotated[str, "ticker symbol"],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """获取内部人士交易"""
        return get_finnhub_company_insider_transactions(ticker, curr_date)

    @staticmethod
    def get_simfin_balance_sheet(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[str, "reporting frequency of the company's financial history: annual/quarterly"],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """获取资产负债表"""
        return get_simfin_balance_sheet(ticker, freq, curr_date)

    @staticmethod
    def get_simfin_cashflow(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[str, "reporting frequency of the company's financial history: annual/quarterly"],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """获取现金流量表"""
        return get_simfin_cashflow(ticker, freq, curr_date)

    @staticmethod
    def get_simfin_income_stmt(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[str, "reporting frequency of the company's financial history: annual/quarterly"],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """获取损益表"""
        return get_simfin_income_stmt(ticker, freq, curr_date)

    @staticmethod
    def get_fundamentals_openai(
        ticker: Annotated[str, "the company's ticker"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """获取 OpenAI 基本面数据"""
        return get_fundamentals_openai(ticker, curr_date)

    @staticmethod
    def get_china_fundamentals(
        ticker: Annotated[str, "中国A股股票代码，如600036"],
        curr_date: Annotated[str, "当前日期，格式为yyyy-mm-dd"],
    ):
        """获取中国A股基本面数据"""
        return get_china_fundamentals(ticker, curr_date)

    # ==================== 统一接口工具 ====================
    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_comprehensive_financials", log_args=True)
    def get_stock_comprehensive_financials(
        ticker: Annotated[str, "股票代码（支持A股6位代码，如：000001、600000）"],
        curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"] = None,
    ) -> str:
        """获取股票完整标准化财务数据"""
        return get_stock_comprehensive_financials(ticker, curr_date, Toolkit._config)

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_fundamentals_unified", log_args=True)
    def get_stock_fundamentals_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"] = None,
        end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"] = None,
        curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"] = None,
    ) -> str:
        """统一的股票基本面分析工具"""
        return get_stock_fundamentals_unified(
            ticker, start_date, end_date, curr_date, Toolkit._config
        )

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_market_data_unified", log_args=True)
    def get_stock_market_data_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"],
        end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"],
    ) -> str:
        """统一的股票市场数据工具"""
        return get_stock_market_data_unified(ticker, start_date, end_date)

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_news_unified", log_args=True)
    def get_stock_news_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"],
    ) -> str:
        """统一的股票新闻工具"""
        return get_stock_news_unified(ticker, curr_date)

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_sentiment_unified", log_args=True)
    def get_stock_sentiment_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"],
    ) -> str:
        """统一的股票情绪分析工具"""
        return get_stock_sentiment_unified(ticker, curr_date)
