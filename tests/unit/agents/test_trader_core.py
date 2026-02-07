# -*- coding: utf-8 -*-
"""
测试交易员核心决策逻辑

测试范围:
- 交易员节点创建
- 不同市场股票处理（A股、港股、美股）
- 历史记忆使用
- 验证和增强决策
- 错误处理
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import functools


class TestCreateTrader:
    """测试创建交易员"""

    @pytest.mark.unit
    def test_create_trader_returns_callable(self):
        """测试 create_trader 返回可调用对象"""
        from tradingagents.agents.trader.trader import create_trader

        # Arrange
        mock_llm = Mock()
        mock_memory = Mock()

        # Act
        trader = create_trader(mock_llm, mock_memory)

        # Assert
        assert callable(trader)

    @pytest.mark.unit
    def test_trader_node_basic_execution(self):
        """测试交易员节点基本执行"""
        from tradingagents.agents.trader.trader import create_trader

        # Arrange
        mock_response = Mock()
        mock_response.content = """
        基于综合分析，建议买入该股票。
        目标价位: ¥35.50
        置信度: 0.85
        风险评分: 0.4
        
        最终交易建议: **买入**
        """
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_memory = Mock()
        mock_memory.get_memories.return_value = []

        trader = create_trader(mock_llm, mock_memory)

        state = {
            "company_of_interest": "000001",
            "investment_plan": "买入计划",
            "market_report": "市场分析报告",
            "sentiment_report": "情绪分析报告",
            "news_report": "新闻分析报告",
            "fundamentals_report": "当前股价：30.00元",
            "data_quality_score": 90.0,
        }

        # Act
        result = trader(state)

        # Assert
        assert "messages" in result
        assert "trader_investment_plan" in result
        assert "sender" in result
        assert result["sender"] == "Trader"

    @pytest.mark.unit
    def test_trader_with_china_stock(self):
        """测试处理中国A股"""
        from tradingagents.agents.trader.trader import create_trader

        mock_response = Mock()
        mock_response.content = "目标价位: ¥35.00\n最终交易建议: **买入**"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_memory = Mock()
        mock_memory.get_memories.return_value = []

        trader = create_trader(mock_llm, mock_memory)

        state = {
            "company_of_interest": "600000",  # 上海股票
            "investment_plan": "计划",
            "market_report": "报告",
            "sentiment_report": "报告",
            "news_report": "报告",
            "fundamentals_report": "当前股价：30.00元",
            "data_quality_score": 90.0,
        }

        result = trader(state)

        # 验证使用了人民币
        assert "trader_investment_plan" in result
        mock_llm.invoke.assert_called_once()
        call_args = mock_llm.invoke.call_args[0][0]
        assert "¥" in str(call_args) or "人民币" in str(call_args)

    @pytest.mark.unit
    def test_trader_with_hk_stock(self):
        """测试处理港股"""
        from tradingagents.agents.trader.trader import create_trader

        mock_response = Mock()
        mock_response.content = "目标价位: $350.00\n最终交易建议: **买入**"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_memory = Mock()
        mock_memory.get_memories.return_value = []

        trader = create_trader(mock_llm, mock_memory)

        state = {
            "company_of_interest": "00700",  # 腾讯港股
            "investment_plan": "计划",
            "market_report": "报告",
            "sentiment_report": "报告",
            "news_report": "报告",
            "fundamentals_report": "当前股价：300.00港元",
            "data_quality_score": 90.0,
        }

        result = trader(state)

        assert "trader_investment_plan" in result

    @pytest.mark.unit
    def test_trader_with_us_stock(self):
        """测试处理美股"""
        from tradingagents.agents.trader.trader import create_trader

        mock_response = Mock()
        mock_response.content = "目标价位: $180.00\n最终交易建议: **买入**"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_memory = Mock()
        mock_memory.get_memories.return_value = []

        trader = create_trader(mock_llm, mock_memory)

        state = {
            "company_of_interest": "AAPL",
            "investment_plan": "计划",
            "market_report": "报告",
            "sentiment_report": "报告",
            "news_report": "报告",
            "fundamentals_report": "当前股价：150.00美元",
            "data_quality_score": 90.0,
        }

        result = trader(state)

        assert "trader_investment_plan" in result

    @pytest.mark.unit
    def test_trader_with_memory(self):
        """测试使用历史记忆"""
        from tradingagents.agents.trader.trader import create_trader

        mock_response = Mock()
        mock_response.content = "目标价位: ¥35.00\n最终交易建议: **买入**"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response

        # 设置历史记忆
        mock_memory = Mock()
        mock_memory.get_memories.return_value = [
            {"recommendation": "历史建议1：谨慎买入"},
            {"recommendation": "历史建议2：观察"},
        ]

        trader = create_trader(mock_llm, mock_memory)

        state = {
            "company_of_interest": "000001",
            "investment_plan": "计划",
            "market_report": "报告",
            "sentiment_report": "报告",
            "news_report": "报告",
            "fundamentals_report": "当前股价：30.00元",
            "data_quality_score": 90.0,
        }

        result = trader(state)

        # 验证调用了记忆功能
        mock_memory.get_memories.assert_called_once()

    @pytest.mark.unit
    def test_trader_without_memory(self):
        """测试无历史记忆时的处理"""
        from tradingagents.agents.trader.trader import create_trader

        mock_response = Mock()
        mock_response.content = "目标价位: ¥35.00\n最终交易建议: **买入**"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response

        # memory为None
        trader = create_trader(mock_llm, None)

        state = {
            "company_of_interest": "000001",
            "investment_plan": "计划",
            "market_report": "报告",
            "sentiment_report": "报告",
            "news_report": "报告",
            "fundamentals_report": "当前股价：30.00元",
            "data_quality_score": 90.0,
        }

        # 不应抛出异常
        result = trader(state)

        assert "trader_investment_plan" in result

    @pytest.mark.unit
    def test_trader_extracts_current_price(self):
        """测试从基本面报告提取当前股价"""
        from tradingagents.agents.trader.trader import create_trader

        mock_response = Mock()
        mock_response.content = "目标价位: ¥35.00\n最终交易建议: **买入**"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_memory = Mock()
        mock_memory.get_memories.return_value = []

        trader = create_trader(mock_llm, mock_memory)

        # 包含明确股价信息的基本面报告
        state = {
            "company_of_interest": "000001",
            "investment_plan": "计划",
            "market_report": "报告",
            "sentiment_report": "报告",
            "news_report": "报告",
            "fundamentals_report": "当前股价：28.50元\n其他信息",
            "data_quality_score": 90.0,
        }

        result = trader(state)

        # 验证交易计划被增强（包含当前股价信息）
        assert "trader_investment_plan" in result
        # 增强后的报告应该包含当前价格
        assert (
            "28.50" in result["trader_investment_plan"]
            or "¥28.50" in result["trader_investment_plan"]
        )

    @pytest.mark.unit
    def test_trader_validation_with_warnings(self):
        """测试验证产生警告的情况"""
        from tradingagents.agents.trader.trader import create_trader

        # LLM返回内容缺少目标价位
        mock_response = Mock()
        mock_response.content = "建议买入\n最终交易建议: **买入**"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_memory = Mock()
        mock_memory.get_memories.return_value = []

        trader = create_trader(mock_llm, mock_memory)

        state = {
            "company_of_interest": "000001",
            "investment_plan": "计划",
            "market_report": "报告",
            "sentiment_report": "报告",
            "news_report": "报告",
            "fundamentals_report": "当前股价：30.00元",
            "data_quality_score": 90.0,
        }

        # 不应抛出异常，应该继续处理
        result = trader(state)

        assert "trader_investment_plan" in result
        # 应该返回增强后的决策（即使验证有警告）
        assert isinstance(result["trader_investment_plan"], str)


class TestTraderEdgeCases:
    """测试交易员边界情况"""

    @pytest.mark.unit
    def test_trader_with_empty_reports(self):
        """测试空报告的处理"""
        from tradingagents.agents.trader.trader import create_trader

        mock_response = Mock()
        mock_response.content = "目标价位: ¥35.00\n最终交易建议: **买入**"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_memory = Mock()
        mock_memory.get_memories.return_value = []

        trader = create_trader(mock_llm, mock_memory)

        state = {
            "company_of_interest": "000001",
            "investment_plan": "",
            "market_report": "",
            "sentiment_report": "",
            "news_report": "",
            "fundamentals_report": "",
            "data_quality_score": 0.0,
        }

        # 不应抛出异常
        result = trader(state)

        assert "trader_investment_plan" in result

    @pytest.mark.unit
    def test_trader_llm_error(self):
        """测试LLM调用失败"""
        from tradingagents.agents.trader.trader import create_trader

        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("API错误")
        mock_memory = Mock()
        mock_memory.get_memories.return_value = []

        trader = create_trader(mock_llm, mock_memory)

        state = {
            "company_of_interest": "000001",
            "investment_plan": "计划",
            "market_report": "报告",
            "sentiment_report": "报告",
            "news_report": "报告",
            "fundamentals_report": "当前股价：30.00元",
            "data_quality_score": 90.0,
        }

        # 应该抛出异常
        with pytest.raises(Exception):
            trader(state)

    @pytest.mark.unit
    def test_trader_different_price_formats(self):
        """测试不同股价格式"""
        from tradingagents.agents.trader.trader import create_trader

        mock_response = Mock()
        mock_response.content = "目标价位: ¥35.00\n最终交易建议: **买入**"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_memory = Mock()
        mock_memory.get_memories.return_value = []

        trader = create_trader(mock_llm, mock_memory)

        # 不同格式的股价信息
        price_formats = [
            "当前股价：30.00元",
            "当前股价: 30.00",
            "股价：30.00",
            "价格：30.00",
        ]

        for price_format in price_formats:
            state = {
                "company_of_interest": "000001",
                "investment_plan": "计划",
                "market_report": "报告",
                "sentiment_report": "报告",
                "news_report": "报告",
                "fundamentals_report": price_format,
                "data_quality_score": 90.0,
            }

            # 重置mock
            mock_llm.reset_mock()
            mock_llm.invoke.return_value = mock_response

            result = trader(state)

            assert "trader_investment_plan" in result


class TestTraderDataQuality:
    """测试数据质量评分影响"""

    @pytest.mark.unit
    def test_trader_with_low_data_quality(self):
        """测试低数据质量评分"""
        from tradingagents.agents.trader.trader import create_trader

        mock_response = Mock()
        mock_response.content = "置信度: 0.8\n目标价位: ¥35.00\n最终交易建议: **买入**"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_memory = Mock()
        mock_memory.get_memories.return_value = []

        trader = create_trader(mock_llm, mock_memory)

        state = {
            "company_of_interest": "000001",
            "investment_plan": "计划",
            "market_report": "报告",
            "sentiment_report": "报告",
            "news_report": "报告",
            "fundamentals_report": "当前股价：30.00元",
            "data_quality_score": 50.0,  # 低质量
        }

        result = trader(state)

        assert "trader_investment_plan" in result

    @pytest.mark.unit
    def test_trader_with_high_data_quality(self):
        """测试高数据质量评分"""
        from tradingagents.agents.trader.trader import create_trader

        mock_response = Mock()
        mock_response.content = "置信度: 0.8\n目标价位: ¥35.00\n最终交易建议: **买入**"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_memory = Mock()
        mock_memory.get_memories.return_value = []

        trader = create_trader(mock_llm, mock_memory)

        state = {
            "company_of_interest": "000001",
            "investment_plan": "计划",
            "market_report": "报告",
            "sentiment_report": "报告",
            "news_report": "报告",
            "fundamentals_report": "当前股价：30.00元",
            "data_quality_score": 95.0,  # 高质量
        }

        result = trader(state)

        assert "trader_investment_plan" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
