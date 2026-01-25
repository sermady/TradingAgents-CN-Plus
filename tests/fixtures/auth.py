# -*- coding: utf-8 -*-
"""
认证相关Fixtures
"""

import pytest
from typing import Dict, Any
from httpx import AsyncClient


@pytest.fixture
def test_user_data() -> Dict[str, Any]:
    """
    测试用户数据
    """
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "Test123!",
        "full_name": "测试用户",
    }


@pytest.fixture
def admin_user_data() -> Dict[str, Any]:
    """
    测试管理员数据
    """
    return {
        "username": "admin",
        "email": "admin@example.com",
        "password": "Admin123!",
        "full_name": "管理员",
        "role": "admin",
    }


@pytest.fixture
async def test_user(
    mongodb_client, test_user_data: Dict[str, Any], test_client: AsyncClient
) -> Dict[str, Any]:
    """
    创建并登录测试用户
    直接在数据库中创建用户，然后通过API登录
    返回用户信息和token
    """
    from app.services.user_service import UserService

    # 直接在数据库中创建用户
    db = mongodb_client["tradingagents_test"]
    hashed_password = UserService.hash_password(test_user_data["password"])

    user_doc = {
        "username": test_user_data["username"],
        "email": test_user_data["email"],
        "full_name": test_user_data.get("full_name", ""),
        "hashed_password": hashed_password,
        "is_active": True,
        "is_admin": False,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }

    # 插入用户
    result = db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)

    # 登录获取token
    login_data = {
        "username": test_user_data["username"],
        "password": test_user_data["password"],
    }
    login_response = await test_client.post("/api/auth/login", json=login_data)
    assert login_response.status_code == 200, f"登录失败: {login_response.text}"

    token_data = login_response.json()

    user_doc_copy = user_doc.copy()
    user_doc_copy["id"] = user_id
    user_doc_copy.pop("hashed_password", None)

    return {
        "user": user_doc_copy,
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "token_type": token_data.get("token_type", "bearer"),
    }


@pytest.fixture
async def admin_user(
    mongodb_client, admin_user_data: Dict[str, Any], test_client: AsyncClient
) -> Dict[str, Any]:
    """
    创建并登录管理员用户
    直接在数据库中创建用户，设置管理员权限
    """
    from app.services.user_service import UserService

    # 直接在数据库中创建管理员用户
    db = mongodb_client["tradingagents_test"]
    hashed_password = UserService.hash_password(admin_user_data["password"])

    user_doc = {
        "username": admin_user_data["username"],
        "email": admin_user_data["email"],
        "full_name": admin_user_data.get("full_name", ""),
        "hashed_password": hashed_password,
        "is_active": True,
        "is_admin": True,  # 设置为管理员
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    }

    # 插入用户
    result = db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)

    # 登录
    login_data = {
        "username": admin_user_data["username"],
        "password": admin_user_data["password"],
    }
    login_response = await test_client.post("/api/auth/login", json=login_data)
    assert login_response.status_code == 200, f"登录失败: {login_response.text}"

    token_data = login_response.json()

    user_doc_copy = user_doc.copy()
    user_doc_copy["id"] = user_id
    user_doc_copy.pop("hashed_password", None)

    return {
        "user": user_doc_copy,
        "access_token": token_data.get("access_token"),
        "refresh_token": token_data.get("refresh_token"),
        "token_type": token_data.get("token_type", "bearer"),
    }


@pytest.fixture
def auth_headers(test_user: Dict[str, Any]) -> Dict[str, str]:
    """
    认证请求头
    """
    token = test_user["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_user_headers(test_user: Dict[str, Any]) -> Dict[str, str]:
    """
    测试用户认证请求头（别名）
    """
    token = test_user["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(admin_user: Dict[str, Any]) -> Dict[str, str]:
    """
    管理员认证请求头
    """
    token = admin_user["access_token"]
    return {"Authorization": f"Bearer {token}"}
