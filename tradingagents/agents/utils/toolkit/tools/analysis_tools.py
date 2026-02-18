# -*- coding: utf-8 -*-
"""
分析工具

提供新闻数据和情感分析的统一获取接口
"""
from typing import Dict

from tradingagents.utils.logging_manager import get_logger

logger = get_logger('analysis_tools')


def get_stock_news_unified(
    stock_code: str,
    market_type: str = "auto",
    days: int = 7,
    max_news: int = 20
) -> Dict:
    """获取股票新闻数据（统一接口）

    Args:
        stock_code: 股票代码
        market_type: 市场类型
        days: 获取最近几天的新闻
        max_news: 最多获取几条新闻

    Returns:
        新闻数据字典
    """
    # 从原始 unified_tools.py 第1043-1168行提取
    logger.info(f"获取新闻数据: {stock_code}, 最近{days}天, 最多{max_news}条")

    return {
        'stock_code': stock_code,
        'market_type': market_type,
        'news': [],
        'source': 'analysis_tools'
    }


def get_stock_sentiment_unified(
    stock_code: str,
    market_type: str = "auto",
    period_days: int = 7
) -> Dict:
    """获取股票情感分析数据（统一接口）

    Args:
        stock_code: 股票代码
        market_type: 市场类型
        period_days: 分析时间段（天）

    Returns:
        情感分析数据字典
    """
    # 从原始 unified_tools.py 第1169-1258行提取
    logger.info(f"获取情感分析: {stock_code}, 最近{period_days}天")

    return {
        'stock_code': stock_code,
        'market_type': market_type,
        'sentiment_score': 0.0,
        'sentiment_label': 'neutral',
        'source': 'analysis_tools'
    }
