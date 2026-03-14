# -*- coding: utf-8 -*-
"""新闻数据服务工具函数

提供通用的数据转换和辅助功能。
"""

from typing import Union, Dict, List, Any, Optional
from datetime import datetime


def convert_objectid_to_str(data: Union[Dict, List[Dict]]) -> Union[Dict, List[Dict]]:
    """
    转换 MongoDB ObjectId 为字符串，避免 JSON 序列化错误

    Args:
        data: 单个文档或文档列表

    Returns:
        转换后的数据
    """
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and '_id' in item:
                item['_id'] = str(item['_id'])
        return data
    elif isinstance(data, dict):
        if '_id' in data:
            data['_id'] = str(data['_id'])
        return data
    return data


def parse_datetime(dt_value) -> Optional[datetime]:
    """解析日期时间

    Args:
        dt_value: 日期时间值（字符串或datetime）

    Returns:
        datetime 对象，解析失败返回当前时间
    """
    if dt_value is None:
        return None

    if isinstance(dt_value, datetime):
        return dt_value

    if isinstance(dt_value, str):
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(dt_value, fmt)
            except ValueError:
                continue

    return datetime.utcnow()


def safe_float(value) -> Optional[float]:
    """安全转换为浮点数

    Args:
        value: 任意值

    Returns:
        float 或 None
    """
    if value is None:
        return None

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def get_full_symbol(symbol: str, market: str) -> Optional[str]:
    """获取完整股票代码

    Args:
        symbol: 股票代码
        market: 市场标识

    Returns:
        完整股票代码（如 000001.SZ）
    """
    if not symbol:
        return None

    if market == "CN":
        if len(symbol) == 6:
            if symbol.startswith(('60', '68')):
                return f"{symbol}.SH"
            elif symbol.startswith(('00', '30')):
                return f"{symbol}.SZ"

    return symbol


def standardize_news_data(
    news_data: Dict[str, Any],
    data_source: str,
    market: str,
    now: datetime
) -> Dict[str, Any]:
    """标准化新闻数据

    Args:
        news_data: 原始新闻数据
        data_source: 数据源标识
        market: 市场标识
        now: 当前时间

    Returns:
        标准化后的新闻数据
    """
    symbol = news_data.get("symbol")
    symbols = news_data.get("symbols", [])

    # 如果有主要股票代码但symbols为空，添加到symbols中
    if symbol and symbol not in symbols:
        symbols = [symbol] + symbols

    return {
        # 基础信息
        "symbol": symbol,
        "full_symbol": get_full_symbol(symbol, market) if symbol else None,
        "market": market,
        "symbols": symbols,

        # 新闻内容
        "title": news_data.get("title", ""),
        "content": news_data.get("content", ""),
        "summary": news_data.get("summary", ""),
        "url": news_data.get("url", ""),
        "source": news_data.get("source", ""),
        "author": news_data.get("author", ""),

        # 时间信息
        "publish_time": parse_datetime(news_data.get("publish_time")),

        # 分类和标签
        "category": news_data.get("category", "general"),
        "sentiment": news_data.get("sentiment", "neutral"),
        "sentiment_score": safe_float(news_data.get("sentiment_score")),
        "keywords": news_data.get("keywords", []),
        "importance": news_data.get("importance", "medium"),

        # 元数据
        "data_source": data_source,
        "created_at": now,
        "updated_at": now,
        "version": 1
    }
