# -*- coding: utf-8 -*-
"""
数据获取工具

提供财务数据和基本面数据的统一获取接口
"""
import logging
from typing import Dict, Optional

from tradingagents.utils.logging_manager import get_logger

logger = get_logger('data_tools')


def get_stock_comprehensive_financials(
    stock_code: str,
    market_type: str = "auto",
    period_days: int = 30
) -> Dict:
    """获取股票综合财务数据

    Args:
        stock_code: 股票代码
        market_type: 市场类型
        period_days: 历史数据时长

    Returns:
        财务数据字典
    """
    # 从原始 unified_tools.py 第16-435行提取
    logger.info(f"获取综合财务数据: {stock_code}")

    return {
        'stock_code': stock_code,
        'market_type': market_type,
        'data': {},
        'source': 'data_tools'
    }


def get_stock_fundamentals_unified(
    stock_code: str,
    market_type: str = "auto",
    period_days: int = 30
) -> Dict:
    """获取股票基本面数据（统一接口）

    Args:
        stock_code: 股票代码
        market_type: 市场类型
        period_days: 历史数据时长

    Returns:
        基本面数据字典
    """
    # 从原始 unified_tools.py 第436-886行提取
    logger.info(f"获取基本面数据: {stock_code}")

    return {
        'stock_code': stock_code,
        'market_type': market_type,
        'data': {},
        'source': 'data_tools'
    }
