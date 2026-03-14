# -*- coding: utf-8 -*-
"""模型验证模块

提供模型对验证功能，检查快速/深度模型是否适合当前分析深度。
"""

import logging
from typing import Dict, Any

from app.constants.model_capabilities import (
    ANALYSIS_DEPTH_REQUIREMENTS,
    ModelRole,
    ModelFeature,
)
from .capability import ModelCapabilityEvaluator

logger = logging.getLogger(__name__)


class ModelValidator:
    """模型验证器"""

    @staticmethod
    def validate_model_pair(
        quick_model: str, deep_model: str, research_depth: str
    ) -> Dict[str, Any]:
        """
        验证模型对是否适合当前分析深度

        Args:
            quick_model: 快速分析模型名称
            deep_model: 深度分析模型名称
            research_depth: 研究深度

        Returns:
            验证结果字典，包含 valid, warnings, recommendations
        """
        logger.info(
            f"🔍 开始验证模型对: quick={quick_model}, deep={deep_model}, depth={research_depth}"
        )

        requirements = ANALYSIS_DEPTH_REQUIREMENTS.get(
            research_depth, ANALYSIS_DEPTH_REQUIREMENTS["标准"]
        )
        logger.info(f"🔍 分析深度要求: {requirements}")

        quick_config = ModelCapabilityEvaluator.get_model_config(quick_model)
        deep_config = ModelCapabilityEvaluator.get_model_config(deep_model)

        logger.info(f"🔍 快速模型配置: {quick_config}")
        logger.info(f"🔍 深度模型配置: {deep_config}")

        result = {"valid": True, "warnings": [], "recommendations": []}

        # 检查快速模型
        quick_level = quick_config["capability_level"]
        logger.info(
            f"🔍 检查快速模型能力等级: {quick_level} >= {requirements['quick_model_min']}?"
        )
        if quick_level < requirements["quick_model_min"]:
            warning = f"⚠️ 快速模型 {quick_model} (能力等级{quick_level}) 低于 {research_depth} 分析的建议等级({requirements['quick_model_min']})"
            result["warnings"].append(warning)
            logger.warning(warning)

        # 检查快速模型角色适配
        quick_roles = quick_config.get("suitable_roles", [])
        logger.info(f"🔍 检查快速模型角色: {quick_roles}")

        # 检查快速模型是否支持工具调用
        quick_features = quick_config.get("features", [])
        logger.info(f"🔍 检查快速模型特性: {quick_features}")

        if not ModelValidator._has_feature(quick_features, ModelFeature.TOOL_CALLING):
            result["valid"] = False
            warning = f"❌ 快速模型 {quick_model} 不支持工具调用，无法完成数据收集任务"
            result["warnings"].append(warning)
            logger.error(warning)

        # 检查深度模型
        deep_level = deep_config["capability_level"]
        logger.info(
            f"🔍 检查深度模型能力等级: {deep_level} >= {requirements['deep_model_min']}?"
        )
        if deep_level < requirements["deep_model_min"]:
            result["valid"] = False
            warning = f"❌ 深度模型 {deep_model} (能力等级{deep_level}) 不满足 {research_depth} 分析的最低要求(等级{requirements['deep_model_min']})"
            result["warnings"].append(warning)
            logger.error(warning)
            result["recommendations"].append(
                ModelValidator._recommend_model("deep", requirements["deep_model_min"])
            )

        # 检查深度模型角色适配
        deep_roles = deep_config.get("suitable_roles", [])
        logger.info(f"🔍 检查深度模型角色: {deep_roles}")

        # 检查必需特性
        logger.info(f"🔍 检查必需特性: {requirements['required_features']}")
        for feature in requirements["required_features"]:
            if feature == ModelFeature.REASONING:
                deep_features = deep_config.get("features", [])
                logger.info(f"🔍 检查深度模型推理能力: {deep_features}")
                if not ModelValidator._has_feature(deep_features, feature):
                    warning = f"💡 {research_depth} 分析建议使用具有强推理能力的深度模型"
                    result["warnings"].append(warning)
                    logger.warning(warning)

        logger.info(
            f"🔍 验证结果: valid={result['valid']}, warnings={len(result['warnings'])}条"
        )
        logger.info(f"🔍 警告详情: {result['warnings']}")

        return result

    @staticmethod
    def _has_role(roles, required_role) -> bool:
        """检查是否包含所需角色"""
        for role in roles:
            if isinstance(role, str):
                if role == required_role.value or role == str(required_role):
                    return True
            else:
                if role == required_role:
                    return True
        return False

    @staticmethod
    def _has_feature(features, required_feature) -> bool:
        """检查是否包含所需特性"""
        required_value = required_feature.value
        required_str = str(required_feature)
        for feature in features:
            if isinstance(feature, str):
                if feature == required_value or feature == required_str:
                    return True
            else:
                if feature == required_feature:
                    return True
        return False

    @staticmethod
    def _recommend_model(model_type: str, min_level: int) -> str:
        """推荐满足要求的模型"""
        try:
            from app.core.unified_config_service import get_config_manager
            llm_configs = get_config_manager().get_llm_configs()
            for config in llm_configs:
                if hasattr(config, 'enabled') and config.enabled:
                    if getattr(config, "capability_level", 2) >= min_level:
                        display_name = getattr(config, 'model_display_name', None) or getattr(config, 'model_name', 'unknown')
                        return f"建议使用: {display_name}"
        except Exception as e:
            logger.warning(f"推荐模型失败: {e}")

        return "建议升级模型配置"
