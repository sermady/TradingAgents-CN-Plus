# -*- coding: utf-8 -*-
"""
FastAPI 全局异常处理器

提供统一的异常处理机制，简化路由代码中的错误处理逻辑。

Features:
- 全局异常捕获和处理
- 统一的错误响应格式
- 自动日志记录
- 支持自定义HTTP异常
"""

import logging
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class APIResponse:
    """标准API响应格式"""

    @staticmethod
    def error(
        message: str,
        detail: str = None,
        code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ) -> dict:
        """
        生成错误响应

        Args:
            message: 用户友好的错误消息
            detail: 详细错误信息（可选）
            code: HTTP状态码

        Returns:
            标准错误响应字典
        """
        response = {
            "success": False,
            "data": None,
            "message": message,
        }

        if detail:
            response["detail"] = detail

        return response


async def global_exception_handler(request: Request, exc: Exception):
    """
    全局异常处理器 - 处理所有未捕获的异常

    Args:
        request: FastAPI请求对象
        exc: 异常对象

    Returns:
        JSONResponse: 标准错误响应
    """
    # 记录异常详情
    logger.error(
        f"未处理的异常: {request.method} {request.url}",
        exc_info=True,
    )

    # 返回标准错误响应
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=APIResponse.error(
            message="服务器内部错误",
            detail=str(exc) if logger.isEnabledFor(logging.DEBUG) else "请查看服务器日志获取详细信息",
        ),
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    HTTP异常处理器 - 处理HTTPException

    Args:
        request: FastAPI请求对象
        exc: HTTPException对象

    Returns:
        JSONResponse: HTTP错误响应
    """
    # 记录HTTP异常
    logger.warning(
        f"HTTP异常: {request.method} {request.url} - "
        f"状态码: {exc.status_code}, 详情: {exc.detail}"
    )

    # 返回HTTP错误响应
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse.error(
            message=exc.detail if isinstance(exc.detail, str) else "请求失败",
            detail=str(exc.detail) if exc.detail else None,
        ),
    )


async def validation_exception_handler(request: Request, exc: ValidationError):
    """
    请求验证异常处理器 - 处理Pydantic验证错误

    Args:
        request: FastAPI请求对象
        exc: ValidationError对象

    Returns:
        JSONResponse: 验证错误响应
    """
    # 记录验证错误
    logger.warning(
        f"请求验证失败: {request.method} {request.url} - "
        f"错误: {exc.errors()}"
    )

    # 格式化验证错误
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=APIResponse.error(
            message="请求参数验证失败",
            detail=f"共有 {len(errors)} 个字段验证失败",
        ),
    )


async def value_exception_handler(request: Request, exc: ValueError):
    """
    值错误处理器 - 处理ValueError

    Args:
        request: FastAPI请求对象
        exc: ValueError对象

    Returns:
        JSONResponse: 值错误响应
    """
    # 记录值错误
    logger.warning(
        f"值错误: {request.method} {request.url} - "
        f"错误: {str(exc)}"
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=APIResponse.error(
            message="请求参数值错误",
            detail=str(exc),
        ),
    )


async def type_exception_handler(request: Request, exc: TypeError):
    """
    类型错误处理器 - 处理TypeError

    Args:
        request: FastAPI请求对象
        exc: TypeError对象

    Returns:
        JSONResponse: 类型错误响应
    """
    # 记录类型错误
    logger.warning(
        f"类型错误: {request.method} {request.url} - "
        f"错误: {str(exc)}"
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=APIResponse.error(
            message="请求参数类型错误",
            detail=str(exc),
        ),
    )


def setup_exception_handlers(app):
    """
    设置全局异常处理器

    Args:
        app: FastAPI应用实例

    Usage:
        from app.main import app
        from app.core.exceptions import setup_exception_handlers

        setup_exception_handlers(app)
    """
    # 注册全局异常处理器
    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(ValueError, value_exception_handler)
    app.add_exception_handler(TypeError, type_exception_handler)

    logger.info("✅ 全局异常处理器已注册")
