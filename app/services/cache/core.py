# -*- coding: utf-8 -*-
"""
统一缓存服务核心模块

整合多级缓存后端，提供统一的缓存接口
"""

import logging
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings

from .backends.file import FileBackend
from .backends.memory import MemoryBackend
from .backends.mongodb import MongoDBBackend
from .backends.redis import RedisBackend
from .key_manager import KeyManager
from .models import CacheEntry
from .stampede_protection import StampedeProtection
from .stats import CacheStats

logger = logging.getLogger(__name__)


class UnifiedCacheService:
    """
    统一缓存服务

    支持多级缓存:
    1. 内存缓存 (最快)
    2. Redis缓存 (分布式)
    3. MongoDB缓存 (持久化)
    4. File缓存 (持久化)
    """

    _instance: Optional["UnifiedCacheService"] = None
    _lock: Lock = Lock()

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 键管理器
        self.key_manager = KeyManager()

        # 统计管理器
        self._stats = CacheStats()

        # 后端实例
        self._memory = MemoryBackend(self._stats)
        self._redis = RedisBackend(self._stats)
        self._mongodb = MongoDBBackend(
            self._stats,
            db_name=settings.MONGODB_DATABASE,
            collection="cache_store"
        )
        self._file = FileBackend(self._stats)

        # 防雪崩保护
        self._stampede = StampedeProtection()

        # 用于内部锁访问
        self._memory_lock = self._memory._lock

        self._initialized = True
        logger.info("✅ 统一缓存服务初始化完成（含防雪崩保护）")

    # ==================== 统一接口 ====================

    def get(
        self, key: str, category: str = "general", levels: Optional[List[str]] = None
    ) -> Tuple[Optional[Any], str]:
        """
        获取缓存值

        Args:
            key: 缓存键
            category: 缓存类别
            levels: 缓存级别 ["memory", "redis", "mongodb", "file"]

        Returns:
            (值, 来源)
        """
        if levels is None:
            levels = ["memory", "redis", "mongodb", "file"]

        key = self.key_manager.normalize_key(key, category)

        for level in levels:
            if level == "memory":
                value, source = self._memory.get(key)
            elif level == "redis":
                value, source = self._redis.get(key)
            elif level == "mongodb":
                value, source = self._mongodb.get(key)
            elif level == "file":
                value, source = self._file.get(key)
            else:
                continue

            if value is not None:
                # 回填到更快的缓存
                if level != "memory" and "memory" in levels:
                    self._memory.set(key, value, ttl=300, category=category)
                return value, source

        return None, "none"

    def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
        category: str = "general",
        levels: Optional[List[str]] = None,
    ):
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间(秒)
            category: 缓存类别
            levels: 缓存级别
        """
        if levels is None:
            levels = ["memory", "redis", "mongodb", "file"]

        key = self.key_manager.normalize_key(key, category)

        for level in levels:
            if level == "memory":
                self._memory.set(key, value, ttl, category)
            elif level == "redis":
                self._redis.set(key, value, ttl, category)
            elif level == "mongodb":
                self._mongodb.set(key, value, ttl, category)
            elif level == "file":
                self._file.set(key, value, ttl, category)

    def delete(
        self, key: str, category: str = "general", levels: Optional[List[str]] = None
    ) -> int:
        """
        删除缓存

        Args:
            key: 缓存键
            category: 缓存类别
            levels: 缓存级别

        Returns:
            删除的缓存数量
        """
        if levels is None:
            levels = ["memory", "redis", "mongodb", "file"]

        key = self.key_manager.normalize_key(key, category)

        deleted = 0
        for level in levels:
            if level == "memory" and self._memory.delete(key):
                deleted += 1
            elif level == "redis" and self._redis.delete(key):
                deleted += 1
            elif level == "mongodb" and self._mongodb.delete(key):
                deleted += 1

        logger.info(f"🗑️ 删除缓存: {key} ({deleted}个级别)")
        return deleted

    def clear_category(self, category: str, levels: Optional[List[str]] = None) -> int:
        """
        清除类别缓存

        Args:
            category: 缓存类别
            levels: 缓存级别

        Returns:
            清除的缓存数量
        """
        if levels is None:
            levels = ["memory", "redis", "mongodb"]

        deleted = 0

        if "memory" in levels:
            deleted += self._memory.clear_category(category)

        if "mongodb" in levels:
            deleted += self._mongodb.clear_category(category)

        if "redis" in levels:
            deleted += self._redis.clear_category(category)

        logger.info(f"🗑️ 清除类别缓存: {category} ({deleted}个)")
        return deleted

    # ==================== 高级功能 ====================

    def get_with_refresh(
        self,
        key: str,
        refresh_func,
        category: str = "general",
        ttl: int = 3600,
        refresh_ttl: int = 30,
        levels: Optional[List[str]] = None,
    ) -> Tuple[Optional[Any], str]:
        """
        获取缓存值，并在需要时自动刷新（防雪崩版本）

        Args:
            key: 缓存键
            refresh_func: 刷新函数
            category: 缓存类别
            ttl: 缓存过期时间
            refresh_ttl: 重建锁超时时间
            levels: 缓存级别

        Returns:
            (值, 来源)
        """
        return self._stampede.get_with_refresh(
            self, key, refresh_func, category, ttl, refresh_ttl, levels
        )

    def get_or_set_with_fallback(
        self,
        key: str,
        factory_func,
        category: str = "general",
        ttl: int = 3600,
        fallback_value: Any = None,
        fallback_ttl: int = 60,
        max_retries: int = 3,
        levels: Optional[List[str]] = None,
    ) -> Tuple[Any, str]:
        """获取或设置缓存，带缓存击穿保护"""
        if levels is None:
            levels = ["memory", "redis", "mongodb"]

        # 步骤1：尝试获取现有缓存
        value, source = self.get(key, category, levels)

        if value is not None:
            return value, source

        # 步骤2：使用防雪崩机制重建缓存
        normalized_key = self.key_manager.normalize_key(key, category)
        refresh_lock = self._stampede._get_refresh_lock(normalized_key)
        acquired = refresh_lock.acquire(blocking=False)

        if not acquired:
            # 其他请求正在重建，等待后重试
            logger.debug(f"⏳ 等待缓存重建: {normalized_key}")
            acquired_timeout = refresh_lock.acquire(timeout=fallback_ttl)
            if acquired_timeout:
                refresh_lock.release()

            # 再次尝试获取
            value, source = self.get(key, category, levels)
            if value is not None:
                return value, source
            # 仍然没有，使用兜底值
            if fallback_value is not None:
                logger.warning(f"⚠️ 使用兜底值: {normalized_key}")
                return fallback_value, "fallback"
            return None, "error"

        # 步骤3：获得锁，尝试重建
        try:
            self._stampede._mark_refreshing(normalized_key)

            # 重试机制
            for attempt in range(max_retries):
                try:
                    logger.info(
                        f"🔄 缓存重建尝试 {attempt + 1}/{max_retries}: {normalized_key}"
                    )
                    new_value = factory_func()

                    if new_value is not None:
                        # 重建成功，保存正常缓存
                        self.set(key, new_value, ttl, category, levels)
                        return new_value, "refreshed"

                    # 工厂函数返回None，短暂等待后重试
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(0.5 * (attempt + 1))

                except Exception as e:
                    logger.error(f"❌ 重建尝试 {attempt + 1} 失败: {e}")
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(0.5 * (attempt + 1))

            # 所有重试都失败，使用兜底值
            if fallback_value is not None:
                logger.warning(f"⚠️ 重建失败，使用兜底值: {normalized_key}")
                # 设置短时效缓存，防止持续冲击
                self.set(key, fallback_value, fallback_ttl, category, levels)
                return fallback_value, "fallback"

            return None, "error"

        finally:
            self._stampede._unmark_refreshing(normalized_key)
            refresh_lock.release()

    def set_circuit_breaker(
        self,
        key: str,
        is_fail: bool,
        category: str = "general",
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
    ) -> bool:
        """设置熔断器状态（简化版缓存击穿保护）"""
        from datetime import datetime, timezone

        cb_key = f"_circuit_breaker:{category}:{key}"

        # 获取当前熔断器状态
        state, _ = self.get(cb_key, "_internal", ["memory"])

        if state is None:
            state = {"failures": 0, "last_failure": None, "open": False}

        if is_fail:
            state["failures"] += 1
            state["last_failure"] = datetime.now(timezone.utc).isoformat()

            if state["failures"] >= failure_threshold:
                state["open"] = True
                logger.warning(f"🔥 熔断器开启: {key} (连续{state['failures']}次失败)")
        else:
            # 成功，减少失败计数
            if state["failures"] > 0:
                state["failures"] -= 1

            # 如果熔断器开启，检查是否可以关闭
            if state["open"] and state["last_failure"]:
                last_fail = datetime.fromisoformat(state["last_failure"])
                elapsed = (datetime.now(timezone.utc) - last_fail).total_seconds()
                if elapsed > recovery_timeout:
                    state["open"] = False
                    state["failures"] = 0
                    logger.info(f"✅ 熔断器关闭: {key} (已恢复{elapsed:.0f}秒)")

        # 保存熔断器状态（短时效）
        self.set(cb_key, state, 300, "_internal", ["memory"])

        return state["open"]

    # ==================== 统计 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return self._stats.get_stats(memory_cache_size=len(self._memory))

    def reset_stats(self):
        """重置统计"""
        self._stats.reset()
