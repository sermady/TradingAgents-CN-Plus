# -*- coding: utf-8 -*-
"""
股票信息标准化工具

提供统一的股票信息标准化函数，用于消除各worker服务中的重复代码。
"""

from typing import Dict, Optional


# 市场默认值配置
MARKET_DEFAULTS = {
    "hk": {
        "currency": "HKD",
        "exchange": "HKEX",
        "market": "香港交易所",
        "area": "香港",
    },
    "us": {
        "currency": "USD",
        "exchange": "NASDAQ",
        "market": "美国市场",
        "area": "美国",
    },
    "cn": {
        "currency": "CNY",
        "exchange": "SSE",
        "market": "上海证券交易所",
        "area": "中国大陆",
    },
}


def normalize_stock_info(
    stock_info: Dict,
    market_type: str = "us",
    source: Optional[str] = None
) -> Dict:
    """
    统一的股票信息标准化函数

    Args:
        stock_info: 原始股票信息字典
        market_type: 市场类型 ('hk'=港股, 'us'=美股, 'cn'=A股)
        source: 数据源（可选，用于日志记录）

    Returns:
        标准化后的股票信息字典

    示例:
        >>> info = {"name": "腾讯", "industry": "科技"}
        >>> normalized = normalize_stock_info(info, market_type="hk")
        >>> print(normalized['currency'])
        'HKD'
        >>> print(normalized['market'])
        '香港交易所'
    """
    # 获取市场默认值
    defaults = MARKET_DEFAULTS.get(market_type.lower(), MARKET_DEFAULTS["us"])

    # 构建标准化信息
    normalized = {
        "name": stock_info.get("name", ""),
        "currency": stock_info.get("currency", defaults["currency"]),
        "exchange": stock_info.get("exchange", defaults["exchange"]),
        "market": stock_info.get("market", defaults["market"]),
        "area": stock_info.get("area", defaults["area"]),
    }

    # 可选字段（如果存在且有值则添加）
    optional_fields = [
        "industry",
        "sector",
        "list_date",
        "total_mv",
        "circ_mv",
        "pe",
        "pb",
        "ps",
        "pcf",
        "market_cap",
        "shares_outstanding",
        "float_shares",
        "employees",
        "website",
        "description",
        "logo",
        "hq_country",
        "hq_city",
        "found_date",
        "main_business",
    ]

    for field in optional_fields:
        if field in stock_info and stock_info[field]:
            normalized[field] = stock_info[field]

    return normalized


def normalize_stock_code(
    stock_code: str,
    market_type: str = "us"
) -> str:
    """
    统一的股票代码标准化函数

    Args:
        stock_code: 原始股票代码
        market_type: 市场类型 ('hk'=港股, 'us'=美股, 'cn'=A股)

    Returns:
        标准化后的股票代码

    示例:
        >>> normalize_stock_code(" 00700  ", market_type="hk")
        '07000'
        >>> normalize_stock_code("aapl", market_type="us")
        'AAPL'
    """
    if not stock_code:
        return stock_code

    market_type = market_type.lower()

    # 港股：去除空格，去掉前导零，补齐到5位
    if market_type == "hk":
        return stock_code.strip().lstrip('0').zfill(5)

    # 美股和其他：去除空格并转大写
    return stock_code.strip().upper()


# 导出
__all__ = [
    "normalize_stock_info",
    "normalize_stock_code",
    "MARKET_DEFAULTS",
]
