# -*- coding: utf-8 -*-
"""
测试队列服务功能

测试范围:
- 队列服务初始化
- 任务入队/出队
- 并发控制
- 任务状态管理
"""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

os.environ["USE_MONGODB_STORAGE"] = "false"
os.environ["TRADINGAGENTS_SKIP_DB_INIT"] = "true"


@pytest.mark.unit
def test_queue_keys_module():
    """测试队列键模块"""
    from app.services.queue import keys

    assert keys is not None
    assert hasattr(keys, "READY_LIST")
    assert hasattr(keys, "TASK_PREFIX")


@pytest.mark.unit
def test_queue_constants():
    """测试队列常量"""
    from app.services.queue import (
        READY_LIST,
        TASK_PREFIX,
        BATCH_PREFIX,
        SET_PROCESSING,
        SET_COMPLETED,
        SET_FAILED,
        DEFAULT_USER_CONCURRENT_LIMIT,
        GLOBAL_CONCURRENT_LIMIT,
        VISIBILITY_TIMEOUT_SECONDS,
    )

    assert READY_LIST is not None
    assert TASK_PREFIX is not None
    assert BATCH_PREFIX is not None
    assert SET_PROCESSING is not None
    assert SET_COMPLETED is not None
    assert SET_FAILED is not None
    assert DEFAULT_USER_CONCURRENT_LIMIT > 0
    assert GLOBAL_CONCURRENT_LIMIT > 0
    assert VISIBILITY_TIMEOUT_SECONDS > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_queue_service_init():
    """测试队列服务初始化"""
    from app.services.queue_service import QueueService

    # Arrange
    mock_redis = AsyncMock()

    # Act
    service = QueueService(mock_redis)

    # Assert
    assert service is not None
    assert service.r == mock_redis
    assert service.user_concurrent_limit > 0
    assert service.global_concurrent_limit > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_queue_service_enqueue_task():
    """测试任务入队"""
    from app.services.queue_service import QueueService

    # Arrange
    mock_redis = AsyncMock()
    mock_redis.lpush = AsyncMock()
    mock_redis.hset = AsyncMock()
    mock_redis.sadd = AsyncMock()

    service = QueueService(mock_redis)

    # Mock the concurrent limit checks
    service._check_user_concurrent_limit = AsyncMock(return_value=True)
    service._check_global_concurrent_limit = AsyncMock(return_value=True)

    # Act
    task_id = await service.enqueue_task(
        user_id="test_user",
        symbol="000001",
        params={"depth": "full"},
    )

    # Assert
    assert task_id is not None
    mock_redis.hset.assert_called_once()
    mock_redis.lpush.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_queue_service_enqueue_task_user_limit():
    """测试用户并发限制"""
    from app.services.queue_service import QueueService

    # Arrange
    mock_redis = AsyncMock()
    service = QueueService(mock_redis)

    # Mock the concurrent limit checks - 用户限制触发
    service._check_user_concurrent_limit = AsyncMock(return_value=False)
    service._check_global_concurrent_limit = AsyncMock(return_value=True)

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        await service.enqueue_task(
            user_id="test_user",
            symbol="000001",
            params={},
        )

    assert "并发限制" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_queue_service_enqueue_task_global_limit():
    """测试全局并发限制"""
    from app.services.queue_service import QueueService

    # Arrange
    mock_redis = AsyncMock()
    service = QueueService(mock_redis)

    # Mock the concurrent limit checks - 全局限制触发
    service._check_user_concurrent_limit = AsyncMock(return_value=True)
    service._check_global_concurrent_limit = AsyncMock(return_value=False)

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        await service.enqueue_task(
            user_id="test_user",
            symbol="000001",
            params={},
        )

    assert "全局并发限制" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_queue_service_enqueue_batch_task():
    """测试批量任务入队"""
    from app.services.queue_service import QueueService

    # Arrange
    mock_redis = AsyncMock()
    mock_redis.lpush = AsyncMock()
    mock_redis.hset = AsyncMock()
    mock_redis.sadd = AsyncMock()

    service = QueueService(mock_redis)
    service._check_user_concurrent_limit = AsyncMock(return_value=True)
    service._check_global_concurrent_limit = AsyncMock(return_value=True)

    # Act
    task_id = await service.enqueue_task(
        user_id="test_user",
        symbol="000001",
        params={},
        batch_id="batch_123",
    )

    # Assert
    assert task_id is not None
    mock_redis.sadd.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
