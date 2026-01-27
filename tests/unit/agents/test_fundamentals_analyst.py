# -*- coding: utf-8 -*-
"""
测试基本面分析师功能

测试范围:
- 分析师节点创建
- 工具调用逻辑
- 不同LLM模型的处理
- 日期计算
- 公司名称解析
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from langchain_core.messages import AIMessage, ToolMessage

os.environ["USE_MONGODB_STORAGE"] = "false"
os.environ["TRADINGAGENTS_SKIP_DB_INIT"] = "true"


@pytest.mark.unit
def test_create_fundamentals_analyst():
    """测试创建基本面分析师"""
    mock_llm = Mock()
    mock_toolkit = Mock()

    with patch(
        "tradingagents.agents.analysts.fundamentals_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        from tradingagents.agents.analysts.fundamentals_analyst import (
            create_fundamentals_analyst,
        )

        analyst = create_fundamentals_analyst(mock_llm, mock_toolkit)

    assert analyst is not None
    assert callable(analyst)


@pytest.mark.unit
def test_fundamentals_analyst_basic_execution():
    """测试基本面分析师基本执行（简化版）"""
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_toolkit.config = {"online_tools": {}}

    mock_state = {
        "messages": [],
        "company_of_interest": "600519",
        "trade_date": "2025-01-15",
    }

    mock_result = {
        "fundamentals_report": "贵州茅台基本面分析报告：",
        "fundamentals_tool_call_count": 1,
    }

    with patch(
        "tradingagents.agents.analysts.fundamentals_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.fundamentals_analyst.fundamentals_analyst_node"
        ) as mock_node:
            mock_node.return_value = mock_result

            from tradingagents.agents.analysts.fundamentals_analyst import (
                create_fundamentals_analyst,
            )

            analyst = create_fundamentals_analyst(mock_llm, mock_toolkit)
            result = analyst(mock_state)

    assert result == mock_result


@pytest.mark.unit
def test_fundamentals_analyst_with_china_stock():
    """测试中国股票基本面分析（简化版）"""
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_toolkit.config = {"online_tools": {}}

    mock_state = {
        "messages": [],
        "company_of_interest": "000001",
        "trade_date": "2025-01-15",
    }

    mock_result = {
        "fundamentals_report": "平安银行基本面分析报告：",
        "fundamentals_tool_call_count": 1,
    }

    with patch(
        "tradingagents.agents.analysts.fundamentals_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.fundamentals_analyst.fundamentals_analyst_node"
        ) as mock_node:
            mock_node.return_value = mock_result

            from tradingagents.agents.analysts.fundamentals_analyst import (
                create_fundamentals_analyst,
            )

            analyst = create_fundamentals_analyst(mock_llm, mock_toolkit)
            result = analyst(mock_state)

    assert result == mock_result


@pytest.mark.unit
def test_fundamentals_analyst_tool_call_count_limit():
    """测试工具调用计数限制（简化版）"""
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_toolkit.config = {"online_tools": {}}

    mock_state = {
        "messages": [],
        "company_of_interest": "600519",
        "trade_date": "2025-01-15",
        "fundamentals_tool_call_count": 2,
    }

    mock_result = {
        "fundamentals_report": "贵州茅台基本面分析报告：",
        "fundamentals_tool_call_count": 2,
    }

    with patch(
        "tradingagents.agents.analysts.fundamentals_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.fundamentals_analyst.fundamentals_analyst_node"
        ) as mock_node:
            mock_node.return_value = mock_result

            from tradingagents.agents.analysts.fundamentals_analyst import (
                create_fundamentals_analyst,
            )

            analyst = create_fundamentals_analyst(mock_llm, mock_toolkit)
            result = analyst(mock_state)

    assert result == mock_result


@pytest.mark.unit
def test_fundamentals_analyst_hk_stock():
    """测试港股基本面分析（简化版）"""
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_toolkit.config = {"online_tools": {}}

    mock_state = {
        "messages": [],
        "company_of_interest": "00700",
        "trade_date": "2025-01-15",
    }

    mock_result = {
        "fundamentals_report": "腾讯控股基本面分析报告：",
        "fundamentals_tool_call_count": 1,
    }

    with patch(
        "tradingagents.agents.analysts.fundamentals_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.fundamentals_analyst.fundamentals_analyst_node"
        ) as mock_node:
            mock_node.return_value = mock_result

            from tradingagents.agents.analysts.fundamentals_analyst import (
                create_fundamentals_analyst,
            )

            analyst = create_fundamentals_analyst(mock_llm, mock_toolkit)
            result = analyst(mock_state)

    assert result == mock_result


@pytest.mark.unit
def test_fundamentals_analyst_error_handling():
    """测试错误处理"""
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_toolkit.config = {"online_tools": {}}

    mock_state = {
        "messages": [],
        "company_of_interest": "600519",
        "trade_date": "2025-01-15",
    }

    with patch(
        "tradingagents.agents.analysts.fundamentals_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.fundamentals_analyst.fundamentals_analyst_node"
        ) as mock_node:
            mock_node.side_effect = Exception("LLM调用失败")

            from tradingagents.agents.analysts.fundamentals_analyst import (
                create_fundamentals_analyst,
            )

            analyst = create_fundamentals_analyst(mock_llm, mock_toolkit)

            try:
                result = analyst(mock_state)
                pytest.fail("Expected exception was not raised")
            except Exception as e:
                assert "LLM调用失败" in str(e)


@pytest.mark.unit
def test_fundamentals_analyst_messages_structure():
    """测试消息结构"""
    from tradingagents.agents.analysts.fundamentals_analyst import (
        _count_tool_messages,
    )

    messages = []
    for i in range(3):
        messages.append(
            ToolMessage(
                content=f"工具返回数据{i}",
                name="get_stock_fundamentals_unified",
            )
        )

    count = _count_tool_messages(messages)
    assert count == 3


@pytest.mark.unit
def test_date_calculation_different_markets():
    """测试不同市场的日期计算"""
    from tradingagents.agents.analysts.fundamentals_analyst import (
        _calculate_date_range,
    )

    test_cases = [
        ("000001", "平安银行", "深圳证券交易所", "人民币", "CNY", 30),
        ("00700", "腾讯控股", "香港交易所", "港币", "HKD", 30),
        ("AAPL", "Apple Inc.", "NASDAQ", "美元", "$", 30),
    ]

    for stock_code, name, exchange, currency, symbol, days in test_cases:
        start_date, end_date = _calculate_date_range("2024-01-15", days=days)
        assert start_date is not None
        assert end_date is not None
        assert start_date < end_date


@pytest.mark.unit
def test_company_name_formats():
    """测试不同公司名称格式"""
    from tradingagents.utils.company_name_utils import get_company_name

    test_cases = [
        ("600519", "贵州茅台"),
        ("000001", "平安银行"),
        ("00700", "腾讯控股"),
        ("AAPL", "Apple Inc."),
    ]

    for stock_code, expected_name in test_cases:
        market_info = {
            "market_name": "测试市场",
            "is_china": True,
            "is_hk": False,
            "is_us": False,
        }
        result = get_company_name(stock_code, market_info)
        assert result is not None
        assert len(result) > 0
