# -*- coding: utf-8 -*-
"""
Refresh Token 服务
提供 refresh token 的注册、撤销、验证等功能
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

# 导入 Redis
from app.core.redis_client import RedisService, get_redis_service

logger = logging.getLogger(__name__)


class RefreshTokenService:
    """
    Refresh Token 管理服务

    使用 Redis 存储 refresh token 的元数据：
    - 用户的所有 refresh token 集合（方便撤销用户的所有token）
    - 全局撤销 token 集合（用于验证 token 是否已被撤销）
    """

    # Redis key 前缀
    USER_REFRESH_TOKENS_PREFIX = "user:refresh_tokens:"
    REVOKED_TOKENS_PREFIX = "revoked:token:"

    def __init__(self):
        self._redis_service: Optional[RedisService] = None

    def _get_redis(self) -> Optional[RedisService]:
        """获取 Redis 服务实例（延迟初始化）"""
        if self._redis_service is None:
            self._redis_service = get_redis_service()

        # 检查Redis是否可用
        if self._redis_service is None or self._redis_service.redis is None:
            return None

        return self._redis_service

    def _get_user_tokens_key(self, user_id: str) -> str:
        """获取用户 refresh token 集合的 key"""
        return f"{self.USER_REFRESH_TOKENS_PREFIX}{user_id}"

    def _get_revoked_token_key(self, jti: str) -> str:
        """获取撤销 token 的 key"""
        return f"{self.REVOKED_TOKENS_PREFIX}{jti}"

    async def register_refresh_token(
        self, user_id: str, jti: str, expires_days: int = 30
    ) -> bool:
        """
        注册新的 refresh token

        Args:
            user_id: 用户ID
            jti: Token 的 JWT ID
            expires_days: Token 过期天数

        Returns:
            bool: 是否注册成功
        """
        try:
            redis = self._get_redis()

            # 如果Redis不可用，记录警告并返回成功（降级处理）
            if redis is None:
                logger.warning("Redis不可用，跳过refresh token注册")
                return True

            key = self._get_user_tokens_key(user_id)
            expires_seconds = expires_days * 24 * 60 * 60

            # 使用 Redis Set 存储用户的所有 refresh token
            await redis.add_to_set(key, jti)
            # 设置过期时间
            await redis.redis.expire(key, expires_seconds)

            logger.debug(f"✅ Refresh token 已注册: user={user_id}, jti={jti[:16]}...")
            return True
        except Exception as e:
            logger.error(f"❌ 注册 refresh token 失败: {e}")
            return False

    async def revoke_refresh_token(self, user_id: str, jti: str) -> bool:
        """
        撤销指定的 refresh token

        Args:
            user_id: 用户ID
            jti: Token 的 JWT ID

        Returns:
            bool: 是否撤销成功
        """
        try:
            redis = self._get_redis()

            # 如果Redis不可用，跳过撤销操作
            if redis is None:
                logger.warning("Redis不可用，跳过refresh token撤销")
                return True

            # 从用户 token 集合中移除
            user_key = self._get_user_tokens_key(user_id)
            await redis.remove_from_set(user_key, jti)

            # 加入全局撤销列表（保留一段时间用于验证）
            revoked_key = self._get_revoked_token_key(jti)
            await redis.set_with_ttl(revoked_key, user_id, 7 * 24 * 60 * 60)  # 保留7天

            logger.info(f"🚫 Refresh token 已撤销: user={user_id}, jti={jti[:16]}...")
            return True
        except Exception as e:
            logger.error(f"❌ 撤销 refresh token 失败: {e}")
            return False

    async def revoke_all_user_tokens(self, user_id: str) -> bool:
        """
        撤销用户的所有 refresh token（登出所有设备）

        Args:
            user_id: 用户ID

        Returns:
            bool: 是否撤销成功
        """
        try:
            redis = self._get_redis()

            # 如果Redis不可用，跳过操作
            if redis is None:
                logger.warning("Redis不可用，跳过撤销所有用户token")
                return True

            key = self._get_user_tokens_key(user_id)

            # 获取所有 token
            tokens = await redis.redis.smembers(key)

            # 逐个加入撤销列表
            for jti in tokens:
                revoked_key = self._get_revoked_token_key(jti)
                await redis.set_with_ttl(revoked_key, user_id, 7 * 24 * 60 * 60)

            # 删除用户 token 集合
            await redis.redis.delete(key)

            logger.info(
                f"🚫 用户所有 refresh token 已撤销: user={user_id}, count={len(tokens)}"
            )
            return True
        except Exception as e:
            logger.error(f"❌ 撤销用户所有 token 失败: {e}")
            return False

    async def is_token_revoked(self, jti: str) -> bool:
        """
        检查 token 是否已被撤销

        Args:
            jti: Token 的 JWT ID

        Returns:
            bool: 是否已撤销
        """
        try:
            redis = self._get_redis()

            # 如果Redis不可用，跳过检查
            if redis is None:
                logger.warning("Redis不可用，跳过token撤销状态检查")
                return False

            revoked_key = self._get_revoked_token_key(jti)
            exists = await redis.redis.exists(revoked_key)
            return bool(exists)
        except Exception as e:
            logger.error(f"❌ 检查 token 撤销状态失败: {e}")
            return False  # 出错时保守起见，假设未撤销

    async def is_token_valid_for_user(self, user_id: str, jti: str) -> bool:
        """
        检查 token 是否对用户有效（存在于用户的 token 集合中且未被撤销）

        Args:
            user_id: 用户ID
            jti: Token 的 JWT ID

        Returns:
            bool: 是否有效
        """
        try:
            redis = self._get_redis()

            # 如果Redis不可用，跳过检查
            if redis is None:
                logger.warning("Redis不可用，跳过token有效性检查")
                return False

            # 检查是否在撤销列表
            if await self.is_token_revoked(jti):
                return False

            # 检查是否存在于用户的 token 集合
            key = self._get_user_tokens_key(user_id)
            is_member = await redis.is_in_set(key, jti)
            return bool(is_member)
        except Exception as e:
            logger.error(f"❌ 验证 token 有效性失败: {e}")
            return False

    async def cleanup_expired_tokens(self) -> int:
        """
        清理过期的 token 记录

        Returns:
            int: 清理的 token 数量
        """
        # Redis 会自动处理过期键，此方法用于手动清理或其他存储后端
        logger.debug("🧹 Refresh token 过期清理完成（Redis 自动处理）")
        return 0

    async def get_user_active_token_count(self, user_id: str) -> int:
        """
        获取用户活跃的 token 数量

        Args:
            user_id: 用户ID

        Returns:
            int: 活跃 token 数量
        """
        try:
            redis = self._get_redis()

            # 如果Redis不可用，返回0
            if redis is None:
                return 0

            key = self._get_user_tokens_key(user_id)
            count = await redis.get_set_size(key)
            return count
        except Exception as e:
            logger.error(f"❌ 获取用户活跃 token 数量失败: {e}")
            return 0


# 全局实例
_refresh_token_service: Optional[RefreshTokenService] = None


def get_refresh_token_service() -> RefreshTokenService:
    """获取全局 RefreshTokenService 实例"""
    global _refresh_token_service
    if _refresh_token_service is None:
        _refresh_token_service = RefreshTokenService()
    return _refresh_token_service


# 导出全局实例供直接导入
refresh_token_service = get_refresh_token_service()
