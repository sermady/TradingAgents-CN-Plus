# -*- coding: utf-8 -*-
"""
股票搜索模块
提供股票搜索相关功能
"""

import logging
from typing import List

from .stock_data import DEFAULT_STOCKS

logger = logging.getLogger(__name__)


def search_stocks(keyword: str, limit: int = 10) -> List[dict]:
    """根据关键词搜索股票

    支持按股票代码、股票名称、行业、地区搜索。
    搜索不区分大小写。

    Args:
        keyword: 搜索关键词
        limit: 最大返回结果数

    Returns:
        匹配的股票信息列表
    """
    if not keyword:
        return []

    keyword = keyword.lower()
    results = []

    for stock in DEFAULT_STOCKS:
        # 检查各个字段是否匹配
        if (
            keyword in stock["code"].lower()
            or keyword in stock["name"].lower()
            or keyword in stock.get("industry", "").lower()
            or keyword in stock.get("area", "").lower()
            or keyword in stock.get("ts_code", "").lower()
        ):
            results.append(stock)
            if len(results) >= limit:
                break

    return results


def search_by_industry(industry: str) -> List[dict]:
    """按行业搜索股票

    Args:
        industry: 行业名称（如 "银行"、"医药"）

    Returns:
        该行业的所有股票
    """
    industry = industry.lower()
    return [
        stock for stock in DEFAULT_STOCKS
        if industry in stock.get("industry", "").lower()
    ]


def search_by_area(area: str) -> List[dict]:
    """按地区搜索股票

    Args:
        area: 地区名称（如 "深圳"、"北京"）

    Returns:
        该地区的所有股票
    """
    area = area.lower()
    return [
        stock for stock in DEFAULT_STOCKS
        if area in stock.get("area", "").lower()
    ]


def get_stocks_by_market(market: str) -> List[dict]:
    """按市场类型获取股票

    Args:
        market: 市场类型（如 "主板"、"创业板"、"中小板"）

    Returns:
        该市场的所有股票
    """
    return [
        stock for stock in DEFAULT_STOCKS
        if stock.get("market") == market
    ]


def get_all_industries() -> List[str]:
    """获取所有行业列表

    Returns:
        去重后的行业名称列表
    """
    industries = {stock.get("industry", "") for stock in DEFAULT_STOCKS}
    return sorted(industries - {""})


def get_all_areas() -> List[str]:
    """获取所有地区列表

    Returns:
        去重后的地区名称列表
    """
    areas = {stock.get("area", "") for stock in DEFAULT_STOCKS}
    return sorted(areas - {""})
