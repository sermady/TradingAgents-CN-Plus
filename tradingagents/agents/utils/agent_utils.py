# -*- coding: utf-8 -*-
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage
from typing import List
from typing import Annotated
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import RemoveMessage
from langchain_core.tools import tool
from datetime import date, timedelta, datetime
import functools
import pandas as pd
import os
from dateutil.relativedelta import relativedelta
from langchain_openai import ChatOpenAI
import tradingagents.dataflows.interface as interface
from tradingagents.default_config import DEFAULT_CONFIG
from langchain_core.messages import HumanMessage

# 导入统一日志系统和工具日志装饰器
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_tool_call, log_analysis_step

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("agents")


def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility

        注意：在并行执行模式下，多个分析师会同时调用此函数。
        为了避免重复删除导致的错误，我们使用一个标记机制确保只执行一次清理。
        """
        from langgraph.graph import END

        messages = state.get("messages", [])

        # 检查是否已经清理过（通过检查最后一个消息是否是占位符）
        if messages and len(messages) > 0:
            last_msg = messages[-1]
            if hasattr(last_msg, "content") and last_msg.content == "__MSG_CLEARED__":
                # 已经清理过了，直接返回空更新
                return {"messages": []}

        # 收集需要删除的消息ID
        removal_operations = []
        seen_ids = set()

        for m in messages:
            if hasattr(m, "id") and m.id and m.id not in seen_ids:
                removal_operations.append(RemoveMessage(id=m.id))
                seen_ids.add(m.id)

        # 添加标记消息表示已清理（而不是 HumanMessage）
        # 使用 AIMessage 作为标记，避免干扰后续流程
        marker_message = AIMessage(content="__MSG_CLEARED__", id="msg_cleared_marker")

        return {"messages": removal_operations + [marker_message]}

    return delete_messages


class Toolkit:
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

    @staticmethod
    def get_reddit_news(
        curr_date: Annotated[str, "Date you want to get news for in yyyy-mm-dd format"],
    ) -> str:
        """
        [内部API] 获取 Reddit 全球新闻（请使用 get_stock_news_unified）
        Retrieve global news from Reddit within a specified time frame.
        Args:
            curr_date (str): Date you want to get news for in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing the latest global news from Reddit in the specified time frame.
        """

        global_news_result = interface.get_reddit_global_news(curr_date, 7, 5)

        return global_news_result

    @staticmethod
    def get_finnhub_news(
        ticker: Annotated[
            str,
            "Search query of a company, e.g. 'AAPL, TSM, etc.",
        ],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ):
        """
        [内部API] 获取 Finnhub 股票新闻（请使用 get_stock_news_unified）
        Retrieve the latest news about a given stock from Finnhub within a date range
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing news about the company within the date range from start_date to end_date
        """

        end_date_str = end_date

        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        look_back_days = (end_date - start_date).days

        finnhub_news_result = interface.get_finnhub_news(
            ticker, end_date_str, look_back_days
        )

        return finnhub_news_result

    @staticmethod
    def get_reddit_stock_info(
        ticker: Annotated[
            str,
            "Ticker of a company. e.g. AAPL, TSM",
        ],
        curr_date: Annotated[str, "Current date you want to get news for"],
    ) -> str:
        """
        [内部API] 获取 Reddit 股票信息（请使用 get_stock_sentiment_unified）
        Retrieve the latest news about a given stock from Reddit, given the current date.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): current date in yyyy-mm-dd format to get news for
        Returns:
            str: A formatted dataframe containing the latest news about the company on the given date
        """

        stock_news_results = interface.get_reddit_company_news(ticker, curr_date, 7, 5)

        return stock_news_results

    @staticmethod
    def get_chinese_social_sentiment(
        ticker: Annotated[str, "Ticker of a company. e.g. AAPL, TSM"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ) -> str:
        """
        [内部API] 获取中国社交媒体情绪（请使用 get_stock_sentiment_unified）
        获取中国社交媒体和财经平台上关于特定股票的情绪分析和讨论热度。
        整合雪球、东方财富股吧、新浪财经等中国本土平台的数据。
        Args:
            ticker (str): 股票代码，如 AAPL, TSM
            curr_date (str): 当前日期，格式为 yyyy-mm-dd
        Returns:
            str: 包含中国投资者情绪分析、讨论热度、关键观点的格式化报告
        """
        try:
            # 这里可以集成多个中国平台的数据
            chinese_sentiment_results = interface.get_chinese_social_sentiment(
                ticker, curr_date
            )
            return chinese_sentiment_results
        except Exception as e:
            # 如果中国平台数据获取失败，回退到原有的Reddit数据
            return interface.get_reddit_company_news(ticker, curr_date, 7, 5)

    @staticmethod
    # @tool  # 已移除：请使用 get_stock_fundamentals_unified 或 get_stock_market_data_unified
    def get_china_stock_data(
        stock_code: Annotated[
            str, "中国股票代码，如 000001(平安银行), 600519(贵州茅台)"
        ],
        start_date: Annotated[str, "开始日期，格式 yyyy-mm-dd"],
        end_date: Annotated[str, "结束日期，格式 yyyy-mm-dd"],
    ) -> str:
        """
        获取中国A股实时和历史数据，通过Tushare等高质量数据源提供专业的股票数据。
        支持实时行情、历史K线、技术指标等全面数据，自动使用最佳数据源。
        Args:
            stock_code (str): 中国股票代码，如 000001(平安银行), 600519(贵州茅台)
            start_date (str): 开始日期，格式 yyyy-mm-dd
            end_date (str): 结束日期，格式 yyyy-mm-dd
        Returns:
            str: 包含实时行情、历史数据、技术指标的完整股票分析报告
        """
        try:
            logger.debug(
                f"📊 [DEBUG] ===== agent_utils.get_china_stock_data 开始调用 ====="
            )
            logger.debug(
                f"📊 [DEBUG] 参数: stock_code={stock_code}, start_date={start_date}, end_date={end_date}"
            )

            from tradingagents.dataflows.interface import get_china_stock_data_unified

            logger.debug(f"📊 [DEBUG] 成功导入统一数据源接口")

            logger.debug(f"📊 [DEBUG] 正在调用统一数据源接口...")
            result = get_china_stock_data_unified(stock_code, start_date, end_date)

            logger.debug(f"📊 [DEBUG] 统一数据源接口调用完成")
            logger.debug(f"📊 [DEBUG] 返回结果类型: {type(result)}")
            logger.debug(f"📊 [DEBUG] 返回结果长度: {len(result) if result else 0}")
            logger.debug(f"📊 [DEBUG] 返回结果前200字符: {str(result)[:200]}...")
            logger.debug(
                f"📊 [DEBUG] ===== agent_utils.get_china_stock_data 调用结束 ====="
            )

            return result
        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            logger.error(
                f"❌ [DEBUG] ===== agent_utils.get_china_stock_data 异常 ====="
            )
            logger.error(f"❌ [DEBUG] 错误类型: {type(e).__name__}")
            logger.error(f"❌ [DEBUG] 错误信息: {str(e)}")
            logger.error(f"❌ [DEBUG] 详细堆栈:")
            print(error_details)
            logger.error(f"❌ [DEBUG] ===== 异常处理结束 =====")
            return f"中国股票数据获取失败: {str(e)}。请检查网络连接或稍后重试。"

    @staticmethod
    def get_china_market_overview(
        curr_date: Annotated[str, "当前日期，格式 yyyy-mm-dd"],
    ) -> str:
        """
        [内部API] 获取中国股市概览（请使用 get_stock_market_data_unified）
        获取中国股市整体概览，包括主要指数的实时行情。
        涵盖上证指数、深证成指、创业板指、科创50等主要指数。
        Args:
            curr_date (str): 当前日期，格式 yyyy-mm-dd
        Returns:
            str: 包含主要指数实时行情的市场概览报告
        """
        try:
            # 使用Tushare获取主要指数数据
            from tradingagents.dataflows.providers.china.tushare import (
                get_tushare_adapter,
            )

            adapter = get_tushare_adapter()

            # 使用Tushare获取主要指数信息
            # 这里可以扩展为获取具体的指数数据
            return f"""# 中国股市概览 - {curr_date}

## 📊 主要指数
- 上证指数: 数据获取中...
- 深证成指: 数据获取中...
- 创业板指: 数据获取中...
- 科创50: 数据获取中...

## 💡 说明
市场概览功能正在从TDX迁移到Tushare，完整功能即将推出。
当前可以使用股票数据获取功能分析个股。

数据来源: Tushare专业数据源
更新时间: {curr_date}
"""

        except Exception as e:
            return f"中国市场概览获取失败: {str(e)}。正在从TDX迁移到Tushare数据源。"

    @staticmethod
    def get_YFin_data(
        symbol: Annotated[str, "ticker symbol of the company"],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ) -> str:
        """
        [内部API] 获取 Yahoo Finance 历史数据（请使用 get_stock_market_data_unified）
        Retrieve the stock price data for a given ticker symbol from Yahoo Finance.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing the stock price data for the specified ticker symbol in the specified date range.
        """

        result_data = interface.get_YFin_data(symbol, start_date, end_date)

        return result_data

    @staticmethod
    def get_YFin_data_online(
        symbol: Annotated[str, "ticker symbol of the company"],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ) -> str:
        """
        [内部API] 获取 Yahoo Finance 在线数据（请使用 get_stock_market_data_unified）
        Retrieve the stock price data for a given ticker symbol from Yahoo Finance.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing the stock price data for the specified ticker symbol in the specified date range.
        """

        result_data = interface.get_YFin_data_online(symbol, start_date, end_date)

        return result_data

    @staticmethod
    def get_stockstats_indicators_report(
        symbol: Annotated[str, "ticker symbol of the company"],
        indicator: Annotated[
            str, "technical indicator to get the analysis and report of"
        ],
        curr_date: Annotated[
            str, "The current trading date you are trading on, YYYY-mm-dd"
        ],
        look_back_days: Annotated[int, "how many days to look back"] = 30,
    ) -> str:
        """
        [内部API] 获取技术指标报告离线（请使用 get_stock_market_data_unified）
        Retrieve stock stats indicators for a given ticker symbol and indicator.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            indicator (str): Technical indicator to get the analysis and report of
            curr_date (str): The current trading date you are trading on, YYYY-mm-dd
            look_back_days (int): How many days to look back, default is 30
        Returns:
            str: A formatted dataframe containing the stock stats indicators for the specified ticker symbol and indicator.
        """

        result_stockstats = interface.get_stock_stats_indicators_window(
            symbol, indicator, curr_date, look_back_days, False
        )

        return result_stockstats

    @staticmethod
    def get_stockstats_indicators_report_online(
        symbol: Annotated[str, "ticker symbol of the company"],
        indicator: Annotated[
            str, "technical indicator to get the analysis and report of"
        ],
        curr_date: Annotated[
            str, "The current trading date you are trading on, YYYY-mm-dd"
        ],
        look_back_days: Annotated[int, "how many days to look back"] = 30,
    ) -> str:
        """
        [内部API] 获取技术指标报告在线（请使用 get_stock_market_data_unified）
        Retrieve stock stats indicators for a given ticker symbol and indicator.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            indicator (str): Technical indicator to get the analysis and report of
            curr_date (str): The current trading date you are trading on, YYYY-mm-dd
            look_back_days (int): How many days to look back, default is 30
        Returns:
            str: A formatted dataframe containing the stock stats indicators for the specified ticker symbol and indicator.
        """

        result_stockstats = interface.get_stock_stats_indicators_window(
            symbol, indicator, curr_date, look_back_days, True
        )

        return result_stockstats

    @staticmethod
    def get_finnhub_company_insider_sentiment(
        ticker: Annotated[str, "ticker symbol for the company"],
        curr_date: Annotated[
            str,
            "current date of you are trading at, yyyy-mm-dd",
        ],
    ):
        """
        [内部API] 获取内部人士情绪（请使用 get_stock_fundamentals_unified）
        Retrieve insider sentiment information about a company (retrieved from public SEC information) for the past 30 days
        Args:
            ticker (str): ticker symbol of the company
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
            str: a report of the sentiment in the past 30 days starting at curr_date
        """

        data_sentiment = interface.get_finnhub_company_insider_sentiment(
            ticker, curr_date, 30
        )

        return data_sentiment

    @staticmethod
    def get_finnhub_company_insider_transactions(
        ticker: Annotated[str, "ticker symbol"],
        curr_date: Annotated[
            str,
            "current date you are trading at, yyyy-mm-dd",
        ],
    ):
        """
        [内部API] 获取内部人士交易（请使用 get_stock_fundamentals_unified）
        Retrieve insider transaction information about a company (retrieved from public SEC information) for the past 30 days
        Args:
            ticker (str): ticker symbol of the company
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
            str: a report of the company's insider transactions/trading information in the past 30 days
        """

        data_trans = interface.get_finnhub_company_insider_transactions(
            ticker, curr_date, 30
        )

        return data_trans

    @staticmethod
    def get_simfin_balance_sheet(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency of the company's financial history: annual/quarterly",
        ],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """
        [内部API] 获取资产负债表（请使用 get_stock_fundamentals_unified）
        Retrieve the most recent balance sheet of a company
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency of the company's financial history: annual / quarterly
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
            str: a report of the company's most recent balance sheet
        """

        data_balance_sheet = interface.get_simfin_balance_sheet(ticker, freq, curr_date)

        return data_balance_sheet

    @staticmethod
    def get_simfin_cashflow(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency of the company's financial history: annual/quarterly",
        ],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """
        [内部API] 获取现金流量表（请使用 get_stock_fundamentals_unified）
        Retrieve the most recent cash flow statement of a company
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency of the company's financial history: annual / quarterly
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
                str: a report of the company's most recent cash flow statement
        """

        data_cashflow = interface.get_simfin_cashflow(ticker, freq, curr_date)

        return data_cashflow

    @staticmethod
    def get_simfin_income_stmt(
        ticker: Annotated[str, "ticker symbol"],
        freq: Annotated[
            str,
            "reporting frequency of the company's financial history: annual/quarterly",
        ],
        curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
    ):
        """
        [内部API] 获取损益表（请使用 get_stock_fundamentals_unified）
        Retrieve the most recent income statement of a company
        Args:
            ticker (str): ticker symbol of the company
            freq (str): reporting frequency of the company's financial history: annual / quarterly
            curr_date (str): current date you are trading at, yyyy-mm-dd
        Returns:
                str: a report of the company's most recent income statement
        """

        data_income_stmt = interface.get_simfin_income_statements(
            ticker, freq, curr_date
        )

        return data_income_stmt

    @staticmethod
    def get_google_news(
        query: Annotated[str, "Query to search with"],
        curr_date: Annotated[str, "Curr date in yyyy-mm-dd format"],
    ):
        """
        [内部API] 获取 Google 新闻（请使用 get_stock_news_unified）
        Retrieve the latest news from Google News based on a query and date range.
        Args:
            query (str): Query to search with
            curr_date (str): Current date in yyyy-mm-dd format
            look_back_days (int): How many days to look back
        Returns:
            str: A formatted string containing the latest news from Google News based on the query and date range.
        """

        google_news_results = interface.get_google_news(query, curr_date, 7)

        return google_news_results

    @staticmethod
    def get_realtime_stock_news(
        ticker: Annotated[str, "Ticker of a company. e.g. AAPL, TSM"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ) -> str:
        """
        [内部API] 获取实时股票新闻（请使用 get_stock_news_unified）
        获取股票的实时新闻分析，解决传统新闻源的滞后性问题。
        整合多个专业财经API，提供15-30分钟内的最新新闻。
        支持多种新闻源轮询机制，优先使用实时新闻聚合器，失败时自动尝试备用新闻源。
        对于A股和港股，会优先使用中文财经新闻源（如东方财富）。

        Args:
            ticker (str): 股票代码，如 AAPL, TSM, 600036.SH
            curr_date (str): 当前日期，格式为 yyyy-mm-dd
        Returns:
            str: 包含实时新闻分析、紧急程度评估、时效性说明的格式化报告
        """
        from tradingagents.dataflows.realtime_news_utils import get_realtime_stock_news

        return get_realtime_stock_news(ticker, curr_date, hours_back=6)

    @staticmethod
    def get_stock_news_openai(
        ticker: Annotated[str, "the company's ticker"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        [内部API] 获取 OpenAI 股票新闻（请使用 get_stock_news_unified）
        Retrieve the latest news about a given stock by using OpenAI's news API.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest news about the company on the given date.
        """

        openai_news_results = interface.get_stock_news_openai(ticker, curr_date)

        return openai_news_results

    @staticmethod
    def get_global_news_openai(
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        [内部API] 获取 OpenAI 全球宏观经济新闻（请使用 get_stock_news_unified）
        Retrieve the latest macroeconomics news on a given date using OpenAI's macroeconomics news API.
        Args:
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest macroeconomic news on the given date.
        """

        openai_news_results = interface.get_global_news_openai(curr_date)

        return openai_news_results

    @staticmethod
    # @tool  # 已移除：请使用 get_stock_fundamentals_unified
    def get_fundamentals_openai(
        ticker: Annotated[str, "the company's ticker"],
        curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest fundamental information about a given stock on a given date by using OpenAI's news API.
        Args:
            ticker (str): Ticker of a company. e.g. AAPL, TSM
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest fundamental information about the company on the given date.
        """
        logger.debug(
            f"📊 [DEBUG] get_fundamentals_openai 被调用: ticker={ticker}, date={curr_date}"
        )

        # 检查是否为中国股票
        import re

        if re.match(r"^\d{6}$", str(ticker)):
            logger.debug(f"📊 [DEBUG] 检测到中国A股代码: {ticker}")
            # 使用统一接口获取中国股票名称
            try:
                from tradingagents.dataflows.interface import (
                    get_china_stock_info_unified,
                )

                stock_info = get_china_stock_info_unified(ticker)

                # 解析股票名称
                if "股票名称:" in stock_info:
                    company_name = (
                        stock_info.split("股票名称:")[1].split("\n")[0].strip()
                    )
                else:
                    company_name = f"股票代码{ticker}"

                logger.debug(f"📊 [DEBUG] 中国股票名称映射: {ticker} -> {company_name}")
            except Exception as e:
                logger.error(f"⚠️ [DEBUG] 从统一接口获取股票名称失败: {e}")
                company_name = f"股票代码{ticker}"

            # 修改查询以包含正确的公司名称
            modified_query = f"{company_name}({ticker})"
            logger.debug(f"📊 [DEBUG] 修改后的查询: {modified_query}")
        else:
            logger.debug(f"📊 [DEBUG] 检测到非中国股票: {ticker}")
            modified_query = ticker

        try:
            openai_fundamentals_results = interface.get_fundamentals_openai(
                modified_query, curr_date
            )
            logger.debug(
                f"📊 [DEBUG] OpenAI基本面分析结果长度: {len(openai_fundamentals_results) if openai_fundamentals_results else 0}"
            )
            return openai_fundamentals_results
        except Exception as e:
            logger.error(f"❌ [DEBUG] OpenAI基本面分析失败: {str(e)}")
            return f"基本面分析失败: {str(e)}"

    @staticmethod
    # @tool  # 已移除：请使用 get_stock_fundamentals_unified
    def get_china_fundamentals(
        ticker: Annotated[str, "中国A股股票代码，如600036"],
        curr_date: Annotated[str, "当前日期，格式为yyyy-mm-dd"],
    ):
        """
        获取中国A股股票的基本面信息，使用中国股票数据源。
        Args:
            ticker (str): 中国A股股票代码，如600036, 000001
            curr_date (str): 当前日期，格式为yyyy-mm-dd
        Returns:
            str: 包含股票基本面信息的格式化字符串
        """
        logger.debug(
            f"📊 [DEBUG] get_china_fundamentals 被调用: ticker={ticker}, date={curr_date}"
        )

        # 检查是否为中国股票
        import re

        if not re.match(r"^\d{6}$", str(ticker)):
            return f"错误：{ticker} 不是有效的中国A股代码格式"

        try:
            # 使用统一数据源接口获取股票数据（默认Tushare，支持备用数据源）
            from tradingagents.dataflows.interface import get_china_stock_data_unified

            logger.debug(f"📊 [DEBUG] 正在获取 {ticker} 的股票数据...")

            # 获取最近30天的数据用于基本面分析
            from datetime import datetime, timedelta

            end_date = datetime.strptime(curr_date, "%Y-%m-%d")
            start_date = end_date - timedelta(days=30)

            stock_data = get_china_stock_data_unified(
                ticker, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
            )

            logger.debug(
                f"📊 [DEBUG] 股票数据获取完成，长度: {len(stock_data) if stock_data else 0}"
            )

            if not stock_data or "获取失败" in stock_data or "❌" in stock_data:
                return f"无法获取股票 {ticker} 的基本面数据：{stock_data}"

            # 调用真正的基本面分析
            from tradingagents.dataflows.optimized_china_data import (
                OptimizedChinaDataProvider,
            )

            # 创建分析器实例
            analyzer = OptimizedChinaDataProvider()

            # 生成真正的基本面分析报告
            fundamentals_report = analyzer._generate_fundamentals_report(
                ticker, stock_data
            )

            logger.debug(f"📊 [DEBUG] 中国基本面分析报告生成完成")
            logger.debug(
                f"📊 [DEBUG] get_china_fundamentals 结果长度: {len(fundamentals_report)}"
            )

            return fundamentals_report

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            logger.error(f"❌ [DEBUG] get_china_fundamentals 失败:")
            logger.error(f"❌ [DEBUG] 错误: {str(e)}")
            logger.error(f"❌ [DEBUG] 堆栈: {error_details}")
            return f"中国股票基本面分析失败: {str(e)}"

    @staticmethod
    # @tool  # 已移除：请使用 get_stock_fundamentals_unified 或 get_stock_market_data_unified
    def get_hk_stock_data_unified(
        symbol: Annotated[str, "港股代码，如：0700.HK、9988.HK等"],
        start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"],
        end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"],
    ) -> str:
        """
        获取港股数据的统一接口，优先使用AKShare数据源，备用Yahoo Finance

        Args:
            symbol: 港股代码 (如: 0700.HK)
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            str: 格式化的港股数据
        """
        logger.debug(
            f"🇭🇰 [DEBUG] get_hk_stock_data_unified 被调用: symbol={symbol}, start_date={start_date}, end_date={end_date}"
        )

        try:
            from tradingagents.dataflows.interface import get_hk_stock_data_unified

            result = get_hk_stock_data_unified(symbol, start_date, end_date)

            logger.debug(
                f"🇭🇰 [DEBUG] 港股数据获取完成，长度: {len(result) if result else 0}"
            )

            return result

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            logger.error(f"❌ [DEBUG] get_hk_stock_data_unified 失败:")
            logger.error(f"❌ [DEBUG] 错误: {str(e)}")
            logger.error(f"❌ [DEBUG] 堆栈: {error_details}")
            return f"港股数据获取失败: {str(e)}"

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_comprehensive_financials", log_args=True)
    def get_stock_comprehensive_financials(
        ticker: Annotated[str, "股票代码（支持A股6位代码，如：000001、600000）"],
        curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"] = None,
    ) -> str:
        """
        获取股票完整标准化财务数据（供分析师使用）

        使用 Tushare 5120积分权限，一次性获取所有财务指标：
        - 估值指标：PE、PE_TTM、PB、PS、股息率
        - 盈利能力：EPS、ROE、ROA、毛利率、净利率
        - 财务数据：营业收入、净利润、经营现金流净额
        - 分红数据：每股分红、股息率、分红历史
        - 资产负债：总资产、总负债、资产负债率

        数据来源：
        - daily_basic: 每日估值指标（PE、PB、PS等）
        - income: 利润表（营收、净利润）
        - cashflow: 现金流量表（经营现金流）
        - fina_indicator: 财务指标（EPS、ROE等）
        - dividend: 分红送股数据

        Args:
            ticker: 股票代码（如：000001、600000）
            curr_date: 当前日期（可选，格式：YYYY-MM-DD）

        Returns:
            str: 标准化的完整财务数据报告
        """
        import asyncio
        from datetime import datetime
        import pandas as pd

        logger.info(f"📊 [完整财务数据] 开始获取 {ticker} 的完整财务数据")

        # 设置默认日期
        if not curr_date:
            curr_date = Toolkit._config.get("trade_date") or datetime.now().strftime(
                "%Y-%m-%d"
            )
            logger.info(f"📅 [完整财务数据] 使用分析日期: {curr_date}")

        try:
            from tradingagents.dataflows.providers.china.tushare import TushareProvider
            from tradingagents.utils.stock_utils import StockUtils

            # 验证股票类型
            market_info = StockUtils.get_market_info(ticker)
            if not market_info["is_china"]:
                return f"❌ 该工具仅支持中国A股，当前股票: {ticker} ({market_info['market_name']})"

            # 初始化 TushareProvider
            provider = TushareProvider()

            # 异步获取完整财务数据
            async def fetch_all_financials():
                await provider.connect()

                # 1. 获取完整财务数据包（包含 income、cashflow、fina_indicator、dividend）
                financial_data = await provider.get_financial_data(ticker, limit=8)

                # 2. 获取每日估值指标（PE、PB、PS等）
                trade_date = curr_date.replace("-", "")
                daily_basic_df = await provider.get_daily_basic(trade_date)

                return financial_data, daily_basic_df

            # 运行异步任务（兼容已有事件循环）
            try:
                # 检查是否已经在事件循环中
                loop = asyncio.get_running_loop()
                # 如果在事件循环中，尝试使用 nest_asyncio
                try:
                    import nest_asyncio

                    nest_asyncio.apply()
                    financial_data, daily_basic_df = asyncio.run(fetch_all_financials())
                except ImportError:
                    logger.warning("⚠️ nest_asyncio 未安装，尝试使用异步兼容模式")
                    # 如果 nest_asyncio 未安装，直接使用 create_task
                    future = asyncio.ensure_future(fetch_all_financials())
                    # 等待任务完成
                    import concurrent.futures

                    executor = concurrent.futures.ThreadPoolExecutor()
                    try:
                        financial_data, daily_basic_df = executor.submit(
                            asyncio.run, fetch_all_financials()
                        ).result()
                    finally:
                        executor.shutdown(wait=False)
            except RuntimeError as e:
                if "no running event loop" in str(e).lower():
                    # 如果没有事件循环，正常使用 asyncio.run
                    financial_data, daily_basic_df = asyncio.run(fetch_all_financials())
                else:
                    raise

            if not financial_data:
                return f"❌ 未能获取 {ticker} 的财务数据"

            # 构建标准化输出
            report_lines = [
                f"# {ticker} 完整财务数据报告",
                f"数据日期: {curr_date}",
                "=" * 60,
                "",
                "## 📊 估值指标",
                "-" * 40,
            ]

            # 从 daily_basic 获取估值指标
            if daily_basic_df is not None and not daily_basic_df.empty:
                # 转换股票代码格式
                ts_code = f"{ticker}.{'SH' if ticker.startswith('6') else 'SZ'}"
                stock_data = daily_basic_df[daily_basic_df["ts_code"] == ts_code]

                if not stock_data.empty:
                    row = stock_data.iloc[0]
                    report_lines.extend(
                        [
                            f"市盈率 (PE): {row.get('pe', 'N/A')}",
                            f"滚动市盈率 (PE_TTM): {row.get('pe_ttm', 'N/A')}",
                            f"市净率 (PB): {row.get('pb', 'N/A')}",
                            f"市销率 (PS): {row.get('ps', 'N/A')}",
                            f"滚动市销率 (PS_TTM): {row.get('ps_ttm', 'N/A')}",
                            f"股息率 (%): {row.get('dv_ratio', 'N/A')}",
                            f"总市值 (万元): {row.get('total_mv', 'N/A'):,.0f}"
                            if pd.notna(row.get("total_mv"))
                            else "总市值 (万元): N/A",
                            f"流通市值 (万元): {row.get('circ_mv', 'N/A'):,.0f}"
                            if pd.notna(row.get("circ_mv"))
                            else "流通市值 (万元): N/A",
                            "",
                        ]
                    )

            # 从 fina_indicator 获取盈利指标
            report_lines.extend(
                [
                    "## 💰 盈利能力指标",
                    "-" * 40,
                ]
            )

            if "indicators" in financial_data and financial_data["indicators"]:
                latest = (
                    financial_data["indicators"][0]
                    if isinstance(financial_data["indicators"], list)
                    else financial_data["indicators"]
                )
                report_lines.extend(
                    [
                        f"每股收益 (EPS): {latest.get('eps', 'N/A')}",
                        f"净资产收益率 (ROE): {latest.get('roe', 'N/A')}%"
                        if latest.get("roe")
                        else "净资产收益率 (ROE): N/A",
                        f"总资产报酬率 (ROA): {latest.get('roa', 'N/A')}%"
                        if latest.get("roa")
                        else "总资产报酬率 (ROA): N/A",
                        f"销售毛利率: {latest.get('grossprofit_margin', 'N/A')}%"
                        if latest.get("grossprofit_margin")
                        else "销售毛利率: N/A",
                        f"销售净利率: {latest.get('netprofit_margin', 'N/A')}%"
                        if latest.get("netprofit_margin")
                        else "销售净利率: N/A",
                        "",
                    ]
                )

            # 从 income 获取营收和利润
            report_lines.extend(
                [
                    "## 📈 营业收入与利润",
                    "-" * 40,
                ]
            )

            if "income" in financial_data and financial_data["income"]:
                latest_income = (
                    financial_data["income"][0]
                    if isinstance(financial_data["income"], list)
                    else financial_data["income"]
                )
                report_lines.extend(
                    [
                        f"营业收入: {latest_income.get('revenue', 'N/A'):,.0f} 万元"
                        if latest_income.get("revenue")
                        else "营业收入: N/A",
                        f"营业总收入: {latest_income.get('total_revenue', 'N/A'):,.0f} 万元"
                        if latest_income.get("total_revenue")
                        else "营业总收入: N/A",
                        f"净利润: {latest_income.get('n_income', 'N/A'):,.0f} 万元"
                        if latest_income.get("n_income")
                        else "净利润: N/A",
                        f"归母净利润: {latest_income.get('n_income_attr_p', 'N/A'):,.0f} 万元"
                        if latest_income.get("n_income_attr_p")
                        else "归母净利润: N/A",
                        "",
                    ]
                )

            # 从 cashflow 获取现金流
            report_lines.extend(
                [
                    "## 💸 现金流量",
                    "-" * 40,
                ]
            )

            if "cashflow" in financial_data and financial_data["cashflow"]:
                latest_cf = (
                    financial_data["cashflow"][0]
                    if isinstance(financial_data["cashflow"], list)
                    else financial_data["cashflow"]
                )
                report_lines.extend(
                    [
                        f"经营现金流净额: {latest_cf.get('n_cashflow_act', 'N/A'):,.0f} 万元"
                        if latest_cf.get("n_cashflow_act")
                        else "经营现金流净额: N/A",
                        f"投资现金流净额: {latest_cf.get('n_cashflow_inv_act', 'N/A'):,.0f} 万元"
                        if latest_cf.get("n_cashflow_inv_act")
                        else "投资现金流净额: N/A",
                        f"筹资现金流净额: {latest_cf.get('n_cashflow_fin_act', 'N/A'):,.0f} 万元"
                        if latest_cf.get("n_cashflow_fin_act")
                        else "筹资现金流净额: N/A",
                        "",
                    ]
                )

            # 从 balancesheet 获取资产负债
            report_lines.extend(
                [
                    "## 🏦 资产负债情况",
                    "-" * 40,
                ]
            )

            if "balancesheet" in financial_data and financial_data["balancesheet"]:
                latest_bs = (
                    financial_data["balancesheet"][0]
                    if isinstance(financial_data["balancesheet"], list)
                    else financial_data["balancesheet"]
                )
                report_lines.extend(
                    [
                        f"总资产: {latest_bs.get('total_assets', 'N/A'):,.0f} 万元"
                        if latest_bs.get("total_assets")
                        else "总资产: N/A",
                        f"总负债: {latest_bs.get('total_liab', 'N/A'):,.0f} 万元"
                        if latest_bs.get("total_liab")
                        else "总负债: N/A",
                        f"股东权益: {latest_bs.get('total_hldr_eqy_exc_min_int', 'N/A'):,.0f} 万元"
                        if latest_bs.get("total_hldr_eqy_exc_min_int")
                        else "股东权益: N/A",
                        "",
                    ]
                )

            # 从 dividend 获取分红数据
            report_lines.extend(
                [
                    "## 💝 分红送股",
                    "-" * 40,
                ]
            )

            if "dividend" in financial_data and financial_data["dividend"]:
                dividends = (
                    financial_data["dividend"]
                    if isinstance(financial_data["dividend"], list)
                    else [financial_data["dividend"]]
                )
                report_lines.append(f"最近 {len(dividends)} 次分红记录:")
                for i, div in enumerate(dividends[:3]):  # 只显示最近3次
                    report_lines.extend(
                        [
                            f"  {i + 1}. 除权除息日: {div.get('ex_date', 'N/A')}",
                            f"     每股现金分红: {div.get('cash_div', 'N/A')} 元"
                            if div.get("cash_div")
                            else "     每股现金分红: N/A",
                            f"     实施进度: {div.get('div_proc', 'N/A')}",
                        ]
                    )
                report_lines.append("")

            # 添加最新股息率
            if "latest_dividend_yield" in financial_data:
                report_lines.extend(
                    [
                        f"最新股息率: {financial_data['latest_dividend_yield']}%",
                        f"最新每股分红: {financial_data.get('latest_cash_div', 'N/A')} 元"
                        if financial_data.get("latest_cash_div")
                        else "最新每股分红: N/A",
                        "",
                    ]
                )

            # 添加财务摘要总结
            report_lines.extend(
                [
                    "=" * 60,
                    "## 📝 财务健康度摘要",
                    "-" * 40,
                ]
            )

            # 根据数据生成简要分析
            health_indicators = []

            if "indicators" in financial_data and financial_data["indicators"]:
                latest = (
                    financial_data["indicators"][0]
                    if isinstance(financial_data["indicators"], list)
                    else financial_data["indicators"]
                )
                roe = latest.get("roe")
                if roe and roe > 15:
                    health_indicators.append(f"✅ ROE {roe}% > 15%，盈利能力优秀")
                elif roe and roe > 10:
                    health_indicators.append(f"✅ ROE {roe}% > 10%，盈利能力良好")
                elif roe:
                    health_indicators.append(f"⚠️ ROE {roe}% < 10%，盈利能力一般")

                debt_ratio = latest.get("debt_to_assets")
                if debt_ratio and debt_ratio < 40:
                    health_indicators.append(
                        f"✅ 资产负债率 {debt_ratio}% < 40%，财务风险较低"
                    )
                elif debt_ratio and debt_ratio < 60:
                    health_indicators.append(f"⚠️ 资产负债率 {debt_ratio}% 适中")
                elif debt_ratio:
                    health_indicators.append(
                        f"❌ 资产负债率 {debt_ratio}% > 60%，财务风险较高"
                    )

            if health_indicators:
                report_lines.extend(health_indicators)
            else:
                report_lines.append("暂无足够数据生成财务健康度分析")

            report_lines.append("")
            report_lines.append(
                f"数据来源: Tushare Pro | 积分要求: 5120 | 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            return "\n".join(report_lines)

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            logger.error(f"❌ [完整财务数据] 获取失败: {e}")
            logger.error(f"详细错误: {error_details}")
            return f"❌ 获取 {ticker} 完整财务数据失败: {str(e)}"

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_fundamentals_unified", log_args=True)
    def get_stock_fundamentals_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"] = None,
        end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"] = None,
        curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"] = None,
    ) -> str:
        """
        统一的股票基本面分析工具
        自动识别股票类型（A股、港股、美股）并调用相应的数据源
        支持基于分析级别的数据获取策略

        Args:
            ticker: 股票代码（如：000001、0700.HK、AAPL）
            start_date: 开始日期（可选，格式：YYYY-MM-DD）
            end_date: 结束日期（可选，格式：YYYY-MM-DD）
            curr_date: 当前日期（可选，格式：YYYY-MM-DD）

        Returns:
            str: 基本面分析数据和报告
        """
        logger.info(f"📊 [统一基本面工具] 分析股票: {ticker}")

        # 🔧 获取分析级别配置，支持基于级别的数据获取策略
        research_depth = Toolkit._config.get("research_depth", "标准")
        logger.info(f"🔧 [分析级别] 当前分析级别: {research_depth}")

        # 数字等级到中文等级的映射
        numeric_to_chinese = {1: "快速", 2: "基础", 3: "标准", 4: "深度", 5: "全面"}

        # 标准化研究深度：支持数字输入
        if isinstance(research_depth, (int, float)):
            research_depth = int(research_depth)
            if research_depth in numeric_to_chinese:
                chinese_depth = numeric_to_chinese[research_depth]
                logger.info(
                    f"🔢 [等级转换] 数字等级 {research_depth} → 中文等级 '{chinese_depth}'"
                )
                research_depth = chinese_depth
            else:
                logger.warning(f"⚠️ 无效的数字等级: {research_depth}，使用默认标准分析")
                research_depth = "标准"
        elif isinstance(research_depth, str):
            # 如果是字符串形式的数字，转换为整数
            if research_depth.isdigit():
                numeric_level = int(research_depth)
                if numeric_level in numeric_to_chinese:
                    chinese_depth = numeric_to_chinese[numeric_level]
                    logger.info(
                        f"🔢 [等级转换] 字符串数字 '{research_depth}' → 中文等级 '{chinese_depth}'"
                    )
                    research_depth = chinese_depth
                else:
                    logger.warning(
                        f"⚠️ 无效的字符串数字等级: {research_depth}，使用默认标准分析"
                    )
                    research_depth = "标准"
            # 如果已经是中文等级，直接使用
            elif research_depth in ["快速", "基础", "标准", "深度", "全面"]:
                logger.info(f"📝 [等级确认] 使用中文等级: '{research_depth}'")
            else:
                logger.warning(f"⚠️ 未知的研究深度: {research_depth}，使用默认标准分析")
                research_depth = "标准"
        else:
            logger.warning(
                f"⚠️ 无效的研究深度类型: {type(research_depth)}，使用默认标准分析"
            )
            research_depth = "标准"

        # 根据分析级别调整数据获取策略
        # 🔧 修正映射关系：data_depth 应该与 research_depth 保持一致
        if research_depth == "快速":
            # 快速分析：获取基础数据，减少数据源调用
            data_depth = "basic"
            logger.info(f"🔧 [分析级别] 快速分析模式：获取基础数据")
        elif research_depth == "基础":
            # 基础分析：获取标准数据
            data_depth = "standard"
            logger.info(f"🔧 [分析级别] 基础分析模式：获取标准数据")
        elif research_depth == "标准":
            # 标准分析：获取标准数据（不是full！）
            data_depth = "standard"
            logger.info(f"🔧 [分析级别] 标准分析模式：获取标准数据")
        elif research_depth == "深度":
            # 深度分析：获取完整数据
            data_depth = "full"
            logger.info(f"🔧 [分析级别] 深度分析模式：获取完整数据")
        elif research_depth == "全面":
            # 全面分析：获取最全面的数据，包含所有可用数据源
            data_depth = "comprehensive"
            logger.info(f"🔧 [分析级别] 全面分析模式：获取最全面数据")
        else:
            # 默认使用标准分析
            data_depth = "standard"
            logger.info(f"🔧 [分析级别] 未知级别，使用标准分析模式")

        # 添加详细的股票代码追踪日志
        logger.info(
            f"🔍 [股票代码追踪] 统一基本面工具接收到的原始股票代码: '{ticker}' (类型: {type(ticker)})"
        )
        logger.info(f"🔍 [股票代码追踪] 股票代码长度: {len(str(ticker))}")
        logger.info(f"🔍 [股票代码追踪] 股票代码字符: {list(str(ticker))}")

        # 保存原始ticker用于对比
        original_ticker = ticker

        try:
            from tradingagents.utils.stock_utils import StockUtils
            from datetime import datetime, timedelta

            # 自动识别股票类型
            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info["is_china"]
            is_hk = market_info["is_hk"]
            is_us = market_info["is_us"]

            logger.info(
                f"🔍 [股票代码追踪] StockUtils.get_market_info 返回的市场信息: {market_info}"
            )
            logger.info(f"📊 [统一基本面工具] 股票类型: {market_info['market_name']}")
            logger.info(
                f"📊 [统一基本面工具] 货币: {market_info['currency_name']} ({market_info['currency_symbol']})"
            )

            # 检查ticker是否在处理过程中发生了变化
            if str(ticker) != str(original_ticker):
                logger.warning(
                    f"🔍 [股票代码追踪] 警告：股票代码发生了变化！原始: '{original_ticker}' -> 当前: '{ticker}'"
                )

            # 设置默认日期 - 优先使用 Toolkit._config 中的 trade_date
            if not curr_date:
                # 尝试从 Toolkit 配置获取分析日期
                curr_date = Toolkit._config.get("trade_date")
                if curr_date:
                    logger.info(
                        f"📅 [统一基本面工具] 使用 Toolkit._config 中的分析日期: {curr_date}"
                    )
                else:
                    curr_date = datetime.now().strftime("%Y-%m-%d")
                    logger.warning(
                        f"⚠️ [统一基本面工具] 未提供分析日期，使用系统时间: {curr_date}"
                    )

            # 基本面分析优化：不需要大量历史数据，只需要当前价格和财务数据
            # 根据数据深度级别设置不同的分析模块数量，而非历史数据范围
            # 🔧 修正映射关系：analysis_modules 应该与 data_depth 保持一致
            if data_depth == "basic":  # 快速分析：基础模块
                analysis_modules = "basic"
                logger.info(f"📊 [基本面策略] 快速分析模式：获取基础财务指标")
            elif data_depth == "standard":  # 基础/标准分析：标准模块
                analysis_modules = "standard"
                logger.info(f"📊 [基本面策略] 标准分析模式：获取标准财务分析")
            elif data_depth == "full":  # 深度分析：完整模块
                analysis_modules = "full"
                logger.info(f"📊 [基本面策略] 深度分析模式：获取完整基本面分析")
            elif data_depth == "comprehensive":  # 全面分析：综合模块
                analysis_modules = "comprehensive"
                logger.info(f"📊 [基本面策略] 全面分析模式：获取综合基本面分析")
            else:
                analysis_modules = "standard"  # 默认标准分析
                logger.info(f"📊 [基本面策略] 默认模式：获取标准基本面分析")

            # 基本面分析策略：
            # 1. 获取10天数据（保证能拿到数据，处理周末/节假日）
            # 2. 只使用最近2天数据参与分析（仅需当前价格）
            days_to_fetch = 10  # 固定获取10天数据
            days_to_analyze = 2  # 只分析最近2天

            logger.info(
                f"📅 [基本面策略] 获取{days_to_fetch}天数据，分析最近{days_to_analyze}天"
            )

            if not start_date:
                start_date = (datetime.now() - timedelta(days=days_to_fetch)).strftime(
                    "%Y-%m-%d"
                )

            if not end_date:
                end_date = curr_date

            result_data = []

            if is_china:
                # 中国A股：基本面分析优化策略 - 只获取必要的当前价格和基本面数据
                logger.info(
                    f"🇨🇳 [统一基本面工具] 处理A股数据，数据深度: {data_depth}..."
                )
                logger.info(f"🔍 [股票代码追踪] 进入A股处理分支，ticker: '{ticker}'")
                logger.info(
                    f"💡 [优化策略] 基本面分析只获取当前价格和财务数据，不获取历史日线数据"
                )

                # 🔧 FIX: 使用统一交易日管理器，确保与技术分析使用相同的数据日期
                from tradingagents.utils.trading_date_manager import (
                    get_trading_date_manager,
                )
                from tradingagents.utils.price_cache import get_price_cache

                date_mgr = get_trading_date_manager()
                trading_date = date_mgr.get_latest_trading_date(curr_date)

                # 如果对齐后的日期不同，记录日志
                if trading_date != curr_date:
                    logger.info(
                        f"📅 [基本面分析] 日期对齐: {curr_date} → {trading_date} (最新交易日)"
                    )

                # 优化策略：基本面分析不需要大量历史日线数据
                # 只获取当前股价信息（最近5天数据以确保包含交易日）和基本面财务数据
                try:
                    # 获取最新股价信息
                    from datetime import datetime, timedelta

                    recent_end_date = trading_date
                    recent_start_date = (
                        datetime.strptime(trading_date, "%Y-%m-%d") - timedelta(days=5)
                    ).strftime("%Y-%m-%d")

                    logger.info(
                        f"📅 [基本面分析] 使用统一交易日: {trading_date}, 查询范围: {recent_start_date} 至 {recent_end_date}"
                    )

                    from tradingagents.dataflows.interface import (
                        get_china_stock_data_unified,
                    )

                    logger.info(
                        f"🔍 [股票代码追踪] 调用 get_china_stock_data_unified（仅获取最新价格），传入参数: ticker='{ticker}', start_date='{recent_start_date}', end_date='{recent_end_date}'"
                    )
                    current_price_data = get_china_stock_data_unified(
                        ticker, recent_start_date, recent_end_date
                    )

                    # 🔍 调试：打印返回数据的前500字符
                    logger.info(
                        f"🔍 [基本面工具调试] A股价格数据返回长度: {len(current_price_data)}"
                    )
                    logger.info(
                        f"🔍 [基本面工具调试] A股价格数据前500字符:\n{current_price_data[:500]}"
                    )

                    result_data.append(f"## A股当前价格信息\n{current_price_data}")
                except Exception as e:
                    logger.error(f"❌ [基本面工具调试] A股价格数据获取失败: {e}")
                    result_data.append(f"## A股当前价格信息\n获取失败: {e}")
                    current_price_data = ""

                try:
                    # 获取基本面财务数据（这是基本面分析的核心）
                    from tradingagents.dataflows.optimized_china_data import (
                        OptimizedChinaDataProvider,
                    )

                    analyzer = OptimizedChinaDataProvider()
                    logger.info(
                        f"🔍 [股票代码追踪] 调用 OptimizedChinaDataProvider._generate_fundamentals_report，传入参数: ticker='{ticker}', analysis_modules='{analysis_modules}'"
                    )

                    # 传递分析模块参数到基本面分析方法
                    fundamentals_data = analyzer._generate_fundamentals_report(
                        ticker, current_price_data, analysis_modules
                    )

                    # 🔍 调试：打印返回数据的前500字符
                    logger.info(
                        f"🔍 [基本面工具调试] A股基本面数据返回长度: {len(fundamentals_data)}"
                    )
                    logger.info(
                        f"🔍 [基本面工具调试] A股基本面数据前500字符:\n{fundamentals_data[:500]}"
                    )

                    result_data.append(f"## A股基本面财务数据\n{fundamentals_data}")
                except Exception as e:
                    logger.error(f"❌ [基本面工具调试] A股基本面数据获取失败: {e}")
                    result_data.append(f"## A股基本面财务数据\n获取失败: {e}")

            elif is_hk:
                # 港股：使用AKShare数据源，支持多重备用方案
                logger.info(
                    f"🇭🇰 [统一基本面工具] 处理港股数据，数据深度: {data_depth}..."
                )

                hk_data_success = False

                # 🔥 统一策略：所有级别都获取完整数据
                # 原因：提示词是统一的，如果数据不完整会导致LLM基于不存在的数据进行分析（幻觉）
                logger.info(
                    f"🔍 [港股基本面] 统一策略：获取完整数据（忽略 data_depth 参数）"
                )

                # 主要数据源：AKShare
                try:
                    from tradingagents.dataflows.interface import (
                        get_hk_stock_data_unified,
                    )

                    hk_data = get_hk_stock_data_unified(ticker, start_date, end_date)

                    # 🔍 调试：打印返回数据的前500字符
                    logger.info(f"🔍 [基本面工具调试] 港股数据返回长度: {len(hk_data)}")
                    logger.info(
                        f"🔍 [基本面工具调试] 港股数据前500字符:\n{hk_data[:500]}"
                    )

                    # 检查数据质量
                    if hk_data and len(hk_data) > 100 and "❌" not in hk_data:
                        result_data.append(f"## 港股数据\n{hk_data}")
                        hk_data_success = True
                        logger.info(f"✅ [统一基本面工具] 港股主要数据源成功")
                    else:
                        logger.warning(f"⚠️ [统一基本面工具] 港股主要数据源质量不佳")

                except Exception as e:
                    logger.error(f"❌ [基本面工具调试] 港股数据获取失败: {e}")

                # 备用方案：基础港股信息
                if not hk_data_success:
                    try:
                        from tradingagents.dataflows.interface import (
                            get_hk_stock_info_unified,
                        )

                        hk_info = get_hk_stock_info_unified(ticker)

                        basic_info = f"""## 港股基础信息

**股票代码**: {ticker}
**股票名称**: {hk_info.get("name", f"港股{ticker}")}
**交易货币**: 港币 (HK$)
**交易所**: 香港交易所 (HKG)
**数据源**: {hk_info.get("source", "基础信息")}

⚠️ 注意：详细的价格和财务数据暂时无法获取，建议稍后重试或使用其他数据源。

**基本面分析建议**：
- 建议查看公司最新财报
- 关注港股市场整体走势
- 考虑汇率因素对投资的影响
"""
                        result_data.append(basic_info)
                        logger.info(f"✅ [统一基本面工具] 港股备用信息成功")

                    except Exception as e2:
                        # 最终备用方案
                        fallback_info = f"""## 港股信息（备用）

**股票代码**: {ticker}
**股票类型**: 港股
**交易货币**: 港币 (HK$)
**交易所**: 香港交易所 (HKG)

❌ 数据获取遇到问题: {str(e2)}

**建议**：
- 请稍后重试
- 或使用其他数据源
- 检查股票代码格式是否正确
"""
                        result_data.append(fallback_info)
                        logger.error(f"❌ [统一基本面工具] 港股所有数据源都失败: {e2}")

            else:
                # 美股：使用OpenAI/Finnhub数据源
                logger.info(f"🇺🇸 [统一基本面工具] 处理美股数据...")

                # 🔥 统一策略：所有级别都获取完整数据
                # 原因：提示词是统一的，如果数据不完整会导致LLM基于不存在的数据进行分析（幻觉）
                logger.info(
                    f"🔍 [美股基本面] 统一策略：获取完整数据（忽略 data_depth 参数）"
                )

                try:
                    from tradingagents.dataflows.interface import (
                        get_fundamentals_openai,
                    )

                    us_data = get_fundamentals_openai(ticker, curr_date)
                    result_data.append(f"## 美股基本面数据\n{us_data}")
                    logger.info(f"✅ [统一基本面工具] 美股数据获取成功")
                except Exception as e:
                    result_data.append(f"## 美股基本面数据\n获取失败: {e}")
                    logger.error(f"❌ [统一基本面工具] 美股数据获取失败: {e}")

            # 组合所有数据
            combined_result = f"""# {ticker} 基本面分析数据

**股票类型**: {market_info["market_name"]}
**货币**: {market_info["currency_name"]} ({market_info["currency_symbol"]})
**分析日期**: {curr_date}
**数据深度级别**: {data_depth}

{chr(10).join(result_data)}

---
*数据来源: 根据股票类型自动选择最适合的数据源*
"""

            # 添加详细的数据获取日志
            logger.info(f"📊 [统一基本面工具] ===== 数据获取完成摘要 =====")
            logger.info(f"📊 [统一基本面工具] 股票代码: {ticker}")
            logger.info(f"📊 [统一基本面工具] 股票类型: {market_info['market_name']}")
            logger.info(f"📊 [统一基本面工具] 数据深度级别: {data_depth}")
            logger.info(f"📊 [统一基本面工具] 获取的数据模块数量: {len(result_data)}")
            logger.info(f"📊 [统一基本面工具] 总数据长度: {len(combined_result)} 字符")

            # 记录每个数据模块的详细信息
            for i, data_section in enumerate(result_data, 1):
                section_lines = data_section.split("\n")
                section_title = section_lines[0] if section_lines else "未知模块"
                section_length = len(data_section)
                logger.info(
                    f"📊 [统一基本面工具] 数据模块 {i}: {section_title} ({section_length} 字符)"
                )

                # 如果数据包含错误信息，特别标记
                if "获取失败" in data_section or "❌" in data_section:
                    logger.warning(f"⚠️ [统一基本面工具] 数据模块 {i} 包含错误信息")
                else:
                    logger.info(f"✅ [统一基本面工具] 数据模块 {i} 获取成功")

            # 根据数据深度级别记录具体的获取策略
            if data_depth in ["basic", "standard"]:
                logger.info(
                    f"📊 [统一基本面工具] 基础/标准级别策略: 仅获取核心价格数据和基础信息"
                )
            elif data_depth in ["full", "detailed", "comprehensive"]:
                logger.info(
                    f"📊 [统一基本面工具] 完整/详细/全面级别策略: 获取价格数据 + 基本面数据"
                )
            else:
                logger.info(f"📊 [统一基本面工具] 默认策略: 获取完整数据")

            logger.info(f"📊 [统一基本面工具] ===== 数据获取摘要结束 =====")

            # 🔍 添加数据验证信息
            try:
                from tradingagents.agents.utils.data_validation_integration import (
                    add_data_validation_to_fundamentals_report,
                )

                combined_result = add_data_validation_to_fundamentals_report(
                    ticker, combined_result
                )
                logger.info(f"✅ [统一基本面工具] {ticker} 数据验证已完成")
            except Exception as e:
                logger.warning(f"⚠️ [统一基本面工具] 数据验证失败: {e}")

            return combined_result

        except Exception as e:
            error_msg = f"统一基本面分析工具执行失败: {str(e)}"
            logger.error(f"❌ [统一基本面工具] {error_msg}")
            return error_msg

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_market_data_unified", log_args=True)
    def get_stock_market_data_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        start_date: Annotated[
            str,
            "开始日期，格式：YYYY-MM-DD。注意：系统会自动扩展到配置的回溯天数（通常为365天），你只需要传递分析日期即可",
        ],
        end_date: Annotated[
            str,
            "结束日期，格式：YYYY-MM-DD。通常与start_date相同，传递当前分析日期即可",
        ],
    ) -> str:
        """
        统一的股票市场数据工具
        自动识别股票类型（A股、港股、美股）并调用相应的数据源获取价格和技术指标数据

        ⚠️ 重要：系统会自动扩展日期范围到配置的回溯天数（通常为365天），以确保技术指标计算有足够的历史数据。
        你只需要传递当前分析日期作为 start_date 和 end_date 即可，无需手动计算历史日期范围。

        Args:
            ticker: 股票代码（如：000001、0700.HK、AAPL）
            start_date: 开始日期（格式：YYYY-MM-DD）。传递当前分析日期即可，系统会自动扩展
            end_date: 结束日期（格式：YYYY-MM-DD）。传递当前分析日期即可

        Returns:
            str: 市场数据和技术分析报告

        示例：
            如果分析日期是 2025-11-09，传递：
            - ticker: "00700.HK"
            - start_date: "2025-11-09"
            - end_date: "2025-11-09"
            系统会自动获取 2024-11-09 到 2025-11-09 的365天历史数据
        """
        logger.info(f"📈 [统一市场工具] 分析股票: {ticker}")

        try:
            from tradingagents.utils.stock_utils import StockUtils

            # 自动识别股票类型
            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info["is_china"]
            is_hk = market_info["is_hk"]
            is_us = market_info["is_us"]

            logger.info(f"📈 [统一市场工具] 股票类型: {market_info['market_name']}")
            logger.info(
                f"📈 [统一市场工具] 货币: {market_info['currency_name']} ({market_info['currency_symbol']}"
            )

            result_data = []

            if is_china:
                # 中国A股：使用中国股票数据源
                logger.info(f"🇨🇳 [统一市场工具] 处理A股市场数据...")

                # 🔧 FIX: 使用统一交易日管理器，确保与基本面分析使用相同的数据日期
                from tradingagents.utils.trading_date_manager import (
                    get_trading_date_manager,
                )

                date_mgr = get_trading_date_manager()
                aligned_end_date = date_mgr.get_latest_trading_date(end_date)

                # 如果对齐后的日期不同，记录日志
                if aligned_end_date != end_date:
                    logger.info(
                        f"📅 [技术分析] 日期对齐: {end_date} → {aligned_end_date} (最新交易日)"
                    )

                try:
                    from tradingagents.dataflows.interface import (
                        get_china_stock_data_unified,
                    )

                    stock_data = get_china_stock_data_unified(
                        ticker, start_date, aligned_end_date
                    )

                    # 🔍 调试：打印返回数据的前500字符
                    logger.info(f"🔍 [市场工具调试] A股数据返回长度: {len(stock_data)}")
                    logger.info(
                        f"🔍 [市场工具调试] A股数据前500字符:\n{stock_data[:500]}"
                    )

                    result_data.append(f"## A股市场数据\n{stock_data}")
                except Exception as e:
                    logger.error(f"❌ [市场工具调试] A股数据获取失败: {e}")
                    result_data.append(f"## A股市场数据\n获取失败: {e}")

            elif is_hk:
                # 港股：使用AKShare数据源
                logger.info(f"🇭🇰 [统一市场工具] 处理港股市场数据...")

                try:
                    from tradingagents.dataflows.interface import (
                        get_hk_stock_data_unified,
                    )

                    hk_data = get_hk_stock_data_unified(ticker, start_date, end_date)

                    # 🔍 调试：打印返回数据的前500字符
                    logger.info(f"🔍 [市场工具调试] 港股数据返回长度: {len(hk_data)}")
                    logger.info(
                        f"🔍 [市场工具调试] 港股数据前500字符:\n{hk_data[:500]}"
                    )

                    result_data.append(f"## 港股市场数据\n{hk_data}")
                except Exception as e:
                    logger.error(f"❌ [市场工具调试] 港股数据获取失败: {e}")
                    result_data.append(f"## 港股市场数据\n获取失败: {e}")

            else:
                # 美股：优先使用FINNHUB API数据源
                logger.info(f"🇺🇸 [统一市场工具] 处理美股市场数据...")

                try:
                    from tradingagents.dataflows.providers.us.optimized import (
                        get_us_stock_data_cached,
                    )

                    us_data = get_us_stock_data_cached(ticker, start_date, end_date)
                    result_data.append(f"## 美股市场数据\n{us_data}")
                except Exception as e:
                    result_data.append(f"## 美股市场数据\n获取失败: {e}")

            # 组合所有数据
            combined_result = f"""# {ticker} 市场数据分析

**股票类型**: {market_info["market_name"]}
**货币**: {market_info["currency_name"]} ({market_info["currency_symbol"]})
**分析期间**: {start_date} 至 {end_date}

{chr(10).join(result_data)}

---
*数据来源: 根据股票类型自动选择最适合的数据源*
"""

            # 🔍 添加数据验证信息
            try:
                from tradingagents.agents.utils.data_validation_integration import (
                    add_data_validation_to_market_report,
                )

                combined_result = add_data_validation_to_market_report(
                    ticker, combined_result
                )
                logger.info(f"✅ [统一市场工具] {ticker} 数据验证已完成")
            except Exception as e:
                logger.warning(f"⚠️ [统一市场工具] 数据验证失败: {e}")

            logger.info(
                f"📈 [统一市场工具] 数据获取完成，总长度: {len(combined_result)}"
            )
            return combined_result

        except Exception as e:
            error_msg = f"统一市场数据工具执行失败: {str(e)}"
            logger.error(f"❌ [统一市场工具] {error_msg}")
            return error_msg

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_news_unified", log_args=True)
    def get_stock_news_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"],
    ) -> str:
        """
        统一的股票新闻工具
        自动识别股票类型（A股、港股、美股）并调用相应的新闻数据源

        数据源策略:
        - A股/港股: 使用东方财富新闻（AKShare）
        - 美股: 使用 Finnhub 新闻
        - 注: 已移除 Google 新闻（国内访问不稳定）

        Args:
            ticker: 股票代码（如：000001、0700.HK、AAPL）
            curr_date: 当前日期（格式：YYYY-MM-DD）

        Returns:
            str: 新闻分析报告
        """
        logger.info(f"📰 [统一新闻工具] 分析股票: {ticker}")

        try:
            from tradingagents.utils.stock_utils import StockUtils
            from datetime import datetime, timedelta

            # 自动识别股票类型
            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info["is_china"]
            is_hk = market_info["is_hk"]
            is_us = market_info["is_us"]

            logger.info(f"📰 [统一新闻工具] 股票类型: {market_info['market_name']}")

            # 计算新闻查询的日期范围
            end_date = datetime.strptime(curr_date, "%Y-%m-%d")
            start_date = end_date - timedelta(days=7)
            start_date_str = start_date.strftime("%Y-%m-%d")

            result_data = []

            if is_china or is_hk:
                # 中国A股和港股：使用AKShare东方财富新闻和Google新闻（中文搜索）
                logger.info(f"🇨🇳🇭🇰 [统一新闻工具] 处理中文新闻...")

                # 1. 尝试获取AKShare东方财富新闻
                try:
                    # 处理股票代码
                    clean_ticker = (
                        ticker.replace(".SH", "")
                        .replace(".SZ", "")
                        .replace(".SS", "")
                        .replace(".HK", "")
                        .replace(".XSHE", "")
                        .replace(".XSHG", "")
                    )

                    logger.info(
                        f"🇨🇳🇭🇰 [统一新闻工具] 尝试获取东方财富新闻: {clean_ticker}"
                    )

                    # 通过 AKShare Provider 获取新闻
                    from tradingagents.dataflows.providers.china.akshare import (
                        AKShareProvider,
                    )

                    provider = AKShareProvider()

                    # 获取东方财富新闻
                    news_df = provider.get_stock_news_sync(symbol=clean_ticker)

                    if news_df is not None and not news_df.empty:
                        # 格式化东方财富新闻
                        em_news_items = []
                        for _, row in news_df.iterrows():
                            # AKShare 返回的字段名
                            news_title = row.get("新闻标题", "") or row.get("标题", "")
                            news_time = row.get("发布时间", "") or row.get("时间", "")
                            news_url = row.get("新闻链接", "") or row.get("链接", "")

                            news_item = f"- **{news_title}** [{news_time}]({news_url})"
                            em_news_items.append(news_item)

                        # 添加到结果中
                        if em_news_items:
                            em_news_text = "\n".join(em_news_items)
                            result_data.append(f"## 东方财富新闻\n{em_news_text}")
                            logger.info(
                                f"🇨🇳🇭🇰 [统一新闻工具] 成功获取{len(em_news_items)}条东方财富新闻"
                            )
                except Exception as em_e:
                    logger.error(f"❌ [统一新闻工具] 东方财富新闻获取失败: {em_e}")
                    result_data.append(f"## 东方财富新闻\n获取失败: {em_e}")

            else:
                # 美股：使用Finnhub新闻
                logger.info(f"🇺🇸 [统一新闻工具] 处理美股新闻...")

                try:
                    from tradingagents.dataflows.interface import get_finnhub_news

                    news_data = get_finnhub_news(ticker, start_date_str, curr_date)
                    result_data.append(f"## 美股新闻\n{news_data}")
                except Exception as e:
                    result_data.append(f"## 美股新闻\n获取失败: {e}")

            # 组合所有数据
            combined_result = f"""# {ticker} 新闻分析

**股票类型**: {market_info["market_name"]}
**分析日期**: {curr_date}
**新闻时间范围**: {start_date_str} 至 {curr_date}

{chr(10).join(result_data)}

---
*数据来源: 根据股票类型自动选择最适合的新闻源*
"""

            logger.info(
                f"📰 [统一新闻工具] 数据获取完成，总长度: {len(combined_result)}"
            )
            return combined_result

        except Exception as e:
            error_msg = f"统一新闻工具执行失败: {str(e)}"
            logger.error(f"❌ [统一新闻工具] {error_msg}")
            return error_msg

    @staticmethod
    @tool
    @log_tool_call(tool_name="get_stock_sentiment_unified", log_args=True)
    def get_stock_sentiment_unified(
        ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
        curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"],
    ) -> str:
        """
        统一的股票情绪分析工具
        自动识别股票类型（A股、港股、美股）并调用相应的情绪数据源

        Args:
            ticker: 股票代码（如：000001、0700.HK、AAPL）
            curr_date: 当前日期（格式：YYYY-MM-DD）

        Returns:
            str: 情绪分析报告
        """
        logger.info(f"😊 [统一情绪工具] 分析股票: {ticker}")

        try:
            from tradingagents.utils.stock_utils import StockUtils

            # 自动识别股票类型
            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info["is_china"]
            is_hk = market_info["is_hk"]
            is_us = market_info["is_us"]

            logger.info(f"😊 [统一情绪工具] 股票类型: {market_info['market_name']}")

            result_data = []

            if is_china or is_hk:
                # 中国A股和港股：使用社交媒体情绪分析
                logger.info(f"🇨🇳🇭🇰 [统一情绪工具] 处理中文市场情绪...")

                try:
                    # 可以集成微博、雪球、东方财富等中文社交媒体情绪
                    # 目前使用基础的情绪分析
                    sentiment_summary = f"""
## 中文市场情绪分析

**股票**: {ticker} ({market_info["market_name"]})
**分析日期**: {curr_date}

### 市场情绪概况
- 由于中文社交媒体情绪数据源暂未完全集成，当前提供基础分析
- 建议关注雪球、东方财富、同花顺等平台的讨论热度
- 港股市场还需关注香港本地财经媒体情绪

### 情绪指标
- 整体情绪: 中性
- 讨论热度: 待分析
- 投资者信心: 待评估

*注：完整的中文社交媒体情绪分析功能正在开发中*
"""
                    result_data.append(sentiment_summary)
                except Exception as e:
                    result_data.append(f"## 中文市场情绪\n获取失败: {e}")

            else:
                # 美股：使用Reddit情绪分析
                logger.info(f"🇺🇸 [统一情绪工具] 处理美股情绪...")

                try:
                    from tradingagents.dataflows.interface import get_reddit_sentiment

                    sentiment_data = get_reddit_sentiment(ticker, curr_date)
                    result_data.append(f"## 美股Reddit情绪\n{sentiment_data}")
                except Exception as e:
                    result_data.append(f"## 美股Reddit情绪\n获取失败: {e}")

            # 组合所有数据
            combined_result = f"""# {ticker} 情绪分析

**股票类型**: {market_info["market_name"]}
**分析日期**: {curr_date}

{chr(10).join(result_data)}

---
*数据来源: 根据股票类型自动选择最适合的情绪数据源*
"""

            logger.info(
                f"😊 [统一情绪工具] 数据获取完成，总长度: {len(combined_result)}"
            )
            return combined_result

        except Exception as e:
            error_msg = f"统一情绪分析工具执行失败: {str(e)}"
            logger.error(f"❌ [统一情绪工具] {error_msg}")
            return error_msg
