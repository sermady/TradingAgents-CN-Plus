# -*- coding: utf-8 -*-
"""
Redis缓存后端

提供Redis分布式缓存实现
"""

import json
import logging
from typing import TYPE_CHECKING, Any, Optional, Tuple

import redis

from app.core.database import get_redis_client
from ..utils import _run_async

if TYPE_CHECKING:
    from ..stats import CacheStats

logger = logging.getLogger(__name__)


class RedisBackend:
    """Redis缓存后端"""

    def __init__(self, stats: "CacheStats", prefix: str = "tradingagents:cache:"):
        """
        初始化Redis缓存后端

        Args:
            stats: 缓存统计管理器
            prefix: Redis键前缀
        """
        self._client = None
        self._prefix = prefix
        self._stats = stats

    def _get_client(self):
        """
        获取Redis客户端

        带健康检查和降级策略的Redis连接管理
        """
        if self._client is None:
            try:
                self._client = get_redis_client()

                # 健康检查：尝试ping Redis
                if self._client:
                    self._client.ping()
                    logger.info("✅ Redis连接成功")
                else:
                    logger.warning("⚠️ Redis连接失败: ping失败")
                    self._client = None

            except redis.ConnectionError as e:
                logger.warning(f"⚠️ Redis连接失败: {e}")
                logger.info("💡 将自动降级到MongoDB缓存")
                self._client = None
            except redis.TimeoutError as e:
                logger.warning(f"⚠️ Redis连接超时: {e}")
                logger.info("💡 将自动降级到MongoDB缓存")
                self._client = None
            except Exception as e:
                logger.warning(f"⚠️ Redis初始化异常: {e}")
                self._client = None
        else:
            # 已有客户端，定期检查健康状态
            try:
                self._client.ping()
            except Exception as e:
                logger.warning(f"⚠️ Redis健康检查失败: {e}")
                logger.info("💡 将自动降级到MongoDB缓存")
                self._client = None

        return self._client

    def get(self, key: str) -> Tuple[Optional[Any], str]:
        """
        从Redis获取缓存

        Args:
            key: 缓存键

        Returns:
            (值, 来源)
        """
        client = self._get_client()
        if client is None:
            return None, "redis"

        try:
            full_key = self._prefix + key
            data = _run_async(client.get(full_key))

            if data:
                value = json.loads(data)
                _run_async(client.expire(full_key, 3600))  # 刷新TTL

                self._stats.increment("hits")
                logger.debug(f"📦 Redis缓存命中: {key}")
                return value, "redis"

            self._stats.increment("misses")
            return None, "redis"

        except Exception as e:
            logger.warning(f"⚠️ Redis读取失败: {e}")
            return None, "redis"

    def set(self, key: str, value: Any, ttl: int = 3600, category: str = "general"):
        """
        设置Redis缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
            category: 缓存类别
        """
        client = self._get_client()
        if client is None:
            return

        try:
            full_key = self._prefix + key
            data = json.dumps(value, ensure_ascii=False)
            _run_async(client.setex(full_key, ttl, data))

            self._stats.increment("sets")
            logger.debug(f"💾 设置Redis缓存: {key} (TTL: {ttl}s)")

        except Exception as e:
            logger.warning(f"⚠️ Redis写入失败: {e}")

    def delete(self, key: str) -> bool:
        """
        删除Redis缓存

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        client = self._get_client()
        if client is None:
            return False

        try:
            full_key = self._prefix + key
            result = _run_async(client.delete(full_key))
            if int(result or 0) > 0:
                self._stats.increment("deletes")
                return True
            return False

        except Exception as e:
            logger.warning(f"⚠️ Redis删除失败: {e}")
            return False

    def clear_category(self, category: str) -> int:
        """
        清除指定类别的缓存

        Args:
            category: 缓存类别

        Returns:
            清除的缓存数量
        """
        client = self._get_client()
        if client is None:
            return 0

        try:
            pattern = self._prefix + category + ":*"

            # 使用异步迭代器收集keys
            async def collect_keys():
                keys = []
                async for key in client.scan_iter(match=pattern):
                    keys.append(key)
                return keys

            keys = _run_async(collect_keys())
            if keys:
                return _run_async(client.delete(*keys))
            return 0

        except Exception as e:
            logger.warning(f"⚠️ 清除Redis缓存失败: {e}")
            return 0
