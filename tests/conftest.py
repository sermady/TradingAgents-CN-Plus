# -*- coding: utf-8 -*-
"""
TradingAgents-CN 测试全局配置

本文件提供全局测试fixtures和配置
"""

import os
import sys
import asyncio
import pytest
from typing import AsyncGenerator, Generator
from httpx import AsyncClient, ASGITransport
from dotenv import load_dotenv

# 将项目根目录加入 sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 加载环境变量
env_file = os.path.join(PROJECT_ROOT, ".env")
if os.path.exists(env_file):
    load_dotenv(env_file)

# 设置测试环境变量
os.environ["TESTING"] = "true"
os.environ.setdefault("MONGODB_DATABASE", "tradingagents_test")
os.environ.setdefault("REDIS_DB", "1")
# 禁用操作日志以避免数据库初始化问题
os.environ["DISABLE_OPERATION_LOG"] = "true"


# ==============================================================================
# 异步事件循环
# ==============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """
    全局事件循环
    使用session级别，所有测试共享同一个事件循环
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==============================================================================
# FastAPI应用和测试客户端
# ==============================================================================


@pytest.fixture(scope="function")
def test_app(mongodb_client, redis_client):
    """
    测试用的FastAPI应用实例
    Override数据库和缓存依赖，使用测试数据库
    """
    from app.main import app
    from app.core.database import get_database
    from app.core.database import get_redis_client
    from motor.motor_asyncio import AsyncIOMotorClient
    from unittest.mock import patch, AsyncMock
    import os

    # Mock 操作日志服务
    with patch(
        "app.services.operation_log_service.log_operation",
        new_callable=AsyncMock(return_value=None),
    ):
        # 创建异步MongoDB客户端（用于override）
        mongodb_host = os.getenv("MONGODB_HOST", "localhost")
        mongodb_port = os.getenv("MONGODB_PORT", "27017")
        mongodb_user = os.getenv("MONGODB_USERNAME")
        mongodb_password = os.getenv("MONGODB_PASSWORD")
        mongodb_auth_source = os.getenv("MONGODB_AUTH_SOURCE", "admin")

        if mongodb_user and mongodb_password:
            conn_str = f"mongodb://{mongodb_user}:{mongodb_password}@{mongodb_host}:{mongodb_port}/tradingagents_test?authSource={mongodb_auth_source}"
        else:
            conn_str = f"mongodb://{mongodb_host}:{mongodb_port}/tradingagents_test"

        async_client = AsyncIOMotorClient(conn_str, connectTimeoutMS=5000)

        # Override数据库依赖 - 返回 motor 客户端的测试数据库
        async def override_get_database():
            return async_client.tradingagents_test

        # Override缓存依赖
        def override_get_redis():
            return redis_client

        app.dependency_overrides[get_database] = override_get_database
        app.dependency_overrides[get_redis_client] = override_get_redis

        yield app

        # 清理
        async_client.close()
        app.dependency_overrides.clear()


@pytest.fixture
async def test_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """
    异步HTTP测试客户端
    """
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def async_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """
    异步HTTP测试客户端（别名）
    """
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ==============================================================================
# 导入Fixtures模块
# ==============================================================================

# 数据库fixtures
from tests.fixtures.database import (
    mongodb_client,
    test_database,
    stock_collection,
    user_collection,
    analysis_collection,
    report_collection,
    favorites_collection,
    screening_collection,
    operation_logs_collection,
    notifications_collection,
    quotes_collection,
    config_collection,
    tags_collection,
)

# Redis fixtures
from tests.fixtures.redis import redis_client, clean_redis, cache_prefix, test_cache_key

# 认证fixtures
from tests.fixtures.auth import (
    test_user_data,
    admin_user_data,
    test_user,
    admin_user,
    auth_headers,
    admin_auth_headers,
    test_user_headers,
)

# 股票数据fixtures
from tests.fixtures.stock_data import (
    sample_stock_a,
    sample_stock_b,
    sample_stock_hk,
    sample_stock_us,
    sample_stocks_list,
    sample_price_data,
    sample_technical_indicators,
    sample_fundamental_data,
    sample_analysis_request,
    sample_analysis_result,
)

# LLM fixtures
from tests.fixtures.llm import (
    mock_openai_response,
    mock_gemini_response,
    mock_dashscope_response,
    mock_deepseek_response,
    mock_llm_factory,
    mock_tool_call,
    sample_llm_messages,
    sample_tool_schemas,
)

# 通用数据fixtures
from tests.fixtures.sample_data import (
    random_string,
    random_email,
    current_timestamp,
    future_timestamp,
    past_timestamp,
    sample_user_data,
    sample_notification,
    sample_operation_log,
    sample_config,
    sample_tag,
    sample_screening_criteria,
    sample_batch_analysis_request,
    pagination_params,
    mock_response_data,
)


# ==============================================================================
# 自动清理fixture
# ==============================================================================


@pytest.fixture(scope="function", autouse=True)
def auto_cleanup(test_database):
    """
    每个测试后自动清理数据库
    autouse=True表示自动应用于所有测试
    """
    yield
    # 清空所有集合（处理数据库不可用的情况）
    try:
        for collection_name in test_database.list_collection_names():
            test_database.drop_collection(collection_name)
    except Exception:
        # 如果数据库不可用或需要认证，忽略清理错误
        pass


# ==============================================================================
# 跳过条件
# ==============================================================================


def pytest_configure(config):
    """
    配置pytest
    添加自定义标记
    """
    config.addinivalue_line(
        "markers", "unit: Unit tests - 单元测试（快速，无外部依赖）"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests - 集成测试（需要数据库/API）"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests - 端到端测试（完整业务流程）"
    )
    config.addinivalue_line(
        "markers", "requires_auth: Tests requiring authentication - 需要认证"
    )
    config.addinivalue_line(
        "markers", "requires_db: Tests requiring database connection - 需要数据库"
    )
    config.addinivalue_line(
        "markers", "requires_redis: Tests requiring Redis - 需要Redis"
    )
    config.addinivalue_line(
        "markers", "requires_llm: Tests requiring LLM API - 需要LLM API"
    )
    config.addinivalue_line("markers", "slow: Slow running tests - 耗时测试（>30秒）")


# ==============================================================================
# 辅助函数
# ==============================================================================


@pytest.fixture
def assert_response_success():
    """
    断言响应成功的辅助函数
    """

    def _assert(response, expected_status_code: int = 200):
        assert response.status_code == expected_status_code, (
            f"Expected status {expected_status_code}, got {response.status_code}\n"
            f"Response: {response.text}"
        )
        data = response.json()
        assert data.get("success") is not False, f"Response indicates failure: {data}"
        return data

    return _assert


@pytest.fixture
def assert_response_error():
    """
    断言响应错误的辅助函数
    """

    def _assert(response, expected_status_code: int = 400):
        assert response.status_code == expected_status_code, (
            f"Expected status {expected_status_code}, got {response.status_code}\n"
            f"Response: {response.text}"
        )
        data = response.json()
        assert data.get("success") is False, (
            f"Expected error response, but got success: {data}"
        )
        return data

    return _assert
