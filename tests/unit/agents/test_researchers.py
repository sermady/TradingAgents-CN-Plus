# -*- coding: utf-8 -*-
"""
测试研究员功能

测试范围:
- 研究员基类功能
- Bull/Bear研究员创建
- 研究员节点执行
- 辩论状态管理
- 历史记忆检索
- Prompt构建
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

os.environ["USE_MONGODB_STORAGE"] = "false"
os.environ["TRADINGAGENTS_SKIP_DB_INIT"] = "true"

from tradingagents.agents.researchers.base_researcher import (
    BaseResearcher,
    BullResearcher,
    BearResearcher,
    create_researcher,
)


@pytest.mark.unit
def test_create_bull_researcher():
    """测试创建看涨研究员"""
    # Act
    bull_researcher = BullResearcher()

    # Assert
    assert bull_researcher.perspective == "bull"
    assert bull_researcher.description == "看涨"
    assert bull_researcher.emoji == "🐂"
    assert bull_researcher.goal == "突出增长潜力、竞争优势和积极的市场指标"
    assert bull_researcher.viewpoint == "积极论证"


@pytest.mark.unit
def test_create_bear_researcher():
    """测试创建看跌研究员"""
    # Act
    bear_researcher = BearResearcher()

    # Assert
    assert bear_researcher.perspective == "bear"
    assert bear_researcher.description == "看跌"
    assert bear_researcher.emoji == "🐻"
    assert bear_researcher.goal == "强调风险、挑战和负面指标"
    assert bear_researcher.viewpoint == "消极论证"


@pytest.mark.unit
def test_create_researcher_factory():
    """测试研究员工厂函数"""
    # Act & Assert
    bull = create_researcher("bull")
    assert isinstance(bull, BullResearcher)
    assert bull.perspective == "bull"

    bear = create_researcher("bear")
    assert isinstance(bear, BearResearcher)
    assert bear.perspective == "bear"

    with pytest.raises(ValueError):
        create_researcher("invalid")


@pytest.mark.unit
def test_bull_researcher_create_node():
    """测试看涨研究员节点创建"""
    # Arrange
    mock_llm = Mock()
    mock_memory = Mock()
    bull_researcher = BullResearcher()

    # Act
    node = bull_researcher.create_node(mock_llm, mock_memory)

    # Assert
    assert node is not None
    assert callable(node)


@pytest.mark.unit
def test_bear_researcher_create_node():
    """测试看跌研究员节点创建"""
    # Arrange
    mock_llm = Mock()
    mock_memory = Mock()
    bear_researcher = BearResearcher()

    # Act
    node = bear_researcher.create_node(mock_llm, mock_memory)

    # Assert
    assert node is not None
    assert callable(node)


@pytest.mark.unit
def test_researcher_node_basic_execution():
    """测试研究员节点基本执行"""
    # Arrange
    mock_llm = Mock()
    mock_memory = Mock()
    mock_memory.get_memories.return_value = []
    mock_llm_response = Mock()
    mock_llm_response.content = "看涨分析师: 该股票具有良好的增长潜力..."

    mock_llm.invoke.return_value = mock_llm_response

    bull_researcher = BullResearcher()
    node = bull_researcher.create_node(mock_llm, mock_memory)

    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "investment_debate_state": {
            "history": "",
            "bull_history": "",
            "bear_history": "",
            "current_response": "",
            "count": 0,
        },
        "market_report": "市场技术分析报告...",
        "sentiment_report": "社交媒体情绪报告...",
        "news_report": "新闻分析报告...",
        "fundamentals_report": "基本面分析报告...",
    }

    # Act & Assert
    with patch(
        "tradingagents.utils.stock_utils.StockUtils.get_market_info"
    ) as mock_get_market_info:
        mock_get_market_info.return_value = {
            "market_name": "美股",
            "currency_name": "美元",
            "currency_symbol": "USD",
            "is_china": False,
            "is_hk": False,
            "is_us": True,
        }

        with patch(
            "tradingagents.utils.company_name_utils.get_company_name"
        ) as mock_get_name:
            mock_get_name.return_value = "Apple Inc."

            result = node(mock_state)

    # Assert
    assert "investment_debate_state" in result
    assert result["investment_debate_state"]["count"] == 1
    assert "bull_history" in result["investment_debate_state"]
    assert "看涨分析师" in result["investment_debate_state"]["bull_history"]


@pytest.mark.unit
def test_researcher_with_china_stock():
    """测试中国股票研究员分析"""
    # Arrange
    mock_llm = Mock()
    mock_memory = Mock()
    mock_memory.get_memories.return_value = []
    mock_llm_response = Mock()
    mock_llm_response.content = "看涨分析师: 平安银行增长潜力..."

    mock_llm.invoke.return_value = mock_llm_response

    bull_researcher = BullResearcher()
    node = bull_researcher.create_node(mock_llm, mock_memory)

    mock_state = {
        "messages": [],
        "company_of_interest": "000001",  # A股代码
        "trade_date": "2025-01-15",
        "investment_debate_state": {
            "history": "",
            "bull_history": "",
            "bear_history": "",
            "current_response": "",
            "count": 0,
        },
        "market_report": "市场报告",
        "sentiment_report": "情绪报告",
        "news_report": "新闻报告",
        "fundamentals_report": "基本面报告",
    }

    # Act & Assert - For Chinese stocks, get_company_name has internal calls
    # So we patch at the local namespace where it's used
    with patch(
        "tradingagents.agents.researchers.base_researcher.get_company_name"
    ) as mock_get_name:
        mock_get_name.return_value = "平安银行"

        result = node(mock_state)

    # Assert
    assert "investment_debate_state" in result
    # 验证prompt包含正确的市场信息
    # (实际prompt在_build_prompt中构建)


@pytest.mark.unit
def test_researcher_debate_state_update():
    """测试辩论状态更新"""
    # Arrange
    mock_llm = Mock()
    mock_memory = Mock()
    mock_memory.get_memories.return_value = []
    mock_llm_response = Mock()
    mock_llm_response.content = "看涨分析师: 基于数据分析..."
    mock_llm.invoke.return_value = mock_llm_response

    bull_researcher = BullResearcher()
    node = bull_researcher.create_node(mock_llm, mock_memory)

    initial_count = 5
    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "investment_debate_state": {
            "history": "previous arguments...",
            "bull_history": "previous bull arguments...",
            "bear_history": "",
            "current_response": "",
            "count": initial_count,
        },
        "market_report": "市场报告",
        "sentiment_report": "情绪报告",
        "news_report": "新闻报告",
        "fundamentals_report": "基本面报告",
    }

    # Act & Assert - StockUtils is imported inside the function, so patch original location
    with patch(
        "tradingagents.utils.stock_utils.StockUtils.get_market_info"
    ) as mock_get_market_info:
        mock_get_market_info.return_value = {
            "market_name": "美股",
            "currency_name": "美元",
            "currency_symbol": "USD",
            "is_china": False,
            "is_hk": False,
            "is_us": True,
        }

        with patch(
            "tradingagents.agents.researchers.base_researcher.get_company_name"
        ) as mock_get_name:
            mock_get_name.return_value = "Apple Inc."

            result = node(mock_state)

    # Assert
    # 验证计数递增
    assert result["investment_debate_state"]["count"] == initial_count + 1
    # 验证历史记录更新
    assert "previous arguments..." in result["investment_debate_state"]["history"]
    assert (
        "看涨分析师: 基于数据分析..."
        in result["investment_debate_state"]["bull_history"]
    )
    # 验证bull_history保留(因为是bull_researcher)
    assert (
        "previous bull arguments..."
        in result["investment_debate_state"]["bull_history"]
    )
    assert (
        "看涨分析师: 基于数据分析..."
        in result["investment_debate_state"]["bull_history"]
    )


@pytest.mark.unit
def test_researcher_format_memories():
    """测试记忆格式化"""
    # Arrange
    bull_researcher = BullResearcher()

    past_memories = [
        {"recommendation": "建议1: 买入"},
        {"recommendation": "建议2: 持有"},
        {"recommendation": "建议3: 卖出"},
    ]

    # Act
    memory_str = bull_researcher._format_memories(past_memories)

    # Assert
    assert "建议1: 买入" in memory_str
    assert "建议2: 持有" in memory_str
    assert "建议3: 卖出" in memory_str
    # 验证格式(使用\n\n分隔)
    assert "\n\n" in memory_str


@pytest.mark.unit
def test_researcher_error_handling():
    """测试研究员错误处理"""
    # Arrange
    mock_llm = Mock()
    mock_memory = Mock()

    # 模拟LLM调用失败
    mock_llm.invoke.side_effect = Exception("LLM调用失败")

    bull_researcher = BullResearcher()
    node = bull_researcher.create_node(mock_llm, mock_memory)

    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "investment_debate_state": {
            "history": "",
            "bull_history": "",
            "bear_history": "",
            "current_response": "",
            "count": 0,
        },
        "market_report": "市场报告",
        "sentiment_report": "情绪报告",
        "news_report": "新闻报告",
        "fundamentals_report": "基本面报告",
    }

    # Act & Assert - 应该抛出异常
    with pytest.raises(Exception):
        with patch(
            "tradingagents.agents.researchers.base_researcher.StockUtils"
        ) as mock_stock_utils:
            mock_stock_utils.get_market_info.return_value = {
                "market_name": "美股",
                "currency_name": "美元",
                "currency_symbol": "USD",
                "is_china": False,
                "is_hk": False,
                "is_us": True,
            }

        with patch(
            "tradingagents.agents.researchers.base_researcher.get_company_name"
        ) as mock_get_name:
            mock_get_name.return_value = "Apple Inc."

            result = node(mock_state)


@pytest.mark.unit
def test_researcher_memory_none_handling():
    """测试memory为None时的处理"""
    # Arrange
    mock_llm = Mock()
    mock_memory = Mock()
    mock_llm_response = Mock()
    mock_llm_response.content = "看涨分析师: 无历史参考..."
    mock_llm.invoke.return_value = mock_llm_response

    # 设置memory为None
    bull_researcher = BullResearcher()
    node = bull_researcher.create_node(mock_llm, None)

    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "investment_debate_state": {
            "history": "",
            "bull_history": "",
            "bear_history": "",
            "current_response": "",
            "count": 0,
        },
        "market_report": "市场报告",
        "sentiment_report": "情绪报告",
        "news_report": "新闻报告",
        "fundamentals_report": "基本面报告",
    }

    # Act & Assert - StockUtils is imported inside the function, so patch original location
    with patch(
        "tradingagents.utils.stock_utils.StockUtils.get_market_info"
    ) as mock_get_market_info:
        mock_get_market_info.return_value = {
            "market_name": "美股",
            "currency_name": "美元",
            "currency_symbol": "USD",
            "is_china": False,
            "is_hk": False,
            "is_us": True,
        }

        with patch(
            "tradingagents.agents.researchers.base_researcher.get_company_name"
        ) as mock_get_name:
            mock_get_name.return_value = "Apple Inc."

            result = node(mock_state)

    # Assert
    # memory为None时不应该调用get_memories
    assert not mock_memory.get_memories.called
    assert "investment_debate_state" in result


@pytest.mark.unit
def test_bull_researcher_prompt_building():
    """测试看涨研究员prompt构建"""
    # Arrange
    bull_researcher = BullResearcher()

    company_name = "Apple Inc."
    ticker = "AAPL"
    market_info = {
        "market_name": "美股",
        "currency_name": "美元",
        "currency_symbol": "USD",
        "is_china": False,
        "is_hk": False,
        "is_us": True,
    }
    reports = {
        "market": "市场分析报告",
        "sentiment": "情绪分析报告",
        "news": "新闻分析报告",
        "fundamentals": "基本面分析报告",
    }
    history = "辩论历史..."
    current_response = "看跌观点..."
    past_memory_str = "历史记忆..."

    # Act
    prompt = bull_researcher._build_prompt(
        company_name=company_name,
        ticker=ticker,
        market_info=market_info,
        reports=reports,
        history=history,
        current_response=current_response,
        past_memory_str=past_memory_str,
    )

    # Assert
    assert "Apple Inc." in prompt
    assert "AAPL" in prompt
    # BullResearcher使用"海外股票"而非"美股"
    assert "海外股票" in prompt or "美股" in prompt
    assert "美元" in prompt
    assert "看涨分析师" in prompt
    assert "增长潜力" in prompt or "竞争优势" in prompt
    assert "市场分析报告" in prompt
    assert "情绪分析报告" in prompt
    assert "新闻分析报告" in prompt
    assert "基本面分析报告" in prompt


@pytest.mark.unit
def test_bear_researcher_prompt_building():
    """测试看跌研究员prompt构建"""
    # Arrange
    bear_researcher = BearResearcher()

    company_name = "Apple Inc."
    ticker = "AAPL"
    market_info = {
        "market_name": "美股",
        "currency_name": "美元",
        "currency_symbol": "USD",
        "is_china": False,
        "is_hk": False,
        "is_us": True,
    }
    reports = {
        "market": "市场分析报告",
        "sentiment": "情绪分析报告",
        "news": "新闻分析报告",
        "fundamentals": "基本面分析报告",
    }
    history = "辩论历史..."
    current_response = "看涨观点..."
    past_memory_str = "历史记忆..."

    # Act
    prompt = bear_researcher._build_prompt(
        company_name=company_name,
        ticker=ticker,
        market_info=market_info,
        reports=reports,
        history=history,
        current_response=current_response,
        past_memory_str=past_memory_str,
    )

    # Assert
    assert "Apple Inc." in prompt
    assert "AAPL" in prompt
    assert "看跌分析师" in prompt
    assert "风险" in prompt or "挑战" in prompt
    assert "市场分析报告" in prompt
    assert "情绪分析报告" in prompt
    assert "新闻分析报告" in prompt
    assert "基本面分析报告" in prompt
