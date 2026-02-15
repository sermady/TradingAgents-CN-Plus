# -*- coding: utf-8 -*-
"""
Tushare 数据提供器模块

该模块将原始的 TushareProvider 类拆分为多个子模块：
- cache_manager: 批量行情缓存管理
- base_provider: TushareProvider 基类（Token管理、连接）
- basic_data: 股票基础信息
- historical_data: 历史行情数据
- realtime_data: 实时行情数据
- financial_data: 财务数据
- news_data: 新闻数据

为了保持向后兼容，所有公共接口都通过 TushareProvider 类暴露。
"""

from .cache_manager import (
    BATCH_QUOTES_CACHE,
    BATCH_CACHE_TTL_SECONDS,
    _get_batch_cache_lock,
    _is_batch_cache_valid,
    _get_cached_batch_quotes,
    _set_cached_batch_quotes,
    _invalidate_batch_cache,
)

from .base_provider import BaseTushareProvider

from .basic_data import BasicDataMixin
from .historical_data import HistoricalDataMixin
from .realtime_data import RealtimeDataMixin
from .financial_data import FinancialDataMixin
from .news_data import NewsDataMixin


# 组合完整的 TushareProvider 类
class TushareProvider(
    BasicDataMixin,
    HistoricalDataMixin,
    RealtimeDataMixin,
    FinancialDataMixin,
    NewsDataMixin,
    BaseTushareProvider,
):
    """
    统一的Tushare数据提供器
    合并app层和tradingagents层的所有优势功能
    """

    def __init__(self):
        # 调用 MRO 中的第一个父类的 __init__
        super().__init__()


# 从 tushare.py 导入全局提供器函数
try:
    from ..tushare import get_tushare_provider
except ImportError:
    # 如果导入失败，定义一个本地版本
    _tushare_provider = None

    def get_tushare_provider() -> "TushareProvider":
        """获取全局Tushare提供器实例"""
        global _tushare_provider
        if _tushare_provider is None:
            _tushare_provider = TushareProvider()
        return _tushare_provider


# 导出公共接口
__all__ = [
    "TushareProvider",
    "BaseTushareProvider",
    "BasicDataMixin",
    "HistoricalDataMixin",
    "RealtimeDataMixin",
    "FinancialDataMixin",
    "NewsDataMixin",
    # 提供器函数
    "get_tushare_provider",
    # 缓存管理
    "BATCH_QUOTES_CACHE",
    "BATCH_CACHE_TTL_SECONDS",
    "_get_batch_cache_lock",
    "_is_batch_cache_valid",
    "_get_cached_batch_quotes",
    "_set_cached_batch_quotes",
    "_invalidate_batch_cache",
]
