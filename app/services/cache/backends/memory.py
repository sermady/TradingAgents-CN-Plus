# -*- coding: utf-8 -*-
"""
内存缓存后端

提供线程安全的内存缓存实现
"""

import logging
from threading import Lock
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

if TYPE_CHECKING:
    from ..stats import CacheStats
    from ..models import CacheEntry

logger = logging.getLogger(__name__)


class MemoryBackend:
    """内存缓存后端"""

    def __init__(self, stats: "CacheStats"):
        """
        初始化内存缓存后端

        Args:
            stats: 缓存统计管理器
        """
        self._cache: Dict[str, "CacheEntry"] = {}
        self._lock = Lock()
        self._stats = stats

    def get(self, key: str) -> Tuple[Optional[Any], str]:
        """
        从内存获取缓存

        Args:
            key: 缓存键

        Returns:
            (值, 来源)
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired():
                    entry.hit_count += 1
                    self._stats.increment("hits")
                    logger.debug(f"📦 内存缓存命中: {key}")
                    return entry.value, "memory"
                else:
                    del self._cache[key]
                    self._stats.increment("expires")
            self._stats.increment("misses")
            return None, "memory"

    def set(self, key: str, value: Any, ttl: int = 3600, category: str = "general"):
        """
        设置内存缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
            category: 缓存类别
        """
        from ..models import CacheEntry

        with self._lock:
            self._cache[key] = CacheEntry(
                key=key, value=value, ttl=ttl, source="memory"
            )
            self._stats.increment("sets")
            logger.debug(f"💾 设置内存缓存: {key} (TTL: {ttl}s)")

    def delete(self, key: str) -> bool:
        """
        删除内存缓存

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.increment("deletes")
                return True
        return False

    def clear_category(self, category: str) -> int:
        """
        清除指定类别的缓存

        Args:
            category: 缓存类别

        Returns:
            清除的缓存数量
        """
        with self._lock:
            keys_to_delete = [
                k for k in self._cache if k.startswith(category + ":")
            ]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)

    def get_entry(self, key: str) -> Optional["CacheEntry"]:
        """
        获取缓存条目（用于检查早期刷新）

        Args:
            key: 缓存键

        Returns:
            缓存条目，如果不存在则返回None
        """
        with self._lock:
            return self._cache.get(key)

    def __len__(self) -> int:
        """返回内存缓存中的条目数量"""
        return len(self._cache)
