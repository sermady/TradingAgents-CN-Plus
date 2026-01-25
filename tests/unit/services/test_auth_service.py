# -*- coding: utf-8 -*-
"""
Auth Service 单元测试

测试认证服务的核心功能：
- 用户注册
- 用户登录
- Token生成和验证
- 密码哈希和验证
- 用户查询
- 权限验证
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError

from app.services.auth_service import AuthService
from app.models.user import UserCreate, UserLogin, UserResponse


# ==============================================================================
# 测试认证服务初始化
# ==============================================================================


@pytest.mark.unit
def test_auth_service_init():
    """测试认证服务初始化"""
    with patch("app.services.auth_service.get_mongo_db"):
        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    service = AuthService()

                    assert service.pwd_context is not None
                    assert isinstance(service.pwd_context, CryptContext)


# ==============================================================================
# 测试密码哈希
# ==============================================================================


@pytest.mark.unit
def test_hash_password():
    """测试密码哈希"""
    with patch("app.services.auth_service.get_mongo_db"):
        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    service = AuthService()

                    password = "Test123!"
                    hashed = service.hash_password(password)

                    # 哈希后的密码应该不同
                    assert hashed != password

                    # 哈希后的密码应该一致（相同密码）
                    hashed2 = service.hash_password(password)
                    assert hashed == hashed2


@pytest.mark.unit
def test_hash_password_different():
    """测试不同密码哈希不同"""
    with patch("app.services.auth_service.get_mongo_db"):
        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    service = AuthService()

                    password1 = "Test123!"
                    password2 = "Test456!"

                    hashed1 = service.hash_password(password1)
                    hashed2 = service.hash_password(password2)

                    # 不同密码应该产生不同哈希
                    assert hashed1 != hashed2


@pytest.mark.unit
def test_verify_password():
    """测试密码验证"""
    with patch("app.services.auth_service.get_mongo_db"):
        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    service = AuthService()

                    password = "Test123!"
                    hashed = service.hash_password(password)

                    # 正确密码应该验证通过
                    assert service.verify_password(password, hashed) is True

                    # 错误密码应该验证失败
                    assert service.verify_password("Wrong123!", hashed) is False


@pytest.mark.unit
def test_verify_empty_password():
    """测试空密码验证"""
    with patch("app.services.auth_service.get_mongo_db"):
        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    service = AuthService()

                    password = ""
                    hashed = service.hash_password(password)

                    assert service.verify_password("", hashed) is True
                    assert service.verify_password("test", hashed) is False


# ==============================================================================
# 测试Token生成
# ==============================================================================


@pytest.mark.unit
def test_create_access_token():
    """测试生成访问Token"""
    with patch("app.services.auth_service.get_mongo_db"):
        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    service = AuthService()

                    data = {"sub": "test_user_id", "username": "testuser"}
                    token = service.create_access_token(data=data)

                    # Token应该不为空
                    assert token is not None
                    assert len(token) > 0

                    # Token应该是有效的JWT格式
                    parts = token.split(".")
                    assert len(parts) == 3


@pytest.mark.unit
def test_decode_access_token():
    """测试解码访问Token"""
    with patch("app.services.auth_service.get_mongo_db"):
        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    service = AuthService()

                    data = {"sub": "test_user_id", "username": "testuser"}
                    token = service.create_access_token(data=data)

                    # 解码Token
                    decoded = service.decode_access_token(token)

                    assert decoded is not None
                    assert decoded["sub"] == "test_user_id"
                    assert decoded["username"] == "testuser"


@pytest.mark.unit
def test_decode_invalid_token():
    """测试解码无效Token"""
    with patch("app.services.auth_service.get_mongo_db"):
        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    service = AuthService()

                    # 无效Token
                    invalid_tokens = [
                        "invalid.token.string",
                        "",
                        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid",
                        "Bearer token",
                    ]

                    for invalid_token in invalid_tokens:
                        decoded = service.decode_access_token(invalid_token)
                        assert decoded is None


@pytest.mark.unit
def test_token_expiration():
    """测试Token过期"""
    with patch("app.services.auth_service.get_mongo_db"):
        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                # 设置过期时间为1秒
                with patch(
                    "app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 0.016
                ):  # 约1秒
                    service = AuthService()

                    data = {"sub": "test_user_id"}
                    token = service.create_access_token(data=data)

                    # 立即解码应该成功
                    decoded = service.decode_access_token(token)
                    assert decoded is not None

                    # 等待过期后应该失败
                    import time

                    time.sleep(2)
                    decoded_expired = service.decode_access_token(token)
                    assert decoded_expired is None


# ==============================================================================
# 测试用户注册
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_user_success():
    """测试成功注册用户"""
    with patch("app.services.auth_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_collection.find_one.return_value = None  # 用户不存在
        mock_collection.insert_one.return_value = AsyncMock(inserted_id="user_123")
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    service = AuthService()

                    user_data = UserCreate(
                        username="testuser",
                        email="test@example.com",
                        password="Test123!",
                        full_name="测试用户",
                    )

                    result = await service.register_user(user_data)

                    assert result is not None
                    assert result.username == "testuser"
                    assert result.email == "test@example.com"
                    assert result.hashed_password is not None
                    assert result.hashed_password != "Test123!"

                    # 验证数据库调用
                    mock_collection.find_one.assert_called()
                    mock_collection.insert_one.assert_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_user_duplicate_username():
    """测试注册重复用户名"""
    with patch("app.services.auth_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        # 用户已存在
        mock_collection.find_one.return_value = {
            "username": "testuser",
            "email": "existing@example.com",
        }
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    service = AuthService()

                    user_data = UserCreate(
                        username="testuser",
                        email="new@example.com",
                        password="Test123!",
                        full_name="测试用户",
                    )

                    # 应该抛出异常或返回错误
                    with pytest.raises(Exception):
                        await service.register_user(user_data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_user_weak_password():
    """测试弱密码注册"""
    with patch("app.services.auth_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_collection.find_one.return_value = None
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    service = AuthService()

                    weak_passwords = [
                        "",
                        "123",
                        "password",
                        "test",
                        "Test",  # 缺少数字和特殊字符
                    ]

                    for weak_password in weak_passwords:
                        user_data = UserCreate(
                            username="testuser",
                            email="test@example.com",
                            password=weak_password,
                            full_name="测试用户",
                        )

                        # 应该抛出验证异常
                        with pytest.raises(Exception):
                            await service.register_user(user_data)


# ==============================================================================
# 测试用户登录
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authenticate_user_success():
    """测试成功认证用户"""
    with patch("app.services.auth_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        # 返回已注册用户
        mock_collection.find_one.return_value = {
            "_id": "user_123",
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": "$2b$12$test_hashed_password",  # 模拟哈希
            "is_active": True,
            "created_at": datetime.utcnow(),
        }
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    service = AuthService()

                    # Mock密码验证
                    with patch.object(service, "verify_password", return_value=True):
                        login_data = UserLogin(username="testuser", password="Test123!")

                        result = await service.authenticate_user(login_data)

                        assert result is not None
                        assert result.access_token is not None
                        assert result.token_type == "bearer"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authenticate_user_wrong_password():
    """测试错误密码"""
    with patch("app.services.auth_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_collection.find_one.return_value = {
            "_id": "user_123",
            "username": "testuser",
            "hashed_password": "$2b$12$test_hashed_password",
            "is_active": True,
        }
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    service = AuthService()

                    # Mock密码验证失败
                    with patch.object(service, "verify_password", return_value=False):
                        login_data = UserLogin(
                            username="testuser", password="Wrong123!"
                        )

                        # 应该抛出异常
                        with pytest.raises(Exception):
                            await service.authenticate_user(login_data)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_authenticate_user_not_found():
    """测试用户不存在"""
    with patch("app.services.auth_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_collection.find_one.return_value = None  # 用户不存在
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    service = AuthService()

                    login_data = UserLogin(username="nonexistent", password="Test123!")

                    # 应该抛出异常
                    with pytest.raises(Exception):
                        await service.authenticate_user(login_data)


# ==============================================================================
# 测试用户查询
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_by_id():
    """测试通过ID获取用户"""
    with patch("app.services.auth_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_collection.find_one.return_value = {
            "_id": "user_123",
            "username": "testuser",
            "email": "test@example.com",
            "is_active": True,
        }
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    service = AuthService()

                    user = await service.get_user_by_id("user_123")

                    assert user is not None
                    assert user.username == "testuser"
                    assert user.email == "test@example.com"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_by_username():
    """测试通过用户名获取用户"""
    with patch("app.services.auth_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_collection.find_one.return_value = {
            "_id": "user_123",
            "username": "testuser",
            "email": "test@example.com",
            "is_active": True,
        }
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    service = AuthService()

                    user = await service.get_user_by_username("testuser")

                    assert user is not None
                    assert user.username == "testuser"


# ==============================================================================
# 测试Token刷新
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_token():
    """测试刷新Token"""
    with patch("app.services.auth_service.get_mongo_db"):
        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    service = AuthService()

                    data = {"sub": "user_123", "username": "testuser"}
                    old_token = service.create_access_token(data=data)

                    # 刷新Token
                    new_token = await service.refresh_token(old_token)

                    assert new_token is not None
                    assert new_token != old_token

                    # 新Token应该包含相同的用户信息
                    decoded_old = service.decode_access_token(old_token)
                    decoded_new = service.decode_access_token(new_token)

                    assert decoded_old["sub"] == decoded_new["sub"]
                    assert decoded_old["username"] == decoded_new["username"]


# ==============================================================================
# 测试错误处理
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_error_handling_in_register():
    """测试注册时的错误处理"""
    with patch("app.services.auth_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        # 模拟数据库错误
        mock_collection.insert_one.side_effect = Exception("Database error")
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    service = AuthService()

                    user_data = UserCreate(
                        username="testuser",
                        email="test@example.com",
                        password="Test123!",
                        full_name="测试用户",
                    )

                    # 应该抛出异常
                    with pytest.raises(Exception):
                        await service.register_user(user_data)


# ==============================================================================
# 测试边界条件
# ==============================================================================


@pytest.mark.unit
def test_hash_password_special_chars():
    """测试特殊字符密码哈希"""
    with patch("app.services.auth_service.get_mongo_db"):
        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    service = AuthService()

                    special_passwords = [
                        "密码123!",
                        "P@ssw0rd",
                        "Test!@#$%",
                        "测试Test123!",
                    ]

                    for password in special_passwords:
                        hashed = service.hash_password(password)
                        assert hashed is not None
                        assert hashed != password
                        assert service.verify_password(password, hashed) is True


@pytest.mark.unit
def test_token_with_extra_data():
    """测试包含额外数据的Token"""
    with patch("app.services.auth_service.get_mongo_db"):
        with patch("app.services.auth_service.JWT_SECRET", "test_secret"):
            with patch("app.services.auth_service.JWT_ALGORITHM", "HS256"):
                with patch("app.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    service = AuthService()

                    data = {
                        "sub": "user_123",
                        "username": "testuser",
                        "role": "admin",
                        "permissions": ["read", "write"],
                    }
                    token = service.create_access_token(data=data)

                    decoded = service.decode_access_token(token)

                    assert decoded is not None
                    assert decoded["sub"] == "user_123"
                    assert decoded["username"] == "testuser"
                    assert decoded["role"] == "admin"
                    assert "read" in decoded["permissions"]
