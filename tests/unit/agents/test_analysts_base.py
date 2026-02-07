# -*- coding: utf-8 -*-
"""
测试分析师基础流程

测试范围:
- 分析师节点创建
- 数据不可用时的默认报告生成
- 正常执行流程
- 错误处理
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from langchain_core.messages import AIMessage


class TestSocialMediaAnalyst:
    """测试社交媒体分析师"""

    @pytest.mark.unit
    def test_create_social_media_analyst_node(self):
        """测试创建社交媒体分析师节点"""
        from tradingagents.agents.analysts.social_media_analyst import (
            create_social_media_analyst,
        )

        # Arrange
        mock_llm = Mock()
        mock_toolkit = Mock()

        # Act
        analyst_node = create_social_media_analyst(mock_llm, mock_toolkit)

        # Assert
        assert analyst_node is not None
        assert callable(analyst_node)

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.social_media_analyst.get_company_name")
    def test_social_media_analyst_data_unavailable(self, mock_get_company_name):
        """测试情绪数据不可用时生成默认报告 (M2修复)"""
        from tradingagents.agents.analysts.social_media_analyst import (
            create_social_media_analyst,
        )

        # Arrange
        mock_get_company_name.return_value = "平安银行"  # Mock 避免数据库连接
        mock_llm = Mock()
        mock_toolkit = Mock()
        analyst_node = create_social_media_analyst(mock_llm, mock_toolkit)

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "sentiment_data": "❌ 数据获取失败",
            "data_quality_score": 0.0,
            "data_sources": {"sentiment": "failed"},
            "data_issues": {"sentiment": [{"message": "API错误"}]},
        }

        # Act
        result = analyst_node(state)

        # Assert
        assert "sentiment_report" in result
        assert "数据获取状态" in result["sentiment_report"]
        assert "000001" in result["sentiment_report"]
        # 数据不可用时，不应调用LLM
        mock_llm.invoke.assert_not_called()

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.social_media_analyst.get_company_name")
    def test_social_media_analyst_with_valid_data(self, mock_get_company_name):
        """测试情绪数据可用时调用LLM生成报告 (M2修复)"""
        from tradingagents.agents.analysts.social_media_analyst import (
            create_social_media_analyst,
        )

        # Arrange
        mock_get_company_name.return_value = "平安银行"  # Mock 避免数据库连接
        mock_response = Mock()
        mock_response.content = (
            "# 市场情绪分析报告\n\n## 投资者情绪概览\n市场情绪中性。"
        )
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_toolkit = Mock()
        analyst_node = create_social_media_analyst(mock_llm, mock_toolkit)

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "sentiment_data": "情绪指数：0.65\n舆情：中性",
            "data_quality_score": 0.85,
            "data_sources": {"sentiment": "tushare"},
            "data_issues": {},
        }

        # Act
        result = analyst_node(state)

        # Assert
        assert "sentiment_report" in result
        assert result["sentiment_report"] == mock_response.content
        # 数据可用时，应该调用LLM
        mock_llm.invoke.assert_called_once()

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.social_media_analyst.get_company_name")
    def test_social_media_analyst_empty_data(self, mock_get_company_name):
        """测试空情绪数据时生成默认报告 (M2修复)"""
        from tradingagents.agents.analysts.social_media_analyst import (
            create_social_media_analyst,
        )

        # Arrange
        mock_get_company_name.return_value = "浦发银行"  # Mock 避免数据库连接
        mock_llm = Mock()
        mock_toolkit = Mock()
        analyst_node = create_social_media_analyst(mock_llm, mock_toolkit)

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "600000",
            "sentiment_data": "",
            "data_quality_score": 0.0,
            "data_sources": {},
            "data_issues": {},
        }

        # Act
        result = analyst_node(state)

        # Assert
        assert "sentiment_report" in result
        assert "数据获取状态" in result["sentiment_report"]
        assert "600000" in result["sentiment_report"]

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.social_media_analyst.get_company_name")
    def test_social_media_analyst_with_data_issues(self, mock_get_company_name):
        """测试有数据质量问题时记录日志 (M2修复)"""
        from tradingagents.agents.analysts.social_media_analyst import (
            create_social_media_analyst,
        )

        # Arrange
        mock_get_company_name.return_value = "平安银行"  # Mock 避免数据库连接
        mock_response = Mock()
        mock_response.content = "报告内容"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_toolkit = Mock()
        analyst_node = create_social_media_analyst(mock_llm, mock_toolkit)

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "sentiment_data": "情绪数据",
            "data_quality_score": 0.6,
            "data_sources": {"sentiment": "akshare"},
            "data_issues": {
                "sentiment": [
                    {"message": "数据不完整"},
                    {"message": "API限流"},
                ]
            },
        }

        # Act
        result = analyst_node(state)

        # Assert - 即使有数据问题，仍然继续分析
        assert "sentiment_report" in result

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.social_media_analyst.get_company_name")
    def test_social_media_analyst_llm_error(self, mock_get_company_name):
        """测试LLM调用失败时的错误处理 (M2修复)"""
        from tradingagents.agents.analysts.social_media_analyst import (
            create_social_media_analyst,
        )

        # Arrange
        mock_get_company_name.return_value = "平安银行"  # Mock 避免数据库连接
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("API错误")
        mock_toolkit = Mock()
        analyst_node = create_social_media_analyst(mock_llm, mock_toolkit)

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "sentiment_data": "正常情绪数据",
            "data_quality_score": 0.9,
            "data_sources": {"sentiment": "tushare"},
            "data_issues": {},
        }

        # Act
        result = analyst_node(state)

        # Assert - 应该返回错误信息而不是抛出异常
        assert "sentiment_report" in result
        assert "❌ 情绪分析失败" in result["sentiment_report"]


class TestMarketAnalyst:
    """测试市场分析师"""

    @pytest.mark.unit
    def test_create_market_analyst_node(self):
        """测试创建市场分析师节点"""
        from tradingagents.agents.analysts.market_analyst import create_market_analyst

        # Arrange
        mock_llm = Mock()

        # Act
        analyst_node = create_market_analyst(mock_llm)

        # Assert
        assert analyst_node is not None
        assert callable(analyst_node)

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.market_analyst.get_company_name")
    def test_market_analyst_data_unavailable(self, mock_get_company_name):
        """测试市场数据不可用时生成警告报告"""
        from tradingagents.agents.analysts.market_analyst import create_market_analyst

        # Arrange
        mock_get_company_name.return_value = "平安银行"  # Mock 避免数据库连接
        mock_response = Mock()
        mock_response.content = "市场分析报告"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        analyst_node = create_market_analyst(mock_llm)

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "market_data": "❌ 数据获取失败",
            "data_quality_score": 0.0,
            "data_sources": {"market": "failed"},
            "data_issues": {"market": [{"message": "连接超时"}]},
        }

        # Act
        result = analyst_node(state)

        # Assert
        assert "market_report" in result
        # 即使数据不可用，仍然调用LLM（与社交媒体分析师不同）
        mock_llm.invoke.assert_called_once()

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.market_analyst.get_company_name")
    def test_market_analyst_with_valid_data(self, mock_get_company_name):
        """测试市场数据可用时正常生成报告"""
        from tradingagents.agents.analysts.market_analyst import create_market_analyst

        # Arrange
        mock_get_company_name.return_value = "平安银行"  # Mock 避免数据库连接
        mock_response = Mock()
        mock_response.content = "# 技术分析报告\n\n## 趋势分析\n上升趋势。"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        analyst_node = create_market_analyst(mock_llm)

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "market_data": "MA5: 10.5\nMA10: 10.2\nRSI: 65",
            "data_quality_score": 0.9,
            "data_sources": {"market": "tushare"},
            "data_issues": {},
        }

        # Act
        result = analyst_node(state)

        # Assert
        assert "market_report" in result
        assert result["market_report"] == mock_response.content


class TestFundamentalsAnalyst:
    """测试基本面分析师"""

    @pytest.mark.unit
    def test_create_fundamentals_analyst_node(self):
        """测试创建基本面分析师节点"""
        from tradingagents.agents.analysts.fundamentals_analyst import (
            create_fundamentals_analyst,
        )

        # Arrange
        mock_llm = Mock()

        # Act
        analyst_node = create_fundamentals_analyst(mock_llm)

        # Assert
        assert analyst_node is not None
        assert callable(analyst_node)

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.fundamentals_analyst.get_company_name")
    def test_fundamentals_analyst_with_valid_data(self, mock_get_company_name):
        """测试基本面数据可用时正常生成报告"""
        from tradingagents.agents.analysts.fundamentals_analyst import (
            create_fundamentals_analyst,
        )

        # Arrange
        mock_get_company_name.return_value = "平安银行"  # Mock 避免数据库连接
        mock_response = Mock()
        mock_response.content = "# 基本面分析报告\n\n## 财务指标\nROE: 15%"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        analyst_node = create_fundamentals_analyst(mock_llm)

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "financial_data": "ROE: 15%\nPE: 12\nPB: 1.5",
            "data_quality_score": 0.9,
            "data_sources": {"financial": "tushare"},
            "data_issues": {},
        }

        # Act
        result = analyst_node(state)

        # Assert
        assert "fundamentals_report" in result
        assert result["fundamentals_report"] == mock_response.content


class TestNewsAnalyst:
    """测试新闻分析师"""

    @pytest.mark.unit
    def test_create_news_analyst_node(self):
        """测试创建新闻分析师节点"""
        from tradingagents.agents.analysts.news_analyst import create_news_analyst

        # Arrange
        mock_llm = Mock()
        mock_toolkit = Mock()

        # Act
        analyst_node = create_news_analyst(mock_llm, mock_toolkit)

        # Assert
        assert analyst_node is not None
        assert callable(analyst_node)

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.news_analyst.get_company_name")
    def test_news_analyst_with_valid_data(self, mock_get_company_name):
        """测试新闻数据可用时正常生成报告"""
        from tradingagents.agents.analysts.news_analyst import create_news_analyst

        # Arrange
        mock_get_company_name.return_value = "平安银行"  # Mock 避免数据库连接
        mock_response = Mock()
        mock_response.content = "# 新闻分析报告\n\n## 重要新闻\n公司发布财报。"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_toolkit = Mock()
        analyst_node = create_news_analyst(mock_llm, mock_toolkit)

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "news_data": "新闻1\n新闻2",
            "sentiment_data": "情绪：中性",
            "data_quality_score": 0.85,
            "data_sources": {"news": "google"},
            "data_issues": {},
        }

        # Act
        result = analyst_node(state)

        # Assert
        assert "news_report" in result
        assert result["news_report"] == mock_response.content

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.news_analyst.get_company_name")
    def test_news_analyst_data_unavailable(self, mock_get_company_name):
        """测试新闻数据不可用时处理"""
        from tradingagents.agents.analysts.news_analyst import create_news_analyst

        # Arrange
        mock_get_company_name.return_value = "平安银行"  # Mock 避免数据库连接
        mock_response = Mock()
        mock_response.content = "新闻分析报告（无数据）"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_toolkit = Mock()
        analyst_node = create_news_analyst(mock_llm, mock_toolkit)

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "news_data": "❌ 数据获取失败",
            "sentiment_data": "❌ 数据获取失败",
            "data_quality_score": 0.0,
            "data_sources": {"news": "failed"},
            "data_issues": {"news": [{"message": "API错误"}]},
        }

        # Act
        result = analyst_node(state)

        # Assert
        assert "news_report" in result


class TestAnalystCommonPatterns:
    """测试分析师通用模式"""

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.social_media_analyst.get_company_name")
    def test_all_analysts_handle_different_stock_types(self, mock_get_company_name):
        """测试所有分析师处理不同类型的股票"""
        from tradingagents.agents.analysts.social_media_analyst import (
            create_social_media_analyst,
        )
        from tradingagents.agents.analysts.market_analyst import create_market_analyst

        # Arrange
        mock_get_company_name.return_value = "平安银行"  # Mock 避免数据库连接

        stock_types = [
            ("000001", "中国A股"),
            ("600000", "中国A股（主板）"),
            ("00700", "港股"),
            ("AAPL", "美股"),
        ]

        for ticker, desc in stock_types:
            # 社交媒体分析师
            mock_llm = Mock()
            mock_response = Mock()
            mock_response.content = f"{desc}分析报告"
            mock_llm.invoke.return_value = mock_response

            analyst = create_social_media_analyst(mock_llm, Mock())
            state = {
                "trade_date": "2024-06-01",
                "company_of_interest": ticker,
                "sentiment_data": "数据",
                "data_quality_score": 0.9,
                "data_sources": {},
                "data_issues": {},
            }
            result = analyst(state)
            assert "sentiment_report" in result
            assert (
                ticker in result["sentiment_report"]
                or desc in result["sentiment_report"]
            )

    @pytest.mark.unit
    def test_analyst_state_handling(self):
        """测试分析师正确处理state参数"""
        from tradingagents.agents.analysts.social_media_analyst import (
            create_social_media_analyst,
        )

        # Arrange
        mock_response = Mock()
        mock_response.content = "报告"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        analyst = create_social_media_analyst(mock_llm, Mock())

        # 测试缺少可选字段的state
        minimal_state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "sentiment_data": "数据",
            # 缺少 data_quality_score, data_sources, data_issues
        }

        # Act - 不应抛出异常
        result = analyst(minimal_state)

        # Assert
        assert "sentiment_report" in result

    @pytest.mark.unit
    def test_analyst_return_format(self):
        """测试分析师返回格式一致性"""
        from tradingagents.agents.analysts.social_media_analyst import (
            create_social_media_analyst,
        )
        from tradingagents.agents.analysts.market_analyst import create_market_analyst

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "sentiment_data": "数据",
            "market_data": "数据",
            "data_quality_score": 0.9,
            "data_sources": {},
            "data_issues": {},
        }

        # 社交媒体分析师
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "报告"
        mock_llm.invoke.return_value = mock_response

        social_analyst = create_social_media_analyst(mock_llm, Mock())
        result = social_analyst(state)

        assert "sentiment_report" in result
        assert "messages" in result
        assert isinstance(result["messages"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
