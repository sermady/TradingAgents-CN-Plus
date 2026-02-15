# -*- coding: utf-8 -*-
"""
模型目录端点

包含：
- 获取所有模型目录 (/model-catalog)
- 获取指定厂家的模型目录 (/model-catalog/{provider})
- 保存模型目录 (/model-catalog)
- 删除模型目录 (/model-catalog/{provider})
- 初始化默认模型目录 (/model-catalog/init)
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.routers.auth_db import get_current_user
from app.models.user import User
from app.models.config import (
    ModelCatalog,
    ModelInfo,
)
from app.services.config_service import config_service
from app.services.operation_log_service import log_operation
from app.models.operation_log import ActionType

router = APIRouter()
logger = logging.getLogger("webapi")


class ModelCatalogRequest(BaseModel):
    """模型目录请求"""
    provider: str
    provider_name: str
    models: List[Dict[str, Any]]


@router.get("/model-catalog", response_model=dict)
async def get_model_catalog(current_user: User = Depends(get_current_user)):
    """获取所有模型目录"""
    try:
        catalogs = await config_service.get_model_catalog()
        return {
            "success": True,
            "data": [catalog.model_dump(by_alias=False) for catalog in catalogs],
            "message": "获取模型目录成功",
        }
    except Exception as e:
        logger.error(f"获取模型目录失败: {e}")
        return {"success": False, "data": [], "message": f"获取模型目录失败: {str(e)}"}


@router.get("/model-catalog/{provider}", response_model=dict)
async def get_provider_model_catalog(
    provider: str, current_user: User = Depends(get_current_user)
):
    """获取指定厂家的模型目录"""
    try:
        catalog = await config_service.get_provider_models(provider)
        if not catalog:
            return {
                "success": False,
                "data": None,
                "message": f"未找到厂家 {provider} 的模型目录",
            }
        return {
            "success": True,
            "data": catalog.model_dump(by_alias=False),
            "message": "获取模型目录成功",
        }
    except Exception as e:
        logger.error(f"获取模型目录失败: {e}")
        return {
            "success": False,
            "data": None,
            "message": f"获取模型目录失败: {str(e)}",
        }


@router.post("/model-catalog", response_model=dict)
async def save_model_catalog(
    request: ModelCatalogRequest, current_user: User = Depends(get_current_user)
):
    """保存或更新模型目录"""
    try:
        logger.info(
            f"📝 收到保存模型目录请求: provider={request.provider}, models数量={len(request.models)}"
        )
        logger.info(f"📝 请求数据: {request.model_dump()}")

        # 转换为 ModelInfo 列表
        models = [ModelInfo(**m) for m in request.models]
        logger.info(f"✅ 成功转换 {len(models)} 个模型")

        catalog = ModelCatalog(
            provider=request.provider,
            provider_name=request.provider_name,
            models=models,
        )
        logger.info(f"✅ 创建 ModelCatalog 对象成功")

        success = await config_service.save_model_catalog(catalog)
        logger.info(f"💾 保存结果: {success}")

        if not success:
            return {"success": False, "data": None, "message": "保存模型目录失败"}

        # 记录操作日志
        await log_operation(
            user_id=str(getattr(current_user, "id", "")),
            username=getattr(current_user, "username", "unknown"),
            action_type=ActionType.CONFIG_MANAGEMENT,
            action="update_model_catalog",
            details={
                "provider": request.provider,
                "provider_name": request.provider_name,
                "models_count": len(request.models),
            },
        )

        return {"success": True, "data": None, "message": "模型目录保存成功"}
    except Exception as e:
        logger.error(f"❌ 保存模型目录失败: {str(e)}", exc_info=True)
        return {
            "success": False,
            "data": None,
            "message": f"保存模型目录失败: {str(e)}",
        }


@router.delete("/model-catalog/{provider}", response_model=dict)
async def delete_model_catalog(
    provider: str, current_user: User = Depends(get_current_user)
):
    """删除模型目录"""
    try:
        success = await config_service.delete_model_catalog(provider)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到厂家 {provider} 的模型目录",
            )

        # 记录操作日志
        await log_operation(
            user_id=str(getattr(current_user, "id", "")),
            username=getattr(current_user, "username", "unknown"),
            action_type=ActionType.CONFIG_MANAGEMENT,
            action="delete_model_catalog",
            details={"provider": provider},
        )

        return {"success": True, "message": "模型目录删除成功"}
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"删除模型目录失败: {str(e)}",
        }


@router.post("/model-catalog/init", response_model=dict)
async def init_model_catalog(current_user: User = Depends(get_current_user)):
    """初始化默认模型目录"""
    try:
        success = await config_service.init_default_model_catalog()
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="初始化模型目录失败",
            )

        return {"success": True, "message": "模型目录初始化成功"}
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"初始化模型目录失败: {str(e)}",
        }
