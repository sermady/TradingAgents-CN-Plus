# -*- coding: utf-8 -*-
"""
缓存管理路由

使用全局异常处理器，简化错误处理逻辑。
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional

from app.routers.auth_db import get_current_user
from app.core.response import ok
from tradingagents.utils.logging_manager import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/cache", tags=["cache"])


@router.get("/stats")
async def get_cache_stats(current_user: dict = Depends(get_current_user)):
    """
    获取缓存统计信息

    注意：异常由全局异常处理器统一处理
    """
    from tradingagents.dataflows.cache import get_cache

    cache = get_cache()

    # 获取缓存统计
    stats = cache.get_cache_stats()

    logger.info(f"用户 {current_user['username']} 获取缓存统计")

    return ok(
        data={
            "totalFiles": stats.get('total_files', 0),
            "totalSize": stats.get('total_size', 0),  # 字节
            "maxSize": 1024 * 1024 * 1024,  # 1GB
            "stockDataCount": stats.get('stock_data_count', 0),
            "newsDataCount": stats.get('news_count', 0),
            "analysisDataCount": stats.get('fundamentals_count', 0)
        },
        message="获取缓存统计成功"
    )


@router.delete("/cleanup")
async def cleanup_old_cache(
    days: int = Query(7, ge=1, le=30, description="清理多少天前的缓存"),
    current_user: dict = Depends(get_current_user)
):
    """
    清理过期缓存

    注意：异常由全局异常处理器统一处理
    """
    from tradingagents.dataflows.cache import get_cache

    cache = get_cache()

    # 清理过期缓存
    cache.clear_old_cache(days)

    logger.info(f"用户 {current_user['username']} 清理了 {days} 天前的缓存")

    return ok(
        data={"days": days},
        message=f"已清理 {days} 天前的缓存"
    )


@router.delete("/clear")
async def clear_all_cache(current_user: dict = Depends(get_current_user)):
    """
    清空所有缓存

    注意：异常由全局异常处理器统一处理
    """
    from tradingagents.dataflows.cache import get_cache

    cache = get_cache()

    # 清空所有缓存（清理所有过期和未过期的缓存）
    # 使用 clear_old_cache(0) 来清理所有缓存
    cache.clear_old_cache(0)

    logger.warning(f"用户 {current_user['username']} 清空了所有缓存")

    return ok(
        data={},
        message="所有缓存已清空"
    )


@router.get("/details")
async def get_cache_details(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: dict = Depends(get_current_user)
):
    """
    获取缓存详情列表

    注意：异常由全局异常处理器统一处理。如果缓存类没有实现这个方法，
    会触发 AttributeError，由全局处理器返回 500 错误。
    """
    from tradingagents.dataflows.cache import get_cache

    cache = get_cache()

    # 获取缓存详情
    details = cache.get_cache_details(page=page, page_size=page_size)

    logger.info(f"用户 {current_user['username']} 获取缓存详情 (页码: {page})")

    return ok(
        data=details,
        message="获取缓存详情成功"
    )


@router.get("/backend-info")
async def get_cache_backend_info(current_user: dict = Depends(get_current_user)):
    """
    获取缓存后端信息

    注意：异常由全局异常处理器统一处理。如果缓存类没有实现这个方法，
    会触发 AttributeError，由全局处理器返回 500 错误。
    """
    from tradingagents.dataflows.cache import get_cache

    cache = get_cache()

    # 获取后端信息
    backend_info = cache.get_cache_backend_info()

    logger.info(f"用户 {current_user['username']} 获取缓存后端信息")

    return ok(
        data=backend_info,
        message="获取缓存后端信息成功"
    )

