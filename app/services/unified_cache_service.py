# -*- coding: utf-8 -*-
"""
统一缓存服务 (Unified Cache Service)

整合MongoDB、Redis和File缓存，提供统一的缓存接口。

特性:
- 多级缓存支持 (Redis > MongoDB > File)
- 统一的缓存键命名规范
- 自动缓存失效策略
- 缓存统计和监控
"""

import json
import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from pathlib import Path
from threading import Lock
import redis
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.core.database import get_mongo_db, get_redis_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheEntry:
    """缓存条目"""

    def __init__(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,  # 默认1小时
        source: str = "memory",
    ):
        self.key = key
        self.value = value
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.ttl = ttl
        self.source = source
        self.hit_count = 0

    def is_expired(self) -> bool:
        """检查是否过期"""
        age = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return age > self.ttl


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

        # 内存缓存
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._memory_lock = Lock()

        # Redis客户端
        self._redis_client = None
        self._redis_prefix = "tradingagents:cache:"

        # MongoDB客户端
        self._mongo_client = None
        self._mongo_db_name = settings.MONGODB_DATABASE
        self._mongo_collection = "cache_store"

        # File缓存路径
        self._file_cache_dir = Path("data/cache")
        self._file_cache_dir.mkdir(parents=True, exist_ok=True)

        # 缓存统计
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0, "expires": 0}
        self._stats_lock = Lock()

        # 防雪崩保护 (Cache Stampede Protection)
        # 使用锁字典防止同一key的并发重建
        self._refresh_locks: Dict[str, Lock] = {}
        self._refresh_locks_lock = Lock()
        # 标记正在重建中的key
        self._refreshing_keys: set = set()
        # 早期刷新阈值（在TTL剩余多少比例时提前刷新）
        self._early_refresh_ratio = 0.2
        # 陈旧数据容忍时间（即使过期也继续使用的时间，单位：秒）
        self._stale_ttl_tolerance = 30

        self._initialized = True
        logger.info("✅ 统一缓存服务初始化完成（含防雪崩保护）")

    # ==================== 键管理 ====================

    @staticmethod
    def normalize_key(key: str, category: str = "general") -> str:
        """
        规范化缓存键

        Args:
            key: 原始键
            category: 缓存类别

        Returns:
            规范化的缓存键
        """
        # 转换为小写
        key = key.lower()
        # 替换特殊字符
        key = key.replace(" ", "_").replace(":", "_").replace("-", "_")
        # 添加类别前缀
        return f"{category}:{key}"

    @staticmethod
    def generate_cache_key(category: str, *args, **kwargs) -> str:
        """
        生成缓存键

        Args:
            category: 缓存类别
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            缓存键字符串
        """
        # 序列化参数
        key_parts = [str(arg) for arg in args]
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))

        # 生成哈希
        key_str = ":".join(key_parts)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()[:16]

        return f"{category}:{key_hash}"

    # ==================== 防雪崩保护方法 ====================

    def _get_refresh_lock(self, key: str) -> Lock:
        """获取指定key的刷新锁（用于防止并发重建）"""
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

    def _should_early_refresh(self, entry: "CacheEntry") -> bool:
        """检查是否应该提前刷新（预防雪崩）

        在TTL剩余20%时提前触发刷新，避免大量请求同时等待缓存过期
        """
        if entry.ttl <= 0:
            return False
        age = (datetime.now(timezone.utc) - entry.created_at).total_seconds()
        remaining_ratio = (entry.ttl - age) / entry.ttl
        return remaining_ratio < self._early_refresh_ratio

    def get_with_refresh(
        self,
        key: str,
        refresh_func,
        category: str = "general",
        ttl: int = 3600,
        refresh_ttl: int = 30,
        levels: List[str] = None,
    ) -> Tuple[Optional[Any], str]:
        """获取缓存值，并在需要时自动刷新（防雪崩版本）

        核心机制：
        1. 优先返回现有缓存（即使已过期，在容忍期内仍可用）
        2. 只有一个请求负责重建缓存
        3. 重建期间其他请求返回旧数据，避免等待

        Args:
            key: 缓存键
            refresh_func: 刷新函数，返回新值
            category: 缓存类别
            ttl: 缓存过期时间（秒）
            refresh_ttl: 重建锁超时时间（秒）
            levels: 缓存级别

        Returns:
            (值, 来源) - 来源可能是 "memory", "redis", "stale", "refreshed", "error"
        """
        if levels is None:
            levels = ["memory", "redis", "mongodb"]

        normalized_key = self.normalize_key(key, category)

        # 步骤1：尝试获取现有缓存
        value, source = self.get(key, category, levels)

        if value is not None:
            # 检查是否需要提前刷新（预防性刷新）
            with self._memory_lock:
                entry = self._memory_cache.get(normalized_key)
                if entry and not self._should_early_refresh(entry):
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
            value, source = self.get(key, category, levels)
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
                self.set(key, new_value, ttl, category, levels)
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

    # ==================== 内存缓存 ====================

    def _get_from_memory(self, key: str) -> Tuple[Optional[Any], str]:
        """
        从内存获取缓存

        Returns:
            (值, 来源)
        """
        with self._memory_lock:
            if key in self._memory_cache:
                entry = self._memory_cache[key]
                if not entry.is_expired():
                    entry.hit_count += 1
                    self._increment_stat("hits")
                    logger.debug(f"📦 内存缓存命中: {key}")
                    return entry.value, "memory"
                else:
                    del self._memory_cache[key]
                    self._increment_stat("expires")
            self._increment_stat("misses")
            return None, "memory"

    def _set_to_memory(
        self, key: str, value: Any, ttl: int = 3600, category: str = "general"
    ):
        """设置内存缓存"""
        with self._memory_lock:
            self._memory_cache[key] = CacheEntry(
                key=key, value=value, ttl=ttl, source="memory"
            )
            self._increment_stat("sets")
            logger.debug(f"💾 设置内存缓存: {key} (TTL: {ttl}s)")

    def _delete_from_memory(self, key: str) -> bool:
        """删除内存缓存"""
        with self._memory_lock:
            if key in self._memory_cache:
                del self._memory_cache[key]
                self._increment_stat("deletes")
                return True
        return False

    # ==================== Redis缓存 ====================

    def _get_redis_client(self) -> Optional[redis.Redis]:
        """获取Redis客户端

        带健康检查和降级策略的Redis连接管理

        Returns:
            Redis客户端，如果不可用则返回None
        """
        if self._redis_client is None:
            try:
                self._redis_client = get_redis_client()

                # 健康检查：尝试ping Redis
                if self._redis_client:
                    self._redis_client.ping()
                    logger.info("✅ Redis连接成功")
                else:
                    logger.warning("⚠️ Redis连接失败: ping失败")
                    self._redis_client = None

            except redis.ConnectionError as e:
                logger.warning(f"⚠️ Redis连接失败: {e}")
                logger.info("💡 将自动降级到MongoDB缓存")
                self._redis_client = None
            except redis.TimeoutError as e:
                logger.warning(f"⚠️ Redis连接超时: {e}")
                logger.info("💡 将自动降级到MongoDB缓存")
                self._redis_client = None
            except Exception as e:
                logger.warning(f"⚠️ Redis初始化异常: {e}")
                self._redis_client = None
        else:
            # 已有客户端，定期检查健康状态
            try:
                self._redis_client.ping()
            except Exception as e:
                logger.warning(f"⚠️ Redis健康检查失败: {e}")
                logger.info("💡 将自动降级到MongoDB缓存")
                self._redis_client = None

        return self._redis_client

    def _get_from_redis(self, key: str) -> Tuple[Optional[Any], str]:
        """
        从Redis获取缓存

        Returns:
            (值, 来源)
        """
        client = self._get_redis_client()
        if client is None:
            return None, "redis"

        try:
            full_key = self._redis_prefix + key
            data = client.get(full_key)

            if data:
                value = json.loads(data)
                client.expire(full_key, 3600)  # 刷新TTL

                with self._stats_lock:
                    self._stats["hits"] += 1
                logger.debug(f"📦 Redis缓存命中: {key}")
                return value, "redis"

            with self._stats_lock:
                self._stats["misses"] += 1
            return None, "redis"

        except Exception as e:
            logger.warning(f"⚠️ Redis读取失败: {e}")
            return None, "redis"

    def _set_to_redis(
        self, key: str, value: Any, ttl: int = 3600, category: str = "general"
    ):
        """设置Redis缓存"""
        client = self._get_redis_client()
        if client is None:
            return

        try:
            full_key = self._redis_prefix + key
            data = json.dumps(value, ensure_ascii=False)
            client.setex(full_key, ttl, data)

            with self._stats_lock:
                self._stats["sets"] += 1
            logger.debug(f"💾 设置Redis缓存: {key} (TTL: {ttl}s)")

        except Exception as e:
            logger.warning(f"⚠️ Redis写入失败: {e}")

    def _delete_from_redis(self, key: str) -> bool:
        """删除Redis缓存"""
        client = self._get_redis_client()
        if client is None:
            return False

        try:
            full_key = self._redis_prefix + key
            result = client.delete(full_key)
            if result > 0:
                with self._stats_lock:
                    self._stats["deletes"] += 1
                return True
            return False

        except Exception as e:
            logger.warning(f"⚠️ Redis删除失败: {e}")
            return False

    # ==================== MongoDB缓存 ====================

    def _get_from_mongodb(self, key: str) -> Tuple[Optional[Any], str]:
        """
        从MongoDB获取缓存

        Returns:
            (值, 来源)
        """
        try:
            db = get_mongo_db()
            collection = db[self._mongo_collection]

            now = datetime.now(timezone.utc)
            doc = collection.find_one({"key": key, "expires_at": {"$gt": now}})

            if doc:
                value = doc.get("value")
                with self._stats_lock:
                    self._stats["hits"] += 1
                logger.debug(f"📦 MongoDB缓存命中: {key}")
                return value, "mongodb"

            with self._stats_lock:
                self._stats["misses"] += 1
            return None, "mongodb"

        except Exception as e:
            logger.warning(f"⚠️ MongoDB读取失败: {e}")
            return None, "mongodb"

    def _set_to_mongodb(
        self, key: str, value: Any, ttl: int = 3600, category: str = "general"
    ):
        """设置MongoDB缓存"""
        try:
            db = get_mongo_db()
            collection = db[self._mongo_collection]

            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

            collection.update_one(
                {"key": key},
                {
                    "$set": {
                        "key": key,
                        "value": value,
                        "category": category,
                        "created_at": datetime.now(timezone.utc),
                        "expires_at": expires_at,
                    }
                },
                upsert=True,
            )

            with self._stats_lock:
                self._stats["sets"] += 1
            logger.debug(f"💾 设置MongoDB缓存: {key} (TTL: {ttl}s)")

        except Exception as e:
            logger.warning(f"⚠️ MongoDB写入失败: {e}")

    def _delete_from_mongodb(self, key: str) -> bool:
        """删除MongoDB缓存"""
        try:
            db = get_mongo_db()
            collection = db[self._mongo_collection]

            result = collection.delete_one({"key": key})
            if result.deleted_count > 0:
                with self._stats_lock:
                    self._stats["deletes"] += 1
                return True
            return False

        except Exception as e:
            logger.warning(f"⚠️ MongoDB删除失败: {e}")
            return False

    # ==================== File缓存 ====================

    def _get_from_file(self, key: str) -> Tuple[Optional[Any], str]:
        """
        从File获取缓存

        Returns:
            (值, 来源)
        """
        try:
            file_path = self._file_cache_dir / f"{key}.json"

            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 检查过期
                expires_at = datetime.fromisoformat(
                    data.get("expires_at", "2099-12-31")
                )
                if expires_at > datetime.now(timezone.utc):
                    with self._stats_lock:
                        self._stats["hits"] += 1
                    logger.debug(f"📦 File缓存命中: {key}")
                    return data.get("value"), "file"
                else:
                    file_path.unlink()  # 删除过期文件
                    with self._stats_lock:
                        self._stats["expires"] += 1

            with self._stats_lock:
                self._stats["misses"] += 1
            return None, "file"

        except Exception as e:
            logger.warning(f"⚠️ File读取失败: {e}")
            return None, "file"

    def _set_to_file(
        self, key: str, value: Any, ttl: int = 3600, category: str = "general"
    ):
        """设置File缓存"""
        try:
            file_path = self._file_cache_dir / f"{key}.json"
            file_path.parent.mkdir(parents=True, exist_ok=True)

            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

            data = {
                "key": key,
                "value": value,
                "category": category,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": expires_at.isoformat(),
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            with self._stats_lock:
                self._stats["sets"] += 1
            logger.debug(f"💾 设置File缓存: {key} (TTL: {ttl}s)")

        except Exception as e:
            logger.warning(f"⚠️ File写入失败: {e}")

    # ==================== 统一接口 ====================

    def get(
        self, key: str, category: str = "general", levels: List[str] = None
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

        key = self.normalize_key(key, category)

        for level in levels:
            if level == "memory":
                value, source = self._get_from_memory(key)
            elif level == "redis":
                value, source = self._get_from_redis(key)
            elif level == "mongodb":
                value, source = self._get_from_mongodb(key)
            elif level == "file":
                value, source = self._get_from_file(key)
            else:
                continue

            if value is not None:
                # 回填到更快的缓存
                if level != "memory" and "memory" in levels:
                    self._set_to_memory(key, value, ttl=300, category=category)
                return value, source

        return None, "none"

    def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
        category: str = "general",
        levels: List[str] = None,
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

        key = self.normalize_key(key, category)

        for level in levels:
            if level == "memory":
                self._set_to_memory(key, value, ttl, category)
            elif level == "redis":
                self._set_to_redis(key, value, ttl, category)
            elif level == "mongodb":
                self._set_to_mongodb(key, value, ttl, category)
            elif level == "file":
                self._set_to_file(key, value, ttl, category)

    def delete(
        self, key: str, category: str = "general", levels: List[str] = None
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

        key = self.normalize_key(key, category)

        deleted = 0
        for level in levels:
            if level == "memory" and self._delete_from_memory(key):
                deleted += 1
            elif level == "redis" and self._delete_from_redis(key):
                deleted += 1
            elif level == "mongodb" and self._delete_from_mongodb(key):
                deleted += 1

        logger.info(f"🗑️ 删除缓存: {key} ({deleted}个级别)")
        return deleted

    def clear_category(self, category: str, levels: List[str] = None) -> int:
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

        # 清除内存缓存
        if "memory" in levels:
            with self._memory_lock:
                keys_to_delete = [
                    k for k in self._memory_cache if k.startswith(category + ":")
                ]
                for key in keys_to_delete:
                    del self._memory_cache[key]
                    deleted += 1

        # 清除MongoDB缓存
        if "mongodb" in levels:
            try:
                db = get_mongo_db()
                collection = db[self._mongo_collection]
                result = collection.delete_many({"category": category})
                deleted += result.deleted_count
            except Exception as e:
                logger.warning(f"⚠️ 清除MongoDB缓存失败: {e}")

        # 清除Redis缓存
        if "redis" in levels:
            client = self._get_redis_client()
            if client:
                try:
                    pattern = self._redis_prefix + category + ":*"
                    keys = list(client.scan_iter(match=pattern))
                    if keys:
                        deleted += client.delete(*keys)
                except Exception as e:
                    logger.warning(f"⚠️ 清除Redis缓存失败: {e}")

        logger.info(f"🗑️ 清除类别缓存: {category} ({deleted}个)")
        return deleted

    # ==================== 缓存击穿保护 ====================

    def get_or_set_with_fallback(
        self,
        key: str,
        factory_func,
        category: str = "general",
        ttl: int = 3600,
        fallback_value: Any = None,
        fallback_ttl: int = 60,
        max_retries: int = 3,
        levels: List[str] = None,
    ) -> Tuple[Any, str]:
        """获取或设置缓存，带缓存击穿保护

        当缓存失效且数据源不可用时，防止大量请求直接冲击后端系统。
        使用降级策略：
        1. 正常获取缓存
        2. 缓存失效时，只有一个请求重建
        3. 重建失败时，返回兜底值并设置短时效缓存

        Args:
            key: 缓存键
            factory_func: 数据工厂函数（用于重建缓存）
            category: 缓存类别
            ttl: 正常缓存过期时间（秒）
            fallback_value: 兜底值（当factory_func失败时使用）
            fallback_ttl: 兜底值缓存时间（秒，默认60秒）
            max_retries: 重建重试次数
            levels: 缓存级别

        Returns:
            (值, 来源) - 来源可能是 "cache", "refreshed", "fallback", "error"
        """
        if levels is None:
            levels = ["memory", "redis", "mongodb"]

        # 步骤1：尝试获取现有缓存
        value, source = self.get(key, category, levels)

        if value is not None:
            return value, source

        # 步骤2：使用防雪崩机制重建缓存
        normalized_key = self.normalize_key(key, category)
        refresh_lock = self._get_refresh_lock(normalized_key)
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
            self._mark_refreshing(normalized_key)

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
            self._unmark_refreshing(normalized_key)
            refresh_lock.release()

    def set_circuit_breaker(
        self,
        key: str,
        is_fail: bool,
        category: str = "general",
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
    ) -> bool:
        """设置熔断器状态（简化版缓存击穿保护）

        当数据源连续失败时，自动启用兜底模式。

        Args:
            key: 缓存键
            is_fail: 本次请求是否失败
            category: 缓存类别
            failure_threshold: 失败阈值，超过则启用兜底
            recovery_timeout: 恢复超时时间（秒）

        Returns:
            True: 当前应该使用兜底模式
            False: 正常模式
        """
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

    def _increment_stat(self, stat: str):
        """增加统计"""
        with self._stats_lock:
            if stat in self._stats:
                self._stats[stat] += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
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
            "memory_cache_size": len(self._memory_cache),
        }

    def reset_stats(self):
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


# 全局缓存服务实例
_cache_service: Optional[UnifiedCacheService] = None


def get_cache_service() -> UnifiedCacheService:
    """获取全局缓存服务实例"""
    global _cache_service
    if _cache_service is None:
        _cache_service = UnifiedCacheService()
    return _cache_service
