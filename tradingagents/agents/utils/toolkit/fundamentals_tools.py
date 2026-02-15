# -*- coding: utf-8 -*-
"""基本面数据工具模块"""

from typing import Annotated

import tradingagents.dataflows.interface as interface
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("agents")


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
    data_income_stmt = interface.get_simfin_income_statements(ticker, freq, curr_date)
    return data_income_stmt


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
                company_name = stock_info.split("股票名称:")[1].split("\n")[0].strip()
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

        # 生成真正的基本面分析报告 (使用默认的 standard 分析模块)
        fundamentals_report = analyzer._generate_fundamentals_report(ticker)

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
