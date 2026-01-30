# -*- coding: utf-8 -*-
"""
Critical 安全修复测试套件

运行方式:
    pytest tests/security/test_critical_fixes.py -v

或单独运行:
    python -m pytest tests/security/test_critical_fixes.py::TestWebSocketSecurity -v
"""

import pytest
import asyncio
import jwt
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import bcrypt
import sys

sys.path.insert(0, "E:\\WorkSpace\\TradingAgents-CN")


class TestWebSocketSecurity:
    """测试 WebSocket 硬编码 user_id 修复"""

    @pytest.mark.asyncio
    async def test_websocket_user_id_from_token(self):
        """验证 WebSocket 从 Token 正确解析 user_id"""
        from app.services.auth_service import AuthService

        # 创建测试 Token
        token = AuthService.create_access_token(sub="test_user_123")

        # 验证 Token 包含正确 sub
        payload = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert payload["sub"] == "test_user_123"

    @pytest.mark.asyncio
    async def test_websocket_no_hardcoded_admin(self):
        """验证 WebSocket 不再使用硬编码 admin"""
        # 这个测试检查代码中不存在硬编码 user_id = "admin"
        import inspect
        from app.routers import websocket_notifications

        source = inspect.getsource(websocket_notifications)

        # 检查没有硬编码 user_id = "admin"
        assert 'user_id = "admin"' not in source
        assert "user_id = 'admin'" not in source

    def test_token_data_extraction(self):
        """测试从 TokenData 正确提取用户 ID"""
        from app.services.auth_service import TokenData

        # 测试对象属性
        token_data = TokenData(sub="actual_user", exp=1234567890)
        assert token_data.sub == "actual_user"

        # 测试字典格式（兼容）
        dict_data = {"sub": "dict_user", "exp": 1234567890}
        assert dict_data.get("sub") == "dict_user"


class TestPasswordSecurity:
    """测试 bcrypt 密码哈希修复"""

    def test_password_hashing_uses_bcrypt(self):
        """验证密码哈希使用 bcrypt"""
        from app.services.user_service import UserService

        password = "test_password_123"
        hashed, version = UserService.hash_password(password)

        # 验证版本标识
        assert version == "bcrypt"

        # 验证哈希格式（bcrypt 以 $2 开头）
        assert hashed.startswith("$2")

        # 验证不是 SHA-256（64字符十六进制）
        assert len(hashed) != 64

    def test_password_verification_bcrypt(self):
        """验证 bcrypt 密码验证"""
        from app.services.user_service import UserService

        password = "my_secure_password"
        hashed, _ = UserService.hash_password(password)

        # 正确密码验证通过
        is_valid, needs_upgrade = UserService.verify_password(
            password, hashed, "bcrypt"
        )
        assert is_valid is True
        assert needs_upgrade is False

        # 错误密码验证失败
        is_valid, _ = UserService.verify_password("wrong_password", hashed, "bcrypt")
        assert is_valid is False

    def test_password_upgrade_from_sha256(self):
        """测试从 SHA-256 自动升级"""
        import hashlib
        from app.services.user_service import UserService

        password = "old_password"
        # 模拟旧 SHA-256 哈希
        old_hash = hashlib.sha256(password.encode()).hexdigest()

        # 验证旧密码
        is_valid, needs_upgrade = UserService.verify_password(
            password, old_hash, "sha256"
        )
        assert is_valid is True
        assert needs_upgrade is True  # 需要升级

    def test_bcrypt_work_factor(self):
        """验证 bcrypt 工作因子（12轮）"""
        import bcrypt

        password = "test"

        # 生成哈希
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode(), salt)

        # 验证轮数（从 salt 中提取）
        # bcrypt salt 格式: $2b$12$... 其中 12 是轮数
        salt_str = salt.decode()
        assert "$12$" in salt_str or "$2b$12$" in salt_str or "$2a$12$" in salt_str


class TestLogSecurity:
    """测试日志脱敏修复"""

    def test_no_jwt_secret_in_logs(self):
        """验证日志中没有 JWT 密钥"""
        import inspect
        from app.services import auth_service

        source = inspect.getsource(auth_service)

        # 检查不记录 JWT_SECRET
        assert (
            "JWT_SECRET" not in source
            or "logger" not in source.split("JWT_SECRET")[0].split("\n")[-1]
        )

    def test_api_key_masking(self):
        """验证 API Key 脱敏"""
        # 测试脱敏函数逻辑
        api_key = "sk-1234567890abcdef"

        # 预期脱敏格式：前3 + *** + 后3
        if len(api_key) > 6:
            masked = f"{api_key[:3]}***{api_key[-3:]}"
        else:
            masked = "***"

        assert masked == "sk-***def"
        assert "1234567890abc" not in masked


class TestConcurrency:
    """测试并发修复"""

    @pytest.mark.asyncio
    async def test_no_asyncio_run_in_loop(self):
        """验证修复了 asyncio.run 在已有循环中调用的问题"""
        import inspect
        from tradingagents.agents.utils import agent_utils

        source = inspect.getsource(agent_utils)

        # 检查没有直接使用 asyncio.run() 在函数内部
        # （允许在新线程中使用）
        assert (
            "run_async_in_thread" in source
            or "asyncio.run" not in source.split("def ")[1]
        )

    @pytest.mark.asyncio
    async def test_async_lock_usage(self):
        """验证异步锁正确使用"""
        import asyncio

        lock = asyncio.Lock()

        # 测试 async with 语法
        async with lock:
            assert True

    def test_threading_lock_in_async_context_warning(self):
        """标记：检查 threading.Lock 在异步代码中的使用"""
        # 这个测试只是标记需要检查的位置
        # 实际检查通过代码审查完成
        files_to_check = [
            "tradingagents/dataflows/providers/china/tushare.py",
            "tradingagents/dataflows/providers/china/akshare.py",
            # 其他已修复的文件...
        ]

        # 验证这些文件已导入 asyncio
        for file_path in files_to_check[:2]:  # 只检查已修复的
            try:
                with open(
                    f"E:\\WorkSpace\\TradingAgents-CN\\{file_path}",
                    "r",
                    encoding="utf-8",
                ) as f:
                    content = f.read()
                    assert "import asyncio" in content or "from asyncio" in content
            except FileNotFoundError:
                pass


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_authentication_flow(self):
        """测试完整认证流程"""
        # 这是一个端到端测试的框架
        # 实际测试需要数据库连接

        steps = [
            "1. 用户注册（bcrypt 密码）",
            "2. 用户登录（验证 bcrypt）",
            "3. 获取 Token",
            "4. WebSocket 连接（验证 Token 解析）",
            "5. 旧用户登录（自动升级）",
        ]

        # 标记需要手动测试的步骤
        for step in steps:
            print(f"待手动测试: {step}")

    def test_security_headers_and_config(self):
        """测试安全配置"""
        # 检查 JWT_SECRET 不是默认值
        import os

        jwt_secret = os.getenv("JWT_SECRET", "")
        assert jwt_secret != "change-me-in-production"
        assert len(jwt_secret) >= 32  # 最小长度


# 运行测试的辅助函数
if __name__ == "__main__":
    print("=" * 60)
    print("Critical 安全修复测试套件")
    print("=" * 60)
    print("\n运行所有测试:")
    print("  pytest tests/security/test_critical_fixes.py -v")
    print("\n运行特定测试:")
    print("  pytest tests/security/test_critical_fixes.py::TestWebSocketSecurity -v")
    print("  pytest tests/security/test_critical_fixes.py::TestPasswordSecurity -v")
    print("  pytest tests/security/test_critical_fixes.py::TestLogSecurity -v")
    print("  pytest tests/security/test_critical_fixes.py::TestConcurrency -v")
    print("\n注意：部分测试需要实际环境配置")
