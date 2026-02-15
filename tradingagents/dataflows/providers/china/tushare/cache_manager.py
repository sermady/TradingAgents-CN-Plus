# -*- coding: utf-8 -*-
"""
批量行情缓存管理模块

提供批量实时行情数据的缓存机制，减少API调用次数。
"""

from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

# 全局批量行情缓存
BATCH_QUOTES_CACHE: Dict[str, Any] = {"data": None, "timestamp": None, "_lock": None}

# 缓存有效期（秒）
BATCH_CACHE_TTL_SECONDS = 30


def _get_batch_cache_lock() -> asyncio.Lock:
    """获取或创建异步锁（线程安全）"""
    if BATCH_QUOTES_CACHE["_lock"] is None:
        # 创建新的异步锁
        BATCH_QUOTES_CACHE["_lock"] = asyncio.Lock()
    return BATCH_QUOTES_CACHE["_lock"]


def _is_batch_cache_valid() -> bool:
    """检查批量缓存是否有效"""
    if BATCH_QUOTES_CACHE["data"] is None or BATCH_QUOTES_CACHE["timestamp"] is None:
        return False
    age = (datetime.now() - BATCH_QUOTES_CACHE["timestamp"]).total_seconds()
    return age < BATCH_CACHE_TTL_SECONDS


def _get_cached_batch_quotes() -> Optional[Dict[str, Dict[str, Any]]]:
    """获取缓存的批量行情"""
    if _is_batch_cache_valid():
        return BATCH_QUOTES_CACHE["data"]
    return None


async def _set_cached_batch_quotes(data: Dict[str, Dict[str, Any]]) -> None:
    """设置批量行情缓存（异步版本）"""
    lock = _get_batch_cache_lock()
    async with lock:
        BATCH_QUOTES_CACHE["data"] = data
        BATCH_QUOTES_CACHE["timestamp"] = datetime.now()


async def _invalidate_batch_cache() -> None:
    """使批量缓存失效（异步版本）"""
    lock = _get_batch_cache_lock()
    async with lock:
        BATCH_QUOTES_CACHE["data"] = None
        BATCH_QUOTES_CACHE["timestamp"] = None
