# -*- coding: utf-8 -*-
"""模型能力评估模块

提供模型能力等级评估和完整配置获取功能。
"""

import logging
from typing import Dict, Any

from app.constants.model_capabilities import (
    DEFAULT_MODEL_CAPABILITIES,
    ModelRole,
    ModelFeature,
)
from app.core.unified_config_service import get_config_manager
from .parser import ModelNameParser

logger = logging.getLogger(__name__)


class ModelCapabilityEvaluator:
    """模型能力评估器"""

    @staticmethod
    def get_model_capability(model_name: str) -> int:
        """
        获取模型的能力等级（支持聚合渠道模型映射）

        Args:
            model_name: 模型名称

        Returns:
            能力等级 (1-5)
        """
        # 1. 优先从数据库配置读取
        try:
            llm_configs = get_config_manager().get_llm_configs()
            for config in llm_configs:
                if hasattr(config, 'model_name') and config.model_name == model_name:
                    return getattr(config, "capability_level", 2)
                elif isinstance(config, dict) and config.get("model_name") == model_name:
                    return config.get("capability_level", 2)
        except Exception as e:
            logger.warning(f"从配置读取模型能力失败: {e}")

        # 2. 从默认映射表读取
        capability, mapped_model = ModelNameParser.get_model_capability_with_mapping(model_name)
        if mapped_model:
            logger.info(f"✅ 使用映射模型 {mapped_model} 的能力等级: {capability}")

        return capability

    @staticmethod
    def get_model_config(model_name: str) -> Dict[str, Any]:
        """
        获取模型的完整配置信息

        Args:
            model_name: 模型名称

        Returns:
            模型配置字典
        """
        # 1. 优先从统一配置管理器读取
        try:
            config_manager = get_config_manager()
            db_config = config_manager._get_mongodb_config()

            if db_config and "llm_configs" in db_config:
                llm_configs = db_config["llm_configs"]
                logger.info(f"🔍 [MongoDB] llm_configs 数量: {len(llm_configs)}")

                for config_dict in llm_configs:
                    if config_dict.get("model_name") == model_name:
                        logger.info(f"🔍 [MongoDB] 找到模型配置: {model_name}")
                        # 将字符串列表转换为枚举列表
                        features_str = config_dict.get("features", [])
                        features_enum = []
                        for feature_str in features_str:
                            try:
                                features_enum.append(ModelFeature(feature_str))
                            except ValueError:
                                logger.warning(f"⚠️ 未知的特性值: {feature_str}")

                        # 将字符串列表转换为枚举列表
                        roles_str = config_dict.get("suitable_roles", ["both"])
                        roles_enum = []
                        for role_str in roles_str:
                            try:
                                roles_enum.append(ModelRole(role_str))
                            except ValueError:
                                logger.warning(f"⚠️ 未知的角色值: {role_str}")

                        if not roles_enum:
                            roles_enum = [ModelRole.BOTH]

                        is_enabled = config_dict.get("enabled", True)

                        logger.info(
                            f"📊 [MongoDB配置] {model_name}: features={features_enum}, "
                            f"roles={roles_enum}, enabled={is_enabled}"
                        )

                        return {
                            "model_name": config_dict.get("model_name"),
                            "capability_level": config_dict.get("capability_level", 2),
                            "suitable_roles": [str(r) for r in roles_enum],
                            "features": [f.value for f in features_enum],
                            "recommended_depths": config_dict.get(
                                "recommended_depths", ["快速", "基础", "标准"]
                            ),
                            "performance_metrics": config_dict.get(
                                "performance_metrics", None
                            ),
                            "enabled": is_enabled,
                        }

            logger.warning(f"未从 MongoDB 找到模型 {model_name} 的配置")
        except Exception as e:
            logger.warning(f"从 MongoDB 读取模型配置失败: {e}", exc_info=True)

        # 2. 从默认映射表读取
        if model_name in DEFAULT_MODEL_CAPABILITIES:
            return DEFAULT_MODEL_CAPABILITIES[model_name]

        # 3. 尝试聚合渠道模型映射
        provider, original_model = ModelNameParser.parse_aggregator_model_name(model_name)
        if original_model and original_model != model_name:
            if original_model in DEFAULT_MODEL_CAPABILITIES:
                logger.info(f"🔄 聚合渠道模型映射: {model_name} -> {original_model}")
                config = DEFAULT_MODEL_CAPABILITIES[original_model].copy()
                config["model_name"] = model_name
                config["_mapped_from"] = original_model
                return config

        # 4. 返回默认配置
        logger.warning(f"未找到模型 {model_name} 的配置，使用默认配置")
        return {
            "model_name": model_name,
            "capability_level": 2,
            "suitable_roles": [ModelRole.BOTH.value],
            "features": [ModelFeature.TOOL_CALLING.value],
            "recommended_depths": ["快速", "基础", "标准"],
            "performance_metrics": {"speed": 3, "cost": 3, "quality": 3},
        }
