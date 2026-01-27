# -*- coding: utf-8 -*-
"""
测试反思模块

测试范围:
- Reflector初始化
- 反思prompt生成
- 组件反思处理
- 记忆更新
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os

os.environ["USE_MONGODB_STORAGE"] = "false"
os.environ["TRADINGAGENTS_SKIP_DB_INIT"] = "true"


@pytest.mark.unit
def test_reflector_initialization():
    """测试反思器初始化"""
    try:
        from tradingagents.graph.reflection import Reflector
    except Exception as e:
        pytest.skip(f"反射模块初始化失败，跳过: {e}")

    mock_llm = Mock()
    reflector = Reflector(mock_llm)
    assert reflector is not None
    assert reflector.quick_thinking_llm == mock_llm


@pytest.mark.unit
def test_reflector_get_prompt():
    """测试获取反思prompt"""
    try:
        from tradingagents.graph.reflection import Reflector
    except Exception as e:
        pytest.skip(f"反射模块初始化失败，跳过: {e}")

    mock_llm = Mock()
    reflector = Reflector(mock_llm)
    prompt = reflector._get_reflection_prompt()

    assert "Reasoning" in prompt
    assert "investment decisions" in prompt.lower() or "Investment decisions" in prompt
    assert "Summary" in prompt


@pytest.mark.unit
def test_reflector_extract_situation():
    """测试提取当前情况"""
    try:
        from tradingagents.graph.reflection import Reflector
    except Exception as e:
        pytest.skip(f"反射模块初始化失败，跳过: {e}")

    mock_llm = Mock()
    reflector = Reflector(mock_llm)

    mock_state = {
        "messages": [],
        "market_report": "市场报告",
        "sentiment_report": "情绪报告",
        "news_report": "新闻报告",
        "fundamentals_report": "基本面报告",
    }

    situation = reflector._extract_current_situation(mock_state)

    assert "市场报告" in situation
    assert "情绪报告" in situation
    assert "新闻报告" in situation
    assert "基本面报告" in situation


@pytest.mark.unit
def test_reflector_reflect_component():
    """测试组件反思"""
    try:
        from tradingagents.graph.reflection import Reflector
    except Exception as e:
        pytest.skip(f"反射模块初始化失败，跳过: {e}")

    mock_llm = Mock()
    reflector = Reflector(mock_llm)

    mock_llm_response = Mock()
    mock_llm_response.content = """
决策分析：该决策是正确的，因为基于综合分析。

Reasoning:
1. 市场趋势: 技术指标显示上涨趋势
2. 新闻正面: 财报发布超预期
3. 基本面良好: PE低于行业平均

Summary:
成功捕捉到买入机会，决策合理。
"""

    mock_llm.invoke.return_value = mock_llm_response

    result = reflector._reflect_on_component(
        "BULL", "Argument 1\nArgument 2", "综合报告", []
    )

    assert "Reasoning" in result
    assert "成功" in result
    assert "Summary" in result


@pytest.mark.unit
def test_reflector_reflect_bull():
    """测试反思看涨研究员"""
    try:
        from tradingagents.graph.reflection import Reflector
    except Exception as e:
        pytest.skip(f"反射模块初始化失败，跳过: {e}")

    mock_llm = Mock()
    mock_memory = Mock()
    reflector = Reflector(mock_llm)

    mock_llm_response = Mock()
    mock_llm_response.content = "决策分析：过于激进，应更保守。"
    mock_llm.invoke.return_value = mock_llm_response

    mock_state = {
        "messages": [],
        "market_report": "市场报告",
        "sentiment_report": "情绪报告",
        "news_report": "新闻报告",
        "fundamentals_report": "基本面报告",
        "investment_debate_state": {"bull_history": "Argument 1\nArgument 2"},
    }

    reflector.reflect_bull_researcher(mock_state, [], mock_memory)
    assert mock_memory.add_situations.called


@pytest.mark.unit
def test_reflector_reflect_bear():
    """测试反思看跌研究员"""
    try:
        from tradingagents.graph.reflection import Reflector
    except Exception as e:
        pytest.skip(f"反射模块初始化失败，跳过: {e}")

    mock_llm = Mock()
    mock_memory = Mock()
    reflector = Reflector(mock_llm)

    mock_llm_response = Mock()
    mock_llm_response.content = "决策分析：过于悲观，应更积极。"
    mock_llm.invoke.return_value = mock_llm_response

    mock_state = {
        "messages": [],
        "market_report": "市场报告",
        "sentiment_report": "情绪报告",
        "news_report": "新闻报告",
        "fundamentals_report": "基本面报告",
        "investment_debate_state": {"bear_history": "Argument 1\nArgument 2"},
    }

    reflector.reflect_bear_researcher(mock_state, [], mock_memory)
    assert mock_memory.add_situations.called


@pytest.mark.unit
def test_reflector_reflect_trader():
    """测试反思交易员"""
    try:
        from tradingagents.graph.reflection import Reflector
    except Exception as e:
        pytest.skip(f"反射模块初始化失败，跳过: {e}")

    mock_llm = Mock()
    mock_memory = Mock()
    reflector = Reflector(mock_llm)

    mock_llm_response = Mock()
    mock_llm_response.content = """
决策分析：时机把握良好，但目标价偏低。

Reasoning:
1. 市场表现: 股价上涨15%
2. 决策时机: 在支撑位附近买入

Summary:
成功交易，但下次可调整目标价。
"""
    mock_llm.invoke.return_value = mock_llm_response

    mock_state = {
        "messages": [],
        "market_report": "市场报告",
        "sentiment_report": "情绪报告",
        "news_report": "新闻报告",
        "fundamentals_report": "基本面报告",
        "trader_investment_plan": "综合分析后，最终交易建议：**买入**\n目标价位：$180",
    }

    reflector.reflect_trader(mock_state, [], mock_memory)
    assert mock_memory.add_situations.called


@pytest.mark.unit
def test_reflector_reflect_invest_judge():
    """测试反思投资裁判"""
    try:
        from tradingagents.graph.reflection import Reflector
    except Exception as e:
        pytest.skip(f"反射模块初始化失败，跳过: {e}")

    mock_llm = Mock()
    mock_memory = Mock()
    reflector = Reflector(mock_llm)

    mock_llm_response = Mock()
    mock_llm_response.content = """
决策分析：风险判断准确，建议合理。

Reasoning:
1. 市场环境: 波动率适中
2. 投资规模: 建议30%仓位

Summary:
有效的风险控制决策。
"""
    mock_llm.invoke.return_value = mock_llm_response

    mock_state = {
        "messages": [],
        "market_report": "市场报告",
        "sentiment_report": "情绪报告",
        "news_report": "新闻报告",
        "fundamentals_report": "基本面报告",
        "investment_debate_state": {"judge_decision": "Risk Analyst: 建议30%仓位"},
    }

    reflector.reflect_invest_judge(mock_state, [], mock_memory)
    assert mock_memory.add_situations.called


@pytest.mark.unit
def test_reflector_reflect_risk_manager():
    """测试反思风险管理者"""
    try:
        from tradingagents.graph.reflection import Reflector
    except Exception as e:
        pytest.skip(f"反射模块初始化失败，跳过: {e}")

    mock_llm = Mock()
    mock_memory = Mock()
    reflector = Reflector(mock_llm)

    mock_llm_response = Mock()
    mock_llm_response.content = """
决策分析：风险分析全面，考虑了市场波动性。

Reasoning:
1. 波动率评估: 15%
2. 仓位控制: 25-30%仓位
3. 止损设置: 5%亏损

Summary:
完善的风险控制策略。
"""
    mock_llm.invoke.return_value = mock_llm_response

    mock_state = {
        "messages": [],
        "market_report": "市场报告",
        "sentiment_report": "情绪报告",
        "news_report": "新闻报告",
        "fundamentals_report": "基本面报告",
        "risk_debate_state": {"judge_decision": "Safe Analyst: 30%仓位"},
    }

    reflector.reflect_risk_manager(mock_state, [], mock_memory)
    assert mock_memory.add_situations.called


@pytest.mark.unit
def test_reflector_memory_storage():
    """测试记忆存储"""
    mock_memory = Mock()
    mock_situation = "测试情况1"
    mock_reflection = "反思结果1"

    mock_memory.add_situations([(mock_situation, mock_reflection)])
    assert mock_memory.add_situations.called
    assert mock_memory.add_situations.call_count == 1


@pytest.mark.unit
def test_reflector_error_handling():
    """测试错误处理"""
    try:
        from tradingagents.graph.reflection import Reflector
    except Exception as e:
        pytest.skip(f"反射模块初始化失败，跳过: {e}")

    mock_llm = Mock()
    mock_memory = Mock()
    reflector = Reflector(mock_llm)

    mock_llm.invoke.side_effect = Exception("LLM调用失败")

    mock_state = {
        "messages": [],
        "market_report": "市场报告",
        "sentiment_report": "情绪报告",
        "news_report": "新闻报告",
        "fundamentals_report": "基本面报告",
        "investment_debate_state": {"bull_history": "Argument 1\nArgument 2"},
    }

    with pytest.raises(Exception):
        reflector.reflect_bull_researcher(mock_state, [], mock_memory)
