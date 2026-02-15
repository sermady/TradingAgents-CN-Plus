# -*- coding: utf-8 -*-
"""
配置服务基类

提供基础的数据库连接和通用方法
"""

import logging
import os
from typing import Optional

from app.core.database import get_mongo_db

logger = logging.getLogger(__name__)


class BaseConfigService:
    """配置服务基类"""

    def __init__(self, db_manager=None):
        self.db = None
        self.db_manager = db_manager

    async def _get_db(self):
        """获取数据库连接"""
        if self.db is None:
            if self.db_manager and self.db_manager.mongo_db is not None:
                # 如果有 DatabaseManager 实例，直接使用
                self.db = self.db_manager.mongo_db
            else:
                # 否则使用全局函数
                self.db = get_mongo_db()
        return self.db

    def _is_valid_api_key(self, api_key: Optional[str]) -> bool:
        """
        判断 API Key 是否有效

        有效条件：
        1. Key 不为空
        2. Key 不是占位符（不以 'your_' 或 'your-' 开头，不以 '_here' 结尾）
        3. Key 不是截断的密钥（不包含 '...'）
        4. Key 长度 > 10（基本的格式验证）

        Args:
            api_key: 待验证的 API Key

        Returns:
            bool: True 表示有效，False 表示无效
        """
        if not api_key:
            return False

        # 去除首尾空格
        api_key = api_key.strip()

        # 检查是否为空
        if not api_key:
            return False

        # 检查是否为占位符（前缀）
        if api_key.startswith("your_") or api_key.startswith("your-"):
            return False

        # 检查是否为占位符（后缀）
        if api_key.endswith("_here") or api_key.endswith("-here"):
            return False

        # 检查是否为截断的密钥（包含 '...'）
        if "..." in api_key:
            return False

        # 检查长度（大多数 API Key 都 > 10 个字符）
        if len(api_key) <= 10:
            return False

        return True

    def _get_env_api_key(self, provider_name: str) -> Optional[str]:
        """从环境变量获取 API 密钥"""
        # 环境变量映射表
        env_key_mapping = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "zhipu": "ZHIPU_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "dashscope": "DASHSCOPE_API_KEY",
            "qianfan": "QIANFAN_API_KEY",
            "azure": "AZURE_OPENAI_API_KEY",
            "siliconflow": "SILICONFLOW_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            # 聚合渠道
            "302ai": "AI302_API_KEY",
            "oneapi": "ONEAPI_API_KEY",
            "newapi": "NEWAPI_API_KEY",
            "custom_aggregator": "CUSTOM_AGGREGATOR_API_KEY",
        }

        env_var = env_key_mapping.get(provider_name)
        if env_var:
            api_key = os.getenv(env_var)
            # 使用统一的验证方法
            if self._is_valid_api_key(api_key):
                return api_key

        return None

    def _truncate_api_key(
        self, api_key: str, prefix_len: int = 6, suffix_len: int = 6
    ) -> str:
        """
        截断 API Key 用于显示

        Args:
            api_key: 完整的 API Key
            prefix_len: 保留前缀长度
            suffix_len: 保留后缀长度

        Returns:
            截断后的 API Key，例如：0f229a...c550ec
        """
        if not api_key or len(api_key) <= prefix_len + suffix_len:
            return api_key

        return f"{api_key[:prefix_len]}...{api_key[-suffix_len:]}"

    async def set_default_config(
        self,
        config_field: str,
        value: str,
        validation_func = None,
        save_func = None
    ) -> bool:
        """
        通用的设置默认配置方法

        Args:
            config_field: 配置字段名称（如 'default_llm', 'default_data_source'）
            value: 要设置的默认值
            validation_func: 可选的验证函数，用于检查值是否有效
            save_func: 可选的保存函数，如果不提供则使用 save_system_config

        Returns:
            bool: 是否设置成功

        Example:
            # 设置默认LLM
            success = await base_config.set_default_config(
                config_field='default_llm',
                value='gpt-4',
                validation_func=lambda config: any(llm.model_name == value for llm in config.llm_configs)
            )

            # 设置默认数据源
            success = await base_config.set_default_config(
                config_field='default_data_source',
                value='tushare',
                validation_func=lambda config: any(ds.name == value for ds in config.data_source_configs)
            )
        """
        try:
            config = await self.get_system_config()
            if not config:
                return False

            # 如果提供了验证函数，验证值是否有效
            if validation_func:
                if not validation_func(config):
                    logger.warning(f"配置值 '{value}' 验证失败")
                    return False

            # 设置默认值
            setattr(config, config_field, value)

            # 保存配置
            if save_func:
                return await save_func(config)
            else:
                return await self.save_system_config(config)

        except Exception as e:
            logger.error(f"设置默认配置失败 [{config_field}={value}]: {e}")
            return False
