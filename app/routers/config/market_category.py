# -*- coding: utf-8 -*-
"""
市场分类端点

包含：
- 获取所有市场分类 (/market-categories)
- 添加市场分类 (/market-categories)
- 更新市场分类 (/market-categories/{category_id})
- 删除市场分类 (/market-categories/{category_id})
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends

from app.routers.auth_db import get_current_user
from app.models.user import User
from app.models.config import (
    MarketCategory,
    MarketCategoryRequest,
)
from app.services.config_service import config_service
from app.services.operation_log_service import log_operation
from app.models.operation_log import ActionType

router = APIRouter()
logger = logging.getLogger("webapi")


@router.get("/market-categories", response_model=dict)
async def get_market_categories(current_user: User = Depends(get_current_user)):
    """获取所有市场分类"""
    try:
        categories = await config_service.get_market_categories()
        return {"success": True, "data": categories, "message": "获取市场分类成功"}
    except Exception as e:
        logger.error(f"获取市场分类失败: {e}")
        return {"success": False, "data": [], "message": f"获取市场分类失败: {str(e)}"}


@router.post("/market-categories", response_model=dict)
async def add_market_category(
    request: MarketCategoryRequest, current_user: User = Depends(get_current_user)
):
    """添加市场分类"""
    try:
        category = MarketCategory(**request.model_dump())
        success = await config_service.add_market_category(category)

        if success:
            # 审计日志（忽略异常）
            try:
                await log_operation(
                    user_id=str(getattr(current_user, "id", "")),
                    username=getattr(current_user, "username", "unknown"),
                    action_type=ActionType.CONFIG_MANAGEMENT,
                    action="add_market_category",
                    details={"id": str(getattr(category, "id", ""))},
                    success=True,
                )
            except Exception:
                pass
            return {"message": "市场分类添加成功", "id": category.id}
        else:
            return {"success": False, "data": None, "message": f"市场分类ID已存在"}
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"添加市场分类失败: {str(e)}",
        }


@router.put("/market-categories/{category_id}", response_model=dict)
async def update_market_category(
    category_id: str,
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    """更新市场分类"""
    try:
        success = await config_service.update_market_category(category_id, request)

        if success:
            # 审计日志（忽略异常）
            try:
                await log_operation(
                    user_id=str(getattr(current_user, "id", "")),
                    username=getattr(current_user, "username", "unknown"),
                    action_type=ActionType.CONFIG_MANAGEMENT,
                    action="update_market_category",
                    details={
                        "category_id": category_id,
                        "changed_keys": list(request.keys()),
                    },
                    success=True,
                )
            except Exception:
                pass
            return {"message": "市场分类更新成功"}
        else:
            return {"success": False, "data": None, "message": "市场分类不存在"}
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"更新市场分类失败: {str(e)}",
        }


@router.delete("/market-categories/{category_id}", response_model=dict)
async def delete_market_category(
    category_id: str, current_user: User = Depends(get_current_user)
):
    """删除市场分类"""
    try:
        success = await config_service.delete_market_category(category_id)

        if success:
            # 审计日志（忽略异常）
            try:
                await log_operation(
                    user_id=str(getattr(current_user, "id", "")),
                    username=getattr(current_user, "username", "unknown"),
                    action_type=ActionType.CONFIG_MANAGEMENT,
                    action="delete_market_category",
                    details={"category_id": category_id},
                    success=True,
                )
            except Exception:
                pass
            return {"message": "市场分类删除成功"}
        else:
            return {
                "success": False,
                "data": None,
                "message": f"无法删除分类，可能还有数据源使用此分类",
            }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"删除市场分类失败: {str(e)}",
        }
