# -*- coding: utf-8 -*-
"""
数据库配置端点

包含：
- 获取所有数据库配置 (/database)
- 获取指定数据库配置 (/database/{db_name})
- 添加数据库配置 (/database, /database/legacy)
- 更新数据库配置 (/database/{db_name})
- 删除数据库配置 (/database/{db_name})
- 测试数据库配置 (/database/{db_name}/test, /test)
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status

from app.routers.auth_db import get_current_user
from app.models.user import User
from app.models.config import (
    DatabaseConfigRequest,
    DatabaseConfig,
    ConfigTestRequest,
    LLMConfig,
    DataSourceConfig,
)
from app.services.config_service import config_service
from app.services.operation_log_service import log_operation
from app.models.operation_log import ActionType

router = APIRouter()
logger = logging.getLogger("webapi")


@router.get("/database", response_model=dict)
async def get_database_configs(current_user: dict = Depends(get_current_user)):
    """获取所有数据库配置"""
    try:
        logger.info("🔄 获取数据库配置列表...")
        configs = await config_service.get_database_configs()
        logger.info(f"✅ 获取到 {len(configs)} 个数据库配置")
        return {"success": True, "data": configs, "message": "获取数据库配置成功"}
    except Exception as e:
        logger.error(f"❌ 获取数据库配置失败: {e}")
        return {
            "success": False,
            "data": [],
            "message": f"获取数据库配置失败: {str(e)}",
        }


@router.get("/database/{db_name}", response_model=dict)
async def get_database_config(
    db_name: str, current_user: dict = Depends(get_current_user)
):
    """获取指定的数据库配置"""
    try:
        logger.info(f"🔄 获取数据库配置: {db_name}")
        config = await config_service.get_database_config(db_name)

        if not config:
            return {
                "success": False,
                "data": None,
                "message": f"数据库配置 '{db_name}' 不存在",
            }

        return {"success": True, "data": config, "message": "获取数据库配置成功"}
    except Exception as e:
        logger.error(f"❌ 获取数据库配置失败: {e}")
        return {
            "success": False,
            "data": None,
            "message": f"获取数据库配置失败: {str(e)}",
        }


@router.post("/database", response_model=dict)
async def add_database_config(
    request: DatabaseConfigRequest, current_user: User = Depends(get_current_user)
):
    """添加数据库配置"""
    try:
        # 开源版本：所有用户都可以修改配置

        # 获取当前配置
        config = await config_service.get_system_config()
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="系统配置不存在"
            )

        # 添加新的数据库配置（方案A：清洗敏感字段）
        _req = request.model_dump()
        _req["password"] = ""
        db_config = DatabaseConfig(**_req)
        config.database_configs.append(db_config)

        success = await config_service.save_system_config(config)
        if success:
            # 审计日志（忽略异常）
            try:
                await log_operation(
                    user_id=str(getattr(current_user, "id", "")),
                    username=getattr(current_user, "username", "unknown"),
                    action_type=ActionType.CONFIG_MANAGEMENT,
                    action="add_database_config",
                    details={"name": db_config.name},
                    success=True,
                )
            except Exception:
                pass
            return {
                "success": True,
                "data": {"name": db_config.name},
                "message": "数据库配置添加成功",
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="数据库配置添加失败",
            )
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"添加数据库配置失败: {str(e)}",
        }


@router.post("/database/legacy", response_model=dict, include_in_schema=False)
async def add_database_config_legacy(
    request: DatabaseConfigRequest, current_user: dict = Depends(get_current_user)
):
    """添加数据库配置（旧版端点）"""
    try:
        logger.info(f"➕ 添加数据库配置: {request.name}")

        # 转换为 DatabaseConfig 对象
        db_config = DatabaseConfig(**request.model_dump())

        # 添加配置
        success = await config_service.add_database_config(db_config)

        if not success:
            return {
                "success": False,
                "data": None,
                "message": f"添加数据库配置失败，可能已存在同名配置",
            }

        # 记录操作日志
        await log_operation(
            user_id=current_user["id"],
            username=current_user.get("username", "unknown"),
            action_type=ActionType.CONFIG_MANAGEMENT,
            action=f"添加数据库配置: {request.name}",
            details={
                "name": request.name,
                "type": request.type,
                "host": request.host,
                "port": request.port,
            },
        )

        return {"success": True, "message": "数据库配置添加成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 添加数据库配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加数据库配置失败: {str(e)}",
        )


@router.put("/database/{db_name}", response_model=dict)
async def update_database_config(
    db_name: str,
    request: DatabaseConfigRequest,
    current_user: dict = Depends(get_current_user),
):
    """更新数据库配置"""
    try:
        logger.info(f"🔄 更新数据库配置: {db_name}")

        # 检查名称是否匹配
        if db_name != request.name:
            return {
                "success": False,
                "data": None,
                "message": f"URL中的名称与请求体中的名称不匹配",
            }

        # 转换为 DatabaseConfig 对象
        db_config = DatabaseConfig(**request.model_dump())

        # 更新配置
        success = await config_service.update_database_config(db_config)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"数据库配置 '{db_name}' 不存在",
            )

        # 记录操作日志
        await log_operation(
            user_id=current_user["id"],
            username=current_user.get("username", "unknown"),
            action_type=ActionType.CONFIG_MANAGEMENT,
            action=f"更新数据库配置: {db_name}",
            details={
                "name": request.name,
                "type": request.type,
                "host": request.host,
                "port": request.port,
            },
        )

        return {"success": True, "message": "数据库配置更新成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新数据库配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新数据库配置失败: {str(e)}",
        )


@router.delete("/database/{db_name}", response_model=dict)
async def delete_database_config(
    db_name: str, current_user: dict = Depends(get_current_user)
):
    """删除数据库配置"""
    try:
        logger.info(f"🗑️ 删除数据库配置: {db_name}")

        # 删除配置
        success = await config_service.delete_database_config(db_name)

        if not success:
            return {
                "success": False,
                "data": None,
                "message": f"数据库配置 '{db_name}' 不存在",
            }

        # 记录操作日志
        await log_operation(
            user_id=current_user["id"],
            username=current_user.get("username", "unknown"),
            action_type=ActionType.CONFIG_MANAGEMENT,
            action=f"删除数据库配置: {db_name}",
            details={"name": db_name},
        )

        return {"success": True, "data": None, "message": "数据库配置删除成功"}

    except Exception as e:
        logger.error(f"❌ 删除数据库配置失败: {e}")
        return {
            "success": False,
            "data": None,
            "message": f"删除数据库配置失败: {str(e)}",
        }


@router.post("/database/{db_name}/test", response_model=dict)
async def test_saved_database_config(
    db_name: str, current_user: dict = Depends(get_current_user)
):
    """测试已保存的数据库配置（从数据库中获取完整配置包括密码）"""
    try:
        logger.info(f"🧪 测试已保存的数据库配置: {db_name}")

        # 从数据库获取完整的系统配置
        config = await config_service.get_system_config()
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="系统配置不存在"
            )

        # 查找指定的数据库配置
        db_config = None
        for db in config.database_configs:
            if db.name == db_name:
                db_config = db
                break

        if not db_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"数据库配置 '{db_name}' 不存在",
            )

        logger.info(f"✅ 找到数据库配置: {db_config.name} ({db_config.type})")
        logger.info(f"📍 连接信息: {db_config.host}:{db_config.port}")
        logger.info(f"🔐 用户名: {db_config.username or '(无)'}")
        logger.info(f"🔐 密码: {'***' if db_config.password else '(无)'}")

        # 使用完整配置进行测试
        result = await config_service.test_database_config(db_config)

        return {
            "success": result.get("success", False),
            "data": result,
            "message": result.get("message", "测试完成"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 测试数据库配置失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"测试数据库配置失败: {str(e)}",
        )


@router.post("/test", response_model=dict)
async def test_config(
    request: ConfigTestRequest, current_user: User = Depends(get_current_user)
):
    """测试配置连接"""
    try:
        if request.config_type == "llm":
            llm_config = LLMConfig(**request.config_data)
            result = await config_service.test_llm_config(llm_config)
        elif request.config_type == "datasource":
            ds_config = DataSourceConfig(**request.config_data)
            result = await config_service.test_data_source_config(ds_config)
        elif request.config_type == "database":
            db_config = DatabaseConfig(**request.config_data)
            result = await config_service.test_database_config(db_config)
        else:
            return {"success": False, "data": None, "message": "不支持的配置类型"}

        return {
            "success": result.get("success", False),
            "data": result,
            "message": result.get("message", "测试完成"),
        }
    except Exception as e:
        return {"success": False, "data": None, "message": f"测试配置失败: {str(e)}"}
