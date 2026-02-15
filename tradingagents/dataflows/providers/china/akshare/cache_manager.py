# -*- coding: utf-8 -*-
"""
AKShare缓存管理模块

提供全局行情缓存功能
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# 全局缓存变量
AKSHARE_QUOTES_CACHE: Dict[str, Dict[str, Any]] = {}
AKSHARE_CACHE_TTL = 15
# 使用 asyncio.Lock 替代 threading.Lock（避免在异步代码中阻塞事件循环）
AKSHARE_CACHE_LOCK = asyncio.Lock()


def _get_akshare_cached_quote(code: str) -> Optional[Dict[str, Any]]:
    """获取AKShare单个股票行情缓存（无锁读取，用于快速检查）"""
    now = datetime.now()
    if code in AKSHARE_QUOTES_CACHE:
        cached = AKSHARE_QUOTES_CACHE[code]
        age = (now - cached["timestamp"]).total_seconds()
        if age < AKSHARE_CACHE_TTL:
            return cached["data"]
    return None


async def _get_akshare_cached_quote_async(code: str) -> Optional[Dict[str, Any]]:
    """获取AKShare单个股票行情缓存（异步版本，带锁）"""
    async with AKSHARE_CACHE_LOCK:
        return _get_akshare_cached_quote(code)
    return None


def _set_akshare_cached_quote(code: str, data: Dict[str, Any]) -> None:
    """设置AKShare单个股票行情缓存（无锁版本，用于同步上下文）"""
    AKSHARE_QUOTES_CACHE[code] = {"data": data, "timestamp": datetime.now()}


async def _set_akshare_cached_quote_async(code: str, data: Dict[str, Any]) -> None:
    """设置AKShare单个股票行情缓存（异步版本，带锁）"""
    async with AKSHARE_CACHE_LOCK:
        AKSHARE_QUOTES_CACHE[code] = {"data": data, "timestamp": datetime.now()}


def _clean_akshare_expired_cache(max_age: int = 60) -> int:
    """清理过期的AKShare缓存"""
    now = datetime.now()
    expired = []
    for code, cached in AKSHARE_QUOTES_CACHE.items():
        age = (now - cached["timestamp"]).total_seconds()
        if age > max_age:
            expired.append(code)
    for code in expired:
        del AKSHARE_QUOTES_CACHE[code]
    return len(expired)


def _clear_all_akshare_cache() -> int:
    """清空所有AKShare缓存（仅用于测试）"""
    with AKSHARE_CACHE_LOCK:
        count = len(AKSHARE_QUOTES_CACHE)
        AKSHARE_QUOTES_CACHE.clear()
    return count
