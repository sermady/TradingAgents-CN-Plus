# -*- coding: utf-8 -*-
"""
不确定性量化器测试

测试 UncertaintyQuantifier 的各种功能
"""

import pytest
from tradingagents.utils.uncertainty_quantifier import UncertaintyQuantifier


class TestUncertaintyQuantifier:

    def test_extract_confidence_from_report(self):
        """测试: 从报告中提取置信度"""
        report = "建议: 买入，置信度: 75%"
        confidence = UncertaintyQuantifier.extract_confidence_from_report(report)
        assert confidence == 0.75

    def test_extract_confidence_default_values(self):
        """测试: 置信度默认值推断"""
        # 强烈语气
        report1 = "强烈推荐买入"
        assert UncertaintyQuantifier.extract_confidence_from_report(report1) == 0.75

        # 谨慎语气
        report2 = "谨慎建议买入"
        assert UncertaintyQuantifier.extract_confidence_from_report(report2) == 0.55

        # 默认
        report3 = "建议买入"
        assert UncertaintyQuantifier.extract_confidence_from_report(report3) == 0.6

    def test_calculate_probability_range(self):
        """测试: 计算概率区间"""
        ranges = UncertaintyQuantifier.calculate_probability_range(
            current_price=19.37,
            target_price=22.0,
            confidence=0.7
        )

        assert "optimistic" in ranges
        assert "base" in ranges
        assert ranges["base"] == 22.0
        assert ranges["optimistic"] >= ranges["base"]

    def test_probability_range_direction(self):
        """测试: 概率区间方向正确"""
        # 目标价高于当前价
        ranges_up = UncertaintyQuantifier.calculate_probability_range(
            current_price=19.37,
            target_price=22.0,
            confidence=0.7
        )
        assert ranges_up["optimistic"] >= ranges_up["base"]
        assert ranges_up["base"] >= ranges_up["pessimistic"]

        # 目标价低于当前价
        ranges_down = UncertaintyQuantifier.calculate_probability_range(
            current_price=22.0,
            target_price=19.37,
            confidence=0.7
        )
        assert ranges_down["optimistic"] <= ranges_down["base"]
        assert ranges_down["base"] <= ranges_down["pessimistic"]

    def test_format_uncertainty_section(self):
        """测试: 格式化不确定性说明"""
        section = UncertaintyQuantifier.format_uncertainty_section(
            current_price=19.37,
            target_price=22.0,
            confidence=0.75
        )

        assert "概率评估" in section
        assert "乐观情景" in section
        assert "基准情景" in section
        assert "谨慎情景" in section
        assert "75%" in section  # 置信度显示

    def test_format_recommendation_with_risk(self):
        """测试: 格式化带风险提示的投资建议"""
        section = UncertaintyQuantifier.format_recommendation_with_risk(
            recommendation="买入",
            current_price=19.37,
            target_price=22.0,
            confidence=0.75,
            stop_loss=18.0
        )

        assert "投资建议" in section
        assert "买入" in section
        assert "19.37" in section
        assert "22.0" in section
        assert "止损" in section


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
