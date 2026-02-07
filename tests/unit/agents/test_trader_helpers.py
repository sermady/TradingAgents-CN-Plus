# -*- coding: utf-8 -*-
"""
测试交易员辅助函数

测试范围:
- 从内容提取投资建议
- 从内容提取目标价位
- 从内容提取置信度
- 从内容提取风险评分
"""

import pytest
from tradingagents.agents.trader.trader import (
    _extract_recommendation_from_content,
    _extract_target_price_from_content,
    _extract_confidence_from_content,
    _extract_risk_score_from_content,
)


class TestExtractRecommendationFromContent:
    """测试从内容提取投资建议"""

    @pytest.mark.unit
    def test_extract_buy_recommendation(self):
        """测试提取买入建议"""
        # Arrange
        content = "最终交易建议：**买入**"

        # Act
        result = _extract_recommendation_from_content(content)

        # Assert
        assert result == "买入"

    @pytest.mark.unit
    def test_extract_sell_recommendation(self):
        """测试提取卖出建议"""
        # Arrange
        content = "最终交易建议：**卖出**"

        # Act
        result = _extract_recommendation_from_content(content)

        # Assert
        assert result == "卖出"

    @pytest.mark.unit
    def test_extract_hold_recommendation(self):
        """测试提取持有建议"""
        # Arrange
        content = "最终交易建议：**持有**"

        # Act
        result = _extract_recommendation_from_content(content)

        # Assert
        assert result == "持有"

    @pytest.mark.unit
    def test_extract_various_formats(self):
        """测试不同格式的建议提取"""
        # 测试各种格式
        formats = [
            ("投资建议：**买入**", "买入"),
            ("建议：卖出", "卖出"),
            ("**持有**", "持有"),
            ("决策：买入", "买入"),
        ]

        for content, expected in formats:
            result = _extract_recommendation_from_content(content)
            assert result == expected, f"Failed for content: {content}"

    @pytest.mark.unit
    def test_extract_no_recommendation(self):
        """测试无建议时返回None"""
        # Arrange
        content = "这是一个分析报告，没有明确的建议"

        # Act
        result = _extract_recommendation_from_content(content)

        # Assert
        assert result is None


class TestExtractTargetPriceFromContent:
    """测试从内容提取目标价位"""

    @pytest.mark.unit
    def test_extract_single_price_with_yuan(self):
        """测试提取单一价格（人民币）"""
        # Arrange
        content = "目标价位：¥180.50"

        # Act
        price, price_range = _extract_target_price_from_content(content, "¥")

        # Assert
        assert price == 180.50
        assert price_range is None

    @pytest.mark.unit
    def test_extract_single_price_with_dollar(self):
        """测试提取单一价格（美元）"""
        # Arrange
        content = "目标价位：$150"

        # Act
        price, price_range = _extract_target_price_from_content(content, "$")

        # Assert
        assert price == 150.0
        assert price_range is None

    @pytest.mark.unit
    def test_extract_price_range_with_yuan(self):
        """测试提取价格区间（人民币）"""
        # Arrange
        content = "目标价位：¥160-180"

        # Act
        price, price_range = _extract_target_price_from_content(content, "¥")

        # Assert
        assert price is None
        assert price_range == "¥160-180"

    @pytest.mark.unit
    def test_extract_price_range_with_dash(self):
        """测试提取价格区间（使用-分隔符）"""
        # Arrange
        content = "目标价格：150-180"

        # Act
        price, price_range = _extract_target_price_from_content(content, "")

        # Assert
        assert price is None
        assert price_range == "150-180"

    @pytest.mark.unit
    def test_extract_no_price(self):
        """测试无价格时返回None"""
        # Arrange
        content = "这是一个分析报告"

        # Act
        price, price_range = _extract_target_price_from_content(content, "¥")

        # Assert
        assert price is None
        assert price_range is None

    @pytest.mark.unit
    def test_extract_alternative_patterns(self):
        """测试其他价格模式"""
        patterns = [
            ("目标：¥200", "¥", (200.0, None)),
            ("价格目标：$175.50", "$", (175.50, None)),
            ("目标价格：100-120", "", (None, "100-120")),
        ]

        for content, currency, expected in patterns:
            price, price_range = _extract_target_price_from_content(content, currency)
            assert (price, price_range) == expected, f"Failed for content: {content}"


class TestExtractConfidenceFromContent:
    """测试从内容提取置信度"""

    @pytest.mark.unit
    def test_extract_decimal_confidence(self):
        """测试提取小数格式置信度"""
        # Arrange
        content = "置信度：0.75"

        # Act
        result = _extract_confidence_from_content(content)

        # Assert
        assert result == 0.75

    @pytest.mark.unit
    def test_extract_percentage_confidence(self):
        """测试提取百分比格式置信度"""
        # Arrange
        content = "置信度：75%"

        # Act
        result = _extract_confidence_from_content(content)

        # Assert
        assert result == 0.75

    @pytest.mark.unit
    def test_extract_float_percentage_confidence(self):
        """测试提取浮点百分比格式置信度"""
        # Arrange
        content = "置信度：82.5%"

        # Act
        result = _extract_confidence_from_content(content)

        # Assert
        assert result == 0.825

    @pytest.mark.unit
    def test_extract_markdown_bold_confidence(self):
        """测试提取Markdown粗体格式置信度"""
        # Arrange
        content = "**置信度**：0.85"

        # Act
        result = _extract_confidence_from_content(content)

        # Assert
        assert result == 0.85

    @pytest.mark.unit
    def test_extract_no_confidence(self):
        """测试无置信度时返回None"""
        # Arrange
        content = "这是一个分析报告"

        # Act
        result = _extract_confidence_from_content(content)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_extract_invalid_confidence(self):
        """测试无效置信度值"""
        # Arrange
        content = "置信度：150"  # 超出有效范围

        # Act
        result = _extract_confidence_from_content(content)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_extract_case_insensitive(self):
        """测试不区分大小写匹配（中文）"""
        # Arrange
        content = "置信度: 0.8"  # 使用英文冒号测试不区分大小写

        # Act
        result = _extract_confidence_from_content(content)

        # Assert
        assert result == 0.8


class TestExtractRiskScoreFromContent:
    """测试从内容提取风险评分"""

    @pytest.mark.unit
    def test_extract_decimal_risk_score(self):
        """测试提取小数格式风险评分"""
        # Arrange
        content = "风险评分：0.45"

        # Act
        result = _extract_risk_score_from_content(content)

        # Assert
        assert result == 0.45

    @pytest.mark.unit
    def test_extract_percentage_risk_score(self):
        """测试提取百分比格式风险评分"""
        # Arrange
        content = "风险评分：45%"

        # Act
        result = _extract_risk_score_from_content(content)

        # Assert
        assert result == 0.45

    @pytest.mark.unit
    def test_extract_markdown_bold_risk_score(self):
        """测试提取Markdown粗体格式风险评分"""
        # Arrange
        content = "**风险评分**：0.30"

        # Act
        result = _extract_risk_score_from_content(content)

        # Assert
        assert result == 0.30

    @pytest.mark.unit
    def test_extract_no_risk_score(self):
        """测试无风险评分时返回None"""
        # Arrange
        content = "这是一个分析报告"

        # Act
        result = _extract_risk_score_from_content(content)

        # Assert
        assert result is None

    @pytest.mark.unit
    def test_extract_case_insensitive(self):
        """测试不区分大小写匹配（中文）"""
        # Arrange
        content = "风险评分: 0.5"  # 使用英文冒号测试不区分大小写

        # Act
        result = _extract_risk_score_from_content(content)

        # Assert
        assert result == 0.5


class TestEdgeCases:
    """测试边界情况"""

    @pytest.mark.unit
    def test_empty_content(self):
        """测试空内容"""
        assert _extract_recommendation_from_content("") is None
        assert _extract_confidence_from_content("") is None
        assert _extract_risk_score_from_content("") is None
        price, price_range = _extract_target_price_from_content("", "¥")
        assert price is None and price_range is None

    @pytest.mark.unit
    def test_whitespace_only_content(self):
        """测试仅空白内容"""
        assert _extract_recommendation_from_content("   \n\t  ") is None
        assert _extract_confidence_from_content("   \n\t  ") is None

    @pytest.mark.unit
    def test_multiple_values_in_content(self):
        """测试包含多个值的内容"""
        content = """
        置信度：0.75
        风险评分：0.45
        最终交易建议：**买入**
        目标价位：¥180
        """

        assert _extract_recommendation_from_content(content) == "买入"
        assert _extract_confidence_from_content(content) == 0.75
        assert _extract_risk_score_from_content(content) == 0.45
        price, _ = _extract_target_price_from_content(content, "¥")
        assert price == 180.0
