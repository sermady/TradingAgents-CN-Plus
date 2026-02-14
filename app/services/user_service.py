# -*- coding: utf-8 -*-
"""
用户服务 - 基于数据库的用户管理

重构：继承BaseCRUDService，消除重复CRUD代码
"""

import hashlib
from datetime import datetime
from typing import Optional, List

from bson import ObjectId

from app.core.config import settings
from app.models.user import User, UserCreate, UserUpdate, UserResponse
from app.services.base_crud_service import BaseCRUDService

# 尝试导入日志管理器
try:
    from tradingagents.utils.logging_manager import get_logger
except ImportError:
    import logging
    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)


logger = get_logger("user_service")


class UserService(BaseCRUDService):
    """用户服务类 - 基于BaseCRUDService"""

    def __init__(self):
        super().__init__()

    @property
    def collection_name(self) -> str:
        """MongoDB集合名称"""
        return "users"

    # ========== 密码工具方法（保留业务逻辑）==========

    @staticmethod
    def hash_password(password: str) -> tuple[str, str]:
        """
        密码哈希 - 使用 bcrypt (12轮)

        Returns:
            tuple: (hashed_password, version)
        """
        import bcrypt
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
        return hashed, "bcrypt"

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str, password_version: str = None) -> tuple[bool, bool]:
        """
        验证密码 - 双轨制支持（bcrypt + 兼容旧 SHA-256）

        Returns:
            tuple: (is_valid, needs_upgrade)
        """
        import bcrypt

        # 如果是 bcrypt 格式
        if password_version == "bcrypt" or hashed_password.startswith("$2"):
            try:
                is_valid = bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
                return is_valid, False
            except Exception:
                return False, False

        # 兼容旧 SHA-256
        if password_version == "sha256" or len(hashed_password) == 64:
            legacy_hash = hashlib.sha256(plain_password.encode()).hexdigest()
            is_valid = legacy_hash == hashed_password
            return is_valid, is_valid

        # 未知格式，尝试 bcrypt 验证
        try:
            is_valid = bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
            return is_valid, False
        except Exception:
            return False, False

    # ========== 用户CRUD操作（使用基类方法）==========

    async def create_user(self, user_data: UserCreate) -> Optional[User]:
        """创建用户"""
        # 检查用户名是否已存在
        existing_user = await self.get_by_field("username", user_data.username)
        if existing_user:
            logger.warning(f"用户名已存在: {user_data.username}")
            return None

        # 检查邮箱是否已存在
        existing_email = await self.get_by_field("email", user_data.email)
        if existing_email:
            logger.warning(f"邮箱已存在: {user_data.email}")
            return None

        # 密码哈希
        hashed_password, password_version = self.hash_password(user_data.password)

        # 创建用户文档
        user_doc = {
            "username": user_data.username,
            "email": user_data.email,
            "hashed_password": hashed_password,
            "password_version": password_version,
            "is_active": True,
            "is_verified": False,
            "is_admin": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_login": None,
            "preferences": {
                "default_market": "A股",
                "default_depth": "3",
                "default_analysts": ["市场分析师", "基本面分析师"],
                "auto_refresh": True,
                "refresh_interval": 30,
                "ui_theme": "light",
                "sidebar_width": 240,
                "language": "zh-CN",
                "notifications_enabled": True,
                "email_notifications": False,
                "desktop_notifications": True,
                "analysis_complete_notification": True,
                "system_maintenance_notification": True,
            },
            "daily_quota": 1000,
            "concurrent_limit": 3,
            "total_analyses": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "favorite_stocks": [],
        }

        user_id = await self.create(user_doc)
        if user_id:
            logger.info(f"用户创建成功: {user_data.username}")
            return await self.get_user_by_id(user_id)
        return None

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        user_doc = await self.get_by_field("username", username)
        if user_doc:
            return User(**user_doc)
        return None

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根据用户ID获取用户"""
        user_doc = await self.get_by_id(user_id)
        if user_doc:
            return User(**user_doc)
        return None

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """用户认证"""
        logger.info(f"开始认证用户: {username}")

        # 查找用户
        user_doc = await self.get_by_field("username", username)
        if not user_doc:
            logger.warning(f"用户不存在: {username}")
            return None

        # 验证密码
        stored_password_hash = user_doc.get("hashed_password", "")
        password_version = user_doc.get("password_version")

        is_valid, needs_upgrade = self.verify_password(password, stored_password_hash, password_version)

        if not is_valid:
            logger.warning(f"密码错误: {username}")
            return None

        # 自动迁移：如果密码是旧 SHA-256 格式，升级到 bcrypt
        if needs_upgrade:
            logger.info(f"用户 {username} 的密码使用旧格式，自动升级到 bcrypt...")
            try:
                new_hashed_password, new_version = self.hash_password(password)
                await self.update(str(user_doc.get("id")), {
                    "hashed_password": new_hashed_password,
                    "password_version": new_version,
                })
                logger.info(f"用户 {username} 的密码已成功升级到 bcrypt")
                user_doc["hashed_password"] = new_hashed_password
                user_doc["password_version"] = new_version
            except Exception as e:
                logger.error(f"密码自动升级失败: {e}")

        # 检查用户是否激活
        if not user_doc.get("is_active", True):
            logger.warning(f"用户已禁用: {username}")
            return None

        # 更新最后登录时间
        await self.update(str(user_doc.get("id")), {"last_login": datetime.utcnow()})

        logger.info(f"用户认证成功: {username}")
        return User(**user_doc)

    async def update_user(self, username: str, user_data: UserUpdate) -> Optional[User]:
        """更新用户信息"""
        # 获取用户
        user = await self.get_user_by_username(username)
        if not user:
            logger.warning(f"用户不存在: {username}")
            return None

        update_data = {}

        # 只更新提供的字段
        if user_data.email:
            # 检查邮箱是否已被其他用户使用
            existing = await self.get_by_field("email", user_data.email)
            if existing and existing.get("username") != username:
                logger.warning(f"邮箱已被使用: {user_data.email}")
                return None
            update_data["email"] = user_data.email

        if user_data.preferences:
            update_data["preferences"] = user_data.preferences.model_dump()

        if user_data.daily_quota is not None:
            update_data["daily_quota"] = user_data.daily_quota

        if user_data.concurrent_limit is not None:
            update_data["concurrent_limit"] = user_data.concurrent_limit

        if not update_data:
            logger.warning(f"无需更新: {username}")
            return user

        success = await self.update(str(user.id), update_data)
        if success:
            logger.info(f"用户信息更新成功: {username}")
            return await self.get_user_by_username(username)
        return None

    async def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """修改密码"""
        # 验证旧密码
        user = await self.authenticate_user(username, old_password)
        if not user:
            logger.warning(f"旧密码验证失败: {username}")
            return False

        # 使用 bcrypt 哈希新密码
        new_hashed_password, password_version = self.hash_password(new_password)
        success = await self.update(str(user.id), {
            "hashed_password": new_hashed_password,
            "password_version": password_version,
        })

        if success:
            logger.info(f"密码修改成功: {username}")
            return True
        return False

    async def reset_password(self, username: str, new_password: str) -> bool:
        """重置密码（管理员操作）"""
        user = await self.get_user_by_username(username)
        if not user:
            logger.warning(f"用户不存在: {username}")
            return False

        new_hashed_password, password_version = self.hash_password(new_password)
        success = await self.update(str(user.id), {
            "hashed_password": new_hashed_password,
            "password_version": password_version,
        })

        if success:
            logger.info(f"密码重置成功: {username}")
            return True
        return False

    async def create_admin_user(
        self,
        username: str = "admin",
        password: str = "admin123",
        email: str = "admin@tradingagents.cn",
    ) -> Optional[User]:
        """创建管理员用户"""
        # 检查是否已存在管理员
        existing_admin = await self.get_by_field("username", username)
        if existing_admin:
            logger.info(f"管理员用户已存在: {username}")
            return User(**existing_admin)

        # 密码哈希
        hashed_password, password_version = self.hash_password(password)

        # 创建管理员用户文档
        admin_doc = {
            "username": username,
            "email": email,
            "hashed_password": hashed_password,
            "password_version": password_version,
            "is_active": True,
            "is_verified": True,
            "is_admin": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_login": None,
            "preferences": {
                "default_market": "A股",
                "default_depth": "深度",
                "ui_theme": "light",
                "language": "zh-CN",
                "notifications_enabled": True,
                "email_notifications": False,
            },
            "daily_quota": 10000,
            "concurrent_limit": 10,
            "total_analyses": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "favorite_stocks": [],
        }

        admin_id = await self.create(admin_doc)
        if admin_id:
            logger.info(f"管理员用户创建成功: {username}")
            logger.info("   请立即修改默认密码！")
            return await self.get_user_by_id(admin_id)
        return None

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """获取用户列表"""
        user_docs = await self.list(skip=skip, limit=limit, sort=[("created_at", -1)])
        users = []

        for user_doc in user_docs:
            user = User(**user_doc)
            users.append(UserResponse(
                id=str(user.id),
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                is_verified=user.is_verified,
                created_at=user.created_at,
                last_login=user.last_login,
                preferences=user.preferences,
                daily_quota=user.daily_quota,
                concurrent_limit=user.concurrent_limit,
                total_analyses=user.total_analyses,
                successful_analyses=user.successful_analyses,
                failed_analyses=user.failed_analyses,
            ))

        return users

    async def deactivate_user(self, username: str) -> bool:
        """禁用用户"""
        user = await self.get_by_field("username", username)
        if not user:
            logger.warning(f"用户不存在: {username}")
            return False

        success = await self.update(user.get("id"), {"is_active": False})
        if success:
            logger.info(f"用户已禁用: {username}")
            return True
        return False

    async def activate_user(self, username: str) -> bool:
        """激活用户"""
        user = await self.get_by_field("username", username)
        if not user:
            logger.warning(f"用户不存在: {username}")
            return False

        success = await self.update(user.get("id"), {"is_active": True})
        if success:
            logger.info(f"用户已激活: {username}")
            return True
        return False


# 全局用户服务实例
user_service = UserService()
