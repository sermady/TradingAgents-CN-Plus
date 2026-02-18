# -*- coding: utf-8 -*-
"""
MongoDB缓存后端

提供MongoDB持久化缓存实现
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Any, Optional, Tuple

from app.core.database import get_mongo_db

if TYPE_CHECKING:
    from ..stats import CacheStats

logger = logging.getLogger(__name__)


class MongoDBBackend:
    """MongoDB缓存后端"""

    def __init__(
        self,
        stats: "CacheStats",
        db_name: str = "tradingagents",
        collection: str = "cache_store",
    ):
        """
        初始化MongoDB缓存后端

        Args:
            stats: 缓存统计管理器
            db_name: 数据库名称
            collection: 集合名称
        """
        self._stats = stats
        self._db_name = db_name
        self._collection = collection

    def get(self, key: str) -> Tuple[Optional[Any], str]:
        """
        从MongoDB获取缓存

        Args:
            key: 缓存键

        Returns:
            (值, 来源)
        """
        try:
            db = get_mongo_db()
            collection = db[self._collection]

            now = datetime.now(timezone.utc)
            doc = collection.find_one({"key": key, "expires_at": {"$gt": now}})

            if doc:
                value = doc.get("value")
                self._stats.increment("hits")
                logger.debug(f"📦 MongoDB缓存命中: {key}")
                return value, "mongodb"

            self._stats.increment("misses")
            return None, "mongodb"

        except Exception as e:
            logger.warning(f"⚠️ MongoDB读取失败: {e}")
            return None, "mongodb"

    def set(self, key: str, value: Any, ttl: int = 3600, category: str = "general"):
        """
        设置MongoDB缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
            category: 缓存类别
        """
        try:
            db = get_mongo_db()
            collection = db[self._collection]

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

            self._stats.increment("sets")
            logger.debug(f"💾 设置MongoDB缓存: {key} (TTL: {ttl}s)")

        except Exception as e:
            logger.warning(f"⚠️ MongoDB写入失败: {e}")

    def delete(self, key: str) -> bool:
        """
        删除MongoDB缓存

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        try:
            db = get_mongo_db()
            collection = db[self._collection]

            result = collection.delete_one({"key": key})
            if result.deleted_count > 0:
                self._stats.increment("deletes")
                return True
            return False

        except Exception as e:
            logger.warning(f"⚠️ MongoDB删除失败: {e}")
            return False

    def clear_category(self, category: str) -> int:
        """
        清除指定类别的缓存

        Args:
            category: 缓存类别

        Returns:
            清除的缓存数量
        """
        try:
            db = get_mongo_db()
            collection = db[self._collection]
            result = collection.delete_many({"category": category})
            return result.deleted_count
        except Exception as e:
            logger.warning(f"⚠️ 清除MongoDB缓存失败: {e}")
            return 0
