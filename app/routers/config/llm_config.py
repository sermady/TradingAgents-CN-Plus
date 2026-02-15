# -*- coding: utf-8 -*-
"""
LLM配置端点

包含：
- 获取所有LLM配置 (/llm)
- 添加/更新LLM配置 (/llm)
- 删除LLM配置 (/llm/{provider}/{model_name})
- 设置默认LLM (/llm/set-default)
- 获取可用模型 (/models)
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.routers.auth_db import get_current_user
from app.models.user import User
from app.models.config import (
    LLMConfigRequest,
    LLMConfig,
)
from app.services.config_service import config_service
from app.services.operation_log_service import log_operation
from app.models.operation_log import ActionType
from app.routers.config.base import sanitize_llm_configs

router = APIRouter()
logger = logging.getLogger("webapi")


class SetDefaultRequest(BaseModel):
    """设置默认配置请求"""
    name: str


@router.get("/llm", response_model=dict)
async def get_llm_configs(current_user: User = Depends(get_current_user)):
    """获取所有大模型配置"""
    try:
        logger.info("🔄 开始获取大模型配置...")
        config = await config_service.get_system_config()

        if not config:
            logger.warning("⚠️ 系统配置为空，返回空列表")
            return {"success": True, "data": [], "message": "获取大模型配置成功"}

        logger.info(f"📊 系统配置存在，大模型配置数量: {len(config.llm_configs)}")

        # 如果没有大模型配置，创建一些示例配置
        if not config.llm_configs:
            logger.info("🔧 没有大模型配置，创建示例配置...")
            # 这里可以根据已有的厂家创建示例配置
            # 暂时返回空列表，让前端显示"暂无配置"

        # 获取所有供应商信息，用于过滤被禁用供应商的模型
        providers = await config_service.get_llm_providers()
        active_provider_names = {p.name for p in providers if p.is_active}

        # 过滤：只返回启用的模型 且 供应商也启用的模型
        filtered_configs = [
            llm_config
            for llm_config in config.llm_configs
            if llm_config.enabled and llm_config.provider in active_provider_names
        ]

        logger.info(
            f"✅ 过滤后的大模型配置数量: {len(filtered_configs)} (原始: {len(config.llm_configs)})"
        )

        return {
            "success": True,
            "data": sanitize_llm_configs(filtered_configs),
            "message": "获取大模型配置成功",
        }
    except Exception as e:
        logger.error(f"❌ 获取大模型配置失败: {e}")
        return {
            "success": False,
            "data": [],
            "message": f"获取大模型配置失败: {str(e)}",
        }


@router.post("/llm", response_model=dict)
async def add_llm_config(
    request: LLMConfigRequest, current_user: User = Depends(get_current_user)
):
    """添加或更新大模型配置"""
    try:
        logger.info(f"🔧 添加/更新大模型配置开始")
        logger.info(f"📊 请求数据: {request.model_dump()}")
        logger.info(f"🏷️ 厂家: {request.provider}, 模型: {request.model_name}")

        # 创建LLM配置
        llm_config_data = request.model_dump()
        logger.info(f"📋 原始配置数据: {llm_config_data}")

        # 如果没有提供API密钥，从厂家配置中获取
        if not llm_config_data.get("api_key"):
            logger.info(f"🔑 API密钥为空，从厂家配置获取: {request.provider}")

            # 获取厂家配置
            providers = await config_service.get_llm_providers()
            logger.info(f"📊 找到 {len(providers)} 个厂家配置")

            for p in providers:
                logger.info(f"   - 厂家: {p.name}, 有API密钥: {bool(p.api_key)}")

            provider_config = next(
                (p for p in providers if p.name == request.provider), None
            )

            if provider_config:
                logger.info(f"✅ 找到厂家配置: {provider_config.name}")
                if provider_config.api_key:
                    llm_config_data["api_key"] = provider_config.api_key
                    logger.info(
                        f"✅ 成功获取厂家API密钥 (长度: {len(provider_config.api_key)})"
                    )
                else:
                    logger.warning(f"⚠️ 厂家 {request.provider} 没有配置API密钥")
                    llm_config_data["api_key"] = ""
            else:
                logger.warning(f"⚠️ 未找到厂家 {request.provider} 的配置")
                llm_config_data["api_key"] = ""
        else:
            logger.info(
                f"🔑 使用提供的API密钥 (长度: {len(llm_config_data.get('api_key', ''))})"
            )

        logger.info(f"📋 最终配置数据: {llm_config_data}")
        # 🔥 修改：允许通过 REST 写入密钥，但如果是无效的密钥则清空
        # 无效的密钥：空字符串、占位符（your_xxx）、长度不够
        if "api_key" in llm_config_data:
            api_key = llm_config_data.get("api_key", "")
            # 如果是无效的 Key，则清空（让系统使用环境变量）
            if (
                not api_key
                or api_key.startswith("your_")
                or api_key.startswith("your-")
                or len(api_key) <= 10
            ):
                llm_config_data["api_key"] = ""

        # 尝试创建LLMConfig对象
        try:
            llm_config = LLMConfig(**llm_config_data)
            logger.info(f"✅ LLMConfig对象创建成功")
        except Exception as e:
            logger.error(f"❌ LLMConfig对象创建失败: {e}")
            logger.error(f"📋 失败的数据: {llm_config_data}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"配置数据验证失败: {str(e)}",
            )

        # 保存配置
        success = await config_service.update_llm_config(llm_config)

        if success:
            logger.info(
                f"✅ 大模型配置更新成功: {llm_config.provider}/{llm_config.model_name}"
            )

            # 同步定价配置到 tradingagents
            try:
                from app.core.config_bridge import sync_pricing_config_now

                sync_pricing_config_now()
                logger.info(f"✅ 定价配置已同步到 tradingagents")
            except Exception as e:
                logger.warning(f"⚠️  同步定价配置失败: {e}")

            # 审计日志（忽略异常）
            try:
                await log_operation(
                    user_id=str(getattr(current_user, "id", "")),
                    username=getattr(current_user, "username", "unknown"),
                    action_type=ActionType.CONFIG_MANAGEMENT,
                    action="update_llm_config",
                    details={
                        "provider": llm_config.provider,
                        "model_name": llm_config.model_name,
                    },
                    success=True,
                )
            except Exception:
                pass
            return {
                "success": True,
                "data": {"model_name": llm_config.model_name},
                "message": "大模型配置更新成功",
            }
        else:
            logger.error(f"❌ 大模型配置保存失败")
            return {"success": False, "data": None, "message": "大模型配置更新失败"}
    except Exception as e:
        logger.error(f"❌ 添加大模型配置异常: {e}")
        import traceback

        logger.error(f"📋 异常堆栈: {traceback.format_exc()}")
        return {
            "success": False,
            "data": None,
            "message": f"添加大模型配置失败: {str(e)}",
        }


@router.delete("/llm/{provider}/{model_name}", response_model=dict)
async def delete_llm_config(
    provider: str, model_name: str, current_user: User = Depends(get_current_user)
):
    """删除大模型配置"""
    try:
        logger.info(
            f"🗑️ 删除大模型配置请求 - provider: {provider}, model_name: {model_name}"
        )
        success = await config_service.delete_llm_config(provider, model_name)

        if success:
            logger.info(f"✅ 大模型配置删除成功 - {provider}/{model_name}")

            # 同步定价配置到 tradingagents
            try:
                from app.core.config_bridge import sync_pricing_config_now

                sync_pricing_config_now()
                logger.info(f"✅ 定价配置已同步到 tradingagents")
            except Exception as e:
                logger.warning(f"⚠️  同步定价配置失败: {e}")

            # 审计日志（忽略异常）
            try:
                await log_operation(
                    user_id=str(getattr(current_user, "id", "")),
                    username=getattr(current_user, "username", "unknown"),
                    action_type=ActionType.CONFIG_MANAGEMENT,
                    action="delete_llm_config",
                    details={"provider": provider, "model_name": model_name},
                    success=True,
                )
            except Exception:
                pass
            return {
                "success": True,
                "data": {"provider": provider, "model_name": model_name},
                "message": "大模型配置删除成功",
            }
        else:
            logger.warning(f"⚠️ 未找到大模型配置 - {provider}/{model_name}")
            return {"success": False, "data": None, "message": "大模型配置不存在"}
    except Exception as e:
        logger.error(f"❌ 删除大模型配置异常 - {provider}/{model_name}: {e}")
        return {
            "success": False,
            "data": None,
            "message": f"删除大模型配置失败: {str(e)}",
        }


@router.post("/llm/set-default", response_model=dict)
async def set_default_llm(
    request: SetDefaultRequest, current_user: User = Depends(get_current_user)
):
    """设置默认大模型"""
    try:
        success = await config_service.set_default_llm(request.name)
        if success:
            # 审计日志（忽略异常）
            try:
                await log_operation(
                    user_id=str(getattr(current_user, "id", "")),
                    username=getattr(current_user, "username", "unknown"),
                    action_type=ActionType.CONFIG_MANAGEMENT,
                    action="set_default_llm",
                    details={"name": request.name},
                    success=True,
                )
            except Exception:
                pass
            return {
                "success": True,
                "data": {"default_llm": request.name},
                "message": "默认大模型设置成功",
            }
        else:
            return {"success": False, "data": None, "message": "指定的大模型不存在"}
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"设置默认大模型失败: {str(e)}",
        }


@router.post("/default/llm", response_model=dict, include_in_schema=False)
async def set_default_llm_legacy(
    request: SetDefaultRequest, current_user: User = Depends(get_current_user)
):
    """设置默认大模型（旧版端点）"""
    try:
        # 开源版本：所有用户都可以修改配置

        success = await config_service.set_default_llm(request.name)
        if success:
            # 审计日志（忽略异常）
            try:
                await log_operation(
                    user_id=str(getattr(current_user, "id", "")),
                    username=getattr(current_user, "username", "unknown"),
                    action_type=ActionType.CONFIG_MANAGEMENT,
                    action="set_default_llm",
                    details={"name": request.name},
                    success=True,
                )
            except Exception:
                pass
            return {"message": f"默认大模型已设置为: {request.name}"}
        else:
            return {
                "success": False,
                "data": None,
                "message": f"设置默认大模型失败，请检查模型名称是否正确",
            }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"设置默认大模型失败: {str(e)}",
        }


@router.get("/models", response_model=dict)
async def get_available_models(current_user: User = Depends(get_current_user)):
    """获取可用的模型列表"""
    try:
        models = await config_service.get_available_models()
        return {"success": True, "data": models, "message": "获取模型列表成功"}
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        return {"success": False, "data": [], "message": f"获取模型列表失败: {str(e)}"}
