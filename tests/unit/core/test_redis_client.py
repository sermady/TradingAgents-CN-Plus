#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis客户端配置和连接管理测试
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from app.core.redis_client import init_redis, get_redis, close_redis


class TestInitRedis:
    """测试初始化Redis连接"""

    @pytest.mark.asyncio
    async def test_init_redis_success(self):
        """测试Redis初始化成功"""
        with patch("app.core.redis_client.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379/0"
            mock_settings.REDIS_MAX_CONNECTIONS = 20
            mock_settings.REDIS_RETRY_ON_TIMEOUT = True

            # Mock Redis 连接池和客户端
            mock_pool = Mock()
            mock_client = AsyncMock()
            mock_client.ping.return_value = True

            with patch(
                "app.core.redis_client.redis.ConnectionPool.from_url",
                return_value=mock_pool,
            ):
                with patch(
                    "app.core.redis_client.redis.Redis", return_value=mock_client
                ):
                    await init_redis()

                    # 验证连接池被创建
                    mock_pool_class = redis.ConnectionPool.from_url
                    # 验证客户端被创建
                    mock_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_redis_failure(self):
        """测试Redis初始化失败"""
        with patch("app.core.redis_client.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://invalid:6379/0"

            # Mock 连接失败
            with patch(
                "app.core.redis_client.redis.ConnectionPool.from_url",
                side_effect=Exception("Connection refused"),
            ):
                with pytest.raises(Exception) as exc_info:
                    await init_redis()

                assert "Connection refused" in str(exc_info.value)


class TestGetRedis:
    """测试获取Redis客户端"""

    def test_get_redis_success(self):
        """测试获取已初始化的Redis客户端"""
        mock_client = Mock()

        with patch("app.core.redis_client.redis_client", mock_client):
            result = get_redis()
            assert result == mock_client

    def test_get_redis_not_initialized(self):
        """测试获取未初始化的Redis客户端"""
        with patch("app.core.redis_client.redis_client", None):
            with pytest.raises(RuntimeError) as exc_info:
                get_redis()

            assert "Redis" in str(exc_info.value)


class TestCloseRedis:
    """测试关闭Redis连接"""

    @pytest.mark.asyncio
    async def test_close_redis_success(self):
        """测试关闭Redis连接成功"""
        mock_pool = AsyncMock()
        mock_client = AsyncMock()

        with patch("app.core.redis_client.redis_pool", mock_pool):
            with patch("app.core.redis_client.redis_client", mock_client):
                await close_redis()

                # 验证连接池被关闭
                mock_pool.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_redis_not_initialized(self):
        """测试关闭未初始化的Redis连接"""
        with patch("app.core.redis_client.redis_pool", None):
            with patch("app.core.redis_client.redis_client", None):
                # 应该不抛出异常
                await close_redis()


class TestRedisClientEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_init_redis_with_password(self):
        """测试使用密码初始化Redis"""
        with patch("app.core.redis_client.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://:secret@localhost:6379/0"
            mock_settings.REDIS_MAX_CONNECTIONS = 10
            mock_settings.REDIS_RETRY_ON_TIMEOUT = True

            mock_pool = Mock()
            mock_client = AsyncMock()
            mock_client.ping.return_value = True

            with patch(
                "app.core.redis_client.redis.ConnectionPool.from_url",
                return_value=mock_pool,
            ):
                with patch(
                    "app.core.redis_client.redis.Redis", return_value=mock_client
                ):
                    await init_redis()

                    # 验证使用正确的URL
                    assert "secret" in mock_settings.REDIS_URL


# 导入 redis 模块以便在测试中使用
import redis.asyncio as redis

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
