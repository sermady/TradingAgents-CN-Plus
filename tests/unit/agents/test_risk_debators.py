# -*- coding: utf-8 -*-
"""
测试风险辩论者功能

测试范围:
- 辩论者基类功能
- 激进/保守/中性辩论者创建
- 辩论者节点执行
- 风险辩论状态管理
- Prompt构建
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

os.environ["USE_MONGODB_STORAGE"] = "false"
os.environ["TRADINGAGENTS_SKIP_DB_INIT"] = "true"

from tradingagents.agents.risk_mgmt.base_debator import (
    BaseDebator,
    AggressiveDebator,
    ConservativeDebator,
    NeutralDebator,
    create_debator,
)


@pytest.mark.unit
def test_create_aggressive_debator():
    """测试创建激进辩论者"""
    # Act
    debator = AggressiveDebator()

    # Assert
    assert debator.debator_type == "risky"
    assert debator.description == "激进"
    assert debator.emoji == "🔥"
    assert "高回报" in debator.goal or "高风险" in debator.goal
    assert "上涨空间" in debator.focus or "增长潜力" in debator.focus


@pytest.mark.unit
def test_create_conservative_debator():
    """测试创建保守辩论者"""
    # Act
    debator = ConservativeDebator()

    # Assert
    assert debator.debator_type == "safe"
    assert debator.description == "安全/保守"
    assert debator.emoji == "🛡️"
    assert "保护" in debator.goal or "安全" in debator.goal
    assert "稳定" in debator.focus or "风险缓解" in debator.focus


@pytest.mark.unit
def test_create_neutral_debator():
    """测试创建中性辩论者"""
    # Act
    debator = NeutralDebator()

    # Assert
    assert debator.debator_type == "neutral"
    assert debator.description == "中性"
    assert debator.emoji == "⚖️"
    assert "平衡" in debator.goal
    assert "全面" in debator.focus or "评估" in debator.focus


@pytest.mark.unit
def test_create_debator_factory():
    """测试辩论者工厂函数"""
    # Act & Assert
    risky = create_debator("risky")
    assert isinstance(risky, AggressiveDebator)
    assert risky.debator_type == "risky"

    safe = create_debator("safe")
    assert isinstance(safe, ConservativeDebator)
    assert safe.debator_type == "safe"

    neutral = create_debator("neutral")
    assert isinstance(neutral, NeutralDebator)
    assert neutral.debator_type == "neutral"

    with pytest.raises(ValueError):
        create_debator("invalid")


@pytest.mark.unit
def test_debator_create_node():
    """测试辩论者节点创建"""
    # Arrange
    mock_llm = Mock()
    debator = AggressiveDebator()

    # Act
    node = debator.create_node(mock_llm)

    # Assert
    assert node is not None
    assert callable(node)


@pytest.mark.unit
def test_debator_node_basic_execution():
    """测试辩论者节点基本执行"""
    # Arrange
    mock_llm = Mock()
    mock_llm_response = Mock()
    mock_llm_response.content = "激进分析师: 该股票具有高增长潜力，建议积极买入..."
    mock_llm.invoke.return_value = mock_llm_response

    debator = AggressiveDebator()
    node = debator.create_node(mock_llm)

    mock_state = {
        "company_of_interest": "000001",
        "trade_date": "2025-01-15",
        "risk_debate_state": {
            "history": "",
            "risky_history": "",
            "safe_history": "",
            "neutral_history": "",
            "current_risky_response": "",
            "current_safe_response": "",
            "current_neutral_response": "",
            "count": 0,
        },
        "market_report": "市场技术分析报告...",
        "sentiment_report": "社交媒体情绪报告...",
        "news_report": "新闻分析报告...",
        "fundamentals_report": "基本面分析报告...",
        "trader_investment_plan": "交易员投资计划...",
    }

    # Mock the prompt builder (imported from prompt_builder module)
    with patch(
        "tradingagents.agents.utils.prompt_builder.build_debator_prompt"
    ) as mock_prompt:
        mock_prompt.return_value = "测试prompt"

        # Act
        result = node(mock_state)

    # Assert
    assert "risk_debate_state" in result
    assert result["risk_debate_state"]["count"] == 1
    assert "risky_history" in result["risk_debate_state"]
    assert result["risk_debate_state"]["latest_speaker"] == "Risky"


@pytest.mark.unit
def test_debator_get_current_responses():
    """测试获取当前回应"""
    # Arrange
    debator = AggressiveDebator()
    risk_debate_state = {
        "current_risky_response": "激进观点",
        "current_safe_response": "保守观点",
        "current_neutral_response": "中性观点",
    }

    # Act
    responses = debator._get_current_responses(risk_debate_state)

    # Assert
    assert responses["risky"] == "激进观点"
    assert responses["safe"] == "保守观点"
    assert responses["neutral"] == "中性观点"


@pytest.mark.unit
def test_debator_get_analyst_reports():
    """测试获取分析师报告"""
    # Arrange
    debator = AggressiveDebator()
    state = {
        "market_report": "市场报告",
        "sentiment_report": "情绪报告",
        "news_report": "新闻报告",
        "fundamentals_report": "基本面报告",
    }

    # Act
    reports = debator._get_analyst_reports(state)

    # Assert
    assert reports["market"] == "市场报告"
    assert reports["sentiment"] == "情绪报告"
    assert reports["news"] == "新闻报告"
    assert reports["fundamentals"] == "基本面报告"


@pytest.mark.unit
def test_debator_debate_state_update():
    """测试辩论状态更新"""
    # Arrange
    mock_llm = Mock()
    mock_llm_response = Mock()
    mock_llm_response.content = "激进分析师: 基于数据分析..."
    mock_llm.invoke.return_value = mock_llm_response

    debator = AggressiveDebator()
    node = debator.create_node(mock_llm)

    initial_count = 5
    mock_state = {
        "company_of_interest": "000001",
        "trade_date": "2025-01-15",
        "risk_debate_state": {
            "history": "previous arguments...",
            "risky_history": "previous risky arguments...",
            "safe_history": "",
            "neutral_history": "",
            "current_risky_response": "",
            "current_safe_response": "",
            "current_neutral_response": "",
            "count": initial_count,
        },
        "market_report": "市场报告",
        "sentiment_report": "情绪报告",
        "news_report": "新闻报告",
        "fundamentals_report": "基本面报告",
        "trader_investment_plan": "交易员计划",
    }

    # Mock the prompt builder (imported from prompt_builder module)
    with patch(
        "tradingagents.agents.utils.prompt_builder.build_debator_prompt"
    ) as mock_prompt:
        mock_prompt.return_value = "测试prompt"

        # Act
        result = node(mock_state)

    # Assert
    # 验证计数递增
    assert result["risk_debate_state"]["count"] == initial_count + 1
    # 验证历史记录更新
    assert "previous arguments..." in result["risk_debate_state"]["history"]
    # 验证current_risky_response更新
    assert "激进分析师" in result["risk_debate_state"]["current_risky_response"]


@pytest.mark.unit
def test_debator_error_handling():
    """测试辩论者错误处理"""
    # Arrange
    mock_llm = Mock()
    # 模拟LLM调用失败
    mock_llm.invoke.side_effect = Exception("LLM调用失败")

    debator = AggressiveDebator()
    node = debator.create_node(mock_llm)

    mock_state = {
        "company_of_interest": "000001",
        "trade_date": "2025-01-15",
        "risk_debate_state": {
            "history": "",
            "risky_history": "",
            "safe_history": "",
            "neutral_history": "",
            "current_risky_response": "",
            "current_safe_response": "",
            "current_neutral_response": "",
            "count": 0,
        },
        "market_report": "市场报告",
        "sentiment_report": "情绪报告",
        "news_report": "新闻报告",
        "fundamentals_report": "基本面报告",
        "trader_investment_plan": "计划",
    }

    # Act & Assert - 应该抛出异常
    with patch(
        "tradingagents.agents.utils.prompt_builder.build_debator_prompt"
    ) as mock_prompt:
        mock_prompt.return_value = "测试prompt"

        with pytest.raises(Exception):
            node(mock_state)


@pytest.mark.unit
def test_conservative_debator_prompt():
    """测试保守辩论者Prompt构建"""
    # Arrange
    debator = ConservativeDebator()
    reports = {
        "market": "市场分析报告",
        "sentiment": "情绪分析报告",
        "news": "新闻分析报告",
        "fundamentals": "基本面分析报告",
    }
    history = "辩论历史..."
    current_responses = {
        "risky": "激进观点...",
        "safe": "",
        "neutral": "中性观点...",
    }
    trader_decision = "交易员决策..."

    # Act & Assert - Mock the prompt builder
    with patch(
        "tradingagents.agents.utils.prompt_builder.build_debator_prompt"
    ) as mock_prompt:
        mock_prompt.return_value = "保守辩论者prompt"

        prompt = debator._build_prompt(
            reports, history, current_responses, trader_decision
        )

        # 验证调用了prompt builder
        mock_prompt.assert_called_once()
        call_kwargs = mock_prompt.call_args[1]
        assert call_kwargs["role"] == "conservative"
        assert call_kwargs["description"] == "安全/保守"


@pytest.mark.unit
def test_neutral_debator_prompt():
    """测试中性辩论者Prompt构建"""
    # Arrange
    debator = NeutralDebator()
    reports = {
        "market": "市场分析报告",
        "sentiment": "情绪分析报告",
        "news": "新闻分析报告",
        "fundamentals": "基本面分析报告",
    }
    history = "辩论历史..."
    current_responses = {
        "risky": "激进观点...",
        "safe": "保守观点...",
        "neutral": "",
    }
    trader_decision = "交易员决策..."

    # Act & Assert - Mock the prompt builder
    with patch(
        "tradingagents.agents.utils.prompt_builder.build_debator_prompt"
    ) as mock_prompt:
        mock_prompt.return_value = "中性辩论者prompt"

        prompt = debator._build_prompt(
            reports, history, current_responses, trader_decision
        )

        # 验证调用了prompt builder
        mock_prompt.assert_called_once()
        call_kwargs = mock_prompt.call_args[1]
        assert call_kwargs["role"] == "neutral"


@pytest.mark.unit
def test_multiple_debators_sequential():
    """测试多个辩论者顺序执行"""
    # Arrange
    mock_llm = Mock()

    responses = [
        "激进分析师: 建议积极买入...",
        "保守分析师: 建议谨慎观望...",
        "中性分析师: 建议适度配置...",
    ]
    mock_llm.invoke.side_effect = [Mock(content=r) for r in responses]

    debators = [
        AggressiveDebator(),
        ConservativeDebator(),
        NeutralDebator(),
    ]

    mock_state = {
        "company_of_interest": "000001",
        "trade_date": "2025-01-15",
        "risk_debate_state": {
            "history": "",
            "risky_history": "",
            "safe_history": "",
            "neutral_history": "",
            "current_risky_response": "",
            "current_safe_response": "",
            "current_neutral_response": "",
            "count": 0,
        },
        "market_report": "市场报告",
        "sentiment_report": "情绪报告",
        "news_report": "新闻报告",
        "fundamentals_report": "基本面报告",
        "trader_investment_plan": "计划",
    }

    # Act
    with patch(
        "tradingagents.agents.utils.prompt_builder.build_debator_prompt"
    ) as mock_prompt:
        mock_prompt.return_value = "测试prompt"

        for debator in debators:
            node = debator.create_node(mock_llm)
            mock_state = node(mock_state)
            mock_state = {
                **mock_state,
                "risk_debate_state": mock_state["risk_debate_state"],
            }

    # Assert
    # 验证最终计数
    assert mock_state["risk_debate_state"]["count"] == 3
    # 验证所有辩论者都有回应
    assert mock_state["risk_debate_state"]["current_risky_response"] != ""
    assert mock_state["risk_debate_state"]["current_safe_response"] != ""
    assert mock_state["risk_debate_state"]["current_neutral_response"] != ""


@pytest.mark.unit
def test_debator_with_empty_reports():
    """测试辩论者处理空报告"""
    # Arrange
    mock_llm = Mock()
    mock_llm_response = Mock()
    mock_llm_response.content = "激进分析师: 缺少数据，无法做出判断..."
    mock_llm.invoke.return_value = mock_llm_response

    debator = AggressiveDebator()
    node = debator.create_node(mock_llm)

    mock_state = {
        "company_of_interest": "000001",
        "trade_date": "2025-01-15",
        "risk_debate_state": {
            "history": "",
            "risky_history": "",
            "safe_history": "",
            "neutral_history": "",
            "current_risky_response": "",
            "current_safe_response": "",
            "current_neutral_response": "",
            "count": 0,
        },
        "market_report": "",
        "sentiment_report": "",
        "news_report": "",
        "fundamentals_report": "",
        "trader_investment_plan": "",
    }

    # Act
    with patch(
        "tradingagents.agents.utils.prompt_builder.build_debator_prompt"
    ) as mock_prompt:
        mock_prompt.return_value = "测试prompt"

        result = node(mock_state)

    # Assert
    assert "risk_debate_state" in result
    assert result["risk_debate_state"]["count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
