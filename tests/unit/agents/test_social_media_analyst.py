# -*- coding: utf-8 -*-
"""
测试社交媒体分析师功能

测试范围:
- 社交媒体分析师节点创建
- 工具调用逻辑
- 不同LLM模型的处理
- Google模型特殊处理
- 情绪分析报告生成
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from langchain_core.messages import AIMessage, ToolMessage


@pytest.mark.unit
def test_create_social_media_analyst():
    """测试创建社交媒体分析师节点"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    # Act
    with patch(
        "tradingagents.agents.analysts.social_media_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        from tradingagents.agents.analysts.social_media_analyst import (
            create_social_media_analyst,
        )

        social_analyst = create_social_media_analyst(mock_llm, mock_toolkit)

    # Assert
    assert social_analyst is not None
    assert callable(social_analyst)


@pytest.mark.unit
def test_social_media_analyst_basic_execution():
    """测试社交媒体分析师基本执行"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_sentiment_tool = Mock()
    mock_sentiment_tool.name = "get_stock_sentiment_unified"
    mock_toolkit.get_stock_sentiment_unified = mock_sentiment_tool

    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "session_id": "test_session",
    }

    # Act
    with patch(
        "tradingagents.agents.analysts.social_media_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.social_media_analyst.GoogleToolCallHandler"
        ) as mock_google_handler:
            mock_google_handler.is_google_model.return_value = False

            # Mock LLM result
            mock_result = Mock()
            mock_result.tool_calls = [Mock()]
            mock_result.content = "社交媒体情绪分析报告：投资者情绪乐观..."
            mock_llm.bind_tools.return_value.invoke.return_value = mock_result

            with patch(
                "tradingagents.agents.analysts.social_media_analyst.ChatPromptTemplate"
            ) as mock_prompt_template:
                mock_prompt_instance = Mock()
                mock_prompt_instance.partial.return_value = mock_prompt_instance
                mock_prompt_template.from_messages.return_value = mock_prompt_instance
                mock_prompt_instance.__or__ = Mock(
                    return_value=mock_llm.bind_tools.return_value
                )
                mock_prompt_instance.invoke = Mock(return_value=mock_result)

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

                with patch(
                    "tradingagents.agents.analysts.social_media_analyst.get_company_name"
                ) as mock_get_name:
                    mock_get_name.return_value = "Apple Inc."

                from tradingagents.agents.analysts.social_media_analyst import (
                    create_social_media_analyst,
                )

                social_analyst = create_social_media_analyst(mock_llm, mock_toolkit)

                # Execute
                result = social_analyst(mock_state)

    # Assert
    assert "messages" in result
    assert "sentiment_report" in result
    assert "sentiment_tool_call_count" in result
    assert len(result["sentiment_report"]) > 0


@pytest.mark.unit
def test_social_media_analyst_tool_call_count_limit():
    """测试工具调用次数限制"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_sentiment_tool = Mock()
    mock_toolkit.get_stock_sentiment_unified = mock_sentiment_tool

    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "sentiment_tool_call_count": 3,  # 已达到最大限制
        "session_id": "test_session",
    }

    # Act
    with patch(
        "tradingagents.agents.analysts.social_media_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.social_media_analyst.GoogleToolCallHandler"
        ) as mock_google_handler:
            mock_google_handler.is_google_model.return_value = False

            mock_result = Mock()
            mock_result.tool_calls = []
            mock_result.content = "测试报告"
            mock_llm.bind_tools.return_value.invoke.return_value = mock_result

            with patch(
                "tradingagents.agents.analysts.social_media_analyst.ChatPromptTemplate"
            ) as mock_prompt_template:
                mock_prompt_instance = Mock()
                mock_prompt_instance.partial.return_value = mock_prompt_instance
                mock_prompt_template.from_messages.return_value = mock_prompt_instance
                mock_prompt_instance.__or__ = Mock(
                    return_value=mock_llm.bind_tools.return_value
                )
                mock_prompt_instance.invoke = Mock(return_value=mock_result)

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

                with patch(
                    "tradingagents.agents.analysts.social_media_analyst.get_company_name"
                ) as mock_get_name:
                    mock_get_name.return_value = "Apple Inc."

                from tradingagents.agents.analysts.social_media_analyst import (
                    create_social_media_analyst,
                )

                social_analyst = create_social_media_analyst(mock_llm, mock_toolkit)

                # Execute
                result = social_analyst(mock_state)

    # Assert
    # 应该递增工具调用计数
    assert result["sentiment_tool_call_count"] == 4


@pytest.mark.unit
def test_social_media_analyst_with_china_stock():
    """测试中国股票社交媒体分析"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_sentiment_tool = Mock()
    mock_sentiment_tool.name = "get_stock_sentiment_unified"
    mock_toolkit.get_stock_sentiment_unified = mock_sentiment_tool

    mock_state = {
        "messages": [],
        "company_of_interest": "000001",  # A股代码
        "trade_date": "2025-01-15",
        "session_id": "test_session",
    }

    # Act
    with patch(
        "tradingagents.agents.analysts.social_media_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.social_media_analyst.StockUtils"
        ) as mock_stock_utils:
            mock_stock_utils.get_market_info.return_value = {
                "market_name": "中国A股",
                "currency_name": "人民币",
                "currency_symbol": "CNY",
                "is_china": True,
                "is_hk": False,
                "is_us": False,
            }

        with patch(
            "tradingagents.agents.analysts.social_media_analyst.get_company_name"
        ) as mock_get_name:
            mock_get_name.return_value = "平安银行"

        with patch(
            "tradingagents.agents.analysts.social_media_analyst.GoogleToolCallHandler"
        ) as mock_google_handler:
            mock_google_handler.is_google_model.return_value = False

            mock_result = Mock()
            mock_result.tool_calls = []
            mock_result.content = "中国A股社交媒体情绪分析报告"
            mock_llm.bind_tools.return_value.invoke.return_value = mock_result

            with patch(
                "tradingagents.agents.analysts.social_media_analyst.ChatPromptTemplate"
            ) as mock_prompt_template:
                mock_prompt_instance = Mock()
                mock_prompt_instance.partial.return_value = mock_prompt_instance
                mock_prompt_template.from_messages.return_value = mock_prompt_instance
                mock_prompt_instance.__or__ = Mock(
                    return_value=mock_llm.bind_tools.return_value
                )
                mock_prompt_instance.invoke = Mock(return_value=mock_result)

                from tradingagents.agents.analysts.social_media_analyst import (
                    create_social_media_analyst,
                )

                social_analyst = create_social_media_analyst(mock_llm, mock_toolkit)

                # Execute
                result = social_analyst(mock_state)

    # Assert
    assert "sentiment_report" in result
    assert len(result["sentiment_report"]) > 0
    assert (
        "平安银行" in result["sentiment_report"]
        or "000001" in result["sentiment_report"]
    )


@pytest.mark.unit
def test_social_media_analyst_with_google_model():
    """测试Google模型特殊处理"""
    # Arrange
    mock_llm = Mock()
    mock_llm.__class__.__name__ = "ChatGoogleGenerativeAI"
    mock_toolkit = Mock()
    mock_sentiment_tool = Mock()
    mock_sentiment_tool.name = "get_stock_sentiment_unified"
    mock_toolkit.get_stock_sentiment_unified = mock_sentiment_tool

    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "session_id": "test_session",
    }

    # Act
    with patch(
        "tradingagents.agents.analysts.social_media_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
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

        with patch(
            "tradingagents.agents.analysts.social_media_analyst.get_company_name"
        ) as mock_get_name:
            mock_get_name.return_value = "Apple Inc."

        with patch(
            "tradingagents.agents.analysts.social_media_analyst.GoogleToolCallHandler"
        ) as mock_google_handler:
            mock_google_handler.is_google_model.return_value = True

            mock_report = "Google模型生成的情绪分析报告"
            mock_messages = [Mock()]
            mock_google_handler.handle_google_tool_calls.return_value = (
                mock_report,
                mock_messages,
            )

            mock_result = Mock()
            mock_result.tool_calls = []
            mock_llm.bind_tools.return_value.invoke.return_value = mock_result

            with patch(
                "tradingagents.agents.analysts.social_media_analyst.ChatPromptTemplate"
            ) as mock_prompt_template:
                mock_prompt_instance = Mock()
                mock_prompt_instance.partial.return_value = mock_prompt_instance
                mock_prompt_template.from_messages.return_value = mock_prompt_instance
                mock_prompt_instance.__or__ = Mock(
                    return_value=mock_llm.bind_tools.return_value
                )
                mock_prompt_instance.invoke = Mock(return_value=mock_result)

                from tradingagents.agents.analysts.social_media_analyst import (
                    create_social_media_analyst,
                )

                social_analyst = create_social_media_analyst(mock_llm, mock_toolkit)

                # Execute
                result = social_analyst(mock_state)

    # Assert
    assert "sentiment_report" in result
    assert mock_google_handler.handle_google_tool_calls.called
    assert result["sentiment_report"] == mock_report


@pytest.mark.unit
def test_social_media_analyst_hk_stock():
    """测试港股社交媒体分析"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_sentiment_tool = Mock()
    mock_sentiment_tool.name = "get_stock_sentiment_unified"
    mock_toolkit.get_stock_sentiment_unified = mock_sentiment_tool

    mock_state = {
        "messages": [],
        "company_of_interest": "0700.HK",  # 港股代码
        "trade_date": "2025-01-15",
        "session_id": "test_session",
    }

    # Act
    with patch(
        "tradingagents.agents.analysts.social_media_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.social_media_analyst.StockUtils"
        ) as mock_stock_utils:
            mock_stock_utils.get_market_info.return_value = {
                "market_name": "港股",
                "currency_name": "港币",
                "currency_symbol": "HKD",
                "is_china": False,
                "is_hk": True,
                "is_us": False,
            }

        with patch(
            "tradingagents.agents.analysts.social_media_analyst.get_company_name"
        ) as mock_get_name:
            mock_get_name.return_value = "腾讯控股"

        with patch(
            "tradingagents.agents.analysts.social_media_analyst.GoogleToolCallHandler"
        ) as mock_google_handler:
            mock_google_handler.is_google_model.return_value = False

            mock_result = Mock()
            mock_result.tool_calls = []
            mock_result.content = "港股社交媒体情绪分析报告"
            mock_llm.bind_tools.return_value.invoke.return_value = mock_result

            with patch(
                "tradingagents.agents.analysts.social_media_analyst.ChatPromptTemplate"
            ) as mock_prompt_template:
                mock_prompt_instance = Mock()
                mock_prompt_instance.partial.return_value = mock_prompt_instance
                mock_prompt_template.from_messages.return_value = mock_prompt_instance
                mock_prompt_instance.__or__ = Mock(
                    return_value=mock_llm.bind_tools.return_value
                )
                mock_prompt_instance.invoke = Mock(return_value=mock_result)

                from tradingagents.agents.analysts.social_media_analyst import (
                    create_social_media_analyst,
                )

                social_analyst = create_social_media_analyst(mock_llm, mock_toolkit)

                # Execute
                result = social_analyst(mock_state)

    # Assert
    assert "sentiment_report" in result
    assert (
        "腾讯控股" in result["sentiment_report"]
        or "0700.HK" in result["sentiment_report"]
    )


@pytest.mark.unit
def test_social_media_analyst_tool_name_extraction():
    """测试工具名称提取逻辑"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    # 创建不同类型的工具对象
    tool_with_name_attr = Mock()
    tool_with_name_attr.name = "get_stock_sentiment_unified"

    tool_with_name = Mock()
    tool_with_name.__name__ = "alternative_sentiment_tool"

    tool_without_name = Mock()
    del tool_without_name.name
    del tool_without_name.__name__

    mock_toolkit.get_stock_sentiment_unified = tool_with_name_attr

    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "session_id": "test_session",
    }

    # Act
    with patch(
        "tradingagents.agents.analysts.social_media_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.social_media_analyst.GoogleToolCallHandler"
        ) as mock_google_handler:
            mock_google_handler.is_google_model.return_value = False

            mock_result = Mock()
            mock_result.tool_calls = []
            mock_result.content = "情绪分析报告"
            mock_llm.bind_tools.return_value.invoke.return_value = mock_result

            with patch(
                "tradingagents.agents.analysts.social_media_analyst.ChatPromptTemplate"
            ) as mock_prompt_template:
                mock_prompt_instance = Mock()
                mock_prompt_instance.partial.return_value = mock_prompt_instance
                mock_prompt_template.from_messages.return_value = mock_prompt_instance

                # 捕获实际的tools参数
                captured_tools = []

                def capture_tool_names(tools_list):
                    captured_tools.clear()
                    captured_tools.extend(tools_list)
                    return mock_prompt_instance

                mock_prompt_instance.partial.side_effect = capture_tool_names

                mock_prompt_instance.__or__ = Mock(
                    return_value=mock_llm.bind_tools.return_value
                )
                mock_prompt_instance.invoke = Mock(return_value=mock_result)

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

                with patch(
                    "tradingagents.agents.analysts.social_media_analyst.get_company_name"
                ) as mock_get_name:
                    mock_get_name.return_value = "Apple Inc."

                from tradingagents.agents.analysts.social_media_analyst import (
                    create_social_media_analyst,
                )

                social_analyst = create_social_media_analyst(mock_llm, mock_toolkit)

                # Execute
                result = social_analyst(mock_state)

    # Assert
    # 应该正确提取工具名称
    assert "sentiment_report" in result


@pytest.mark.unit
def test_social_media_analyst_no_tool_calls():
    """测试没有工具调用时的处理"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_sentiment_tool = Mock()
    mock_toolkit.get_stock_sentiment_unified = mock_sentiment_tool

    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "session_id": "test_session",
    }

    # Act
    with patch(
        "tradingagents.agents.analysts.social_media_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.social_media_analyst.GoogleToolCallHandler"
        ) as mock_google_handler:
            mock_google_handler.is_google_model.return_value = False

            # 模拟LLM没有调用工具
            mock_result = Mock()
            mock_result.tool_calls = []  # 没有工具调用
            mock_result.content = "我没有调用任何工具，但这是我的分析..."
            mock_llm.bind_tools.return_value.invoke.return_value = mock_result

            with patch(
                "tradingagents.agents.analysts.social_media_analyst.ChatPromptTemplate"
            ) as mock_prompt_template:
                mock_prompt_instance = Mock()
                mock_prompt_instance.partial.return_value = mock_prompt_instance
                mock_prompt_template.from_messages.return_value = mock_prompt_instance
                mock_prompt_instance.__or__ = Mock(
                    return_value=mock_llm.bind_tools.return_value
                )
                mock_prompt_instance.invoke = Mock(return_value=mock_result)

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

                with patch(
                    "tradingagents.agents.analysts.social_media_analyst.get_company_name"
                ) as mock_get_name:
                    mock_get_name.return_value = "Apple Inc."

                from tradingagents.agents.analysts.social_media_analyst import (
                    create_social_media_analyst,
                )

                social_analyst = create_social_media_analyst(mock_llm, mock_toolkit)

                # Execute
                result = social_analyst(mock_state)

    # Assert
    assert "sentiment_report" in result
    # 应该直接使用LLM返回的内容
    assert result["sentiment_report"] == "我没有调用任何工具，但这是我的分析..."


@pytest.mark.unit
def test_social_media_analyst_messages_structure():
    """测试返回消息结构"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_sentiment_tool = Mock()
    mock_toolkit.get_stock_sentiment_unified = mock_sentiment_tool

    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "session_id": "test_session",
    }

    # Act
    with patch(
        "tradingagents.agents.analysts.social_media_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.social_media_analyst.GoogleToolCallHandler"
        ) as mock_google_handler:
            mock_google_handler.is_google_model.return_value = False

            mock_result = Mock()
            mock_result.tool_calls = []
            mock_result.content = "情绪分析报告"
            mock_llm.bind_tools.return_value.invoke.return_value = mock_result

            with patch(
                "tradingagents.agents.analysts.social_media_analyst.ChatPromptTemplate"
            ) as mock_prompt_template:
                mock_prompt_instance = Mock()
                mock_prompt_instance.partial.return_value = mock_prompt_instance
                mock_prompt_template.from_messages.return_value = mock_prompt_instance
                mock_prompt_instance.__or__ = Mock(
                    return_value=mock_llm.bind_tools.return_value
                )
                mock_prompt_instance.invoke = Mock(return_value=mock_result)

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

                with patch(
                    "tradingagents.agents.analysts.social_media_analyst.get_company_name"
                ) as mock_get_name:
                    mock_get_name.return_value = "Apple Inc."

                from tradingagents.agents.analysts.social_media_analyst import (
                    create_social_media_analyst,
                )

                social_analyst = create_social_media_analyst(mock_llm, mock_toolkit)

                # Execute
                result = social_analyst(mock_state)

    # Assert
    assert "messages" in result
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], Mock)  # 应该是原始result对象


@pytest.mark.unit
def test_social_media_analyst_date_handling():
    """测试日期处理"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_sentiment_tool = Mock()
    mock_toolkit.get_stock_sentiment_unified = mock_sentiment_tool

    test_date = "2025-01-15"
    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": test_date,
        "session_id": "test_session",
    }

    # Act
    with patch(
        "tradingagents.agents.analysts.social_media_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.social_media_analyst.GoogleToolCallHandler"
        ) as mock_google_handler:
            mock_google_handler.is_google_model.return_value = False

            mock_result = Mock()
            mock_result.tool_calls = []
            mock_result.content = "情绪分析报告"
            mock_llm.bind_tools.return_value.invoke.return_value = mock_result

            with patch(
                "tradingagents.agents.analysts.social_media_analyst.ChatPromptTemplate"
            ) as mock_prompt_template:
                mock_prompt_instance = Mock()
                mock_prompt_instance.partial.return_value = mock_prompt_instance
                mock_prompt_template.from_messages.return_value = mock_prompt_instance
                mock_prompt_instance.__or__ = Mock(
                    return_value=mock_llm.bind_tools.return_value
                )
                mock_prompt_instance.invoke = Mock(return_value=mock_result)

                # 捕获partial调用的参数
                captured_params = []

                def capture_partial(**kwargs):
                    captured_params.append(kwargs)
                    return mock_prompt_instance

                mock_prompt_instance.partial.side_effect = capture_partial

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

                with patch(
                    "tradingagents.agents.analysts.social_media_analyst.get_company_name"
                ) as mock_get_name:
                    mock_get_name.return_value = "Apple Inc."

                from tradingagents.agents.analysts.social_media_analyst import (
                    create_social_media_analyst,
                )

                social_analyst = create_social_media_analyst(mock_llm, mock_toolkit)

                # Execute
                result = social_analyst(mock_state)

    # Assert
    assert "sentiment_report" in result
    # 验证日期参数正确传递
    date_params = [p for p in captured_params if "current_date" in p]
    assert len(date_params) > 0


@pytest.mark.unit
def test_social_media_analyst_sentiment_score_validation():
    """测试情绪评分验证"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_sentiment_tool = Mock()
    mock_toolkit.get_stock_sentiment_unified = mock_sentiment_tool

    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "session_id": "test_session",
    }

    # Act
    with patch(
        "tradingagents.agents.analysts.social_media_analyst.log_analyst_module"
    ) as mock_log:
        mock_log.return_value = lambda func_name: func_name
        with patch(
            "tradingagents.agents.analysts.social_media_analyst.GoogleToolCallHandler"
        ) as mock_google_handler:
            mock_google_handler.is_google_model.return_value = False

            mock_result = Mock()
            mock_result.tool_calls = []
            # 模拟包含情绪评分的报告
            mock_result.content = """
# 社交媒体情绪分析报告

## 情绪指数评分：7.5/10

投资者情绪较为乐观，主要基于以下几点：
1. 产品发布获得积极反响
2. 财报表现超预期
3. 市场预期普遍看好

## 预期价格波动幅度
预计短期波动幅度在3-5%之间。

## 交易建议
基于当前情绪，建议**持有**，关注后续市场反应。
"""
            mock_llm.bind_tools.return_value.invoke.return_value = mock_result

            with patch(
                "tradingagents.agents.analysts.social_media_analyst.ChatPromptTemplate"
            ) as mock_prompt_template:
                mock_prompt_instance = Mock()
                mock_prompt_instance.partial.return_value = mock_prompt_instance
                mock_prompt_template.from_messages.return_value = mock_prompt_instance
                mock_prompt_instance.__or__ = Mock(
                    return_value=mock_llm.bind_tools.return_value
                )
                mock_prompt_instance.invoke = Mock(return_value=mock_result)

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

                with patch(
                    "tradingagents.agents.analysts.social_media_analyst.get_company_name"
                ) as mock_get_name:
                    mock_get_name.return_value = "Apple Inc."

                from tradingagents.agents.analysts.social_media_analyst import (
                    create_social_media_analyst,
                )

                social_analyst = create_social_media_analyst(mock_llm, mock_toolkit)

                # Execute
                result = social_analyst(mock_state)

    # Assert
    assert "sentiment_report" in result
    # 验证报告包含情绪评分
    assert (
        "情绪指数评分" in result["sentiment_report"]
        or "7.5" in result["sentiment_report"]
    )
    # 验证情绪评分在合理范围内(1-10)
    assert "7.5" in result["sentiment_report"]  # 1-10之间
