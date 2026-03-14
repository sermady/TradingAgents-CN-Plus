# -*- coding: utf-8 -*-
import time
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from app.utils.timezone import now_tz
from typing import Optional, Tuple
import jwt
from pydantic import BaseModel
from app.core.config import settings

logger = logging.getLogger(__name__)


class TokenStatus(Enum):
    """Token 验证状态"""
    VALID = "valid"
    EXPIRED = "expired"
    INVALID = "invalid"


class TokenData(BaseModel):
    sub: str
    exp: int


class TokenVerifyResult(BaseModel):
    """Token 验证结果"""
    status: TokenStatus
    data: Optional[TokenData] = None
    error_message: Optional[str] = None


class AuthService:
    TOKEN_TYPE_ACCESS = "access"
    TOKEN_TYPE_REFRESH = "refresh"

    @staticmethod
    def create_access_token(
        sub: str, expires_minutes: int | None = None, expires_delta: int | None = None
    ) -> str:
        """创建 Access Token (短有效期)"""
        if expires_delta:
            expire = now_tz() + timedelta(seconds=expires_delta)
        else:
            expire = now_tz() + timedelta(
                minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        payload = {
            "sub": sub,
            "exp": expire,
            "type": AuthService.TOKEN_TYPE_ACCESS,
            "iat": now_tz()
        }
        token = jwt.encode(
            payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
        )
        return token

    @staticmethod
    def create_refresh_token(sub: str) -> str:
        """创建 Refresh Token (长有效期，仅用于获取新的 Access Token)"""
        expire = now_tz() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        payload = {
            "sub": sub,
            "exp": expire,
            "type": AuthService.TOKEN_TYPE_REFRESH,
            "iat": now_tz(),
            "jti": f"{sub}_{int(time.time() * 1000)}"  # JWT ID，用于唯一标识和撤销
        }
        token = jwt.encode(
            payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
        )
        return token

    @staticmethod
    def verify_token(token: str, expected_type: str | None = None) -> TokenVerifyResult:
        """
        验证 Token，返回详细结果

        Args:
            token: JWT Token
            expected_type: 期望的 Token 类型 ("access" 或 "refresh")，None 表示不检查

        Returns:
            TokenVerifyResult: 包含状态、数据和错误信息
        """
        logger.debug(f"🔍 开始验证token")
        logger.debug(f"📝 Token长度: {len(token) if token else 0}")

        if not token:
            return TokenVerifyResult(
                status=TokenStatus.INVALID,
                error_message="Token 为空"
            )

        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
            )
            logger.debug(f"✅ Token解码成功")

            # 检查 Token 类型
            token_type = payload.get("type")
            if expected_type and token_type != expected_type:
                logger.warning(f"❌ Token类型不匹配: 期望={expected_type}, 实际={token_type}")
                return TokenVerifyResult(
                    status=TokenStatus.INVALID,
                    error_message=f"Token类型错误: 期望{expected_type}"
                )

            token_data = TokenData(
                sub=payload.get("sub"), exp=int(payload.get("exp", time.time()))
            )
            logger.debug(f"🎯 Token数据: sub={token_data.sub}, exp={token_data.exp}, type={token_type}")

            # 额外检查过期（虽然 PyJWT 已经检查过）
            current_time = int(time.time())
            if token_data.exp < current_time:
                logger.warning(f"⏰ Token已过期: exp={token_data.exp}, now={current_time}")
                return TokenVerifyResult(
                    status=TokenStatus.EXPIRED,
                    data=token_data,
                    error_message="Token已过期"
                )

            logger.debug(f"✅ Token验证成功")
            return TokenVerifyResult(status=TokenStatus.VALID, data=token_data)

        except jwt.ExpiredSignatureError:
            logger.warning("⏰ Token签名已过期")
            return TokenVerifyResult(
                status=TokenStatus.EXPIRED,
                error_message="Token已过期"
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"❌ Token无效: {e}")
            return TokenVerifyResult(
                status=TokenStatus.INVALID,
                error_message=f"Token无效: {str(e)}"
            )
        except Exception as e:
            logger.error(f"💥 Token验证异常: {e}")
            return TokenVerifyResult(
                status=TokenStatus.INVALID,
                error_message=f"Token验证失败: {str(e)}"
            )

    @staticmethod
    def verify_access_token(token: str) -> TokenVerifyResult:
        """验证 Access Token"""
        return AuthService.verify_token(token, expected_type=AuthService.TOKEN_TYPE_ACCESS)

    @staticmethod
    def verify_refresh_token(token: str) -> TokenVerifyResult:
        """验证 Refresh Token"""
        return AuthService.verify_token(token, expected_type=AuthService.TOKEN_TYPE_REFRESH)
