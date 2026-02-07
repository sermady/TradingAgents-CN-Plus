# -*- coding: utf-8 -*-
"""
测试管理模块

测试范围:
- 研究管理器 (Research Manager)
- 风险管理器 (Risk Manager)
- 历史记忆使用
- 决策生成
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import time


class TestResearchManager:
    """测试研究管理器"""

    @pytest.mark.unit
    def test_create_research_manager(self):
        """测试创建研究管理器"""
        from tradingagents.agents.managers.research_manager import (
            create_research_manager,
        )

        # Arrange
        mock_llm = Mock()
        mock_memory = Mock()

        # Act
        manager = create_research_manager(mock_llm, mock_memory)

        # Assert
        assert callable(manager)

    @pytest.mark.unit
    def test_research_manager_basic_execution(self):
        """测试研究管理器基本执行"""
        from tradingagents.agents.managers.research_manager import (
            create_research_manager,
        )

        # Arrange
        mock_response = Mock()
        mock_response.content = """
        基于综合分析，建议买入。
        目标价位：¥35.00
        理由：基本面良好，技术形态突破。
        """
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_memory = Mock()
        mock_memory.get_memories.return_value = []

        manager = create_research_manager(mock_llm, mock_memory)

        state = {
            "company_of_interest": "000001",
            "trade_date": "2024-06-01",
            "market_report": "技术分析报告",
            "sentiment_report": "情绪分析报告",
            "news_report": "新闻分析报告",
            "fundamentals_report": "基本面分析报告",
            "investment_debate_state": {
                "history": "看涨观点：技术突破\n看跌观点：估值偏高",
                "count": 2,
            },
        }

        # Act
        result = manager(state)

        # Assert
        assert "investment_plan" in result
        assert "messages" in result
        mock_llm.invoke.assert_called_once()

    @pytest.mark.unit
    def test_research_manager_with_memory(self):
        """测试研究管理器使用历史记忆"""
        from tradingagents.agents.managers.research_manager import (
            create_research_manager,
        )

        mock_response = Mock()
        mock_response.content = "建议买入"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response

        mock_memory = Mock()
        mock_memory.get_memories.return_value = [
            {"recommendation": "历史决策1：成功买入"},
            {"recommendation": "历史决策2：及时卖出"},
        ]

        manager = create_research_manager(mock_llm, mock_memory)

        state = {
            "company_of_interest": "000001",
            "trade_date": "2024-06-01",
            "market_report": "报告",
            "sentiment_report": "报告",
            "news_report": "报告",
            "fundamentals_report": "报告",
            "investment_debate_state": {
                "history": "辩论历史",
                "count": 2,
            },
        }

        result = manager(state)

        # 验证使用了记忆功能
        mock_memory.get_memories.assert_called_once()
        assert "investment_plan" in result

    @pytest.mark.unit
    def test_research_manager_without_memory(self):
        """测试研究管理器无历史记忆"""
        from tradingagents.agents.managers.research_manager import (
            create_research_manager,
        )

        mock_response = Mock()
        mock_response.content = "建议买入"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response

        # memory为None
        manager = create_research_manager(mock_llm, None)

        state = {
            "company_of_interest": "000001",
            "trade_date": "2024-06-01",
            "market_report": "报告",
            "sentiment_report": "报告",
            "news_report": "报告",
            "fundamentals_report": "报告",
            "investment_debate_state": {
                "history": "辩论历史",
                "count": 2,
            },
        }

        # 不应抛出异常
        result = manager(state)

        assert "investment_plan" in result

    @pytest.mark.unit
    def test_research_manager_empty_debate_history(self):
        """测试空辩论历史"""
        from tradingagents.agents.managers.research_manager import (
            create_research_manager,
        )

        mock_response = Mock()
        mock_response.content = "建议持有"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_memory = Mock()
        mock_memory.get_memories.return_value = []

        manager = create_research_manager(mock_llm, mock_memory)

        state = {
            "company_of_interest": "000001",
            "trade_date": "2024-06-01",
            "market_report": "报告",
            "sentiment_report": "报告",
            "news_report": "报告",
            "fundamentals_report": "报告",
            "investment_debate_state": {
                "history": "",
                "count": 0,
            },
        }

        result = manager(state)

        assert "investment_plan" in result

    @pytest.mark.unit
    def test_research_manager_llm_error(self):
        """测试LLM调用失败"""
        from tradingagents.agents.managers.research_manager import (
            create_research_manager,
        )

        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("API错误")
        mock_memory = Mock()
        mock_memory.get_memories.return_value = []

        manager = create_research_manager(mock_llm, mock_memory)

        state = {
            "company_of_interest": "000001",
            "trade_date": "2024-06-01",
            "market_report": "报告",
            "sentiment_report": "报告",
            "news_report": "报告",
            "fundamentals_report": "报告",
            "investment_debate_state": {
                "history": "辩论历史",
                "count": 2,
            },
        }

        # 应该抛出异常
        with pytest.raises(Exception):
            manager(state)


class TestRiskManager:
    """测试风险管理器"""

    @pytest.mark.unit
    def test_create_risk_manager(self):
        """测试创建风险管理器"""
        from tradingagents.agents.managers.risk_manager import create_risk_manager

        mock_llm = Mock()
        mock_memory = Mock()

        manager = create_risk_manager(mock_llm, mock_memory)

        assert callable(manager)

    @pytest.mark.unit
    def test_research_manager_basic_execution(self):
        """测试研究管理器基本执行"""
        from tradingagents.agents.managers.research_manager import (
            create_research_manager,
        )

        # Arrange
        mock_response = Mock()
        mock_response.content = """
        基于综合分析，建议买入。
        目标价位：¥35.00
        理由：基本面良好，技术形态突破。
        """
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_memory = Mock()
        mock_memory.get_memories.return_value = []

        manager = create_research_manager(mock_llm, mock_memory)

        state = {
            "company_of_interest": "000001",
            "trade_date": "2024-06-01",
            "market_report": "技术分析报告",
            "sentiment_report": "情绪分析报告",
            "news_report": "新闻分析报告",
            "fundamentals_report": "基本面分析报告",
            "investment_debate_state": {
                "history": "看涨观点：技术突破\n看跌观点：估值偏高",
                "count": 2,
                "bull_history": "看涨：技术突破",
                "bear_history": "看跌：估值偏高",
            },
        }

        # Act
        result = manager(state)

        # Assert
        assert "investment_plan" in result
        # Research manager returns investment_plan and updates state
        mock_llm.invoke.assert_called_once()

    @pytest.mark.unit
    def test_risk_manager_with_memory(self):
        """测试风险管理器使用历史记忆"""
        from tradingagents.agents.managers.risk_manager import create_risk_manager

        mock_response = Mock()
        mock_response.content = "建议买入"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response

        mock_memory = Mock()
        mock_memory.get_memories.return_value = [
            {"recommendation": "历史风险决策1：保守策略成功"},
            {"recommendation": "历史风险决策2：激进策略失败"},
        ]

        manager = create_risk_manager(mock_llm, mock_memory)

        state = {
            "company_of_interest": "000001",
            "trade_date": "2024-06-01",
            "market_report": "报告",
            "sentiment_report": "报告",
            "news_report": "报告",
            "fundamentals_report": "报告",
            "investment_plan": "计划",
            "risk_debate_state": {
                "history": "风险辩论",
                "count": 3,
                "risky_history": "激进：高回报",
                "safe_history": "保守：低风险",
                "neutral_history": "中性：平衡",
                "current_risky_response": "激进观点",
                "current_safe_response": "保守观点",
                "current_neutral_response": "中性观点",
            },
        }

        result = manager(state)

        mock_memory.get_memories.assert_called_once()
        assert "final_trade_decision" in result

    @pytest.mark.unit
    def test_risk_manager_without_memory(self):
        """测试风险管理器无历史记忆"""
        from tradingagents.agents.managers.risk_manager import create_risk_manager

        mock_response = Mock()
        mock_response.content = "建议持有"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response

        manager = create_risk_manager(mock_llm, None)

        state = {
            "company_of_interest": "000001",
            "trade_date": "2024-06-01",
            "market_report": "报告",
            "sentiment_report": "报告",
            "news_report": "报告",
            "fundamentals_report": "报告",
            "investment_plan": "计划",
            "risk_debate_state": {
                "history": "风险辩论",
                "count": 3,
                "risky_history": "激进：高回报",
                "safe_history": "保守：低风险",
                "neutral_history": "中性：平衡",
                "current_risky_response": "激进观点",
                "current_safe_response": "保守观点",
                "current_neutral_response": "中性观点",
            },
        }

        result = manager(state)

        assert "final_trade_decision" in result

    @pytest.mark.unit
    def test_risk_manager_empty_debate(self):
        """测试空风险辩论"""
        from tradingagents.agents.managers.risk_manager import create_risk_manager

        mock_response = Mock()
        mock_response.content = "建议观望"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_memory = Mock()
        mock_memory.get_memories.return_value = []

        manager = create_risk_manager(mock_llm, mock_memory)

        state = {
            "company_of_interest": "000001",
            "trade_date": "2024-06-01",
            "market_report": "报告",
            "sentiment_report": "报告",
            "news_report": "报告",
            "fundamentals_report": "报告",
            "investment_plan": "计划",
            "risk_debate_state": {
                "history": "",
                "count": 0,
            },
        }

        result = manager(state)

        assert "final_trade_decision" in result


class TestManagerEdgeCases:
    """测试管理模块边界情况"""

    @pytest.mark.unit
    def test_research_manager_missing_optional_fields(self):
        """测试研究管理器处理缺失可选字段"""
        from tradingagents.agents.managers.research_manager import (
            create_research_manager,
        )

        mock_response = Mock()
        mock_response.content = "建议买入"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_memory = Mock()
        mock_memory.get_memories.return_value = []

        manager = create_research_manager(mock_llm, mock_memory)

        # 缺少 trade_date 等可选字段
        state = {
            "company_of_interest": "000001",
            "market_report": "报告",
            "sentiment_report": "报告",
            "news_report": "报告",
            "fundamentals_report": "报告",
            "investment_debate_state": {
                "history": "辩论",
            },
        }

        # 不应抛出异常
        result = manager(state)

        assert "investment_plan" in result

    @pytest.mark.unit
    def test_risk_manager_missing_optional_fields(self):
        """测试风险管理器处理缺失可选字段"""
        from tradingagents.agents.managers.risk_manager import create_risk_manager

        mock_response = Mock()
        mock_response.content = "建议持有"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_memory = Mock()
        mock_memory.get_memories.return_value = []

        manager = create_risk_manager(mock_llm, mock_memory)

        # 缺少 trade_date 等可选字段
        state = {
            "company_of_interest": "000001",
            "market_report": "报告",
            "sentiment_report": "报告",
            "news_report": "报告",
            "fundamentals_report": "报告",
            "investment_plan": "计划",
            "risk_debate_state": {
                "history": "辩论",
            },
        }

        # 不应抛出异常
        result = manager(state)

        assert "final_trade_decision" in result

    @pytest.mark.unit
    def test_managers_with_different_stock_types(self):
        """测试管理器处理不同股票类型"""
        from tradingagents.agents.managers.research_manager import (
            create_research_manager,
        )

        stocks = [
            ("000001", "A股"),
            ("00700", "港股"),
            ("AAPL", "美股"),
        ]

        for ticker, market in stocks:
            mock_response = Mock()
            mock_response.content = f"{market}分析建议"
            mock_llm = Mock()
            mock_llm.invoke.return_value = mock_response
            mock_memory = Mock()
            mock_memory.get_memories.return_value = []

            manager = create_research_manager(mock_llm, mock_memory)

            state = {
                "company_of_interest": ticker,
                "trade_date": "2024-06-01",
                "market_report": "报告",
                "sentiment_report": "报告",
                "news_report": "报告",
                "fundamentals_report": "报告",
                "investment_debate_state": {
                    "history": "辩论",
                    "count": 2,
                },
            }

            result = manager(state)

            assert "investment_plan" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
