# -*- coding: utf-8 -*-
"""
AKShare统一数据提供器

基于AKShare SDK的统一数据同步方案，提供标准化的数据接口

此文件为入口文件，实际实现已拆分到 akshare/ 子模块中：
- akshare/cache_manager.py    - 缓存管理
- akshare/base_provider.py    - 基类和初始化
- akshare/basic_data.py       - 股票基础信息
- akshare/realtime_data.py    - 实时行情数据
- akshare/historical_data.py  - 历史行情数据
- akshare/financial_data.py   - 财务数据
- akshare/news_data.py        - 新闻数据

向后兼容说明：
所有原有导入路径保持不变，此模块导出所有公共API
"""

# 从子模块导入所有公共API，保持向后兼容
from .akshare.cache_manager import (
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
from .akshare.base_provider import AKShareProvider
from .akshare import get_akshare_provider

__all__ = [
    # 缓存管理
    "AKSHARE_QUOTES_CACHE",
    "AKSHARE_CACHE_TTL",
    "AKSHARE_CACHE_LOCK",
    "_get_akshare_cached_quote",
    "_get_akshare_cached_quote_async",
    "_set_akshare_cached_quote",
    "_set_akshare_cached_quote_async",
    "_clean_akshare_expired_cache",
    "_clear_all_akshare_cache",
    # 主类
    "AKShareProvider",
    "get_akshare_provider",
]
