# -*- coding: utf-8 -*-
"""模型名称解析模块

提供聚合渠道模型名称解析和映射功能。
"""

import logging
from typing import Tuple, Optional

from app.constants.model_capabilities import DEFAULT_MODEL_CAPABILITIES

logger = logging.getLogger(__name__)


class ModelNameParser:
    """模型名称解析器"""

    # 聚合渠道提供商映射
    PROVIDER_MAP = {
        "openai": "openai",
        "anthropic": "anthropic",
        "google": "google",
        "deepseek": "deepseek",
        "alibaba": "qwen",
        "qwen": "qwen",
        "zhipu": "zhipu",
        "baidu": "baidu",
        "moonshot": "moonshot",
    }

    @classmethod
    def parse_aggregator_model_name(
        cls, model_name: str
    ) -> Tuple[Optional[str], str]:
        """
        解析聚合渠道的模型名称

        Args:
            model_name: 模型名称，可能包含前缀（如 openai/gpt-4, anthropic/claude-3-sonnet）

        Returns:
            (原厂商, 原模型名) 元组
        """
        if "/" in model_name:
            parts = model_name.split("/", 1)
            if len(parts) == 2:
                provider_hint = parts[0].lower()
                original_model = parts[1]

                provider = cls.PROVIDER_MAP.get(provider_hint)
                return provider, original_model

        return None, model_name

    @classmethod
    def get_model_capability_with_mapping(
        cls, model_name: str
    ) -> Tuple[int, Optional[str]]:
        """
        获取模型能力等级（支持聚合渠道映射）

        Returns:
            (能力等级, 映射的原模型名) 元组
        """
        # 从默认映射表读取
        if model_name in DEFAULT_MODEL_CAPABILITIES:
            logger.info(f"✅ 从默认映射找到模型 {model_name} 的配置")
            default_config = DEFAULT_MODEL_CAPABILITIES[model_name]
            return default_config["capability_level"], None

        # 尝试解析聚合渠道模型名
        provider, original_model = cls.parse_aggregator_model_name(model_name)
        if original_model and original_model != model_name:
            # 尝试用原模型名查找
            if original_model in DEFAULT_MODEL_CAPABILITIES:
                logger.info(f"🔄 聚合渠道模型映射: {model_name} -> {original_model}")
                return DEFAULT_MODEL_CAPABILITIES[original_model][
                    "capability_level"
                ], original_model

        # 返回默认值
        return 2, None
