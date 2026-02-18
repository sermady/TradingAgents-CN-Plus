# -*- coding: utf-8 -*-
"""
统一缓存服务模块

提供多级缓存支持 (Memory > Redis > MongoDB > File)
"""

from .core import UnifiedCacheService
from .models import CacheEntry
from .utils import get_cache_service

__all__ = [
    "UnifiedCacheService",
    "CacheEntry",
    "get_cache_service",
]
