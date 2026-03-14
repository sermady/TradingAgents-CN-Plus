# -*- coding: utf-8 -*-
"""模型推荐模块

根据分析深度推荐合适的模型对。
"""

import logging
from typing import Tuple, List, Dict, Any

from app.constants.model_capabilities import (
    ANALYSIS_DEPTH_REQUIREMENTS,
    ModelRole,
    ModelFeature,
)
from app.core.unified_config_service import get_config_manager

logger = logging.getLogger(__name__)


class ModelRecommender:
    """模型推荐器"""

    @staticmethod
    def recommend_models_for_depth(research_depth: str) -> Tuple[str, str]:
        """
        根据分析深度推荐合适的模型对

        Args:
            research_depth: 研究深度

        Returns:
            (quick_model, deep_model) 元组
        """
        requirements = ANALYSIS_DEPTH_REQUIREMENTS.get(
            research_depth, ANALYSIS_DEPTH_REQUIREMENTS["标准"]
        )

        # 获取所有启用的模型
        try:
            llm_configs = get_config_manager().get_llm_configs()
            enabled_models = []
            for c in llm_configs:
                if isinstance(c, dict):
                    is_enabled = c.get("enabled", True)
                    model_name = c.get("model_name", "unknown")
                else:
                    is_enabled = getattr(c, "enabled", True)
                    model_name = getattr(c, "model_name", "unknown")

                if is_enabled:
                    enabled_models.append(c)
                    logger.debug(f"✅ 模型已启用: {model_name}")

        except Exception as e:
            logger.error(f"获取模型配置失败: {e}")
            return ModelRecommender._get_default_models()

        if not enabled_models:
            logger.warning("没有启用的模型，使用默认配置")
            return ModelRecommender._get_default_models()

        # 筛选适合快速分析的模型
        quick_candidates = ModelRecommender._filter_quick_models(enabled_models, requirements)

        # 筛选适合深度分析的模型
        deep_candidates = ModelRecommender._filter_deep_models(enabled_models, requirements)

        # 按性价比排序
        quick_candidates.sort(key=ModelRecommender._get_sort_key, reverse=True)
        deep_candidates.sort(key=ModelRecommender._get_sort_key, reverse=True)

        # 选择最佳模型
        quick_model = ModelRecommender._extract_model_name(quick_candidates)
        deep_model = ModelRecommender._extract_model_name(deep_candidates)

        # 如果没找到合适的，使用系统默认
        if not quick_model or not deep_model:
            return ModelRecommender._get_default_models()

        logger.info(
            f"🤖 为 {research_depth} 分析推荐模型: "
            f"quick={quick_model}, deep={deep_model}"
        )

        return quick_model, deep_model

    @staticmethod
    def _filter_quick_models(models: List[Any], requirements: Dict) -> List[Any]:
        """筛选适合快速分析的模型"""
        candidates = []
        for m in models:
            roles, level, features = ModelRecommender._extract_model_attrs(m)

            # 将字符串角色转换为枚举
            roles_enum = []
            for role_str in roles:
                try:
                    roles_enum.append(ModelRole(role_str))
                except ValueError:
                    roles_enum.append(ModelRole.BOTH)

            # 将字符串特性转换为枚举
            features_enum = []
            for feature_str in features:
                try:
                    features_enum.append(ModelFeature(feature_str))
                except ValueError:
                    pass

            if (
                (ModelRole.QUICK_ANALYSIS in roles_enum or ModelRole.BOTH in roles_enum)
                and level >= requirements["quick_model_min"]
                and ModelFeature.TOOL_CALLING in features_enum
            ):
                candidates.append(m)

        return candidates

    @staticmethod
    def _filter_deep_models(models: List[Any], requirements: Dict) -> List[Any]:
        """筛选适合深度分析的模型"""
        candidates = []
        for m in models:
            roles, level, _ = ModelRecommender._extract_model_attrs(m)

            # 将字符串角色转换为枚举
            roles_enum = []
            for role_str in roles:
                try:
                    roles_enum.append(ModelRole(role_str))
                except ValueError:
                    roles_enum.append(ModelRole.BOTH)

            if (
                ModelRole.DEEP_ANALYSIS in roles_enum or ModelRole.BOTH in roles_enum
            ) and level >= requirements["deep_model_min"]:
                candidates.append(m)

        return candidates

    @staticmethod
    def _extract_model_attrs(m):
        """提取模型属性"""
        if isinstance(m, dict):
            roles = m.get("suitable_roles", ["both"])
            level = m.get("capability_level", 2)
            features = m.get("features", [])
        else:
            roles = getattr(m, "suitable_roles", ["both"])
            level = getattr(m, "capability_level", 2)
            features = getattr(m, "features", [])
        return roles, level, features

    @staticmethod
    def _get_sort_key(x) -> tuple:
        """获取排序键"""
        if isinstance(x, dict):
            level = x.get("capability_level", 2)
            perf = x.get("performance_metrics") or {}
            cost = perf.get("cost", 3)
            quality = perf.get("quality", 3)
        else:
            level = getattr(x, "capability_level", 2)
            perf = getattr(x, "performance_metrics", None) or {}
            cost = perf.get("cost", 3)
            quality = perf.get("quality", 3)
        return level, cost, quality

    @staticmethod
    def _extract_model_name(candidates) -> str:
        """从候选列表中提取模型名称"""
        if not candidates:
            return None
        first = candidates[0]
        if isinstance(first, dict):
            return first.get("model_name")
        return getattr(first, "model_name", None)

    @staticmethod
    def _get_default_models() -> Tuple[str, str]:
        """获取默认模型对"""
        try:
            config_manager = get_config_manager()
            quick_model = config_manager.get_quick_analysis_model()
            deep_model = config_manager.get_deep_analysis_model()

            # 修复：如果返回的是整个配置对象，尝试提取 model_name
            if isinstance(quick_model, dict):
                quick_model = quick_model.get("model_name", "qwen-turbo")

            if isinstance(deep_model, dict):
                deep_model = deep_model.get("model_name", "qwen-plus")

            # 确保返回的是字符串
            if not isinstance(quick_model, str):
                quick_model = "qwen-turbo"

            if not isinstance(deep_model, str):
                deep_model = "qwen-plus"

            logger.info(f"✅ 使用系统默认模型: quick={quick_model}, deep={deep_model}")
            return quick_model, deep_model
        except Exception as e:
            logger.error(f"❌ 获取默认模型失败: {e}")
            return "qwen-turbo", "qwen-plus"
