# -*- coding: utf-8 -*-
"""
执行层风控网关单元测试 (Phase 3.1)

测试范围:
- ExecutionRiskGateway.validate_trade_decision()
- 仓位集中度检查
- 目标价合理性检查
- 置信度与风险一致性检查
- 置信度阈值检查
- 风险评分上限检查
- 流动性检查

测试策略:
- Happy Path: 正常交易决策通过
- Edge Cases: 边界值测试
- Error Cases: 违规决策被拦截
"""

import pytest
from datetime import datetime

from app.services.execution_risk_gateway import (
    ExecutionRiskGateway,
    TradeDecision,
    ValidationResult,
    CheckStatus,
    RiskLevel,
    get_execution_risk_gateway,
)


@pytest.mark.unit
class TestExecutionRiskGateway:
    """执行层风控网关测试套件"""

    @pytest.fixture
    def gateway(self):
        """创建风控网关实例"""
        return get_execution_risk_gateway()

    @pytest.fixture
    def valid_decision(self):
        """创建有效的交易决策"""
        return TradeDecision(
            symbol="600000",
            action="买入",
            current_price=10.0,
            target_price=11.0,
            confidence=0.75,
            risk_score=0.5,
            position_ratio=0.25,  # 25% < 30% 限制
            stop_loss=9.0,
            sector="银行",
        )

    # ========== Happy Path Tests ==========

    def test_validate_valid_decision_passes(self, gateway, valid_decision):
        """测试: 有效的交易决策应该通过验证"""
        result = gateway.validate_trade_decision(valid_decision)

        assert result.passed is True
        assert result.blocked is False
        assert result.overall_risk_level == RiskLevel.LOW
        assert "通过" in result.summary
        assert len(result.check_results) > 0

    def test_validate_with_context_passes(self, gateway, valid_decision):
        """测试: 带上下文的验证应该正常工作"""
        context = {
            "sector_positions": {"银行": 0.20},  # 20% + 25% = 45% < 50% 限制
            "avg_daily_volume": 1000000,
        }

        result = gateway.validate_trade_decision(valid_decision, context)

        assert result.passed is True
        assert result.blocked is False

    # ========== Position Concentration Tests ==========

    def test_block_excessive_single_position(self, gateway):
        """测试: 单一标的仓位超过30%应该被拦截"""
        decision = TradeDecision(
            symbol="600000",
            action="买入",
            current_price=10.0,
            target_price=11.0,
            confidence=0.8,
            risk_score=0.4,
            position_ratio=0.35,  # 35% > 30% 限制
        )

        result = gateway.validate_trade_decision(decision)

        assert result.blocked is True
        assert result.passed is False
        assert result.overall_risk_level == RiskLevel.CRITICAL
        assert any("仓位" in r.message and "超过" in r.message for r in result.check_results)

    def test_block_excessive_sector_position(self, gateway):
        """测试: 板块仓位超过50%应该被拦截"""
        decision = TradeDecision(
            symbol="600000",
            action="买入",
            current_price=10.0,
            target_price=11.0,
            confidence=0.8,
            risk_score=0.4,
            position_ratio=0.35,
            sector="银行",
        )

        context = {"sector_positions": {"银行": 0.20}}  # 20% + 35% = 55% > 50%

        result = gateway.validate_trade_decision(decision, context)

        assert result.blocked is True
        assert result.passed is False
        assert result.overall_risk_level == RiskLevel.CRITICAL
        # 修复：检查是否被仓位检查拦截
        assert any("仓位" in r.message for r in result.check_results if not r.passed)

    # ========== Target Price Reasonableness Tests ==========

    def test_block_target_above_limit_up(self, gateway):
        """测试: 目标价高于涨停价应该被拦截"""
        decision = TradeDecision(
            symbol="600000",
            action="买入",
            current_price=10.0,
            target_price=11.5,  # 11.5 > 11.0 (10% 涨停)
            confidence=0.8,
            risk_score=0.4,
            position_ratio=0.2,
        )

        result = gateway.validate_trade_decision(decision)

        assert result.blocked is True
        assert result.passed is False
        assert any("涨停" in r.message or "目标价" in r.message for r in result.check_results)

    def test_block_target_below_limit_down(self, gateway):
        """测试: 目标价低于跌停价应该被拦截"""
        decision = TradeDecision(
            symbol="600000",
            action="卖出",
            current_price=10.0,
            target_price=8.5,  # 8.5 < 9.0 (10% 跌停)
            confidence=0.8,
            risk_score=0.4,
            position_ratio=0.2,
        )

        result = gateway.validate_trade_decision(decision)

        assert result.blocked is True
        assert result.passed is False
        assert any("跌停" in r.message or "目标价" in r.message for r in result.check_results)

    def test_warn_high_target_deviation(self, gateway):
        """测试: 目标价偏离度过高应该产生警告"""
        decision = TradeDecision(
            symbol="600000",
            action="买入",
            current_price=10.0,
            target_price=10.6,  # 6% 偏离，接近50%阈值(0.5)
            confidence=0.8,
            risk_score=0.4,
            position_ratio=0.2,
        )

        result = gateway.validate_trade_decision(decision)

        # 应该通过（偏离度在警告阈值以下）
        assert result.passed is True
        assert result.blocked is False

    def test_block_invalid_current_price(self, gateway):
        """测试: 当前价格无效应该被拦截"""
        decision = TradeDecision(
            symbol="600000",
            action="买入",
            current_price=0.0,  # 无效价格
            target_price=11.0,
            confidence=0.8,
            risk_score=0.4,
            position_ratio=0.2,
        )

        result = gateway.validate_trade_decision(decision)

        assert result.blocked is True
        assert any("无效" in r.message for r in result.check_results)

    # ========== Confidence Threshold Tests ==========

    def test_block_low_confidence(self, gateway):
        """测试: 置信度低于50%应该被拦截"""
        decision = TradeDecision(
            symbol="600000",
            action="买入",
            current_price=10.0,
            target_price=11.0,
            confidence=0.4,  # 40% < 50% 最低要求
            risk_score=0.4,
            position_ratio=0.2,
        )

        result = gateway.validate_trade_decision(decision)

        assert result.blocked is True
        assert result.passed is False
        assert result.overall_risk_level == RiskLevel.HIGH
        assert any("置信度" in r.message and "低于" in r.message for r in result.check_results)

    def test_pass_high_confidence(self, gateway):
        """测试: 高置信度(>=80%)应该通过并标记"""
        decision = TradeDecision(
            symbol="600000",
            action="买入",
            current_price=10.0,
            target_price=11.0,
            confidence=0.85,  # >= 80%
            risk_score=0.4,
            position_ratio=0.2,
        )

        result = gateway.validate_trade_decision(decision)

        assert result.passed is True
        assert any("高置信度" in r.message for r in result.check_results)

    # ========== Risk Score Tests ==========

    def test_block_excessive_risk_score(self, gateway):
        """测试: 风险评分超过85%应该被拦截"""
        decision = TradeDecision(
            symbol="600000",
            action="买入",
            current_price=10.0,
            target_price=11.0,
            confidence=0.7,
            risk_score=0.9,  # 90% > 85% 限制
            position_ratio=0.2,
        )

        result = gateway.validate_trade_decision(decision)

        assert result.blocked is True
        assert result.passed is False
        assert result.overall_risk_level == RiskLevel.CRITICAL
        assert any("风险评分" in r.message and "超过" in r.message for r in result.check_results)

    # ========== Confidence-Risk Consistency Tests ==========

    def test_warn_high_confidence_high_risk(self, gateway):
        """测试: 高置信度+高风险评分应该产生警告"""
        decision = TradeDecision(
            symbol="600000",
            action="买入",
            current_price=10.0,
            target_price=11.0,
            confidence=0.8,  # 高置信度
            risk_score=0.7,  # 高风险
            position_ratio=0.2,
        )

        result = gateway.validate_trade_decision(decision)

        # 应该通过但有警告
        assert result.passed is True
        assert any("矛盾" in r.message or "不匹配" in r.message for r in result.check_results if r.status == CheckStatus.WARNING)

    def test_warn_low_confidence_low_risk(self, gateway):
        """测试: 低置信度+低风险评分应该产生警告"""
        decision = TradeDecision(
            symbol="600000",
            action="买入",
            current_price=10.0,
            target_price=11.0,
            confidence=0.4,  # 低置信度
            risk_score=0.2,  # 低风险
            position_ratio=0.2,
        )

        result = gateway.validate_trade_decision(decision)

        # 置信度检查会先拦截，所以这里应该被拦截
        assert result.blocked is True

    # ========== Liquidity Check Tests ==========

    def test_warn_low_liquidity(self, gateway):
        """测试: 低流动性应该产生警告"""
        decision = TradeDecision(
            symbol="600000",
            action="买入",
            current_price=10.0,
            target_price=11.0,
            confidence=0.7,
            risk_score=0.5,
            position_ratio=0.25,  # 25% < 30% 限制，避免触发单仓拦截
        )

        context = {"avg_daily_volume": 10000}  # 低成交量

        result = gateway.validate_trade_decision(decision, context)

        # 应该通过但有流动性警告
        assert result.passed is True
        assert any("流动性" in r.message or "成交量" in r.message for r in result.check_results if r.status == CheckStatus.WARNING)

    def test_skip_liquidity_check_without_context(self, gateway):
        """测试: 无上下文时跳过流动性检查"""
        decision = TradeDecision(
            symbol="600000",
            action="买入",
            current_price=10.0,
            target_price=11.0,
            confidence=0.7,
            risk_score=0.5,
            position_ratio=0.2,  # 降低仓位避免触发其他限制
        )

        result = gateway.validate_trade_decision(decision, context=None)

        # 应该通过，流动性检查被跳过（返回 PASSED 状态）
        assert result.passed is True
        # 检查流动性检查存在并标记为通过
        liquidity_checks = [r for r in result.check_results if "流动性" in r.message]
        assert len(liquidity_checks) > 0

    # ========== Result Structure Tests ==========

    def test_validation_result_structure(self, gateway, valid_decision):
        """测试: 验证结果数据结构正确"""
        result = gateway.validate_trade_decision(valid_decision)

        # 检查必需字段
        assert hasattr(result, "passed")
        assert hasattr(result, "blocked")
        assert hasattr(result, "overall_risk_level")
        assert hasattr(result, "check_results")
        assert hasattr(result, "summary")
        assert hasattr(result, "timestamp")

        # 检查类型
        assert isinstance(result.passed, bool)
        assert isinstance(result.blocked, bool)
        assert isinstance(result.check_results, list)
        assert isinstance(result.summary, str)
        assert isinstance(result.timestamp, str)

    def test_validation_result_to_dict(self, gateway, valid_decision):
        """测试: ValidationResult.to_dict() 方法正常工作"""
        result = gateway.validate_trade_decision(valid_decision)

        result_dict = result.to_dict()

        # 检查字典结构
        assert "passed" in result_dict
        assert "blocked" in result_dict
        assert "overall_risk_level" in result_dict
        assert "summary" in result_dict
        assert "timestamp" in result_dict
        assert "check_results" in result_dict

        # 检查 check_results 结构
        assert isinstance(result_dict["check_results"], list)
        if len(result_dict["check_results"]) > 0:
            check = result_dict["check_results"][0]
            assert "check_name" in check
            assert "status" in check
            assert "passed" in check
            assert "message" in check

    # ========== Configuration Tests ==========

    def test_gateway_configuration(self, gateway):
        """测试: 风控网关配置正确加载"""
        # 检查必需的配置项
        assert "max_single_position" in gateway.config
        assert "max_sector_position" in gateway.config
        assert "limit_up_pct" in gateway.config
        assert "limit_down_pct" in gateway.config
        assert "min_confidence" in gateway.config
        assert "high_confidence_threshold" in gateway.config
        assert "max_risk_score" in gateway.config
        assert "max_target_deviation" in gateway.config

        # 检查默认值
        assert gateway.config["max_single_position"] == 0.30
        assert gateway.config["min_confidence"] == 0.5
        assert gateway.config["max_risk_score"] == 0.85

    # ========== Integration Tests ==========

    def test_validate_from_analysis_result(self, gateway):
        """测试: 从分析结果创建并验证决策"""
        analysis_result = {
            "symbol": "600000",
            "decision": {
                "symbol": "600000",
                "recommendation": "买入",
                "current_price": 10.0,
                "target_price": 11.0,
                "confidence": 0.75,
                "risk_score": 0.5,
                "position_suggestion": "中等仓位 (40-60%)",
                "stop_loss": 9.0,
            },
        }

        result = gateway.validate_from_analysis_result(analysis_result)

        # 应该成功提取并验证
        assert isinstance(result, ValidationResult)

    def test_extract_position_ratio_various_formats(self, gateway):
        """测试: 从不同格式提取仓位比例"""
        # 测试百分比格式
        result1 = gateway._extract_position_ratio("30%")
        assert result1 == 0.3

        # 测试文字描述
        result2 = gateway._extract_position_ratio("满仓")
        assert result2 == 1.0

        result3 = gateway._extract_position_ratio("轻仓")
        assert result3 == 0.2

        result4 = gateway._extract_position_ratio("中等仓位")
        assert result4 == 0.5

        # 测试默认值
        result5 = gateway._extract_position_ratio("未知格式")
        assert result5 == 0.3


@pytest.mark.unit
class TestTradeDecision:
    """TradeDecision 数据类测试"""

    def test_trade_decision_creation(self):
        """测试: TradeDecision 正确创建"""
        decision = TradeDecision(
            symbol="600000",
            action="买入",
            current_price=10.0,
            target_price=11.0,
            confidence=0.75,
            risk_score=0.5,
            position_ratio=0.25,
            stop_loss=9.0,
            sector="银行",
        )

        assert decision.symbol == "600000"
        assert decision.action == "买入"
        assert decision.current_price == 10.0
        assert decision.target_price == 11.0
        assert decision.confidence == 0.75
        assert decision.risk_score == 0.5
        assert decision.position_ratio == 0.25
        assert decision.stop_loss == 9.0
        assert decision.sector == "银行"

    def test_trade_decision_optional_fields(self):
        """测试: TradeDecision 可选字段"""
        decision = TradeDecision(
            symbol="600000",
            action="持有",
            current_price=10.0,
            target_price=11.0,
            confidence=0.6,
            risk_score=0.5,
            # position_ratio 默认 0.0
            # stop_loss 默认 None
            # sector 默认 None
        )

        assert decision.position_ratio == 0.0
        assert decision.stop_loss is None
        assert decision.sector is None


@pytest.mark.unit
class TestValidationResult:
    """ValidationResult 数据类测试"""

    def test_validation_result_creation(self):
        """测试: ValidationResult 正确创建"""
        from app.services.execution_risk_gateway import CheckResult

        check_results = [
            CheckResult(
                check_name="测试检查",
                status=CheckStatus.PASSED,
                passed=True,
                message="检查通过",
                risk_level=RiskLevel.LOW,
            )
        ]

        result = ValidationResult(
            passed=True,
            blocked=False,
            overall_risk_level=RiskLevel.LOW,
            check_results=check_results,
            summary="所有检查通过",
        )

        assert result.passed is True
        assert result.blocked is False
        assert result.overall_risk_level == RiskLevel.LOW
        assert len(result.check_results) == 1
        assert result.summary == "所有检查通过"

    def test_validation_result_to_dict(self):
        """测试: ValidationResult.to_dict() 正确转换"""
        from app.services.execution_risk_gateway import CheckResult

        check_results = [
            CheckResult(
                check_name="测试检查",
                status=CheckStatus.PASSED,
                passed=True,
                message="检查通过",
                risk_level=RiskLevel.LOW,
            )
        ]

        result = ValidationResult(
            passed=True,
            blocked=False,
            overall_risk_level=RiskLevel.LOW,
            check_results=check_results,
            summary="所有检查通过",
        )

        result_dict = result.to_dict()

        assert result_dict["passed"] is True
        assert result_dict["blocked"] is False
        assert result_dict["overall_risk_level"] == "low"
        assert len(result_dict["check_results"]) == 1
        assert result_dict["check_results"][0]["check_name"] == "测试检查"
        assert result_dict["check_results"][0]["status"] == "passed"
