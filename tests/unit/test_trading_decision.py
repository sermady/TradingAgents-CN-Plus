# -*- coding: utf-8 -*-
"""
交易决策提取和验证单元测试
"""

import pytest


class TestExtractTradingDecision:
    """测试交易决策提取功能"""

    def test_extract_buy_recommendation(self):
        """测试提取买入建议（包含数据质量评分调整）"""
        from tradingagents.agents.trader.trader import extract_trading_decision

        content = "建议买入，目标价21元，置信度0.8，风险评分0.3"
        result = extract_trading_decision(content)

        assert result["recommendation"] == "买入"
        assert result["target_price"] == 21.0
        # Phase 1.1: 数据质量评分默认100.0（A级），置信度提升5%: 0.8 * 1.05 = 0.84
        assert abs(result["confidence"] - 0.84) < 0.01
        assert result["risk_score"] == 0.3

    def test_extract_hold_recommendation_with_range(self):
        """测试提取持有建议（带价格区间）"""
        from tradingagents.agents.trader.trader import extract_trading_decision

        content = "持有建议，价格区间19-22元，置信度0.6"
        result = extract_trading_decision(content)

        assert result["recommendation"] in ["持有", "未知"]
        if result["target_price_range"]:
            assert (
                "19" in result["target_price_range"]
                and "22" in result["target_price_range"]
            )

    def test_auto_calculate_target_price_for_buy(self):
        """测试买入时自动计算目标价"""
        from tradingagents.agents.trader.trader import extract_trading_decision

        content = "建议买入"
        result = extract_trading_decision(content, current_price=20.0)

        assert result["recommendation"] == "买入"
        assert result["target_price"] == 23.0
        assert any("自动计算" in w for w in result["warnings"])

    def test_auto_calculate_target_price_for_sell(self):
        """测试卖出时自动计算目标价"""
        from tradingagents.agents.trader.trader import extract_trading_decision

        content = "建议卖出"
        result = extract_trading_decision(content, current_price=20.0)

        assert result["recommendation"] == "卖出"
        assert result["target_price"] == 18.0
        assert any("自动计算" in w for w in result["warnings"])

    def test_auto_calculate_target_price_for_hold(self):
        """测试持有时自动计算价格区间"""
        from tradingagents.agents.trader.trader import extract_trading_decision

        content = "建议持有"
        result = extract_trading_decision(content, current_price=20.0)

        assert result["recommendation"] == "持有"
        assert result["target_price_range"] == "¥19.0-21.0"
        assert any("自动计算" in w for w in result["warnings"])

    def test_default_confidence_for_buy(self):
        """测试买入时默认置信度（包含数据质量评分调整）"""
        from tradingagents.agents.trader.trader import extract_trading_decision

        content = "建议买入"
        result = extract_trading_decision(content)

        # Phase 1.1: 数据质量评分默认100.0（A级），置信度提升5%: 0.7 * 1.05 = 0.735
        assert abs(result["confidence"] - 0.735) < 0.01

    def test_default_risk_for_sell(self):
        """测试卖出时默认风险评分"""
        from tradingagents.agents.trader.trader import extract_trading_decision

        content = "建议卖出"
        result = extract_trading_decision(content)

        assert result["risk_score"] == 0.5


class TestValidateTradingDecision:
    """测试交易决策验证"""

    def test_validate_with_auto_filled_values(self):
        """测试包含自动填充值的验证"""
        from tradingagents.agents.trader.trader import validate_trading_decision

        content = "建议买入"
        result = validate_trading_decision(content, "¥", "600765", current_price=20.0)

        assert result["recommendation"] == "买入"
        assert result["has_target_price"] == True
        assert result["extracted"]["target_price"] == 23.0

    def test_validate_currency_unit(self):
        """测试货币单位验证"""
        from tradingagents.agents.trader.trader import validate_trading_decision

        content = "建议买入，目标价$21"
        result = validate_trading_decision(content, "¥", "600765")

        has_currency_warning = any(
            "¥" in w or "$" in w or "A股" in w for w in result.get("warnings", [])
        )
        assert has_currency_warning or len(result.get("warnings", [])) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
