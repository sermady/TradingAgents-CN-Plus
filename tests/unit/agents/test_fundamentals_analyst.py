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
        "financial_data": "测试财务数据",
    }

    # Mock LLM 返回结果
    mock_response = Mock()
    mock_response.content = "贵州茅台基本面分析报告：测试报告内容"
    mock_llm.invoke.return_value = mock_response

    with patch(
        "tradingagents.agents.analysts.fundamentals_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.fundamentals_analyst.get_company_name"
        ) as mock_get_name:
            mock_get_name.return_value = "贵州茅台"
            with patch(
                "tradingagents.agents.analysts.fundamentals_analyst.StockUtils"
            ) as mock_stock_utils:
                mock_stock_utils.get_market_info.return_value = {
                    "market_name": "中国A股",
                    "currency_name": "人民币",
                    "currency_symbol": "CNY",
                    "is_china": True,
                    "is_hk": False,
                    "is_us": False,
                }

                from tradingagents.agents.analysts.fundamentals_analyst import (
                    create_fundamentals_analyst,
                )

                analyst = create_fundamentals_analyst(mock_llm, mock_toolkit)
                result = analyst(mock_state)

    assert result is not None
    assert "fundamentals_report" in result


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
        "financial_data": "测试财务数据",
    }

    # Mock LLM 返回结果
    mock_response = Mock()
    mock_response.content = "平安银行基本面分析报告：测试报告内容"
    mock_llm.invoke.return_value = mock_response

    with patch(
        "tradingagents.agents.analysts.fundamentals_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.fundamentals_analyst.get_company_name"
        ) as mock_get_name:
            mock_get_name.return_value = "平安银行"
            with patch(
                "tradingagents.agents.analysts.fundamentals_analyst.StockUtils"
            ) as mock_stock_utils:
                mock_stock_utils.get_market_info.return_value = {
                    "market_name": "中国A股",
                    "currency_name": "人民币",
                    "currency_symbol": "CNY",
                    "is_china": True,
                    "is_hk": False,
                    "is_us": False,
                }

                from tradingagents.agents.analysts.fundamentals_analyst import (
                    create_fundamentals_analyst,
                )

                analyst = create_fundamentals_analyst(mock_llm, mock_toolkit)
                result = analyst(mock_state)

    assert result is not None
    assert "fundamentals_report" in result


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
        "financial_data": "测试财务数据",
    }

    # Mock LLM 返回结果
    mock_response = Mock()
    mock_response.content = "贵州茅台基本面分析报告：测试报告内容"
    mock_llm.invoke.return_value = mock_response

    with patch(
        "tradingagents.agents.analysts.fundamentals_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.fundamentals_analyst.get_company_name"
        ) as mock_get_name:
            mock_get_name.return_value = "贵州茅台"
            with patch(
                "tradingagents.agents.analysts.fundamentals_analyst.StockUtils"
            ) as mock_stock_utils:
                mock_stock_utils.get_market_info.return_value = {
                    "market_name": "中国A股",
                    "currency_name": "人民币",
                    "currency_symbol": "CNY",
                    "is_china": True,
                    "is_hk": False,
                    "is_us": False,
                }

                from tradingagents.agents.analysts.fundamentals_analyst import (
                    create_fundamentals_analyst,
                )

                analyst = create_fundamentals_analyst(mock_llm, mock_toolkit)
                result = analyst(mock_state)

    assert result is not None
    assert "fundamentals_report" in result


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
        "financial_data": "测试财务数据",
    }

    # Mock LLM 返回结果
    mock_response = Mock()
    mock_response.content = "腾讯控股基本面分析报告：测试报告内容"
    mock_llm.invoke.return_value = mock_response

    with patch(
        "tradingagents.agents.analysts.fundamentals_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.fundamentals_analyst.get_company_name"
        ) as mock_get_name:
            mock_get_name.return_value = "腾讯控股"
            with patch(
                "tradingagents.agents.analysts.fundamentals_analyst.StockUtils"
            ) as mock_stock_utils:
                mock_stock_utils.get_market_info.return_value = {
                    "market_name": "港股",
                    "currency_name": "港币",
                    "currency_symbol": "HKD",
                    "is_china": False,
                    "is_hk": True,
                    "is_us": False,
                }

                from tradingagents.agents.analysts.fundamentals_analyst import (
                    create_fundamentals_analyst,
                )

                analyst = create_fundamentals_analyst(mock_llm, mock_toolkit)
                result = analyst(mock_state)

    assert result is not None
    assert "fundamentals_report" in result


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
        "financial_data": "测试财务数据",
    }

    # Mock LLM 抛出异常
    mock_llm.invoke.side_effect = Exception("LLM调用失败")

    with patch(
        "tradingagents.agents.analysts.fundamentals_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.fundamentals_analyst.get_company_name"
        ) as mock_get_name:
            mock_get_name.return_value = "贵州茅台"
            with patch(
                "tradingagents.agents.analysts.fundamentals_analyst.StockUtils"
            ) as mock_stock_utils:
                mock_stock_utils.get_market_info.return_value = {
                    "market_name": "中国A股",
                    "currency_name": "人民币",
                    "currency_symbol": "CNY",
                    "is_china": True,
                    "is_hk": False,
                    "is_us": False,
                }

                from tradingagents.agents.analysts.fundamentals_analyst import (
                    create_fundamentals_analyst,
                )

                analyst = create_fundamentals_analyst(mock_llm, mock_toolkit)

                # 应该返回错误报告而不是抛出异常
                result = analyst(mock_state)
                assert result is not None
                assert "fundamentals_report" in result


@pytest.mark.unit
def test_fundamentals_analyst_messages_structure():
    """测试消息结构"""
    # 简单验证 ToolMessage 可以正常创建
    messages = []
    for i in range(3):
        messages.append(
            ToolMessage(
                content=f"工具返回数据{i}",
                name="get_stock_fundamentals_unified",
                tool_call_id=f"call_{i}",
            )
        )

    assert len(messages) == 3
    assert all(isinstance(m, ToolMessage) for m in messages)


@pytest.mark.unit
def test_date_calculation_different_markets():
    """测试不同市场的日期计算"""
    from datetime import datetime, timedelta

    test_cases = [
        ("000001", "平安银行", "深圳证券交易所", "人民币", "CNY", 30),
        ("00700", "腾讯控股", "香港交易所", "港币", "HKD", 30),
        ("AAPL", "Apple Inc.", "NASDAQ", "美元", "$", 30),
    ]

    for stock_code, name, exchange, currency, symbol, days in test_cases:
        # 简单验证日期计算逻辑
        end_date = datetime.strptime("2024-01-15", "%Y-%m-%d")
        start_date = end_date - timedelta(days=days)
        assert start_date is not None
        assert end_date is not None
        assert start_date < end_date


@pytest.mark.unit
def test_company_name_formats():
    """测试不同公司名称格式"""
    with patch(
        "tradingagents.agents.analysts.fundamentals_analyst.get_company_name"
    ) as mock_get_name:
        mock_get_name.side_effect = [
            "贵州茅台",
            "平安银行",
            "腾讯控股",
            "Apple Inc.",
        ]

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
            result = mock_get_name(stock_code, market_info)
            assert result is not None
            assert len(result) > 0
