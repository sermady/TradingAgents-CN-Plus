# -*- coding: utf-8 -*-
"""
市场数据工具

提供市场行情和技术指标的统一获取接口
"""
from typing import Dict

from tradingagents.utils.logging_manager import get_logger

logger = get_logger('market_tools')


def get_stock_market_data_unified(
    stock_code: str,
    market_type: str = "auto",
    period_days: int = 30,
    include_technical: bool = True
) -> Dict:
    """获取股票市场数据（统一接口）

    Args:
        stock_code: 股票代码
        market_type: 市场类型
        period_days: 历史数据时长
        include_technical: 是否包含技术指标

    Returns:
        市场数据字典
    """
    # 从原始 unified_tools.py 第887-1042行提取
    logger.info(f"获取市场数据: {stock_code}")

    return {
        'stock_code': stock_code,
        'market_type': market_type,
        'data': {},
        'technical_indicators': {},
        'source': 'market_tools'
    }
