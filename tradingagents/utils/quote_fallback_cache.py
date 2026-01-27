# -*- coding: utf-8 -*-
"""
行情兜底缓存模块

当实时行情请求失败时，提供最后有效报价的缓存兜底机制。
确保系统在高延迟或网络不稳定情况下仍能返回可用的旧数据。
"""

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
    行情兜底缓存

    特性：
    - 存储最后有效的行情数据
    - 支持TTL过期机制
    - 线程安全
    - 可配置过期阈值（用于判断缓存是否"过于陈旧"）
    """

    def __init__(self, ttl: int = DEFAULT_TTL, stale_threshold: int = STALE_THRESHOLD):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._ttl = ttl
        self._stale_threshold = stale_threshold

    def set(self, code: str, data: Dict[str, Any]) -> None:
        """存储行情数据（带时间戳）"""
        with self._lock:
            self._cache[code] = data.copy()
            self._cache[code]["_cached_at"] = datetime.now().isoformat()
            self._cache[code]["_cache_timestamp"] = time.time()
            self._timestamps[code] = time.time()

    def get(self, code: str) -> Optional[Dict[str, Any]]:
        """获取缓存的行情数据"""
        with self._lock:
            if code not in self._cache:
                return None

            timestamp = self._timestamps.get(code, 0)
            age = time.time() - timestamp

            if age > self._ttl:
                del self._cache[code]
                del self._timestamps[code]
                return None

            return self._cache[code].copy()

    def get_with_stale_info(self, code: str) -> tuple[Optional[Dict[str, Any]], bool]:
        """
        获取缓存的行情数据，同时返回是否过期的信息

        Returns:
            (data, is_stale): 数据字典和是否过期标记
        """
        with self._lock:
            if code not in self._cache:
                return None, True

            timestamp = self._timestamps.get(code, 0)
            age = time.time() - timestamp
            is_stale = age > self._stale_threshold

            if age > self._ttl:
                del self._cache[code]
                del self._timestamps[code]
                return None, True

            result = self._cache[code].copy()
            result["_is_stale"] = is_stale
            result["_age_seconds"] = age
            return result, is_stale

    def get_last_valid(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取最后有效的报价（即使已过期）

        用于在网络完全失败时返回兜底数据
        """
        with self._lock:
            if code not in self._cache:
                return None

            data = self._cache[code].copy()
            timestamp = self._timestamps.get(code, 0)
            age = time.time() - timestamp
            data["_age_seconds"] = age
            data["_is_stale"] = True
            return data

    def is_stale(self, code: str) -> bool:
        """检查缓存是否过期（超过TTL）"""
        with self._lock:
            if code not in self._timestamps:
                return True
            age = time.time() - self._timestamps[code]
            return age > self._ttl

    def is_very_stale(self, code: str) -> bool:
        """检查缓存是否非常陈旧（超过stale_threshold）"""
        with self._lock:
            if code not in self._timestamps:
                return True
            age = time.time() - self._timestamps[code]
            return age > self._stale_threshold

    def update_from_quotes(self, quotes_map: Dict[str, Dict[str, Any]]) -> int:
        """
        从行情映射更新缓存

        Args:
            quotes_map: 股票代码到行情数据的映射

        Returns:
            更新的股票数量
        """
        count = 0
        with self._lock:
            for code, data in quotes_map.items():
                self._cache[code] = data.copy()
                self._cache[code]["_cached_at"] = datetime.now().isoformat()
                self._cache[code]["_cache_timestamp"] = time.time()
                self._timestamps[code] = time.time()
                count += 1
        return count

    def get_stale_codes(self) -> list[tuple[str, float]]:
        """获取所有陈旧缓存的代码和年龄"""
        now = time.time()
        stale = []
        with self._lock:
            for code, timestamp in self._timestamps.items():
                age = now - timestamp
                if age > self._ttl:
                    stale.append((code, age))
        return stale

    def cleanup(self) -> int:
        """清理过期缓存"""
        count = 0
        now = time.time()
        with self._lock:
            expired = [
                code for code, ts in self._timestamps.items() if now - ts > self._ttl
            ]
            for code in expired:
                del self._cache[code]
                del self._timestamps[code]
                count += 1
        if count > 0:
            logger.debug(f"清理了 {count} 条过期缓存")
        return count

    def clear(self) -> int:
        """清空所有缓存"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._timestamps.clear()
        return count

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            now = time.time()
            ages = [now - ts for ts in self._timestamps.values()]
            return {
                "total_codes": len(self._cache),
                "fresh_count": sum(1 for a in ages if a <= self._ttl),
                "stale_count": sum(
                    1 for a in ages if self._ttl < a <= self._stale_threshold
                ),
                "very_stale_count": sum(1 for a in ages if a > self._stale_threshold),
                "ttl_seconds": self._ttl,
                "stale_threshold_seconds": self._stale_threshold,
            }


_fallback_cache = None
_fallback_cache_lock = threading.Lock()


def get_fallback_cache() -> QuoteFallbackCache:
    """获取全局兜底缓存单例"""
    global _fallback_cache
    if _fallback_cache is None:
        with _fallback_cache_lock:
            if _fallback_cache is None:
                _fallback_cache = QuoteFallbackCache()
    return _fallback_cache


def update_fallback_cache_from_manager(quotes_map: Dict[str, Dict[str, Any]]) -> None:
    """从行情管理器更新兜底缓存"""
    cache = get_fallback_cache()
    count = cache.update_from_quotes(quotes_map)
    if count > 0:
        logger.debug(f"更新兜底缓存: {count} 只股票")


def get_fallback_quote(code: str) -> tuple[Optional[Dict[str, Any]], str]:
    """
    获取兜底行情

    Returns:
        (data, status): 数据和状态描述
        - status: "fresh" | "stale" | "very_stale" | "not_found"
    """
    cache = get_fallback_cache()
    data, is_stale = cache.get_with_stale_info(code)

    if data is None:
        return None, "not_found"

    if not is_stale:
        return data, "fresh"

    is_very_stale = cache.is_very_stale(code)
    if is_very_stale:
        return data, "very_stale"

    return data, "stale"
