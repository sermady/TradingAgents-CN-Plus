# -*- coding: utf-8 -*-
"""
测试条件逻辑模块

测试范围:
- ConditionalLogic初始化
- 市场分析师继续判断
- 社交媒体分析师继续判断
- 新闻分析师继续判断
- 基本面分析师继续判断
- 投资辩论继续判断
- 风险讨论继续判断
- 工具调用次数检查
"""

import pytest
from unittest.mock import Mock, patch
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage

from tradingagents.graph.conditional_logic import ConditionalLogic


@pytest.mark.unit
def test_conditional_logic_initialization():
    """测试条件逻辑初始化"""
    # Arrange
    logic = ConditionalLogic()

    # Assert
    assert logic is not None
    assert logic.max_debate_rounds == 1
    assert logic.max_risk_discuss_rounds == 1


@pytest.mark.unit
def test_conditional_logic_custom_config():
    """测试自定义配置"""
    # Arrange
    logic = ConditionalLogic(max_debate_rounds=3, max_risk_discuss_rounds=2)

    # Assert
    assert logic.max_debate_rounds == 3
    assert logic.max_risk_discuss_rounds == 2


@pytest.mark.unit
def test_should_continue_market_with_report():
    """测试有报告时市场分析师应该继续"""
    # Arrange
    logic = ConditionalLogic()
    state = {
        "messages": [HumanMessage(content="开始市场分析")],
        "market_report": "市场分析报告内容" * 200,  # 足过100字符
        "market_tool_call_count": 0,
    }

    # Act
    result = logic.should_continue_market(state)

    # Assert
    assert result == "Msg Clear Market"


@pytest.mark.unit
def test_should_continue_market_without_report():
    """测试无报告时市场分析师应该继续"""
    # Arrange
    logic = ConditionalLogic()
    state = {
        "messages": [HumanMessage(content="分析中...")],
        "market_report": "",
        "market_tool_call_count": 0,
    }

    # Act
    result = logic.should_continue_market(state)

    # Assert
    assert result == "Msg Clear Market"


@pytest.mark.unit
def test_should_continue_market_max_tool_calls():
    """测试达到最大工具调用次数时强制结束"""
    # Arrange
    logic = ConditionalLogic()
    state = {
        "messages": [AIMessage(content="分析中...", tool_calls=[])],
        "market_report": "简短报告",
        "market_tool_call_count": 3,  # 达到最大值
    }

    # Act
    result = logic.should_continue_market(state)

    # Assert
    assert result == "Msg Clear Market"


@pytest.mark.unit
def test_should_continue_market_with_tool_calls():
    """测试有工具调用时应该执行工具"""
    # Arrange
    logic = ConditionalLogic()
    mock_tool_call = {"name": "test_tool", "id": "test_id", "args": {}}
    state = {
        "messages": [AIMessage(content="分析中...", tool_calls=[mock_tool_call])],
        "market_report": "",
        "market_tool_call_count": 1,
    }

    # Act
    result = logic.should_continue_market(state)

    # Assert
    assert result == "tools_market"


@pytest.mark.unit
def test_should_continue_social_with_report():
    """测试有报告时社交媒体分析师应该继续"""
    # Arrange
    logic = ConditionalLogic()
    state = {
        "messages": [HumanMessage(content="开始社交分析")],
        "sentiment_report": "情绪分析报告内容" * 200,
        "sentiment_tool_call_count": 0,
    }

    # Act
    result = logic.should_continue_social(state)

    # Assert
    assert result == "Msg Clear Social"


@pytest.mark.unit
def test_should_continue_social_without_report():
    """测试无报告时社交媒体分析师应该继续"""
    # Arrange
    logic = ConditionalLogic()
    state = {
        "messages": [HumanMessage(content="分析中...")],
        "sentiment_report": "",
        "sentiment_tool_call_count": 0,
    }

    # Act
    result = logic.should_continue_social(state)

    # Assert
    assert result == "Msg Clear Social"


@pytest.mark.unit
def test_should_continue_social_max_tool_calls():
    """测试达到最大工具调用次数时强制结束"""
    # Arrange
    logic = ConditionalLogic()
    state = {
        "messages": [AIMessage(content="分析中...", tool_calls=[])],
        "sentiment_report": "简短报告",
        "sentiment_tool_call_count": 3,
    }

    # Act
    result = logic.should_continue_social(state)

    # Assert
    assert result == "Msg Clear Social"


@pytest.mark.unit
def test_should_continue_social_with_tool_calls():
    """测试有工具调用时应该执行工具"""
    # Arrange
    logic = ConditionalLogic()
    mock_tool_call = {"name": "test_tool", "id": "test_id", "args": {}}
    state = {
        "messages": [AIMessage(content="分析中...", tool_calls=[mock_tool_call])],
        "sentiment_report": "",
        "sentiment_tool_call_count": 1,
    }

    # Act
    result = logic.should_continue_social(state)

    # Assert
    assert result == "tools_social"


@pytest.mark.unit
def test_should_continue_news_with_report():
    """测试有报告时新闻分析师应该继续"""
    # Arrange
    logic = ConditionalLogic()
    state = {
        "messages": [HumanMessage(content="开始新闻分析")],
        "news_report": "新闻分析报告内容" * 200,
        "news_tool_call_count": 0,
    }

    # Act
    result = logic.should_continue_news(state)

    # Assert
    assert result == "Msg Clear News"


@pytest.mark.unit
def test_should_continue_news_without_report():
    """测试无报告时新闻分析师应该继续"""
    # Arrange
    logic = ConditionalLogic()
    state = {
        "messages": [HumanMessage(content="分析中...")],
        "news_report": "",
        "news_tool_call_count": 0,
    }

    # Act
    result = logic.should_continue_news(state)

    # Assert
    assert result == "Msg Clear News"


@pytest.mark.unit
def test_should_continue_news_max_tool_calls():
    """测试达到最大工具调用次数时强制结束"""
    # Arrange
    logic = ConditionalLogic()
    state = {
        "messages": [AIMessage(content="分析中...", tool_calls=[])],
        "news_report": "简短报告",
        "news_tool_call_count": 3,
    }

    # Act
    result = logic.should_continue_news(state)

    # Assert
    assert result == "Msg Clear News"


@pytest.mark.unit
def test_should_continue_news_with_tool_calls():
    """测试有工具调用时应该执行工具"""
    # Arrange
    logic = ConditionalLogic()
    mock_tool_call = {"name": "test_tool", "id": "test_id", "args": {}}
    state = {
        "messages": [AIMessage(content="分析中...", tool_calls=[mock_tool_call])],
        "news_report": "",
        "news_tool_call_count": 1,
    }

    # Act
    result = logic.should_continue_news(state)

    # Assert
    assert result == "tools_news"


@pytest.mark.unit
def test_should_continue_fundamentals_with_report():
    """测试有报告时基本面分析师应该继续"""
    # Arrange
    logic = ConditionalLogic()
    state = {
        "messages": [HumanMessage(content="开始基本面分析")],
        "fundamentals_report": "基本面分析报告内容" * 200,
        "fundamentals_tool_call_count": 0,
    }

    # Act
    result = logic.should_continue_fundamentals(state)

    # Assert
    assert result == "Msg Clear Fundamentals"


@pytest.mark.unit
def test_should_continue_fundamentals_without_report():
    """测试无报告时基本面分析师应该继续"""
    # Arrange
    logic = ConditionalLogic()
    state = {
        "messages": [HumanMessage(content="分析中...")],
        "fundamentals_report": "",
        "fundamentals_tool_call_count": 0,
    }

    # Act
    result = logic.should_continue_fundamentals(state)

    # Assert
    assert result == "Msg Clear Fundamentals"


@pytest.mark.unit
def test_should_continue_fundamentals_max_tool_calls():
    """测试达到最大工具调用次数时强制结束"""
    # Arrange
    logic = ConditionalLogic()
    state = {
        "messages": [AIMessage(content="分析中...", tool_calls=[])],
        "fundamentals_report": "简短报告",
        "fundamentals_tool_call_count": 1,
    }

    # Act
    result = logic.should_continue_fundamentals(state)

    # Assert
    assert result == "Msg Clear Fundamentals"


@pytest.mark.unit
def test_should_continue_fundamentals_with_tool_calls():
    """测试有工具调用时应该执行工具"""
    # Arrange
    logic = ConditionalLogic()
    mock_tool_call = {"name": "test_tool", "id": "test_id", "args": {}}
    state = {
        "messages": [AIMessage(content="分析中...", tool_calls=[mock_tool_call])],
        "fundamentals_report": "",
        "fundamentals_tool_call_count": 0,
    }

    # Act
    result = logic.should_continue_fundamentals(state)

    # Assert
    assert result == "tools_fundamentals"


@pytest.mark.unit
def test_should_continue_debate_with_count():
    """测试投资辩论继续判断"""
    # Arrange
    logic = ConditionalLogic()
    state = {
        "investment_debate_state": {
            "count": 1,
            "current_response": "Bull Researcher: ...",
            "bull_history": "Argument 1\nArgument 2",
        }
    }

    # Act
    result = logic.should_continue_debate(state)

    # Assert
    # 小于最大次数，应该继续
    assert "Bear Researcher" in result


@pytest.mark.unit
def test_should_continue_debate_max_count():
    """测试投资辩论达到最大次数"""
    # Arrange
    logic = ConditionalLogic()
    state = {
        "investment_debate_state": {
            "count": 2,  # 最大次数
            "current_response": "Bull Researcher: ...",
            "bull_history": "Argument 1\nArgument 2",
        }
    }

    # Act
    result = logic.should_continue_debate(state)

    # Assert
    # 达到最大次数，应该结束
    assert result == "Research Manager"


@pytest.mark.unit
def test_should_continue_risk_analysis_with_count():
    """测试风险讨论继续判断"""
    # Arrange
    logic = ConditionalLogic()
    state = {"risk_debate_state": {"count": 1, "latest_speaker": "Risky Analyst"}}

    # Act
    result = logic.should_continue_risk_analysis(state)

    # Assert
    # 小于最大次数，应该继续
    assert "Safe Analyst" in result or "Neutral Analyst" in result


@pytest.mark.unit
def test_should_continue_risk_analysis_max_count():
    """测试风险讨论达到最大次数"""
    # Arrange
    logic = ConditionalLogic()
    state = {
        "risk_debate_state": {
            "count": 3,  # 最大次数
            "latest_speaker": "Risky Analyst",
        }
    }

    # Act
    result = logic.should_continue_risk_analysis(state)

    # Assert
    # 达到最大次数，应该结束
    assert result == "Risk Judge"
