# -*- coding: utf-8 -*-
"""
Composite Providers Module

提供组合式的数据提供器，封装多个底层数据源的组合逻辑。
这是 DataSourceManager 重构的一部分。

Available Providers:
- RealtimeQuoteProvider: 实时行情数据提供器
"""

from .realtime_quote_provider import RealtimeQuoteProvider, get_realtime_quote_provider

__all__ = [
    "RealtimeQuoteProvider",
    "get_realtime_quote_provider",
]
