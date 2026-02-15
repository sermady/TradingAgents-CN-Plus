# -*- coding: utf-8 -*-
"""股票数据工具模块"""
from typing import Annotated

import tradingagents.dataflows.interface as interface
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("agents")


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
