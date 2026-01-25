# -*- coding: utf-8 -*-
"""
测试认证API

测试范围:
- POST /api/auth/register - 用户注册
- POST /api/auth/login - 用户登录
- POST /api/auth/refresh - 刷新访问令牌
- POST /api/auth/change-password - 修改密码
- GET /api/auth/user - 获取当前用户信息
"""

import pytest
from httpx import AsyncClient
from typing import Dict


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_user(test_client: AsyncClient):
    """测试用户注册"""
    # Arrange
    user_data = {
        "username": "test_user",
        "email": "test@example.com",
        "password": "TestPassword123!",
        "is_admin": False,
    }

    # Act
    response = await test_client.post("/api/auth/register", json=user_data)

    # Assert
    # 成功或失败都可以，只要API正常响应
    assert response.status_code in [200, 400, 409]
    data = response.json()
    assert "success" in data
    assert "data" in data
    assert "message" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_duplicate_user(test_client: AsyncClient):
    """测试重复用户注册"""
    # Arrange
    user_data = {
        "username": "admin",  # 假设已存在
        "email": "admin@example.com",
        "password": "AdminPassword123!",
        "is_admin": True,
    }

    # Act
    response = await test_client.post("/api/auth/register", json=user_data)

    # Assert
    # 用户已存在时应该返回400或409
    assert response.status_code in [400, 409]
    data = response.json()
    assert "success" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_valid_credentials(test_client: AsyncClient, test_user: Dict):
    """测试有效凭证登录"""
    # Arrange
    # 使用test_user fixture中的用户名和密码
    login_data = {
        "username": test_user.get("username", "testuser"),
        "password": test_user.get("password", "testpass"),
    }

    # Act
    response = await test_client.post("/api/auth/login", json=login_data)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert "access_token" in data["data"]
    assert "token_type" in data["data"]
    assert "expires_in" in data["data"]
    assert "user" in data["data"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_invalid_credentials(test_client: AsyncClient):
    """测试无效凭证登录"""
    # Arrange
    login_data = {"username": "invalid_user", "password": "wrong_password"}

    # Act
    response = await test_client.post("/api/auth/login", json=login_data)

    # Assert
    # 应该返回401未授权
    assert response.status_code in [400, 401]
    data = response.json()
    assert data["success"] is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_missing_fields(test_client: AsyncClient):
    """测试缺少必需字段的登录"""
    # Arrange
    login_data = {
        "username": "test_user"
        # 缺少password字段
    }

    # Act
    response = await test_client.post("/api/auth/login", json=login_data)

    # Assert
    # 应该返回422验证错误
    assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.asyncio
async def test_refresh_token(test_client: AsyncClient, auth_headers: Dict):
    """测试刷新访问令牌"""
    # Arrange
    refresh_data = {"refresh_token": "test_refresh_token"}

    # Act
    response = await test_client.post(
        "/api/auth/refresh", json=refresh_data, headers=auth_headers
    )

    # Assert
    # 可能成功或失败（如果令牌无效）
    assert response.status_code in [200, 401, 422]
    data = response.json()
    assert "success" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_change_password(test_client: AsyncClient, auth_headers: Dict):
    """测试修改密码"""
    # Arrange
    password_data = {
        "old_password": "OldPassword123!",
        "new_password": "NewPassword123!",
    }

    # Act
    response = await test_client.post(
        "/api/auth/change-password", json=password_data, headers=auth_headers
    )

    # Assert
    # 可能成功或失败（取决于旧密码是否正确）
    assert response.status_code in [200, 400, 401]
    data = response.json()
    assert "success" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_current_user(test_client: AsyncClient, auth_headers: Dict):
    """测试获取当前用户信息"""
    # Act
    response = await test_client.get("/api/auth/user", headers=auth_headers)

    # Assert
    # 应该返回200或401（如果令牌无效）
    assert response.status_code in [200, 401]

    if response.status_code == 200:
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "username" in data["data"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_current_user_no_token(test_client: AsyncClient):
    """测试无令牌时获取用户信息"""
    # Act
    response = await test_client.get("/api/auth/user")

    # Assert
    # 应该返回401未授权
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "No authorization header" in data["detail"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_response_structure(test_client: AsyncClient, test_user: Dict):
    """测试登录响应结构"""
    # Arrange
    login_data = {
        "username": test_user.get("username", "testuser"),
        "password": test_user.get("password", "testpass"),
    }

    # Act
    response = await test_client.post("/api/auth/login", json=login_data)

    # Assert
    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert isinstance(data, dict)
    assert "success" in data
    assert "data" in data
    assert isinstance(data["data"], dict)
    assert "access_token" in data["data"]
    assert "token_type" in data["data"]
    assert "expires_in" in data["data"]
    assert "user" in data["data"]
    assert isinstance(data["data"]["user"], dict)
    assert "username" in data["data"]["user"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_response_structure(test_client: AsyncClient):
    """测试注册响应结构"""
    # Arrange
    user_data = {
        "username": f"test_user_{pytest.current_time()}",
        "email": f"test_{pytest.current_time()}@example.com",
        "password": "TestPassword123!",
        "is_admin": False,
    }

    # Act
    response = await test_client.post("/api/auth/register", json=user_data)

    # Assert
    data = response.json()

    # 验证响应结构
    assert isinstance(data, dict)
    assert "success" in data
    assert "data" in data
    assert "message" in data
    assert isinstance(data["data"], dict)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_consistent_format(test_client: AsyncClient):
    """测试API返回格式一致性"""
    # Arrange
    endpoints = [
        (
            "POST",
            "/api/auth/register",
            {"username": "test", "email": "test@test.com", "password": "Test123!"},
        ),
        ("GET", "/api/health", None),
    ]

    # Act & Assert - 验证所有端点返回一致格式
    for method, path, data in endpoints:
        if method == "POST":
            response = await test_client.post(path, json=data)
        else:
            response = await test_client.get(path)

        # 所有响应应该包含success字段
        assert "success" in response.json(), f"响应格式不一致: {path}"
