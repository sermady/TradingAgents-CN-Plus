# -*- coding: utf-8 -*-
"""
测试中国市场分析师功能

测试范围:
- 中国市场分析师节点创建
- A股特色数据分析（涨跌停、换手率、量比）
- 数据不可用时的处理
- 错误处理
"""

import pytest
from unittest.mock import Mock, patch


class TestChinaMarketAnalyst:
    """测试中国市场分析师"""

    @pytest.mark.unit
    def test_create_china_market_analyst_node(self):
        """测试创建中国市场分析师节点"""
        from tradingagents.agents.analysts.china_market_analyst import (
            create_china_market_analyst,
        )

        # Arrange
        mock_llm = Mock()
        mock_toolkit = Mock()

        # Act
        analyst_node = create_china_market_analyst(mock_llm, mock_toolkit)

        # Assert
        assert analyst_node is not None
        assert callable(analyst_node)

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.china_market_analyst.get_company_name")
    @patch("tradingagents.agents.analysts.china_market_analyst.StockUtils")
    def test_china_market_analyst_with_valid_data(
        self, mock_stock_utils, mock_get_company_name
    ):
        """测试A股数据可用时正常生成报告"""
        from tradingagents.agents.analysts.china_market_analyst import (
            create_china_market_analyst,
        )

        # Arrange
        mock_get_company_name.return_value = "平安银行"
        mock_stock_utils.get_market_info.return_value = {
            "market_name": "深圳A股",
            "is_china": True,
        }
        mock_response = Mock()
        mock_response.content = "# A股市场特色分析报告\n\n## 涨跌停分析\n未触及涨跌停。"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response

        analyst_node = create_china_market_analyst(mock_llm, Mock())

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "china_market_data": "涨停价: 12.50\n跌停价: 10.20\n换手率: 5.5%\n量比: 1.8",
            "data_quality_score": 0.9,
            "data_sources": {"china_market": "tushare"},
            "data_issues": {},
        }

        # Act
        result = analyst_node(state)

        # Assert
        assert "china_market_report" in result
        assert result["china_market_report"] == mock_response.content
        mock_llm.invoke.assert_called_once()

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.china_market_analyst.get_company_name")
    @patch("tradingagents.agents.analysts.china_market_analyst.StockUtils")
    def test_china_market_analyst_data_unavailable(
        self, mock_stock_utils, mock_get_company_name
    ):
        """测试A股数据不可用时生成警告报告"""
        from tradingagents.agents.analysts.china_market_analyst import (
            create_china_market_analyst,
        )

        # Arrange
        mock_get_company_name.return_value = "平安银行"
        mock_stock_utils.get_market_info.return_value = {
            "market_name": "深圳A股",
            "is_china": True,
        }
        mock_response = Mock()
        mock_response.content = "A股分析报告（数据不可用）"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response

        analyst_node = create_china_market_analyst(mock_llm, Mock())

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "china_market_data": "❌ 数据获取失败",
            "data_quality_score": 0.0,
            "data_sources": {"china_market": "failed"},
            "data_issues": {"china_market": [{"message": "连接超时"}]},
        }

        # Act
        result = analyst_node(state)

        # Assert
        assert "china_market_report" in result
        assert "china_market_report" in result
        # 数据不可用时，仍然调用LLM进行分析
        mock_llm.invoke.assert_called_once()

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.china_market_analyst.get_company_name")
    @patch("tradingagents.agents.analysts.china_market_analyst.StockUtils")
    def test_china_market_analyst_empty_data(
        self, mock_stock_utils, mock_get_company_name
    ):
        """测试空A股数据时生成警告报告"""
        from tradingagents.agents.analysts.china_market_analyst import (
            create_china_market_analyst,
        )

        # Arrange
        mock_get_company_name.return_value = "浦发银行"
        mock_stock_utils.get_market_info.return_value = {
            "market_name": "上海A股",
            "is_china": True,
        }
        mock_response = Mock()
        mock_response.content = "A股分析报告（无数据）"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response

        analyst_node = create_china_market_analyst(mock_llm, Mock())

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "600000",
            "china_market_data": "",
            "data_quality_score": 0.0,
            "data_sources": {},
            "data_issues": {},
        }

        # Act
        result = analyst_node(state)

        # Assert
        assert "china_market_report" in result

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.china_market_analyst.get_company_name")
    @patch("tradingagents.agents.analysts.china_market_analyst.StockUtils")
    def test_china_market_analyst_limit_up_down(
        self, mock_stock_utils, mock_get_company_name
    ):
        """测试涨跌停数据分析"""
        from tradingagents.agents.analysts.china_market_analyst import (
            create_china_market_analyst,
        )

        # Arrange
        mock_get_company_name.return_value = "平安银行"
        mock_stock_utils.get_market_info.return_value = {
            "market_name": "深圳A股",
            "is_china": True,
        }
        mock_response = Mock()
        mock_response.content = "# A股分析报告\n\n触及涨停，封板强度强。"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response

        analyst_node = create_china_market_analyst(mock_llm, Mock())

        # 测试涨停情况
        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "china_market_data": (
                "涨停价: 12.50\n"
                "跌停价: 10.20\n"
                "当前价: 12.50\n"
                "涨幅: +10.00%\n"
                "换手率: 8.5%\n"
                "量比: 3.2"
            ),
            "data_quality_score": 0.95,
            "data_sources": {"china_market": "tushare"},
            "data_issues": {},
        }

        # Act
        result = analyst_node(state)

        # Assert
        assert "china_market_report" in result
        assert result["china_market_report"] == mock_response.content

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.china_market_analyst.get_company_name")
    @patch("tradingagents.agents.analysts.china_market_analyst.StockUtils")
    def test_china_market_analyst_turnover_rate_levels(
        self, mock_stock_utils, mock_get_company_name
    ):
        """测试换手率分级分析"""
        from tradingagents.agents.analysts.china_market_analyst import (
            create_china_market_analyst,
        )

        # Arrange
        mock_get_company_name.return_value = "平安银行"
        mock_stock_utils.get_market_info.return_value = {
            "market_name": "深圳A股",
            "is_china": True,
        }
        mock_response = Mock()
        mock_response.content = "换手率分析：异常活跃，关注资金流向。"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response

        analyst_node = create_china_market_analyst(mock_llm, Mock())

        # 测试高换手率（>20%，极度活跃）
        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "china_market_data": (
                "涨停价: 12.50\n"
                "跌停价: 10.20\n"
                "换手率: 25.5%\n"  # >20% 极度活跃
                "量比: 4.5"
            ),
            "data_quality_score": 0.9,
            "data_sources": {"china_market": "tushare"},
            "data_issues": {},
        }

        # Act
        result = analyst_node(state)

        # Assert
        assert "china_market_report" in result

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.china_market_analyst.get_company_name")
    @patch("tradingagents.agents.analysts.china_market_analyst.StockUtils")
    def test_china_market_analyst_volume_ratio(
        self, mock_stock_utils, mock_get_company_name
    ):
        """测试量比分析"""
        from tradingagents.agents.analysts.china_market_analyst import (
            create_china_market_analyst,
        )

        # Arrange
        mock_get_company_name.return_value = "平安银行"
        mock_stock_utils.get_market_info.return_value = {
            "market_name": "深圳A股",
            "is_china": True,
        }
        mock_response = Mock()
        mock_response.content = "量比>1.5，放量明显，资金关注度提升。"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response

        analyst_node = create_china_market_analyst(mock_llm, Mock())

        # 测试放量情况（量比>1.5）
        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "china_market_data": (
                "涨停价: 12.50\n"
                "跌停价: 10.20\n"
                "换手率: 12.5%\n"
                "量比: 2.8"  # >1.5 放量
            ),
            "data_quality_score": 0.9,
            "data_sources": {"china_market": "tushare"},
            "data_issues": {},
        }

        # Act
        result = analyst_node(state)

        # Assert
        assert "china_market_report" in result

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.china_market_analyst.get_company_name")
    @patch("tradingagents.agents.analysts.china_market_analyst.StockUtils")
    def test_china_market_analyst_with_data_issues(
        self, mock_stock_utils, mock_get_company_name
    ):
        """测试有数据质量问题时记录日志"""
        from tradingagents.agents.analysts.china_market_analyst import (
            create_china_market_analyst,
        )

        # Arrange
        mock_get_company_name.return_value = "平安银行"
        mock_stock_utils.get_market_info.return_value = {
            "market_name": "深圳A股",
            "is_china": True,
        }
        mock_response = Mock()
        mock_response.content = "A股分析报告"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response

        analyst_node = create_china_market_analyst(mock_llm, Mock())

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "china_market_data": "涨停价: 12.50\n换手率: 5.5%",
            "data_quality_score": 0.7,
            "data_sources": {"china_market": "akshare"},
            "data_issues": {
                "china_market": [
                    {"message": "换手率数据不完整"},
                    {"message": "量比数据缺失"},
                ]
            },
        }

        # Act
        result = analyst_node(state)

        # Assert - 即使有数据问题，仍然继续分析
        assert "china_market_report" in result

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.china_market_analyst.get_company_name")
    @patch("tradingagents.agents.analysts.china_market_analyst.StockUtils")
    def test_china_market_analyst_llm_error(
        self, mock_stock_utils, mock_get_company_name
    ):
        """测试LLM调用失败时的错误处理"""
        from tradingagents.agents.analysts.china_market_analyst import (
            create_china_market_analyst,
        )

        # Arrange
        mock_get_company_name.return_value = "平安银行"
        mock_stock_utils.get_market_info.return_value = {
            "market_name": "深圳A股",
            "is_china": True,
        }
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("API调用失败")

        analyst_node = create_china_market_analyst(mock_llm, Mock())

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "china_market_data": "涨停价: 12.50\n换手率: 5.5%",
            "data_quality_score": 0.9,
            "data_sources": {"china_market": "tushare"},
            "data_issues": {},
        }

        # Act
        result = analyst_node(state)

        # Assert - 应该返回错误信息而不是抛出异常
        assert "china_market_report" in result
        assert "❌ 中国市场分析失败" in result["china_market_report"]
        assert "API调用失败" in result["china_market_report"]

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.china_market_analyst.get_company_name")
    @patch("tradingagents.agents.analysts.china_market_analyst.StockUtils")
    def test_china_market_analyst_different_board_types(
        self, mock_stock_utils, mock_get_company_name
    ):
        """测试不同板块类型的股票分析（主板、创业板、科创板）"""
        from tradingagents.agents.analysts.china_market_analyst import (
            create_china_market_analyst,
        )

        # Arrange
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "A股板块分析报告"
        mock_llm.invoke.return_value = mock_response

        analyst_node = create_china_market_analyst(mock_llm, Mock())

        # 测试不同的股票代码
        stock_types = [
            ("000001", "深圳主板"),
            ("600000", "上海主板"),
            ("300001", "创业板"),
            ("688001", "科创板"),
        ]

        for ticker, board_type in stock_types:
            mock_get_company_name.return_value = f"测试{board_type}股票"
            mock_stock_utils.get_market_info.return_value = {
                "market_name": f"{board_type}A股",
                "is_china": True,
            }

            state = {
                "trade_date": "2024-06-01",
                "company_of_interest": ticker,
                "china_market_data": f"涨停价: 12.50\n{board_type}特色数据",
                "data_quality_score": 0.9,
                "data_sources": {"china_market": "tushare"},
                "data_issues": {},
            }

            # Act
            result = analyst_node(state)

            # Assert
            assert "china_market_report" in result
            assert result["china_market_report"] == mock_response.content

    @pytest.mark.unit
    @patch("tradingagents.agents.analysts.china_market_analyst.get_company_name")
    @patch("tradingagents.agents.analysts.china_market_analyst.StockUtils")
    def test_china_market_analyst_return_format(
        self, mock_stock_utils, mock_get_company_name
    ):
        """测试返回格式一致性"""
        from tradingagents.agents.analysts.china_market_analyst import (
            create_china_market_analyst,
        )

        # Arrange
        mock_get_company_name.return_value = "平安银行"
        mock_stock_utils.get_market_info.return_value = {
            "market_name": "深圳A股",
            "is_china": True,
        }
        mock_response = Mock()
        mock_response.content = "A股市场分析报告"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response

        analyst_node = create_china_market_analyst(mock_llm, Mock())

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "china_market_data": "涨停价: 12.50",
            "data_quality_score": 0.9,
            "data_sources": {},
            "data_issues": {},
        }

        # Act
        result = analyst_node(state)

        # Assert
        assert "china_market_report" in result
        assert "messages" in result
        assert isinstance(result["messages"], list)
        assert len(result["messages"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
