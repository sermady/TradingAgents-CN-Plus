# -*- coding: utf-8 -*-
"""
测试健康检查API

测试范围:
- /health 端点 - 轻量级健康检查
- /health/detailed 端点 - 详细健康检查
- /healthz 端点 - Kubernetes健康检查
- /readyz 端点 - Kubernetes就绪检查
"""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_endpoint(test_client: AsyncClient):
    """测试轻量级健康检查端点"""
    # Arrange & Act
    response = await test_client.get("/api/health")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert data["data"]["status"] == "ok"
    assert "timestamp" in data["data"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_detailed_endpoint(test_client: AsyncClient):
    """测试详细健康检查端点"""
    # Arrange & Act
    response = await test_client.get("/api/health/detailed")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert data["data"]["status"] == "ok"
    assert "version" in data["data"]
    assert "timestamp" in data["data"]
    assert "service" in data["data"]
    assert "checks" in data["data"]
    assert "mongodb" in data["data"]["checks"]
    assert "redis" in data["data"]["checks"]
    assert "response_time_ms" in data["data"]
    assert data["data"]["service"] == "TradingAgents-CN API"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_healthz_endpoint(test_client: AsyncClient):
    """测试Kubernetes健康检查端点"""
    # Arrange & Act
    response = await test_client.get("/api/healthz")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_readyz_endpoint(test_client: AsyncClient):
    """测试Kubernetes就绪检查端点"""
    # Arrange & Act
    response = await test_client.get("/api/readyz")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_response_structure(test_client: AsyncClient):
    """测试健康检查响应结构"""
    # Arrange & Act
    response = await test_client.get("/api/health")

    # Assert
    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert isinstance(data, dict)
    assert "success" in data
    assert "data" in data
    assert isinstance(data["data"], dict)
    assert "status" in data["data"]
    assert "timestamp" in data["data"]
    assert isinstance(data["data"]["status"], str)
    assert isinstance(data["data"]["timestamp"], int)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_detailed_checks(test_client: AsyncClient):
    """测试详细健康检查包含数据库状态"""
    # Arrange & Act
    response = await test_client.get("/api/health/detailed")

    # Assert
    assert response.status_code == 200
    data = response.json()

    # 验证数据库检查
    checks = data["data"]["checks"]
    assert "mongodb" in checks
    assert "redis" in checks
    # 数据库状态应该是"connected"或包含"error"
    assert isinstance(checks["mongodb"], str)
    assert isinstance(checks["redis"], str)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_response_time(test_client: AsyncClient):
    """测试健康检查响应时间"""
    # Arrange & Act
    response = await test_client.get("/api/health/detailed")

    # Assert
    assert response.status_code == 200
    data = response.json()

    # 验证响应时间
    response_time = data["data"]["response_time_ms"]
    assert isinstance(response_time, (int, float))
    assert response_time >= 0
    # 响应时间应该小于1秒（1000ms）
    assert response_time < 1000
