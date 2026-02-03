# -*- coding: utf-8 -*-
"""
投资建议标准化器测试

测试 RecommendationStandardizer 的各种功能
"""

import pytest
from tradingagents.utils.recommendation_standardizer import (
    RecommendationStandardizer,
    StandardRecommendation
)

class TestRecommendationStandardizer:

    def test_normalize_buy_recommendations(self):
        """测试: 标准化各种买入表述"""
        assert RecommendationStandardizer.normalize("建议买入") == StandardRecommendation.BUY
        assert RecommendationStandardizer.normalize("逢低买入") == StandardRecommendation.BUY
        assert RecommendationStandardizer.normalize("谨慎看多") == StandardRecommendation.MODERATE_BUY
        assert RecommendationStandardizer.normalize("谨慎买入") == StandardRecommendation.MODERATE_BUY

    def test_normalize_sell_recommendations(self):
        """测试: 标准化各种卖出表述"""
        assert RecommendationStandardizer.normalize("建议卖出") == StandardRecommendation.SELL
        assert RecommendationStandardizer.normalize("坚决回避") == StandardRecommendation.STRONG_SELL
        assert RecommendationStandardizer.normalize("强烈卖出") == StandardRecommendation.STRONG_SELL

    def test_normalize_hold_recommendations(self):
        """测试: 标准化持有/中性表述"""
        assert RecommendationStandardizer.normalize("持有") == StandardRecommendation.HOLD
        assert RecommendationStandardizer.normalize("观望") == StandardRecommendation.NEUTRAL
        assert RecommendationStandardizer.normalize("中性") == StandardRecommendation.NEUTRAL

    def test_soften_absolute_language(self):
        """测试: 软化绝对化用词"""
        text = "建议坚决回避，必须立即清仓"
        softened = RecommendationStandardizer.soften_absolute_language(text)

        assert "坚决回避" not in softened
        assert "必须" not in softened
        assert "谨慎观望" in softened or "建议" in softened

    def test_extract_recommendation_with_confidence(self):
        """测试: 提取建议和置信度"""
        text = "建议: 买入，置信度: 75%，理由: 技术面改善"
        result = RecommendationStandardizer.extract_recommendation_with_confidence(text)

        assert result["recommendation"] == StandardRecommendation.BUY.value
        assert result["confidence"] == "75%"
        assert "技术面改善" in result["reasoning"]

    def test_extract_with_missing_confidence(self):
        """测试: 置信度缺失时的默认值"""
        text = "建议: 买入，理由: 趋势向好"
        result = RecommendationStandardizer.extract_recommendation_with_confidence(text)

        assert result["recommendation"] == StandardRecommendation.BUY.value
        assert result["confidence"] == "未明确"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
