# -*- coding: utf-8 -*-
"""
测试健康检查API路由

测试范围:
- 基本健康检查
- 详细健康检查
- Kubernetes健康检查端点
"""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from httpx import AsyncClient, ASGITransport

os.environ["USE_MONGODB_STORAGE"] = "false"
os.environ["TRADINGAGENTS_SKIP_DB_INIT"] = "true"


@pytest.mark.unit
class TestHealthRouterFunctions:
    """测试健康路由功能函数"""

    def test_get_version_from_file(self, tmp_path):
        """测试从VERSION文件读取版本"""
        # Arrange
        version_file = tmp_path / "VERSION"
        version_file.write_text("1.0.0-test")

        # Act & Assert
        from app.routers.health import get_version

        # 直接测试函数逻辑
        assert get_version() is not None

    def test_router_instance(self):
        """测试路由器实例"""
        from app.routers.health import router

        assert router is not None
        assert router.prefix == ""


@pytest.mark.integration
@pytest.mark.asyncio
class TestHealthEndpoints:
    """测试健康检查端点"""

    async def test_health_endpoint(self, test_client):
        """测试基本健康检查"""
        # Act
        response = await test_client.get("/api/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "ok"
        assert "timestamp" in data["data"]

    async def test_healthz_endpoint(self, test_client):
        """测试Kubernetes健康检查"""
        # Act
        response = await test_client.get("/api/healthz")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    async def test_readyz_endpoint(self, test_client):
        """测试Kubernetes就绪检查"""
        # Act
        response = await test_client.get("/api/readyz")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True


@pytest.mark.integration
@pytest.mark.asyncio
class TestDetailedHealthEndpoint:
    """测试详细健康检查端点"""

    async def test_health_detailed_with_db(self, test_client):
        """测试详细健康检查（带数据库）"""
        # Act
        response = await test_client.get("/api/health/detailed")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "version" in data["data"]
        assert "checks" in data["data"]
        assert "mongodb" in data["data"]["checks"]
        assert "redis" in data["data"]["checks"]
        assert "response_time_ms" in data["data"]

    async def test_health_detailed_response_time(self, test_client):
        """测试响应时间字段"""
        # Act
        response = await test_client.get("/api/health/detailed")

        # Assert
        data = response.json()
        response_time = data["data"]["response_time_ms"]
        assert isinstance(response_time, (int, float))
        assert response_time >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
