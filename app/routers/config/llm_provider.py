# -*- coding: utf-8 -*-
"""
LLM提供商端点

包含：
- 获取所有提供商 (/llm/providers)
- 添加提供商 (/llm/providers)
- 更新提供商 (/llm/providers/{provider_id})
- 删除提供商 (/llm/providers/{provider_id})
- 切换状态 (/llm/providers/{provider_id}/toggle)
- 获取模型列表 (/llm/providers/{provider_id}/fetch-models)
- 迁移环境变量 (/llm/providers/migrate-env)
- 初始化聚合渠道 (/llm/providers/init-aggregators)
- 测试API (/llm/providers/{provider_id}/test)
"""

import logging
from fastapi import APIRouter, Depends

from app.routers.auth_db import get_current_user
from app.models.user import User
from app.models.config import (
    LLMProvider,
    LLMProviderRequest,
    LLMProviderResponse,
)
from app.services.config_service import config_service
from app.services.operation_log_service import log_operation
from app.models.operation_log import ActionType

router = APIRouter()
logger = logging.getLogger("webapi")


@router.get("/llm/providers", response_model=dict)
async def get_llm_providers(current_user: User = Depends(get_current_user)):
    """获取所有大模型厂家"""
    from app.utils.api_key_utils import (
        is_valid_api_key,
        truncate_api_key,
        get_env_api_key_for_provider,
    )

    providers = await config_service.get_llm_providers()
    result = []

    for provider in providers:
        # 处理 API Key：优先使用数据库配置，如果数据库没有则检查环境变量
        db_key_valid = is_valid_api_key(provider.api_key)
        if db_key_valid:
            # 数据库中有有效的 API Key，返回缩略版本
            api_key_display = truncate_api_key(provider.api_key)
        else:
            # 数据库中没有有效的 API Key，尝试从环境变量读取
            env_key = get_env_api_key_for_provider(provider.name)
            if env_key:
                # 环境变量中有有效的 API Key，返回缩略版本
                api_key_display = truncate_api_key(env_key)
            else:
                api_key_display = None

        # 处理 API Secret（同样的逻辑）
        db_secret_valid = is_valid_api_key(provider.api_secret)
        if db_secret_valid:
            api_secret_display = truncate_api_key(provider.api_secret)
        else:
            # 注意：API Secret 通常不在环境变量中，所以这里只检查数据库
            api_secret_display = None

        result.append(
            LLMProviderResponse(
                id=str(provider.id),
                name=provider.name,
                display_name=provider.display_name,
                description=provider.description,
                website=provider.website,
                api_doc_url=provider.api_doc_url,
                logo_url=provider.logo_url,
                is_active=provider.is_active,
                supported_features=provider.supported_features,
                default_base_url=provider.default_base_url,
                # 返回缩略的 API Key（前6位 + "..." + 后6位）
                api_key=api_key_display,
                api_secret=api_secret_display,
                extra_config={
                    **provider.extra_config,
                    "has_api_key": bool(api_key_display),
                    "has_api_secret": bool(api_secret_display),
                },
                created_at=provider.created_at,
                updated_at=provider.updated_at,
            )
        )

    return {"success": True, "data": result, "message": "获取厂家列表成功"}


@router.post("/llm/providers", response_model=dict)
async def add_llm_provider(
    request: LLMProviderRequest, current_user: User = Depends(get_current_user)
):
    """添加大模型厂家（方案A：REST不接受密钥，强制清洗）"""
    sanitized = request.model_dump()
    if "api_key" in sanitized:
        sanitized["api_key"] = ""
    provider = LLMProvider(**sanitized)
    provider_id = await config_service.add_llm_provider(provider)

    # 审计日志（忽略异常）
    try:
        await log_operation(
            user_id=str(getattr(current_user, "id", "")),
            username=getattr(current_user, "username", "unknown"),
            action_type=ActionType.CONFIG_MANAGEMENT,
            action="add_llm_provider",
            details={"provider_id": str(provider_id), "name": request.name},
            success=True,
        )
    except Exception:
        pass
    return {
        "success": True,
        "message": "厂家添加成功",
        "data": {"id": str(provider_id)},
    }


@router.put("/llm/providers/{provider_id}", response_model=dict)
async def update_llm_provider(
    provider_id: str,
    request: LLMProviderRequest,
    current_user: User = Depends(get_current_user),
):
    """更新大模型厂家"""
    from app.utils.api_key_utils import should_skip_api_key_update

    update_data = request.model_dump(exclude_unset=True)

    # 🔥 修改：处理 API Key 的更新逻辑
    # 1. 如果 API Key 是空字符串，表示用户想清空密钥 → 保存空字符串
    # 2. 如果 API Key 是占位符或截断的密钥（如 "sk-99054..."），则删除该字段（不更新）
    # 3. 如果 API Key 是有效的完整密钥，则更新
    if "api_key" in update_data:
        api_key = update_data.get("api_key", "")
        # 如果应该跳过更新（占位符或截断的密钥），则删除该字段
        if should_skip_api_key_update(api_key):
            del update_data["api_key"]
        # 如果是空字符串，保留（表示清空）
        # 如果是有效的完整密钥，保留（表示更新）

    if "api_secret" in update_data:
        api_secret = update_data.get("api_secret", "")
        # 同样的逻辑处理 API Secret
        if should_skip_api_key_update(api_secret):
            del update_data["api_secret"]

    success = await config_service.update_llm_provider(provider_id, update_data)

    if success:
        # 审计日志（忽略异常）
        try:
            await log_operation(
                user_id=str(getattr(current_user, "id", "")),
                username=getattr(current_user, "username", "unknown"),
                action_type=ActionType.CONFIG_MANAGEMENT,
                action="update_llm_provider",
                details={
                    "provider_id": provider_id,
                    "changed_keys": list(request.model_dump().keys()),
                },
                success=True,
            )
        except Exception:
            pass
        return {"success": True, "message": "厂家更新成功", "data": {}}
    else:
        return {"success": False, "data": None, "message": "厂家不存在"}


@router.delete("/llm/providers/{provider_id}", response_model=dict)
async def delete_llm_provider(
    provider_id: str, current_user: User = Depends(get_current_user)
):
    """删除大模型厂家"""
    success = await config_service.delete_llm_provider(provider_id)

    if success:
        # 审计日志（忽略异常）
        try:
            await log_operation(
                user_id=str(getattr(current_user, "id", "")),
                username=getattr(current_user, "username", "unknown"),
                action_type=ActionType.CONFIG_MANAGEMENT,
                action="delete_llm_provider",
                details={"provider_id": provider_id},
                success=True,
            )
        except Exception:
            pass
        return {"success": True, "message": "厂家删除成功", "data": {}}
    else:
        return {"success": False, "data": None, "message": "厂家不存在"}


@router.patch("/llm/providers/{provider_id}/toggle", response_model=dict)
async def toggle_llm_provider(
    provider_id: str, request: dict, current_user: User = Depends(get_current_user)
):
    """切换大模型厂家状态"""
    is_active = request.get("is_active", True)
    success = await config_service.toggle_llm_provider(provider_id, is_active)

    if success:
        # 审计日志（忽略异常）
        try:
            await log_operation(
                user_id=str(getattr(current_user, "id", "")),
                username=getattr(current_user, "username", "unknown"),
                action_type=ActionType.CONFIG_MANAGEMENT,
                action="toggle_llm_provider",
                details={"provider_id": provider_id, "is_active": bool(is_active)},
                success=True,
            )
        except Exception:
            pass
        return {
            "success": True,
            "message": f"厂家已{'启用' if is_active else '禁用'}",
            "data": {},
        }
    else:
        return {"success": False, "data": None, "message": "厂家不存在"}


@router.post("/llm/providers/{provider_id}/fetch-models", response_model=dict)
async def fetch_provider_models(
    provider_id: str, current_user: User = Depends(get_current_user)
):
    """从厂家 API 获取模型列表"""
    result = await config_service.fetch_provider_models(provider_id)
    return result


@router.post("/llm/providers/migrate-env", response_model=dict)
async def migrate_env_to_providers(current_user: User = Depends(get_current_user)):
    """将环境变量配置迁移到厂家管理"""
    result = await config_service.migrate_env_to_providers()
    # 审计日志（忽略异常）
    try:
        await log_operation(
            user_id=str(getattr(current_user, "id", "")),
            username=getattr(current_user, "username", "unknown"),
            action_type=ActionType.CONFIG_MANAGEMENT,
            action="migrate_env_to_providers",
            details={
                "migrated_count": result.get("migrated_count", 0),
                "skipped_count": result.get("skipped_count", 0),
            },
            success=bool(result.get("success", False)),
        )
    except Exception:
        pass

    return {
        "success": result["success"],
        "message": result["message"],
        "data": {
            "migrated_count": result.get("migrated_count", 0),
            "skipped_count": result.get("skipped_count", 0),
        },
    }


@router.post("/llm/providers/init-aggregators", response_model=dict)
async def init_aggregator_providers(current_user: User = Depends(get_current_user)):
    """初始化聚合渠道厂家配置（302.AI、OpenRouter等）"""
    result = await config_service.init_aggregator_providers()

    # 审计日志（忽略异常）
    try:
        await log_operation(
            user_id=str(getattr(current_user, "id", "")),
            username=getattr(current_user, "username", "unknown"),
            action_type=ActionType.CONFIG_MANAGEMENT,
            action="init_aggregator_providers",
            details={
                "added_count": result.get("added", 0),
                "skipped_count": result.get("skipped", 0),
            },
            success=bool(result.get("success", False)),
        )
    except Exception:
        pass

    return {
        "success": result["success"],
        "message": result["message"],
        "data": {
            "added_count": result.get("added", 0),
            "skipped_count": result.get("skipped", 0),
        },
    }


@router.post("/llm/providers/{provider_id}/test", response_model=dict)
async def test_provider_api(
    provider_id: str, current_user: User = Depends(get_current_user)
):
    """测试厂家API密钥"""
    logger.info(f"🧪 收到API测试请求 - provider_id: {provider_id}")
    result = await config_service.test_provider_api(provider_id)
    logger.info(f"🧪 API测试结果: {result}")
    return result
