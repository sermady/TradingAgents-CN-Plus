# -*- coding: utf-8 -*-
"""
统一的公司名称获取工具

此模块提供统一的公司名称获取接口，支持A股、港股和美股。
消除了之前在6个分析师/研究员文件中的重复代码。

Usage:
    from tradingagents.utils.company_name_utils import get_company_name

    # 基本用法
    name = get_company_name("000001")  # A股
    name = get_company_name("AAPL")    # 美股
    name = get_company_name("0700.HK") # 港股

    # 传入已知的市场信息（避免重复检测）
    market_info = StockUtils.get_market_info(ticker)
    name = get_company_name(ticker, market_info)
"""

from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")

# 美股名称映射（常用股票的中文名称）
US_STOCK_NAMES = {
    'AAPL': '苹果公司',
    'TSLA': '特斯拉',
    'NVDA': '英伟达',
    'MSFT': '微软',
    'GOOGL': '谷歌',
    'GOOG': '谷歌',
    'AMZN': '亚马逊',
    'META': 'Meta',
    'NFLX': '奈飞',
    'AMD': 'AMD',
    'INTC': '英特尔',
    'BABA': '阿里巴巴',
    'JD': '京东',
    'PDD': '拼多多',
    'NIO': '蔚来',
    'XPEV': '小鹏汽车',
    'LI': '理想汽车',
}


def get_company_name(ticker: str, market_info: dict = None) -> str:
    """
    统一获取公司名称

    根据股票代码获取对应的公司名称，支持A股、港股和美股。

    Args:
        ticker: 股票代码
        market_info: 市场信息字典（可选）。如果不传入，会自动检测。
                    包含 is_china, is_hk, is_us 等字段。

    Returns:
        str: 公司名称。如果无法获取，返回 "股票代码{ticker}" 格式的默认值。

    Examples:
        >>> get_company_name("000001")
        '平安银行'
        >>> get_company_name("AAPL")
        '苹果公司'
        >>> get_company_name("0700.HK")
        '腾讯控股'
    """
    # 如果没有传入市场信息，自动检测
    if market_info is None:
        try:
            from tradingagents.agents.utils.stock_utils import StockUtils
            market_info = StockUtils.get_market_info(ticker)
        except Exception as e:
            logger.warning(f"无法检测股票市场类型: {ticker}, 错误: {e}")
            return f"股票{ticker}"

    try:
        if market_info.get('is_china'):
            return _get_china_company_name(ticker)
        elif market_info.get('is_hk'):
            return _get_hk_company_name(ticker)
        elif market_info.get('is_us'):
            return _get_us_company_name(ticker)
        else:
            return f"股票{ticker}"

    except Exception as e:
        logger.error(f"获取公司名称失败: {ticker}, 错误: {e}")
        return f"股票{ticker}"


def _get_china_company_name(ticker: str) -> str:
    """
    获取A股公司名称

    使用统一数据接口获取中国A股公司名称，如果失败则尝试降级方案。

    Args:
        ticker: A股股票代码（如 "000001"）

    Returns:
        str: 公司名称
    """
    try:
        # 主要方案：使用统一接口获取股票信息
        from tradingagents.dataflows.interface import get_china_stock_info_unified
        stock_info = get_china_stock_info_unified(ticker)

        logger.debug(f"[公司名称工具] A股信息返回: {stock_info[:200] if stock_info else 'None'}...")

        # 解析股票名称
        if stock_info and "股票名称:" in stock_info:
            company_name = stock_info.split("股票名称:")[1].split("\n")[0].strip()
            logger.debug(f"[公司名称工具] A股名称解析成功: {ticker} -> {company_name}")
            return company_name

    except Exception as e:
        logger.warning(f"[公司名称工具] 统一接口获取A股名称失败: {ticker}, 错误: {e}")

    # 降级方案：尝试从数据源管理器获取
    try:
        from tradingagents.dataflows.data_source_manager import get_china_stock_info_unified as get_info_dict
        info_dict = get_info_dict(ticker)
        if info_dict and info_dict.get('name'):
            company_name = info_dict['name']
            logger.debug(f"[公司名称工具] 降级方案成功: {ticker} -> {company_name}")
            return company_name
    except Exception as e:
        logger.warning(f"[公司名称工具] 降级方案也失败: {ticker}, 错误: {e}")

    logger.warning(f"[公司名称工具] 无法获取A股名称: {ticker}")
    return f"股票代码{ticker}"


def _get_hk_company_name(ticker: str) -> str:
    """
    获取港股公司名称

    使用改进的港股工具获取公司名称，如果失败则返回默认格式。

    Args:
        ticker: 港股股票代码（如 "0700.HK"）

    Returns:
        str: 公司名称
    """
    try:
        from tradingagents.dataflows.providers.hk.improved_hk import get_hk_company_name_improved
        company_name = get_hk_company_name_improved(ticker)
        logger.debug(f"[公司名称工具] 港股名称获取成功: {ticker} -> {company_name}")
        return company_name
    except Exception as e:
        logger.debug(f"[公司名称工具] 港股名称获取失败: {ticker}, 错误: {e}")
        # 降级方案：生成友好的默认名称
        clean_ticker = ticker.replace('.HK', '').replace('.hk', '')
        return f"港股{clean_ticker}"


def _get_us_company_name(ticker: str) -> str:
    """
    获取美股公司名称

    使用预定义的美股名称映射表，如果不在映射表中则返回默认格式。

    Args:
        ticker: 美股股票代码（如 "AAPL"）

    Returns:
        str: 公司名称
    """
    upper_ticker = ticker.upper()
    company_name = US_STOCK_NAMES.get(upper_ticker, f"美股{ticker}")
    logger.debug(f"[公司名称工具] 美股名称映射: {ticker} -> {company_name}")
    return company_name


def add_us_stock_name(ticker: str, name: str) -> None:
    """
    动态添加美股名称映射

    Args:
        ticker: 美股股票代码
        name: 公司中文名称
    """
    US_STOCK_NAMES[ticker.upper()] = name
    logger.info(f"[公司名称工具] 添加美股名称映射: {ticker} -> {name}")
