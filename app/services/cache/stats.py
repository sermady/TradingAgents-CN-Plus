# -*- coding: utf-8 -*-
"""
缓存统计模块
"""

import logging
from threading import Lock
from typing import Any, Dict

logger = logging.getLogger(__name__)


class CacheStats:
    """缓存统计管理器"""

    def __init__(self):
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "expires": 0,
        }
        self._stats_lock = Lock()

    def increment(self, stat: str):
        """增加统计计数"""
        with self._stats_lock:
            if stat in self._stats:
                self._stats[stat] += 1

    def get_stats(self, memory_cache_size: int = 0) -> Dict[str, Any]:
        """
        获取缓存统计

        Args:
            memory_cache_size: 当前内存缓存大小

        Returns:
            统计信息字典
        """
        with self._stats_lock:
            stats = self._stats.copy()

        total = stats["hits"] + stats["misses"]
        hit_rate = (stats["hits"] / total * 100) if total > 0 else 0

        return {
            "hits": stats["hits"],
            "misses": stats["misses"],
            "sets": stats["sets"],
            "deletes": stats["deletes"],
            "expires": stats["expires"],
            "hit_rate": f"{hit_rate:.2f}%",
            "memory_cache_size": memory_cache_size,
        }

    def reset(self):
        """重置统计"""
        with self._stats_lock:
            self._stats = {
                "hits": 0,
                "misses": 0,
                "sets": 0,
                "deletes": 0,
                "expires": 0,
            }
        logger.info("📊 缓存统计已重置")
