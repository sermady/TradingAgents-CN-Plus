# -*- coding: utf-8 -*-
"""
配置路由基础模块

包含共享的脱敏函数和基础依赖
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter

from app.models.config import (
    LLMConfig,
    DataSourceConfig,
    DatabaseConfig,
)

logger = logging.getLogger("webapi")


# ===== 敏感字段响应脱敏函数 =====

def sanitize_llm_configs(items: List[LLMConfig]) -> List[LLMConfig]:
    """脱敏LLM配置，移除API密钥"""
    try:
        return [LLMConfig(**{**i.model_dump(), "api_key": None}) for i in items]
    except Exception:
        return items


def sanitize_datasource_configs(items: List[DataSourceConfig]) -> List[DataSourceConfig]:
    """
    脱敏数据源配置，返回缩略的 API Key

    逻辑：
    1. 如果数据库中有有效的 API Key，返回缩略版本
    2. 如果数据库中没有，尝试从环境变量读取并返回缩略版本
    3. 如果都没有，返回 None
    """
    try:
        from app.utils.api_key_utils import (
            is_valid_api_key,
            truncate_api_key,
            get_env_api_key_for_datasource,
        )

        result = []
        for item in items:
            data = item.model_dump()

            # 处理 API Key
            db_key = data.get("api_key")
            if is_valid_api_key(db_key):
                # 数据库中有有效的 API Key，返回缩略版本
                data["api_key"] = truncate_api_key(db_key)
            else:
                # 数据库中没有有效的 API Key，尝试从环境变量读取
                ds_type = data.get("type")
                if isinstance(ds_type, str):
                    env_key = get_env_api_key_for_datasource(ds_type)
                    if env_key:
                        # 环境变量中有有效的 API Key，返回缩略版本
                        data["api_key"] = truncate_api_key(env_key)
                    else:
                        data["api_key"] = None
                else:
                    data["api_key"] = None

            # 处理 API Secret（同样的逻辑）
            db_secret = data.get("api_secret")
            if is_valid_api_key(db_secret):
                data["api_secret"] = truncate_api_key(db_secret)
            else:
                data["api_secret"] = None

            result.append(DataSourceConfig(**data))

        return result
    except Exception as e:
        print(f"⚠️ 脱敏数据源配置失败: {e}")
        return items


def sanitize_database_configs(items: List[DatabaseConfig]) -> List[DatabaseConfig]:
    """脱敏数据库配置，移除密码"""
    try:
        return [DatabaseConfig(**{**i.model_dump(), "password": None}) for i in items]
    except Exception:
        return items


def sanitize_kv(d: Dict[str, Any]) -> Dict[str, Any]:
    """对字典中的可能敏感键进行脱敏（仅用于响应）。"""
    try:
        if not isinstance(d, dict):
            return d
        sens_patterns = ("key", "secret", "password", "token", "client_secret")
        redacted = {}
        for k, v in d.items():
            if isinstance(k, str) and any(p in k.lower() for p in sens_patterns):
                redacted[k] = None
            else:
                redacted[k] = v
        return redacted
    except Exception:
        return d


# 创建基础router（供子模块使用）
router = APIRouter()
