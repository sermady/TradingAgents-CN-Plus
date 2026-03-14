# -*- coding: utf-8 -*-
"""
模型能力管理服务

提供模型能力评估、验证和推荐功能。
"""

from typing import Tuple, Dict, Any

from .parser import ModelNameParser
from .capability import ModelCapabilityEvaluator
from .validator import ModelValidator
from .recommender import ModelRecommender


class ModelCapabilityService:
    """模型能力管理服务"""

    def __init__(self):
        self._parser = ModelNameParser()
        self._evaluator = ModelCapabilityEvaluator()
        self._validator = ModelValidator()
        self._recommender = ModelRecommender()

    def _parse_aggregator_model_name(self, model_name: str) -> Tuple[str, str]:
        """解析聚合渠道的模型名称"""
        return self._parser.parse_aggregator_model_name(model_name)

    def _get_model_capability_with_mapping(self, model_name: str) -> Tuple[int, str]:
        """获取模型能力等级（支持聚合渠道映射）"""
        return self._parser.get_model_capability_with_mapping(model_name)

    def get_model_capability(self, model_name: str) -> int:
        """获取模型的能力等级"""
        return self._evaluator.get_model_capability(model_name)

    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """获取模型的完整配置信息"""
        return self._evaluator.get_model_config(model_name)

    def validate_model_pair(
        self, quick_model: str, deep_model: str, research_depth: str
    ) -> Dict[str, Any]:
        """验证模型对是否适合当前分析深度"""
        return self._validator.validate_model_pair(quick_model, deep_model, research_depth)

    def recommend_models_for_depth(self, research_depth: str) -> Tuple[str, str]:
        """根据分析深度推荐合适的模型对"""
        return self._recommender.recommend_models_for_depth(research_depth)

    def _get_default_models(self) -> Tuple[str, str]:
        """获取默认模型对"""
        return self._recommender._get_default_models()

    def _recommend_model(self, model_type: str, min_level: int) -> str:
        """推荐满足要求的模型"""
        return self._validator._recommend_model(model_type, min_level)


# 单例
_model_capability_service = None


def get_model_capability_service() -> ModelCapabilityService:
    """获取模型能力服务单例"""
    global _model_capability_service
    if _model_capability_service is None:
        _model_capability_service = ModelCapabilityService()
    return _model_capability_service
