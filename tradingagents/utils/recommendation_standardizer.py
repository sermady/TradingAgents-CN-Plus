# -*- coding: utf-8 -*-
"""
投资建议标准化器

统一 AI 分析师的投资建议格式和用词
"""

from typing import Dict, Optional
from enum import Enum
import re

class StandardRecommendation(Enum):
    """标准化的投资建议"""
    STRONG_BUY = "强烈买入"
    BUY = "买入"
    MODERATE_BUY = "谨慎买入"
    HOLD = "持有"
    MODERATE_SELL = "谨慎卖出"
    SELL = "卖出"
    STRONG_SELL = "强烈卖出"
    NEUTRAL = "中性观望"

class RecommendationStandardizer:
    """投资建议标准化器"""

    NORMALIZATION_MAP = {
        # 优先匹配更长的模式
        "强烈买入": StandardRecommendation.STRONG_BUY,
        "强烈卖出": StandardRecommendation.STRONG_SELL,
        "坚决回避": StandardRecommendation.STRONG_SELL,
        "逢低买入": StandardRecommendation.BUY,
        "谨慎看多": StandardRecommendation.MODERATE_BUY,
        "谨慎买入": StandardRecommendation.MODERATE_BUY,
        "谨慎看空": StandardRecommendation.MODERATE_SELL,
        "谨慎卖出": StandardRecommendation.MODERATE_SELL,
        "买入": StandardRecommendation.BUY,
        "看多": StandardRecommendation.BUY,
        "卖出": StandardRecommendation.SELL,
        "看空": StandardRecommendation.SELL,
        "持有": StandardRecommendation.HOLD,
        "观望": StandardRecommendation.NEUTRAL,
        "中性": StandardRecommendation.NEUTRAL,
    }

    ABSOLUTE_WORD_REPLACEMENTS = {
        "坚决回避": "建议谨慎观望",
        "必须": "建议",
        "务必": "建议",
        "绝对": "倾向于",
        "一定": "大概率",
    }

    @classmethod
    def normalize(cls, text: str) -> StandardRecommendation:
        """将非标准建议映射到标准建议"""
        for pattern, rec in cls.NORMALIZATION_MAP.items():
            if pattern in text:
                return rec
        return StandardRecommendation.NEUTRAL

    @classmethod
    def soften_absolute_language(cls, text: str) -> str:
        """软化绝对化用词"""
        result = text
        for absolute, softer in cls.ABSOLUTE_WORD_REPLACEMENTS.items():
            result = result.replace(absolute, softer)
        return result

    @classmethod
    def extract_recommendation_with_confidence(cls, text: str) -> Dict:
        """提取投资建议及其置信度"""
        recommendation = cls.normalize(text)
        confidence_match = re.search(r'(置信度|确定性|把握)[：:]\s*(\d+[%％])', text)
        confidence = confidence_match.group(2) if confidence_match else "未明确"
        reasoning = ""
        reason_match = re.search(r'(理由|依据|原因)[：:]\s*([^\n]+)', text)
        if reason_match:
            reasoning = reason_match.group(2).strip()
        return {
            "recommendation": recommendation.value,
            "confidence": confidence,
            "reasoning": reasoning
        }
