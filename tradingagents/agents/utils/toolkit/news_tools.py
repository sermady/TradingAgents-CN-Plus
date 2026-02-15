# -*- coding: utf-8 -*-
"""新闻获取工具模块"""
from typing import Annotated

import tradingagents.dataflows.interface as interface
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("agents")


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
    end_date_dt = __import__("datetime").datetime.strptime(end_date, "%Y-%m-%d")
    start_date_dt = __import__("datetime").datetime.strptime(start_date, "%Y-%m-%d")
    look_back_days = (end_date_dt - start_date_dt).days

    finnhub_news_result = interface.get_finnhub_news(
        ticker, end_date_str, look_back_days
    )

    return finnhub_news_result


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
    Returns:
        str: A formatted string containing the latest news from Google News based on the query and date range.
    """
    google_news_results = interface.get_google_news(query, curr_date, 7)
    return google_news_results


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
