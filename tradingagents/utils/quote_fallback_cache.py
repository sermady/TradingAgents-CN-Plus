# -*- coding: utf-8 -*-
"""
行情兜底缓存模块（支持异步）

当实时行情请求失败时，提供最后有效报价的缓存兜底机制。
确保系统在高延迟或网络不稳定情况下仍能返回可用的旧数据。

🔥 修复：添加 asyncio.Lock 支持，避免在异步代码中阻塞事件循环
- 保留 threading.Lock 供同步代码使用
- 新增异步方法使用 asyncio.Lock
- 混合场景下自动检测并使用合适的锁
"""

import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_TTL = 300
STALE_THRESHOLD = 600


class QuoteFallbackCache:
    """
    行情兜底缓存（线程安全 + 异步安全）

    特性：
    - 存储最后有效的行情数据
    - 支持TTL过期机制
    - 线程安全（threading.Lock）
    - 异步安全（asyncio.Lock）
    - 可配置过期阈值（用于判断缓存是否"过于陈旧"）
    """

    def __init__(self, ttl: int = DEFAULT_TTL, stale_threshold: int = STALE_THRESHOLD):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, float] = {}
        # 🔥 修复：同时支持同步和异步锁
        self._thread_lock = threading.Lock()
        self._async_lock: Optional[asyncio.Lock] = None
        self._ttl = ttl
        self._stale_threshold = stale_threshold

    def _get_async_lock(self) -> asyncio.Lock:
        """获取或创建异步锁（延迟初始化）"""
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        return self._async_lock

    def set(self, code: str, data: Dict[str, Any]) -> None:
        """存储行情数据（同步版本，使用 thread锁）"""
        with self._thread_lock:
            self._cache[code] = data.copy()
            self._cache[code]["_cached_at"] = datetime.now().isoformat()
            self._cache[code]["_cache_timestamp"] = time.time()
            self._timestamps[code] = time.time()

    async def set_async(self, code: str, data: Dict[str, Any]) -> None:
        """存储行情数据（异步版本，使用 asyncio锁）"""
        async with self._get_async_lock():
            self._cache[code] = data.copy()
            self._cache[code]["_cached_at"] = datetime.now().isoformat()
            self._cache[code]["_cache_timestamp"] = time.time()
            self._timestamps[code] = time.time()

    def get(self, code: str) -> Optional[Dict[str, Any]]:
        """获取缓存的行情数据（同步版本）"""
        with self._thread_lock:
            return self._get_impl(code)

    async def get_async(self, code: str) -> Optional[Dict[str, Any]]:
        """获取缓存的行情数据（异步版本）"""
        async with self._get_async_lock():
            return self._get_impl(code)

    def _get_impl(self, code: str) -> Optional[Dict[str, Any]]:
        """实际获取逻辑（无锁，内部使用）"""
        if code not in self._cache:
            return None

        now = time.time()
        timestamp = self._timestamps.get(code, 0)

        # 检查是否过期
        if now - timestamp > self._ttl:
            # 过期但可能还能用（stale数据）
            if now - timestamp > self._stale_threshold:
                logger.warning(
                    f"缓存数据过于陈旧: {code}, 年龄: {now - timestamp:.0f}s"
                )
                return None
            else:
                # 返回陈旧数据但标记
                data = self._cache[code].copy()
                data["_stale"] = True
                data["_stale_seconds"] = now - timestamp
                return data

        # 返回有效数据
        return self._cache[code].copy()

    def is_stale(self, code: str) -> bool:
        """检查缓存是否陈旧（同步版本）"""
        with self._thread_lock:
            return self._is_stale_impl(code)

    async def is_stale_async(self, code: str) -> bool:
        """检查缓存是否陈旧（异步版本）"""
        async with self._get_async_lock():
            return self._is_stale_impl(code)

    def _is_stale_impl(self, code: str) -> bool:
        """实际检查逻辑（无锁）"""
        if code not in self._cache:
            return True

        now = time.time()
        timestamp = self._timestamps.get(code, 0)
        return (now - timestamp) > self._ttl

    def clear(self, code: str = None) -> None:
        """清除缓存（同步版本）"""
        with self._thread_lock:
            self._clear_impl(code)

    async def clear_async(self, code: str = None) -> None:
        """清除缓存（异步版本）"""
        async with self._get_async_lock():
            self._clear_impl(code)

    def _clear_impl(self, code: str = None) -> None:
        """实际清除逻辑（无锁）"""
        if code:
            self._cache.pop(code, None)
            self._timestamps.pop(code, None)
        else:
            self._cache.clear()
            self._timestamps.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计（同步版本）"""
        with self._thread_lock:
            return self._get_stats_impl()

    async def get_stats_async(self) -> Dict[str, Any]:
        """获取缓存统计（异步版本）"""
        async with self._get_async_lock():
            return self._get_stats_impl()

    def _get_stats_impl(self) -> Dict[str, Any]:
        """实际统计逻辑（无锁）"""
        now = time.time()
        total = len(self._cache)
        expired = sum(
            1
            for code in self._cache
            if (now - self._timestamps.get(code, 0)) > self._ttl
        )
        stale = sum(
            1
            for code in self._cache
            if (now - self._timestamps.get(code, 0)) > self._stale_threshold
        )

        return {
            "total_cached": total,
            "expired": expired,
            "stale": stale,
            "valid": total - expired,
            "ttl_seconds": self._ttl,
            "stale_threshold": self._stale_threshold,
        }


# 全局兜底缓存实例（向后兼容）
_fallback_cache: Optional[QuoteFallbackCache] = None
_fallback_cache_lock = threading.Lock()


def get_fallback_cache() -> QuoteFallbackCache:
    """获取全局兜底缓存实例（线程安全）"""
    global _fallback_cache
    if _fallback_cache is None:
        with _fallback_cache_lock:
            if _fallback_cache is None:
                _fallback_cache = QuoteFallbackCache()
    return _fallback_cache


async def get_fallback_cache_async() -> QuoteFallbackCache:
    """获取全局兜底缓存实例（异步安全）"""
    global _fallback_cache
    if _fallback_cache is None:
        # 使用 asyncio.Lock 保护初始化
        async with asyncio.Lock():
            if _fallback_cache is None:
                _fallback_cache = QuoteFallbackCache()
    return _fallback_cache
