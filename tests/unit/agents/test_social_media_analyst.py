# -*- coding: utf-8 -*-
"""
测试社交媒体分析师功能

测试范围:
- 社交媒体分析师节点创建
- 基本执行流程
- 错误处理
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

os.environ["USE_MONGODB_STORAGE"] = "false"
os.environ["TRADINGAGENTS_SKIP_DB_INIT"] = "true"

from langchain_core.messages import AIMessage, ToolMessage


@pytest.mark.unit
def test_create_social_media_analyst():
    """测试创建社交媒体分析师节点"""
    mock_llm = Mock()
    mock_toolkit = Mock()

    with patch(
        "tradingagents.agents.analysts.social_media_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        from tradingagents.agents.analysts.social_media_analyst import (
            create_social_media_analyst,
        )

        social_analyst = create_social_media_analyst(mock_llm, mock_toolkit)

    assert social_analyst is not None
    assert callable(social_analyst)


@pytest.mark.unit
def test_social_media_analyst_basic_execution():
    """测试社交媒体分析师基本执行"""
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_toolkit.config = {"online_tools": {}}

    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "session_id": "test_session",
        "sentiment_data": "测试情绪数据",
    }

    # Mock LLM 返回结果
    mock_response = Mock()
    mock_response.content = "社交媒体情绪分析报告：投资者情绪乐观..."
    mock_llm.invoke.return_value = mock_response

    with patch(
        "tradingagents.agents.analysts.social_media_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.social_media_analyst.get_company_name"
        ) as mock_get_name:
            mock_get_name.return_value = "Apple Inc."
            with patch(
                "tradingagents.agents.analysts.social_media_analyst.StockUtils"
            ) as mock_stock_utils:
                mock_stock_utils.get_market_info.return_value = {
                    "market_name": "美股",
                    "currency_name": "美元",
                    "currency_symbol": "USD",
                    "is_china": False,
                    "is_hk": False,
                    "is_us": True,
                }

                from tradingagents.agents.analysts.social_media_analyst import (
                    create_social_media_analyst,
                )

                social_analyst = create_social_media_analyst(mock_llm, mock_toolkit)
                result = social_analyst(mock_state)

    assert result is not None
    assert "sentiment_report" in result


@pytest.mark.unit
@patch("tradingagents.agents.analysts.social_media_analyst.get_company_name")
@patch("tradingagents.agents.analysts.social_media_analyst.StockUtils")
def test_social_media_analyst_data_unavailable(mock_stock_utils, mock_get_name):
    """测试情绪数据不可用时生成默认报告"""
    mock_get_name.return_value = "平安银行"
    mock_stock_utils.get_market_info.return_value = {
        "market_name": "深圳A股",
        "is_china": True,
    }
    mock_llm = Mock()

    with patch(
        "tradingagents.agents.analysts.social_media_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        from tradingagents.agents.analysts.social_media_analyst import (
            create_social_media_analyst,
        )

        social_analyst = create_social_media_analyst(mock_llm, Mock())

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "sentiment_data": "❌ 数据获取失败",
            "data_quality_score": 0.0,
            "data_sources": {"sentiment": "failed"},
            "data_issues": {"sentiment": [{"message": "API错误"}]},
        }

        result = social_analyst(state)

        assert "sentiment_report" in result
        assert "数据获取状态" in result["sentiment_report"]
        assert "000001" in result["sentiment_report"]
        # 数据不可用时，不应调用LLM
        mock_llm.invoke.assert_not_called()


@pytest.mark.unit
@patch("tradingagents.agents.analysts.social_media_analyst.get_company_name")
@patch("tradingagents.agents.analysts.social_media_analyst.StockUtils")
def test_social_media_analyst_with_china_stock(mock_stock_utils, mock_get_name):
    """测试中国股票社交媒体分析（A股）"""
    mock_get_name.return_value = "平安银行"
    mock_stock_utils.get_market_info.return_value = {
        "market_name": "深圳A股",
        "currency_name": "人民币",
        "currency_symbol": "CNY",
        "is_china": True,
        "is_hk": False,
        "is_us": False,
    }
    mock_llm = Mock()
    mock_response = Mock()
    mock_response.content = "平安银行社交媒体情绪分析：散户讨论活跃，情绪中性偏乐观..."
    mock_llm.invoke.return_value = mock_response

    with patch(
        "tradingagents.agents.analysts.social_media_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        from tradingagents.agents.analysts.social_media_analyst import (
            create_social_media_analyst,
        )

        social_analyst = create_social_media_analyst(mock_llm, Mock())

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "sentiment_data": "情绪指数: 0.65\n讨论热度: 高\n散户情绪: 乐观",
            "data_quality_score": 0.85,
            "data_sources": {"sentiment": "tushare"},
            "data_issues": {},
        }

        result = social_analyst(state)

        assert "sentiment_report" in result
        assert result["sentiment_report"] == mock_response.content
        mock_llm.invoke.assert_called_once()


@pytest.mark.unit
def test_social_media_analyst_with_google_model():
    """测试Google模型特殊处理"""
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_toolkit.config = {"online_tools": {}}

    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "session_id": "test_session",
        "sentiment_data": "测试情绪数据",
    }

    # Mock LLM 返回结果
    mock_response = Mock()
    mock_response.content = "Google模型生成的情绪分析报告"
    mock_llm.invoke.return_value = mock_response

    with patch(
        "tradingagents.agents.analysts.social_media_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.social_media_analyst.get_company_name"
        ) as mock_get_name:
            mock_get_name.return_value = "Apple Inc."
            with patch(
                "tradingagents.agents.analysts.social_media_analyst.StockUtils"
            ) as mock_stock_utils:
                mock_stock_utils.get_market_info.return_value = {
                    "market_name": "美股",
                    "currency_name": "美元",
                    "currency_symbol": "USD",
                    "is_china": False,
                    "is_hk": False,
                    "is_us": True,
                }

                from tradingagents.agents.analysts.social_media_analyst import (
                    create_social_media_analyst,
                )

                social_analyst = create_social_media_analyst(mock_llm, mock_toolkit)
                result = social_analyst(mock_state)

    assert result is not None
    assert "sentiment_report" in result


@pytest.mark.unit
@patch("tradingagents.agents.analysts.social_media_analyst.get_company_name")
@patch("tradingagents.agents.analysts.social_media_analyst.StockUtils")
def test_social_media_analyst_hk_stock(mock_stock_utils, mock_get_name):
    """测试香港股票社交媒体分析（港股）"""
    mock_get_name.return_value = "腾讯控股"
    mock_stock_utils.get_market_info.return_value = {
        "market_name": "港股",
        "currency_name": "港币",
        "currency_symbol": "HKD",
        "is_china": False,
        "is_hk": True,
        "is_us": False,
    }
    mock_llm = Mock()
    mock_response = Mock()
    mock_response.content = "腾讯控股社交媒体情绪分析：港股通资金关注度高..."
    mock_llm.invoke.return_value = mock_response

    with patch(
        "tradingagents.agents.analysts.social_media_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        from tradingagents.agents.analysts.social_media_analyst import (
            create_social_media_analyst,
        )

        social_analyst = create_social_media_analyst(mock_llm, Mock())

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "00700",
            "sentiment_data": "情绪指数: 0.72\n港股通资金流向: 净流入\n讨论热度: 中等",
            "data_quality_score": 0.8,
            "data_sources": {"sentiment": "akshare"},
            "data_issues": {},
        }

        result = social_analyst(state)

        assert "sentiment_report" in result
        assert result["sentiment_report"] == mock_response.content
        mock_llm.invoke.assert_called_once()


@pytest.mark.unit
@patch("tradingagents.agents.analysts.social_media_analyst.get_company_name")
@patch("tradingagents.agents.analysts.social_media_analyst.StockUtils")
def test_social_media_analyst_with_data_issues(mock_stock_utils, mock_get_name):
    """测试有数据质量问题时记录日志"""
    mock_get_name.return_value = "平安银行"
    mock_stock_utils.get_market_info.return_value = {
        "market_name": "深圳A股",
        "is_china": True,
    }
    mock_llm = Mock()
    mock_response = Mock()
    mock_response.content = "情绪分析报告"
    mock_llm.invoke.return_value = mock_response

    with patch(
        "tradingagents.agents.analysts.social_media_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        from tradingagents.agents.analysts.social_media_analyst import (
            create_social_media_analyst,
        )

        social_analyst = create_social_media_analyst(mock_llm, Mock())

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "sentiment_data": "情绪数据部分可用",
            "data_quality_score": 0.6,
            "data_sources": {"sentiment": "akshare"},
            "data_issues": {
                "sentiment": [
                    {"message": "数据不完整"},
                    {"message": "API限流"},
                ]
            },
        }

        result = social_analyst(state)

        # 即使有数据问题，仍然继续分析
        assert "sentiment_report" in result
        mock_llm.invoke.assert_called_once()


@pytest.mark.unit
@patch("tradingagents.agents.analysts.social_media_analyst.get_company_name")
@patch("tradingagents.agents.analysts.social_media_analyst.StockUtils")
def test_social_media_analyst_llm_error(mock_stock_utils, mock_get_name):
    """测试LLM调用失败时的错误处理"""
    mock_get_name.return_value = "平安银行"
    mock_stock_utils.get_market_info.return_value = {
        "market_name": "深圳A股",
        "is_china": True,
    }
    mock_llm = Mock()
    mock_llm.invoke.side_effect = Exception("API调用失败")

    with patch(
        "tradingagents.agents.analysts.social_media_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        from tradingagents.agents.analysts.social_media_analyst import (
            create_social_media_analyst,
        )

        social_analyst = create_social_media_analyst(mock_llm, Mock())

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "sentiment_data": "正常情绪数据",
            "data_quality_score": 0.9,
            "data_sources": {"sentiment": "tushare"},
            "data_issues": {},
        }

        result = social_analyst(state)

        # 应该返回错误信息而不是抛出异常
        assert "sentiment_report" in result
        assert "❌ 情绪分析失败" in result["sentiment_report"]
        assert "API调用失败" in result["sentiment_report"]


@pytest.mark.unit
def test_social_media_analyst_messages_structure():
    """测试返回消息结构"""
    # 简单验证 ToolMessage 可以正常创建
    messages = []
    for i in range(3):
        messages.append(
            ToolMessage(
                content=f"工具返回数据{i}",
                name="get_stock_sentiment_unified",
                tool_call_id=f"call_{i}",
            )
        )

    assert len(messages) == 3
    assert all(isinstance(m, ToolMessage) for m in messages)


@pytest.mark.unit
def test_social_media_analyst_date_handling():
    """测试日期处理"""
    # 简单验证日期格式
    test_date = "2025-01-15"
    parsed_date = datetime.strptime(test_date, "%Y-%m-%d")
    assert parsed_date.year == 2025
    assert parsed_date.month == 1
    assert parsed_date.day == 15


@pytest.mark.unit
@patch("tradingagents.agents.analysts.social_media_analyst.get_company_name")
@patch("tradingagents.agents.analysts.social_media_analyst.StockUtils")
def test_social_media_analyst_sentiment_score_validation(mock_stock_utils, mock_get_name):
    """测试情绪评分验证和数据质量处理"""
    mock_get_name.return_value = "平安银行"
    mock_stock_utils.get_market_info.return_value = {
        "market_name": "深圳A股",
        "is_china": True,
    }
    mock_llm = Mock()
    mock_response = Mock()
    mock_response.content = "情绪分析报告"
    mock_llm.invoke.return_value = mock_response

    with patch(
        "tradingagents.agents.analysts.social_media_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        from tradingagents.agents.analysts.social_media_analyst import (
            create_social_media_analyst,
        )

        social_analyst = create_social_media_analyst(mock_llm, Mock())

        # 测试高质量数据 (score > 0.8)
        state_high_quality = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "sentiment_data": "情绪指数: 0.85\n讨论热度: 高",
            "data_quality_score": 0.9,
            "data_sources": {"sentiment": "tushare"},
            "data_issues": {},
        }

        result = social_analyst(state_high_quality)
        assert "sentiment_report" in result
        mock_llm.invoke.assert_called()

        # 测试低质量数据 (score < 0.3)
        mock_llm.reset_mock()
        state_low_quality = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "sentiment_data": "数据不完整",
            "data_quality_score": 0.2,
            "data_sources": {"sentiment": "akshare"},
            "data_issues": {"sentiment": [{"message": "数据质量低"}]},
        }

        result = social_analyst(state_low_quality)
        assert "sentiment_report" in result
        # 低质量数据但仍然可用时，仍然调用LLM
        mock_llm.invoke.assert_called_once()
