# -*- coding: utf-8 -*-
"""技术指标工具模块"""
from typing import Annotated

import tradingagents.dataflows.interface as interface


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
