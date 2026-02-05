# -*- coding: utf-8 -*-
"""
测试新闻分析师功能

测试范围:
- 新闻分析师节点创建
- 基本执行流程
- 错误处理
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from langchain_core.messages import AIMessage, ToolMessage

os.environ["USE_MONGODB_STORAGE"] = "false"
os.environ["TRADINGAGENTS_SKIP_DB_INIT"] = "true"


@pytest.mark.unit
def test_create_news_analyst():
    """测试创建新闻分析师节点"""
    mock_llm = Mock()
    mock_toolkit = Mock()

    with patch(
        "tradingagents.agents.analysts.news_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        from tradingagents.agents.analysts.news_analyst import create_news_analyst

        news_analyst = create_news_analyst(mock_llm, mock_toolkit)

    assert news_analyst is not None
    assert callable(news_analyst)


@pytest.mark.unit
def test_news_analyst_basic_execution():
    """测试新闻分析师基本执行"""
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_toolkit.config = {"online_tools": {}}

    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "session_id": "test_session",
        "news_data": "测试新闻数据",
    }

    # Mock LLM 返回结果
    mock_response = Mock()
    mock_response.content = "新闻分析报告：AAPL的财务状况良好..."
    mock_llm.invoke.return_value = mock_response

    with patch(
        "tradingagents.agents.analysts.news_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.news_analyst.get_company_name"
        ) as mock_get_name:
            mock_get_name.return_value = "Apple Inc."
            with patch(
                "tradingagents.agents.analysts.news_analyst.StockUtils"
            ) as mock_stock_utils:
                mock_stock_utils.get_market_info.return_value = {
                    "market_name": "美股",
                    "currency_name": "美元",
                    "currency_symbol": "USD",
                    "is_china": False,
                    "is_hk": False,
                    "is_us": True,
                }

                from tradingagents.agents.analysts.news_analyst import (
                    create_news_analyst,
                )

                news_analyst = create_news_analyst(mock_llm, mock_toolkit)
                result = news_analyst(mock_state)

    assert result is not None
    assert "news_report" in result


@pytest.mark.unit
def test_news_analyst_tool_call_count_limit():
    """测试工具调用次数限制"""
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_toolkit.config = {"online_tools": {}}

    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "session_id": "test_session",
        "news_tool_call_count": 3,
        "news_data": "测试新闻数据",
    }

    # Mock LLM 返回结果
    mock_response = Mock()
    mock_response.content = "新闻分析报告"
    mock_llm.invoke.return_value = mock_response

    with patch(
        "tradingagents.agents.analysts.news_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.news_analyst.get_company_name"
        ) as mock_get_name:
            mock_get_name.return_value = "Apple Inc."
            with patch(
                "tradingagents.agents.analysts.news_analyst.StockUtils"
            ) as mock_stock_utils:
                mock_stock_utils.get_market_info.return_value = {
                    "market_name": "美股",
                    "currency_name": "美元",
                    "currency_symbol": "USD",
                    "is_china": False,
                    "is_hk": False,
                    "is_us": True,
                }

                from tradingagents.agents.analysts.news_analyst import (
                    create_news_analyst,
                )

                news_analyst = create_news_analyst(mock_llm, mock_toolkit)
                result = news_analyst(mock_state)

    assert result is not None
    assert "news_report" in result


@pytest.mark.unit
def test_news_analyst_with_china_stock():
    """测试中国股票新闻分析"""
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_toolkit.config = {"online_tools": {}}

    mock_state = {
        "messages": [],
        "company_of_interest": "000001",
        "trade_date": "2025-01-15",
        "session_id": "test_session",
        "news_data": "测试新闻数据",
    }

    # Mock LLM 返回结果
    mock_response = Mock()
    mock_response.content = "中国A股新闻分析报告：平安银行(000001)的相关新闻..."
    mock_llm.invoke.return_value = mock_response

    with patch(
        "tradingagents.agents.analysts.news_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.news_analyst.get_company_name"
        ) as mock_get_name:
            mock_get_name.return_value = "平安银行"
            with patch(
                "tradingagents.agents.analysts.news_analyst.StockUtils"
            ) as mock_stock_utils:
                mock_stock_utils.get_market_info.return_value = {
                    "market_name": "中国A股",
                    "currency_name": "人民币",
                    "currency_symbol": "CNY",
                    "is_china": True,
                    "is_hk": False,
                    "is_us": False,
                }

                from tradingagents.agents.analysts.news_analyst import (
                    create_news_analyst,
                )

                news_analyst = create_news_analyst(mock_llm, mock_toolkit)
                result = news_analyst(mock_state)

    assert result is not None
    assert "news_report" in result


@pytest.mark.unit
def test_news_analyst_error_handling():
    """测试错误处理"""
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_toolkit.config = {"online_tools": {}}

    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "session_id": "test_session",
        "news_data": "测试新闻数据",
    }

    # Mock LLM 抛出异常
    mock_llm.invoke.side_effect = Exception("LLM调用失败")

    with patch(
        "tradingagents.agents.analysts.news_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.news_analyst.get_company_name"
        ) as mock_get_name:
            mock_get_name.return_value = "Apple Inc."
            with patch(
                "tradingagents.agents.analysts.news_analyst.StockUtils"
            ) as mock_stock_utils:
                mock_stock_utils.get_market_info.return_value = {
                    "market_name": "美股",
                    "currency_name": "美元",
                    "currency_symbol": "USD",
                    "is_china": False,
                    "is_hk": False,
                    "is_us": True,
                }

                from tradingagents.agents.analysts.news_analyst import (
                    create_news_analyst,
                )

                news_analyst = create_news_analyst(mock_llm, mock_toolkit)

                # 应该返回错误报告而不是抛出异常
                result = news_analyst(mock_state)
                assert result is not None
                assert "news_report" in result


@pytest.mark.unit
def test_news_analyst_messages_structure():
    """测试返回消息结构"""
    # 简单验证 ToolMessage 可以正常创建
    messages = []
    for i in range(3):
        messages.append(
            ToolMessage(
                content=f"工具返回数据{i}",
                name="get_stock_news_unified",
                tool_call_id=f"call_{i}",
            )
        )

    assert len(messages) == 3
    assert all(isinstance(m, ToolMessage) for m in messages)


@pytest.mark.unit
def test_news_analyst_date_handling():
    """测试日期处理"""
    # 简单验证日期格式
    test_date = "2025-01-15"
    parsed_date = datetime.strptime(test_date, "%Y-%m-%d")
    assert parsed_date.year == 2025
    assert parsed_date.month == 1
    assert parsed_date.day == 15


@pytest.mark.unit
def test_news_analyst_hk_stock():
    """测试港股新闻分析"""
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_toolkit.config = {"online_tools": {}}

    mock_state = {
        "messages": [],
        "company_of_interest": "0700.HK",
        "trade_date": "2025-01-15",
        "session_id": "test_session",
        "news_data": "测试新闻数据",
    }

    # Mock LLM 返回结果
    mock_response = Mock()
    mock_response.content = "港股新闻分析报告：腾讯控股(0700.HK)的相关新闻..."
    mock_llm.invoke.return_value = mock_response

    with patch(
        "tradingagents.agents.analysts.news_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.news_analyst.get_company_name"
        ) as mock_get_name:
            mock_get_name.return_value = "腾讯控股"
            with patch(
                "tradingagents.agents.analysts.news_analyst.StockUtils"
            ) as mock_stock_utils:
                mock_stock_utils.get_market_info.return_value = {
                    "market_name": "港股",
                    "currency_name": "港币",
                    "currency_symbol": "HKD",
                    "is_china": False,
                    "is_hk": True,
                    "is_us": False,
                }

                from tradingagents.agents.analysts.news_analyst import (
                    create_news_analyst,
                )

                news_analyst = create_news_analyst(mock_llm, mock_toolkit)
                result = news_analyst(mock_state)

    assert result is not None
    assert "news_report" in result
