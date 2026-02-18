# -*- coding: utf-8 -*-
"""
缓存防雪崩保护模块

防止缓存失效时大量请求同时冲击后端系统
"""

import logging
from datetime import datetime, timezone
from threading import Lock
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple

from .utils import _run_async

if TYPE_CHECKING:
    from .core import UnifiedCacheService

logger = logging.getLogger(__name__)


class StampedeProtection:
    """缓存防雪崩保护器"""

    def __init__(self, early_refresh_ratio: float = 0.2, stale_ttl_tolerance: int = 30):
        """
        初始化防雪崩保护器

        Args:
            early_refresh_ratio: 早期刷新阈值（TTL剩余比例）
            stale_ttl_tolerance: 陈旧数据容忍时间（秒）
        """
        self._early_refresh_ratio = early_refresh_ratio
        self._stale_ttl_tolerance = stale_ttl_tolerance

        # 刷新锁管理
        self._refresh_locks: Dict[str, Lock] = {}
        self._refresh_locks_lock = Lock()
        self._refreshing_keys: set = set()

    def _get_refresh_lock(self, key: str) -> Lock:
        """获取指定key的刷新锁"""
        with self._refresh_locks_lock:
            if key not in self._refresh_locks:
                self._refresh_locks[key] = Lock()
            return self._refresh_locks[key]

    def _is_refreshing(self, key: str) -> bool:
        """检查指定key是否正在刷新中"""
        with self._refresh_locks_lock:
            return key in self._refreshing_keys

    def _mark_refreshing(self, key: str):
        """标记key正在刷新中"""
        with self._refresh_locks_lock:
            self._refreshing_keys.add(key)

    def _unmark_refreshing(self, key: str):
        """取消标记key正在刷新中"""
        with self._refresh_locks_lock:
            self._refreshing_keys.discard(key)

    def should_early_refresh(self, entry) -> bool:
        """
        检查是否应该提前刷新（预防雪崩）

        在TTL剩余20%时提前触发刷新，避免大量请求同时等待缓存过期
        """
        if entry.ttl <= 0:
            return False
        age = (datetime.now(timezone.utc) - entry.created_at).total_seconds()
        remaining_ratio = (entry.ttl - age) / entry.ttl
        return remaining_ratio < self._early_refresh_ratio

    def get_with_refresh(
        self,
        service: "UnifiedCacheService",
        key: str,
        refresh_func: Callable[[], Any],
        category: str = "general",
        ttl: int = 3600,
        refresh_ttl: int = 30,
        levels: Optional[list] = None,
    ) -> Tuple[Optional[Any], str]:
        """
        获取缓存值，并在需要时自动刷新（防雪崩版本）

        核心机制：
        1. 优先返回现有缓存（即使已过期，在容忍期内仍可用）
        2. 只有一个请求负责重建缓存
        3. 重建期间其他请求返回旧数据，避免等待

        Args:
            service: 缓存服务实例
            key: 缓存键
            refresh_func: 刷新函数，返回新值
            category: 缓存类别
            ttl: 缓存过期时间（秒）
            refresh_ttl: 重建锁超时时间（秒）
            levels: 缓存级别

        Returns:
            (值, 来源) - 来源可能是 "memory", "redis", "stale", "refreshed", "error"
        """
        from .models import CacheEntry

        if levels is None:
            levels = ["memory", "redis", "mongodb"]

        normalized_key = service.key_manager.normalize_key(key, category)

        # 步骤1：尝试获取现有缓存
        value, source = service.get(key, category, levels)

        if value is not None:
            # 检查是否需要提前刷新（预防性刷新）
            with service._memory_lock:
                entry = service._memory_cache.get(normalized_key)
                if entry and not self.should_early_refresh(entry):
                    # 缓存正常，无需刷新
                    return value, source

        # 步骤2：尝试获取刷新锁（只有一个请求能重建）
        refresh_lock = self._get_refresh_lock(normalized_key)
        acquired = refresh_lock.acquire(blocking=False)

        if not acquired:
            # 其他请求正在重建，返回现有值（即使过期）
            if value is not None:
                logger.debug(f"⚡ 缓存重建中，返回旧值: {normalized_key}")
                return value, f"{source}_stale"
            # 没有旧值，等待其他请求重建完成
            acquired_timeout = refresh_lock.acquire(timeout=refresh_ttl)
            if acquired_timeout:
                refresh_lock.release()
            # 再次尝试获取缓存
            value, source = service.get(key, category, levels)
            if value is not None:
                return value, source
            return None, "timeout"

        # 步骤3：获得锁，执行重建
        try:
            self._mark_refreshing(normalized_key)
            logger.info(f"🔄 缓存重建: {normalized_key}")

            # 执行刷新函数
            new_value = refresh_func()

            if new_value is not None:
                # 保存新缓存
                service.set(key, new_value, ttl, category, levels)
                return new_value, "refreshed"
            else:
                # 刷新失败，返回旧值
                if value is not None:
                    logger.warning(f"⚠️ 刷新失败，使用旧值: {normalized_key}")
                    return value, f"{source}_stale"
                return None, "error"

        except Exception as e:
            logger.error(f"❌ 缓存重建异常 {normalized_key}: {e}")
            # 异常时返回旧值
            if value is not None:
                return value, f"{source}_stale"
            return None, "error"
        finally:
            self._unmark_refreshing(normalized_key)
            refresh_lock.release()
