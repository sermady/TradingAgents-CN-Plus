# -*- coding: utf-8 -*-
"""
风控验证体系 Wave 1 测试脚本

测试内容:
1. 数据质量评分系统
2. 执行层风控网关
3. RateLimitMiddleware 配置
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


def test_data_quality_score():
    """测试数据质量评分系统"""
    print("\n" + "=" * 60)
    print("测试 1: 数据质量评分系统")
    print("=" * 60)

    try:
        from tradingagents.dataflows.data_source_manager import (
            ValidatedDataResult,
            DataSourceManager,
        )

        # 测试 ValidatedDataResult
        result = ValidatedDataResult(
            data={"current_price": 100.0, "volume": 10000},
            quality_score=85.5,
            quality_grade="B",
            quality_issues=["测试问题"],
            data_source="Tushare",
        )

        assert result.quality_score == 85.5
        assert result.quality_grade == "B"
        assert result.is_valid(min_score=60)
        assert not result.is_valid(min_score=90)

        print("✅ ValidatedDataResult 数据结构正常")
        print(f"   质量评分: {result.quality_score}/100")
        print(f"   质量等级: {result.quality_grade}")
        print(f"   是否有效(>=60): {result.is_valid()}")

        # 测试 DataSourceManager._score_to_grade
        manager = DataSourceManager()

        test_cases = [
            (95, "A"),
            (85, "B"),
            (75, "C"),
            (65, "D"),
            (50, "F"),
        ]

        for score, expected in test_cases:
            grade = manager._score_to_grade(score)
            assert grade == expected, f"期望 {expected} 但得到 {grade}"
            print(f"✅ 评分 {score} -> 等级 {grade}")

        print("\n✅ 数据质量评分系统测试通过")
        return True

    except Exception as e:
        print(f"\n❌ 数据质量评分系统测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_execution_risk_gateway():
    """测试执行层风控网关"""
    print("\n" + "=" * 60)
    print("测试 2: 执行层风控网关")
    print("=" * 60)

    try:
        from app.services.execution_risk_gateway import (
            ExecutionRiskGateway,
            TradeDecision,
            CheckStatus,
            RiskLevel,
        )

        gateway = ExecutionRiskGateway()

        # 测试正常决策
        normal_decision = TradeDecision(
            symbol="000001.SZ",
            action="买入",
            current_price=100.0,
            target_price=105.0,
            confidence=0.75,
            risk_score=0.4,
            position_ratio=0.2,
        )

        result = gateway.validate_trade_decision(normal_decision)

        print(f"✅ 正常决策验证完成")
        print(f"   通过状态: {result.passed}")
        print(f"   拦截状态: {result.blocked}")
        print(f"   整体风险等级: {result.overall_risk_level.value}")
        print(f"   检查项数: {len(result.check_results)}")

        assert result.passed, "正常决策应该通过"
        assert not result.blocked, "正常决策不应该被拦截"

        # 测试高风险决策（目标价超出涨停范围）
        risky_decision = TradeDecision(
            symbol="000001.SZ",
            action="买入",
            current_price=100.0,
            target_price=120.0,  # 超出涨停价110
            confidence=0.9,
            risk_score=0.4,
            position_ratio=0.2,
        )

        result2 = gateway.validate_trade_decision(risky_decision)

        print(f"\n✅ 高风险决策验证完成")
        print(f"   通过状态: {result2.passed}")
        print(f"   拦截状态: {result2.blocked}")
        print(f"   整体风险等级: {result2.overall_risk_level.value}")
        print(f"   摘要: {result2.summary}")

        assert result2.blocked, "高风险决策应该被拦截"

        # 测试仓位集中度超标
        high_position_decision = TradeDecision(
            symbol="000001.SZ",
            action="买入",
            current_price=100.0,
            target_price=105.0,
            confidence=0.8,
            risk_score=0.4,
            position_ratio=0.5,  # 超过30%限制
        )

        result3 = gateway.validate_trade_decision(high_position_decision)

        print(f"\n✅ 高仓位决策验证完成")
        print(f"   通过状态: {result3.passed}")
        print(f"   拦截状态: {result3.blocked}")
        print(f"   整体风险等级: {result3.overall_risk_level.value}")

        assert result3.blocked, "高仓位决策应该被拦截"

        print("\n✅ 执行层风控网关测试通过")
        return True

    except Exception as e:
        print(f"\n❌ 执行层风控网关测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_agent_state_fields():
    """测试 AgentState 数据质量字段"""
    print("\n" + "=" * 60)
    print("测试 3: AgentState 数据质量字段")
    print("=" * 60)

    try:
        from tradingagents.agents.utils.agent_states import (
            AgentState,
            InvestDebateState,
            RiskDebateState,
        )

        # 检查 AgentState 类是否有数据质量字段
        import inspect

        # 获取 AgentState 的注解字段
        if hasattr(AgentState, "__annotations__"):
            annotations = AgentState.__annotations__
            assert "data_quality_score" in annotations, "缺少 data_quality_score 字段"
            assert "data_quality_grade" in annotations, "缺少 data_quality_grade 字段"
            assert "data_quality_issues" in annotations, "缺少 data_quality_issues 字段"

            print("✅ AgentState 包含数据质量字段:")
            print(f"   data_quality_score: {annotations['data_quality_score']}")
            print(f"   data_quality_grade: {annotations['data_quality_grade']}")
            print(f"   data_quality_issues: {annotations['data_quality_issues']}")

        # 验证字段默认值
        defaults = AgentState.__dataclass_fields__ if hasattr(AgentState, "__dataclass_fields__") else {}
        if "data_quality_score" in defaults:
            default_score = defaults["data_quality_score"].default
            assert default_score == 100.0, f"默认值应该是100.0，实际是{default_score}"
            print(f"\n✅ 字段默认值正确:")
            print(f"   data_quality_score 默认: {default_score}")
            print(f"   data_quality_grade 默认: {defaults.get('data_quality_grade', {}).default}")

        print("\n✅ AgentState 字段测试通过")
        return True

    except Exception as e:
        print(f"\n❌ AgentState 字段测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_trader_confidence_adjustment():
    """测试交易员置信度根据数据质量调整"""
    print("\n" + "=" * 60)
    print("测试 4: 交易员置信度调整")
    print("=" * 60)

    try:
        from tradingagents.agents.trader.trader import extract_trading_decision

        # 测试内容 - 模拟决策文本
        content = """
        投资建议: 买入
        目标价位: ¥35.50
        置信度: 0.75
        风险评分: 0.4
        最终交易建议: 买入
        """

        # 高质量数据（A级，>=90）
        result_high = extract_trading_decision(content, 30.0, 95.0)
        confidence_high = result_high["confidence"]

        # 中等质量数据（B级，80-89）
        result_medium = extract_trading_decision(content, 30.0, 85.0)
        confidence_medium = result_medium["confidence"]

        # 边缘质量数据（D级，60-69）
        result_low = extract_trading_decision(content, 30.0, 65.0)
        confidence_low = result_low["confidence"]

        # F级数据（<60）
        result_f = extract_trading_decision(content, 30.0, 55.0)
        confidence_f = result_f["confidence"]

        print(f"✅ 不同质量评分的置信度调整:")
        print(f"   A级(95分): {confidence_high:.2f}")
        print(f"   B级(85分): {confidence_medium:.2f}")
        print(f"   D级(65分): {confidence_low:.2f} (降低10%)")
        print(f"   F级(55分): {confidence_f:.2f} (降低20%)")

        # 验证调整逻辑
        assert confidence_low < confidence_medium, "D级应该比B级置信度低"
        assert confidence_f < confidence_low, "F级应该比D级置信度低"
        assert confidence_high >= confidence_medium, "A级应该不低于B级"

        print("\n✅ 置信度调整测试通过")
        return True

    except Exception as e:
        print(f"\n❌ 置信度调整测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("TradingAgents-CN 风控验证体系 Wave 1 测试")
    print("=" * 60)

    results = []

    # 运行所有测试
    results.append(("数据质量评分系统", test_data_quality_score()))
    results.append(("执行层风控网关", test_execution_risk_gateway()))
    results.append(("AgentState 字段", test_agent_state_fields()))
    results.append(("交易员置信度调整", test_trader_confidence_adjustment()))

    # 打印总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}: {name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！Wave 1 实施成功！")
        return 0
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败，请检查实现")
        return 1


if __name__ == "__main__":
    sys.exit(main())
