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

        self._initialized = True
        logger.info("✅ 统一缓存服务初始化完成")

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
