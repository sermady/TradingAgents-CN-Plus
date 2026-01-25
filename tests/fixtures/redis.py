# -*- coding: utf-8 -*-
"""
Redis相关Fixtures
"""

import pytest
from typing import Generator
from redis import Redis


@pytest.fixture(scope="session")
def redis_client() -> Generator[Redis, None, None]:
    """
    测试Redis客户端
    使用db=1作为测试数据库，避免与生产环境冲突
    """
    redis = Redis(
        host="localhost",
        port=6379,
        db=1,  # 使用db=1作为测试数据库
        decode_responses=True,  # 自动解码为字符串
    )
    # 测试连接
    try:
        redis.ping()
        yield redis
    finally:
        # 清空测试数据库
        redis.flushdb()
        redis.close()


@pytest.fixture(scope="function")
def clean_redis(redis_client: Redis):
    """
    每个测试后清理Redis
    """
    yield
    redis_client.flushdb()


@pytest.fixture
def cache_prefix():
    """缓存键前缀"""
    return "test:"


@pytest.fixture
def test_cache_key(cache_prefix):
    """生成测试缓存键"""

    def _generate_key(key: str) -> str:
        return f"{cache_prefix}{key}"

    return _generate_key
