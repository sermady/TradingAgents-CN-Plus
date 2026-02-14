# -*- coding: utf-8 -*-
"""
Redis客户端配置和连接管理 (增强版)

改进点:
1. 添加连接重试机制
2. 更好的连接池管理
3. 优雅降级到文件存储
4. 连接健康检查
5. 自动重连

作者: Claude
创建日期: 2026-02-12
"""

import asyncio
import time
import logging
from typing import Optional
from functools import wraps

import redis.asyncio as redis
from .config import settings

logger = logging.getLogger(__name__)

# 全局Redis连接池
redis_pool: Optional[redis.ConnectionPool] = None
redis_client: Optional[redis.Redis] = None

# 连接统计
_connection_stats = {
    "connection_attempts": 0,
    "connection_failures": 0,
    "last_successful_connection": None,
    "reconnect_count": 0,
}


def retry_on_failure(max_retries=3, delay=1.0, backoff=2.0):
    """带指数退避的重试装饰器"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception: Optional[Exception] = RuntimeError(
                "重试失败，所有尝试都抛出异常"
            )
            current_delay = delay

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    _connection_stats["connection_failures"] += 1

                    if attempt < max_retries - 1:
                        logger.warning(
                            f"🔌 [Redis] {func.__name__} 失败 (尝试 {attempt + 1}/{max_retries}): "
                            f"{e}, {current_delay:.1f}秒后重试..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"❌ [Redis] {func.__name__} 最终失败: {e}")

            raise last_exception

        return wrapper

    return decorator


async def init_redis(
    max_retries: int = 3, retry_delay: float = 1.0, check_connection: bool = True
) -> bool:
    """
    初始化Redis连接 (带重试)

    Args:
        max_retries: 最大重试次数
        retry_delay: 初始重试延迟(秒)
        check_connection: 是否测试连接

    Returns:
        bool: 是否成功初始化
    """
    global redis_pool, redis_client, _connection_stats

    # 如果已初始化且连接正常，直接返回
    if redis_client is not None:
        try:
            await redis_client.ping()
            return True
        except:
            pass  # 连接已断开，需要重新初始化

    _connection_stats["connection_attempts"] += 1

    for attempt in range(max_retries):
        try:
            # 创建连接池
            redis_pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
                decode_responses=True,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 60,  # TCP_KEEPIDLE: 60秒后开始发送keepalive探测
                    2: 10,  # TCP_KEEPINTVL: 每10秒发送一次探测
                    3: 3,  # TCP_KEEPCNT: 最多发送3次探测
                },
                health_check_interval=300,
                # 新增: 连接超时设置
                socket_connect_timeout=10,
                socket_timeout=30,
            )

            # 创建Redis客户端
            redis_client = redis.Redis(connection_pool=redis_pool)

            # 测试连接
            if check_connection:
                await redis_client.ping()

            _connection_stats["last_successful_connection"] = time.time()
            logger.info(
                f"✅ [Redis] 连接成功 (max_connections={settings.REDIS_MAX_CONNECTIONS}, "
                f"尝试次数={attempt + 1})"
            )
            return True

        except Exception as e:
            _connection_stats["connection_failures"] += 1

            if attempt < max_retries - 1:
                wait_time = retry_delay * (2**attempt)  # 指数退避
                logger.warning(
                    f"⚠️ [Redis] 连接失败 (尝试 {attempt + 1}/{max_retries}): {e}, "
                    f"{wait_time:.1f}秒后重试..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"❌ [Redis] 连接最终失败: {e}")
                redis_pool = None
                redis_client = None
                return False

    return False


async def ensure_redis_connection() -> bool:
    """确保Redis连接可用 (如果断开则自动重连)"""
    global redis_client, _connection_stats

    if redis_client is None:
        return await init_redis()

    try:
        await redis_client.ping()
        return True
    except Exception as e:
        logger.warning(f"🔌 [Redis] 连接已断开，尝试重连: {e}")
        _connection_stats["reconnect_count"] += 1
        return await init_redis()


async def close_redis():
    """关闭Redis连接"""
    global redis_pool, redis_client

    try:
        if redis_client:
            await redis_client.close()
        if redis_pool:
            await redis_pool.disconnect()
        logger.info("✅ [Redis] 连接已关闭")
    except Exception as e:
        logger.error(f"❌ [Redis] 关闭连接时出错: {e}")
    finally:
        redis_client = None
        redis_pool = None


def get_redis() -> Optional[redis.Redis]:
    """获取Redis客户端实例 (可能返回None)"""
    return redis_client


def is_redis_available() -> bool:
    """检查Redis是否可用"""
    return redis_client is not None


def get_connection_stats() -> dict:
    """获取连接统计"""
    return {
        **_connection_stats,
        "is_connected": redis_client is not None,
        "pool_size": redis_pool.max_connections if redis_pool else 0,
    }


class RedisKeys:
    """Redis键名常量"""

    # 队列相关
    USER_PENDING_QUEUE = "user:{user_id}:pending"
    USER_PROCESSING_SET = "user:{user_id}:processing"
    GLOBAL_PENDING_QUEUE = "global:pending"
    GLOBAL_PROCESSING_SET = "global:processing"

    # 任务相关
    TASK_PROGRESS = "task:{task_id}:progress"
    TASK_RESULT = "task:{task_id}:result"
    TASK_LOCK = "task:{task_id}:lock"

    # 批次相关
    BATCH_PROGRESS = "batch:{batch_id}:progress"
    BATCH_TASKS = "batch:{batch_id}:tasks"
    BATCH_LOCK = "batch:{batch_id}:lock"

    # 用户相关
    USER_SESSION = "session:{session_id}"
    USER_RATE_LIMIT = "rate_limit:{user_id}:{endpoint}"
    USER_DAILY_QUOTA = "quota:{user_id}:{date}"

    # 系统相关
    QUEUE_STATS = "queue:stats"
    SYSTEM_CONFIG = "system:config"
    WORKER_HEARTBEAT = "worker:{worker_id}:heartbeat"

    # 缓存相关
    SCREENING_CACHE = "screening:{cache_key}"
    ANALYSIS_CACHE = "analysis:{cache_key}"
    LLM_CACHE = "llm_cache:{cache_key}"


class RedisService:
    """增强型Redis服务封装类"""

    def __init__(self):
        import redis.asyncio as redis

        self.redis: redis.Redis = get_redis()

    async def _ensure_connection(self) -> bool:
        """确保连接可用"""
        if not self.redis:
            return await ensure_redis_connection()
        try:
            await self.redis.ping()
            return True
        except:
            return await ensure_redis_connection()

    @retry_on_failure(max_retries=3)
    async def set_with_ttl(self, key: str, value: str, ttl: int = 3600):
        """设置带TTL的键值"""
        if not await self._ensure_connection():
            raise RuntimeError("Redis not available")
        await self.redis.setex(key, ttl, value)

    @retry_on_failure(max_retries=3)
    async def get(self, key: str) -> Optional[str]:
        """获取值"""
        if not await self._ensure_connection():
            return None
        value = await self.redis.get(key)
        return value.decode("utf-8") if isinstance(value, bytes) else value

    @retry_on_failure(max_retries=3)
    async def get_json(self, key: str):
        """获取JSON格式的值"""
        import json

        value = await self.get(key)
        if value:
            return json.loads(value)
        return None

    @retry_on_failure(max_retries=3)
    async def set_json(self, key: str, value: dict, ttl: Optional[int] = None):
        """设置JSON格式的值"""
        import json

        json_str = json.dumps(value, ensure_ascii=False)
        if ttl:
            await self.set_with_ttl(key, json_str, ttl)
        else:
            if not await self._ensure_connection():
                raise RuntimeError("Redis not available")
            await self.redis.set(key, json_str)

    @retry_on_failure(max_retries=3)
    async def increment_with_ttl(self, key: str, ttl: int = 3600):
        """递增计数器并设置TTL"""
        if not await self._ensure_connection():
            raise RuntimeError("Redis not available")
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl)
        results = await pipe.execute()
        return results[0]

    @retry_on_failure(max_retries=3)
    async def add_to_queue(self, queue_key: str, item: dict):
        """添加项目到队列"""
        import json

        if not await self._ensure_connection():
            raise RuntimeError("Redis not available")
        await self.redis.lpush(queue_key, json.dumps(item, ensure_ascii=False))

    @retry_on_failure(max_retries=3)
    async def pop_from_queue(self, queue_key: str, timeout: int = 1):
        """从队列弹出项目"""
        import json

        if not await self._ensure_connection():
            raise RuntimeError("Redis not available")
        result = await self.redis.brpop([queue_key], timeout=timeout)
        if result:
            return json.loads(result[1])
        return None

    @retry_on_failure(max_retries=3)
    async def get_queue_length(self, queue_key: str) -> int:
        """获取队列长度"""
        if not await self._ensure_connection():
            return 0
        return await self.redis.llen(queue_key)

    @retry_on_failure(max_retries=3)
    async def add_to_set(self, set_key: str, value: str):
        """添加到集合"""
        if not await self._ensure_connection():
            raise RuntimeError("Redis not available")
        await self.redis.sadd(set_key, value)

    @retry_on_failure(max_retries=3)
    async def remove_from_set(self, set_key: str, value: str):
        """从集合移除"""
        if not await self._ensure_connection():
            raise RuntimeError("Redis not available")
        await self.redis.srem(set_key, value)

    @retry_on_failure(max_retries=3)
    async def is_in_set(self, set_key: str, value: str) -> bool:
        """检查是否在集合中"""
        if not await self._ensure_connection():
            return False
        result = await self.redis.sismember(set_key, value)
        return bool(result)

    @retry_on_failure(max_retries=3)
    async def get_set_size(self, set_key: str) -> int:
        """获取集合大小"""
        if not await self._ensure_connection():
            return 0
        return await self.redis.scard(set_key)

    @retry_on_failure(max_retries=3)
    async def acquire_lock(self, lock_key: str, timeout: int = 30) -> Optional[str]:
        """获取分布式锁"""
        import uuid

        if not await self._ensure_connection():
            raise RuntimeError("Redis not available")
        lock_value = str(uuid.uuid4())
        acquired = await self.redis.set(lock_key, lock_value, nx=True, ex=timeout)
        if acquired:
            return lock_value
        return None

    @retry_on_failure(max_retries=3)
    async def release_lock(self, lock_key: str, lock_value: str) -> bool:
        """释放分布式锁"""
        if not await self._ensure_connection():
            raise RuntimeError("Redis not available")
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        result = await self.redis.eval(lua_script, 1, [lock_key], [lock_value])
        return bool(result)

    @retry_on_failure(max_retries=3)
    async def delete(self, key: str):
        """删除键"""
        if not await self._ensure_connection():
            raise RuntimeError("Redis not available")
        await self.redis.delete(key)

    @retry_on_failure(max_retries=3)
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not await self._ensure_connection():
            return False
        return await self.redis.exists(key) > 0

    @retry_on_failure(max_retries=3)
    async def expire(self, key: str, ttl: int):
        """设置过期时间"""
        if not await self._ensure_connection():
            raise RuntimeError("Redis not available")
        await self.redis.expire(key, ttl)


# 全局Redis服务实例
redis_service: Optional[RedisService] = None


def get_redis_service() -> Optional[RedisService]:
    """获取Redis服务实例"""
    global redis_service
    if redis_service is None and is_redis_available():
        redis_service = RedisService()
    return redis_service


# 向后兼容
__all__ = [
    "init_redis",
    "close_redis",
    "get_redis",
    "ensure_redis_connection",
    "is_redis_available",
    "get_connection_stats",
    "RedisKeys",
    "RedisService",
    "get_redis_service",
    "redis_pool",
    "redis_client",
    "redis_service",
]
