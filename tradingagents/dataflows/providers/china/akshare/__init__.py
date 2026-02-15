# -*- coding: utf-8 -*-
"""
AKShare数据提供器模块

将原akshare.py拆分为多个子模块，便于维护
"""

from .cache_manager import (
    AKSHARE_QUOTES_CACHE,
    AKSHARE_CACHE_TTL,
    AKSHARE_CACHE_LOCK,
    _get_akshare_cached_quote,
    _get_akshare_cached_quote_async,
    _set_akshare_cached_quote,
    _set_akshare_cached_quote_async,
    _clean_akshare_expired_cache,
    _clear_all_akshare_cache,
)
from .base_provider import AKShareProvider
from .basic_data import BasicDataMixin
from .realtime_data import RealtimeDataMixin
from .historical_data import HistoricalDataMixin
from .financial_data import FinancialDataMixin
from .news_data import NewsDataMixin

__all__ = [
    # Cache manager
    "AKSHARE_QUOTES_CACHE",
    "AKSHARE_CACHE_TTL",
    "AKSHARE_CACHE_LOCK",
    "_get_akshare_cached_quote",
    "_get_akshare_cached_quote_async",
    "_set_akshare_cached_quote",
    "_set_akshare_cached_quote_async",
    "_clean_akshare_expired_cache",
    "_clear_all_akshare_cache",
    # Provider
    "AKShareProvider",
    "BasicDataMixin",
    "RealtimeDataMixin",
    "HistoricalDataMixin",
    "FinancialDataMixin",
    "NewsDataMixin",
    "get_akshare_provider",
]


# 全局提供器实例
_akshare_provider = None


def get_akshare_provider():
    """获取全局AKShare提供器实例"""
    global _akshare_provider
    if _akshare_provider is None:
        _akshare_provider = AKShareProvider()
    return _akshare_provider
