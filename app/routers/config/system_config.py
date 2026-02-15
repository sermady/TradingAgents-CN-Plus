# -*- coding: utf-8 -*-
"""
系统配置端点

包含：
- 配置重载 (/reload)
- 系统配置获取 (/system)
- 系统设置管理 (/settings)
- 配置导入导出 (/export, /import)
- 传统配置迁移 (/migrate-legacy)
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.routers.auth_db import get_current_user
from app.models.user import User
from app.models.config import (
    SystemConfigResponse,
)
from app.services.config_service import config_service
from app.utils.timezone import now_tz
from app.services.operation_log_service import log_operation
from app.models.operation_log import ActionType
from app.services.config_provider import provider as config_provider
from app.routers.config.base import (
    sanitize_llm_configs,
    sanitize_datasource_configs,
    sanitize_database_configs,
    sanitize_kv,
)

router = APIRouter()
logger = logging.getLogger("webapi")


class SetDefaultRequest(BaseModel):
    """设置默认配置请求"""
    name: str


@router.post("/reload", summary="重新加载配置")
async def reload_config(current_user: dict = Depends(get_current_user)):
    """
    重新加载配置并桥接到环境变量

    用于配置更新后立即生效，无需重启服务
    """
    try:
        from app.core.config_bridge import reload_bridged_config

        success = reload_bridged_config()

        if success:
            await log_operation(
                user_id=str(current_user.get("user_id", "")),
                username=current_user.get("username", "unknown"),
                action_type=ActionType.CONFIG_MANAGEMENT,
                action="重载配置",
                details={"action": "reload_config"},
                ip_address="",
                user_agent="",
            )

            return {
                "success": True,
                "message": "配置重载成功",
                "data": {"reloaded_at": now_tz().isoformat()},
            }
        else:
            return {"success": False, "message": "配置重载失败，请查看日志"}
    except Exception as e:
        logger.error(f"配置重载失败: {e}", exc_info=True)
        return {"success": False, "message": f"配置重载失败: {str(e)}", "data": None}


@router.get("/system", response_model=dict)
async def get_system_config(current_user: User = Depends(get_current_user)):
    """获取系统配置"""
    try:
        config = await config_service.get_system_config()
        if not config:
            return {"success": False, "data": None, "message": "系统配置不存在"}

        return {
            "success": True,
            "data": SystemConfigResponse(
                config_name=config.config_name,
                config_type=config.config_type,
                llm_configs=sanitize_llm_configs(config.llm_configs),
                default_llm=config.default_llm,
                data_source_configs=sanitize_datasource_configs(
                    config.data_source_configs
                ),
                default_data_source=config.default_data_source,
                database_configs=sanitize_database_configs(config.database_configs),
                system_settings=sanitize_kv(config.system_settings),
                created_at=config.created_at,
                updated_at=config.updated_at,
                version=config.version,
                is_active=config.is_active,
            ).model_dump(by_alias=False),
            "message": "获取系统配置成功",
        }
    except Exception as e:
        logger.error(f"获取系统配置失败: {e}")
        return {
            "success": False,
            "data": None,
            "message": f"获取系统配置失败: {str(e)}",
        }


@router.get("/settings", response_model=dict)
async def get_system_settings(current_user: User = Depends(get_current_user)):
    """获取系统设置"""
    try:
        effective = await config_provider.get_effective_system_settings()
        return {
            "success": True,
            "data": sanitize_kv(effective),
            "message": "获取系统设置成功",
        }
    except Exception as e:
        logger.error(f"获取系统设置失败: {e}")
        return {"success": False, "data": {}, "message": f"获取系统设置失败: {str(e)}"}


@router.get("/settings/meta", response_model=dict)
async def get_system_settings_meta(current_user: User = Depends(get_current_user)):
    """获取系统设置的元数据（敏感性、可编辑性、来源、是否有值）。
    返回结构：{success, data: {items: [{key,sensitive,editable,source,has_value}]}, message}
    """
    try:
        meta_map = await config_provider.get_system_settings_meta()
        items = [{"key": k, **v} for k, v in meta_map.items()]
        return {"success": True, "data": {"items": items}, "message": ""}
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"获取系统设置元数据失败: {str(e)}",
        }


@router.put("/settings", response_model=dict)
async def update_system_settings(
    settings: Dict[str, Any], current_user: User = Depends(get_current_user)
):
    """更新系统设置"""
    try:
        # 打印接收到的设置（用于调试）
        logger.info(f"📝 接收到的系统设置更新请求，包含 {len(settings)} 项")
        if "quick_analysis_model" in settings:
            logger.info(f"  ✓ quick_analysis_model: {settings['quick_analysis_model']}")
        else:
            logger.warning(f"  ⚠️  未包含 quick_analysis_model")
        if "deep_analysis_model" in settings:
            logger.info(f"  ✓ deep_analysis_model: {settings['deep_analysis_model']}")
        else:
            logger.warning(f"  ⚠️  未包含 deep_analysis_model")

        success = await config_service.update_system_settings(settings)
        if success:
            # 审计日志（忽略日志异常，不影响主流程）
            try:
                await log_operation(
                    user_id=str(getattr(current_user, "id", "")),
                    username=getattr(current_user, "username", "unknown"),
                    action_type=ActionType.CONFIG_MANAGEMENT,
                    action="update_system_settings",
                    details={"changed_keys": list(settings.keys())},
                    success=True,
                )
            except Exception:
                pass
            # 失效缓存
            try:
                config_provider.invalidate()
            except Exception:
                pass
            return {"success": True, "data": None, "message": "系统设置更新成功"}
        else:
            return {"success": False, "data": None, "message": "系统设置更新失败"}
    except Exception as e:
        # 审计失败记录（忽略日志异常）
        try:
            await log_operation(
                user_id=str(getattr(current_user, "id", "")),
                username=getattr(current_user, "username", "unknown"),
                action_type=ActionType.CONFIG_MANAGEMENT,
                action="update_system_settings",
                details={"changed_keys": list(settings.keys())},
                success=False,
                error_message=str(e),
            )
        except Exception:
            pass
        return {
            "success": False,
            "data": None,
            "message": f"更新系统设置失败: {str(e)}",
        }


@router.post("/export", response_model=dict)
async def export_config(current_user: User = Depends(get_current_user)):
    """导出配置"""
    try:
        config_data = await config_service.export_config()
        # 审计日志（忽略异常）
        try:
            await log_operation(
                user_id=str(getattr(current_user, "id", "")),
                username=getattr(current_user, "username", "unknown"),
                action_type=ActionType.DATA_EXPORT,
                action="export_config",
                details={"size": len(str(config_data))},
                success=True,
            )
        except Exception:
            pass
        return {
            "message": "配置导出成功",
            "data": config_data,
            "exported_at": now_tz().isoformat(),
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"导出配置失败: {str(e)}",
        }


@router.post("/import", response_model=dict)
async def import_config(
    config_data: Dict[str, Any], current_user: User = Depends(get_current_user)
):
    """导入配置"""
    try:
        success = await config_service.import_config(config_data)
        if success:
            # 审计日志（忽略异常）
            try:
                await log_operation(
                    user_id=str(getattr(current_user, "id", "")),
                    username=getattr(current_user, "username", "unknown"),
                    action_type=ActionType.DATA_IMPORT,
                    action="import_config",
                    details={"keys": list(config_data.keys())[:10]},
                    success=True,
                )
            except Exception:
                pass
            return {"message": "配置导入成功"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="配置导入失败"
            )
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"导入配置失败: {str(e)}",
        }


@router.post("/migrate-legacy", response_model=dict)
async def migrate_legacy_config(current_user: User = Depends(get_current_user)):
    """迁移传统配置"""
    try:
        success = await config_service.migrate_legacy_config()
        if success:
            # 审计日志（忽略异常）
            try:
                await log_operation(
                    user_id=str(getattr(current_user, "id", "")),
                    username=getattr(current_user, "username", "unknown"),
                    action_type=ActionType.CONFIG_MANAGEMENT,
                    action="migrate_legacy_config",
                    details={},
                    success=True,
                )
            except Exception:
                pass
            return {"message": "传统配置迁移成功"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="传统配置迁移失败",
            )
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"迁移传统配置失败: {str(e)}",
        }
