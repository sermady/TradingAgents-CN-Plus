# -*- coding: utf-8 -*-
"""
数据源分组端点

包含：
- 获取所有数据源分组关系 (/datasource-groupings)
- 添加数据源到分类 (/datasource-groupings)
- 从分类中移除数据源 (/datasource-groupings/{data_source_name}/{category_id})
- 更新数据源分组关系 (/datasource-groupings/{data_source_name}/{category_id})
- 更新分类中数据源的排序 (/market-categories/{category_id}/datasource-order)
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from app.routers.auth_db import get_current_user
from app.models.user import User
from app.models.config import (
    DataSourceGrouping,
    DataSourceGroupingRequest,
    DataSourceOrderRequest,
)
from app.services.config_service import config_service
from app.services.operation_log_service import log_operation
from app.models.operation_log import ActionType

router = APIRouter()
logger = logging.getLogger("webapi")


@router.get("/datasource-groupings", response_model=dict)
async def get_datasource_groupings(current_user: User = Depends(get_current_user)):
    """获取所有数据源分组关系"""
    try:
        groupings = await config_service.get_datasource_groupings()
        return {"success": True, "data": groupings, "message": "获取数据源分组关系成功"}
    except Exception as e:
        logger.error(f"获取数据源分组关系失败: {e}")
        return {
            "success": False,
            "data": [],
            "message": f"获取数据源分组关系失败: {str(e)}",
        }


@router.post("/datasource-groupings", response_model=dict)
async def add_datasource_to_category(
    request: DataSourceGroupingRequest, current_user: User = Depends(get_current_user)
):
    """将数据源添加到分类"""
    try:
        grouping = DataSourceGrouping(**request.model_dump())
        success = await config_service.add_datasource_to_category(grouping)

        if success:
            # 审计日志（忽略异常）
            try:
                await log_operation(
                    user_id=str(getattr(current_user, "id", "")),
                    username=getattr(current_user, "username", "unknown"),
                    action_type=ActionType.CONFIG_MANAGEMENT,
                    action="add_datasource_to_category",
                    details={
                        "data_source_name": request.data_source_name,
                        "category_id": request.category_id,
                    },
                    success=True,
                )
            except Exception:
                pass
            return {"message": "数据源添加到分类成功"}
        else:
            return {"success": False, "data": None, "message": f"数据源已在该分类中"}
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"添加数据源到分类失败: {str(e)}",
        }


@router.delete(
    "/datasource-groupings/{data_source_name}/{category_id}", response_model=dict
)
async def remove_datasource_from_category(
    data_source_name: str,
    category_id: str,
    current_user: User = Depends(get_current_user),
):
    """从分类中移除数据源"""
    try:
        success = await config_service.remove_datasource_from_category(
            data_source_name, category_id
        )

        if success:
            # 审计日志（忽略异常）
            try:
                await log_operation(
                    user_id=str(getattr(current_user, "id", "")),
                    username=getattr(current_user, "username", "unknown"),
                    action_type=ActionType.CONFIG_MANAGEMENT,
                    action="remove_datasource_from_category",
                    details={
                        "data_source_name": data_source_name,
                        "category_id": category_id,
                    },
                    success=True,
                )
            except Exception:
                pass
            return {"message": "数据源从分类中移除成功"}
        else:
            return {"success": False, "data": None, "message": "数据源分组关系不存在"}
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"从分类中移除数据源失败: {str(e)}",
        }


@router.put(
    "/datasource-groupings/{data_source_name}/{category_id}", response_model=dict
)
async def update_datasource_grouping(
    data_source_name: str,
    category_id: str,
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    """更新数据源分组关系"""
    try:
        success = await config_service.update_datasource_grouping(
            data_source_name, category_id, request
        )

        if success:
            # 审计日志（忽略异常）
            try:
                await log_operation(
                    user_id=str(getattr(current_user, "id", "")),
                    username=getattr(current_user, "username", "unknown"),
                    action_type=ActionType.CONFIG_MANAGEMENT,
                    action="update_datasource_grouping",
                    details={
                        "data_source_name": data_source_name,
                        "category_id": category_id,
                        "changed_keys": list(request.keys()),
                    },
                    success=True,
                )
            except Exception:
                pass
            return {"message": "数据源分组关系更新成功"}
        else:
            return {"success": False, "data": None, "message": "数据源分组关系不存在"}
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"更新数据源分组关系失败: {str(e)}",
        }


@router.put("/market-categories/{category_id}/datasource-order", response_model=dict)
async def update_category_datasource_order(
    category_id: str,
    request: DataSourceOrderRequest,
    current_user: User = Depends(get_current_user),
):
    """更新分类中数据源的排序"""
    try:
        success = await config_service.update_category_datasource_order(
            category_id, request.data_sources
        )

        if success:
            # 审计日志（忽略异常）
            try:
                await log_operation(
                    user_id=str(getattr(current_user, "id", "")),
                    username=getattr(current_user, "username", "unknown"),
                    action_type=ActionType.CONFIG_MANAGEMENT,
                    action="update_category_datasource_order",
                    details={
                        "category_id": category_id,
                        "data_sources": request.data_sources,
                    },
                    success=True,
                )
            except Exception:
                pass
            return {"message": "数据源排序更新成功"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="数据源排序更新失败",
            )
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"更新数据源排序失败: {str(e)}",
        }
