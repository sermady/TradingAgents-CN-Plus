# -*- coding: utf-8 -*-
"""
测试辩论轮次配置和执行

测试范围:
- ConditionalLogic 辩论轮次配置
- 投资辩论轮次计算逻辑
- 风险讨论轮次计算逻辑
- 2轮辩论的正确执行
"""

import pytest
from tradingagents.graph.conditional_logic import ConditionalLogic
from tradingagents.agents.utils.agent_states import AgentState


@pytest.mark.unit
def test_conditional_logic_default_rounds():
    """测试 ConditionalLogic 默认辩论轮次为 2"""
    # Arrange & Act
    logic = ConditionalLogic()

    # Assert
    assert logic.max_debate_rounds == 2, "默认投资辩论轮次应为 2"
    assert logic.max_risk_discuss_rounds == 2, "默认风险讨论轮次应为 2"


@pytest.mark.unit
def test_conditional_logic_custom_rounds():
    """测试自定义辩论轮次"""
    # Arrange & Act
    logic = ConditionalLogic(max_debate_rounds=3, max_risk_discuss_rounds=1)

    # Assert
    assert logic.max_debate_rounds == 3, "投资辩论轮次应为 3"
    assert logic.max_risk_discuss_rounds == 1, "风险讨论轮次应为 1"


@pytest.mark.unit
def test_debate_max_count_calculation():
    """测试投资辩论最大次数计算"""
    # Arrange
    logic = ConditionalLogic(max_debate_rounds=2)

    # Act
    # 每轮辩论 = Bull + Bear 各发言一次 = 2次
    # max_count = 2 * max_debate_rounds = 2 * 2 = 4
    max_count = 2 * logic.max_debate_rounds

    # Assert
    assert max_count == 4, f"2轮辩论应有4次发言，实际: {max_count}"


@pytest.mark.unit
def test_debate_max_count_with_3_rounds():
    """测试3轮投资辩论最大次数计算"""
    # Arrange
    logic = ConditionalLogic(max_debate_rounds=3)

    # Act
    max_count = 2 * logic.max_debate_rounds

    # Assert
    assert max_count == 6, f"3轮辩论应有6次发言，实际: {max_count}"


@pytest.mark.unit
def test_risk_discuss_max_count_calculation():
    """测试风险讨论最大次数计算"""
    # Arrange
    logic = ConditionalLogic(max_risk_discuss_rounds=2)

    # Act
    # 每轮讨论 = Risky + Safe + Neutral 各发言一次 = 3次
    # max_count = 3 * max_risk_discuss_rounds = 3 * 2 = 6
    max_count = 3 * logic.max_risk_discuss_rounds

    # Assert
    assert max_count == 6, f"2轮风险讨论应有6次发言，实际: {max_count}"


@pytest.mark.unit
def test_should_continue_debate_logic():
    """测试投资辩论继续逻辑"""
    # Arrange
    logic = ConditionalLogic(max_debate_rounds=2)

    # 创建模拟状态
    state = AgentState()
    state["investment_debate_state"] = {
        "count": 0,
        "current_response": "Bull Researcher: 初始观点"
    }

    # Act & Assert - 第0次，应继续
    next_speaker = logic.should_continue_debate(state)
    assert next_speaker == "Bear Researcher", f"第0次后应轮到 Bear，实际: {next_speaker}"

    # 第1次后（Bull 发言完），应继续
    state["investment_debate_state"]["count"] = 1
    state["investment_debate_state"]["current_response"] = "Bear Researcher: 反驳观点"
    next_speaker = logic.should_continue_debate(state)
    assert next_speaker == "Bull Researcher", f"第1次后应轮到 Bull，实际: {next_speaker}"

    # 第3次后，应继续
    state["investment_debate_state"]["count"] = 3
    state["investment_debate_state"]["current_response"] = "Bear Researcher: 第二轮反驳"
    next_speaker = logic.should_continue_debate(state)
    assert next_speaker == "Bull Researcher", f"第3次后应轮到 Bull，实际: {next_speaker}"

    # 第4次后（2轮完成），应结束
    state["investment_debate_state"]["count"] = 4
    state["investment_debate_state"]["current_response"] = "Bull Researcher: 第二轮观点"
    next_speaker = logic.should_continue_debate(state)
    assert next_speaker == "Research Manager", f"第4次后应结束，实际: {next_speaker}"


@pytest.mark.unit
def test_should_continue_risk_analysis_logic():
    """测试风险讨论继续逻辑"""
    # Arrange
    logic = ConditionalLogic(max_risk_discuss_rounds=2)

    # 创建模拟状态
    state = AgentState()
    state["risk_debate_state"] = {
        "count": 0,
        "latest_speaker": "Neutral"
    }

    # Act & Assert - 第0次，应继续到 Risky
    next_speaker = logic.should_continue_risk_analysis(state)
    assert next_speaker == "Risky Analyst", f"第0次后应轮到 Risky，实际: {next_speaker}"

    # 第1次后（Risky 发言完），应继续到 Safe
    state["risk_debate_state"]["count"] = 1
    state["risk_debate_state"]["latest_speaker"] = "Risky"
    next_speaker = logic.should_continue_risk_analysis(state)
    assert next_speaker == "Safe Analyst", f"第1次后应轮到 Safe，实际: {next_speaker}"

    # 第2次后（Safe 发言完），应继续到 Neutral
    state["risk_debate_state"]["count"] = 2
    state["risk_debate_state"]["latest_speaker"] = "Safe"
    next_speaker = logic.should_continue_risk_analysis(state)
    assert next_speaker == "Neutral Analyst", f"第2次后应轮到 Neutral，实际: {next_speaker}"

    # 第3次后（Neutral 发言完），应继续到 Risky（第2轮开始）
    state["risk_debate_state"]["count"] = 3
    state["risk_debate_state"]["latest_speaker"] = "Neutral"
    next_speaker = logic.should_continue_risk_analysis(state)
    assert next_speaker == "Risky Analyst", f"第3次后应轮到 Risky（第2轮），实际: {next_speaker}"

    # 第6次后（2轮完成），应结束
    state["risk_debate_state"]["count"] = 6
    state["risk_debate_state"]["latest_speaker"] = "Neutral"
    next_speaker = logic.should_continue_risk_analysis(state)
    assert next_speaker == "Risk Judge", f"第6次后应结束，实际: {next_speaker}"


@pytest.mark.unit
def test_single_round_debate():
    """测试单轮辩论模式（向后兼容）"""
    # Arrange
    logic = ConditionalLogic(max_debate_rounds=1)

    # 创建模拟状态
    state = AgentState()
    state["investment_debate_state"] = {
        "count": 0,
        "current_response": "Bull Researcher: 初始观点"
    }

    # Act & Assert - 第0次，应继续
    next_speaker = logic.should_continue_debate(state)
    assert next_speaker == "Bear Researcher"

    # 第1次后（Bear 发言完），第2次后应结束（1轮 = 2次发言）
    state["investment_debate_state"]["count"] = 1
    state["investment_debate_state"]["current_response"] = "Bear Researcher: 反驳观点"
    next_speaker = logic.should_continue_debate(state)
    assert next_speaker == "Bull Researcher"

    # 第2次后（1轮完成），应结束
    state["investment_debate_state"]["count"] = 2
    state["investment_debate_state"]["current_response"] = "Bull Researcher: 回应"
    next_speaker = logic.should_continue_debate(state)
    assert next_speaker == "Research Manager", f"单轮辩论应在2次发言后结束，实际: {next_speaker}"


@pytest.mark.unit
def test_risk_assessment_in_prompts():
    """验证风险管理提示词包含新的风险评估要求"""
    # 这个测试确保风险管理分析师的提示词包含新增的风险评估要求
    # 实际的 LLM 调用测试在集成测试中进行

    required_keywords = [
        "流动性风险评估",
        "集中度风险评估",
        "宏观经济风险评估"
    ]

    # 读取风险管理分析师文件
    import os
    risk_mgmt_dir = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..", "tradingagents", "agents", "risk_mgmt"
    )

    for filename in ["aggresive_debator.py", "conservative_debator.py", "neutral_debator.py"]:
        filepath = os.path.join(risk_mgmt_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 验证每个文件都包含所有必需的风险评估关键词
        for keyword in required_keywords:
            assert keyword in content, (
                f"{filename} 应包含 '{keyword}' 风险评估要求"
            )


@pytest.mark.unit
def test_data_issues_logging_pattern():
    """验证分析师遵循数据质量问题日志记录模式"""
    import os
    import re

    analysts_dir = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..", "tradingagents", "agents", "analysts"
    )

    # 需要检查的分析师文件（应包含 data_issues 处理）
    analysts_to_check = [
        "market_analyst.py",
        "fundamentals_analyst.py",
        "news_analyst.py",
        "china_market_analyst.py",
        "social_media_analyst.py",
    ]

    for filename in analysts_to_check:
        filepath = os.path.join(analysts_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 检查是否获取 data_issues
        assert 'data_issues = state.get("data_issues"' in content, (
            f"{filename} 应从 state 获取 data_issues"
        )

        # 检查是否有日志记录逻辑
        assert "logger.warning" in content, (
            f"{filename} 应有日志记录逻辑"
        )


if __name__ == "__main__":
    # 可以直接运行此文件进行快速测试
    print("🧪 运行辩论轮次测试...")
    test_conditional_logic_default_rounds()
    print("✅ 默认辩论轮次测试通过")

    test_conditional_logic_custom_rounds()
    print("✅ 自定义辩论轮次测试通过")

    test_debate_max_count_calculation()
    print("✅ 投资辩论次数计算测试通过")

    test_risk_discuss_max_count_calculation()
    print("✅ 风险讨论次数计算测试通过")

    test_should_continue_debate_logic()
    print("✅ 投资辩论逻辑测试通过")

    test_should_continue_risk_analysis_logic()
    print("✅ 风险讨论逻辑测试通过")

    test_risk_assessment_in_prompts()
    print("✅ 风险评估提示词测试通过")

    test_data_issues_logging_pattern()
    print("✅ 数据问题日志模式测试通过")

    print("\n🎉 所有测试通过！")
