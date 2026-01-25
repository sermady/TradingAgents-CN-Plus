# -*- coding: utf-8 -*-
"""
测试新闻分析师功能

测试范围:
- 新闻分析师节点创建
- 工具调用逻辑
- 不同LLM模型的处理
- 强制补救机制
- Google模型特殊处理
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from langchain_core.messages import AIMessage, ToolMessage


@pytest.mark.unit
def test_create_news_analyst():
    """测试创建新闻分析师节点"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    # Act
    with patch(
        "tradingagents.agents.analysts.news_analyst.create_unified_news_tool"
    ) as mock_create_tool:
        mock_create_tool.return_value = Mock(name="get_stock_news_unified")
        with patch(
            "tradingagents.agents.analysts.news_analyst.log_analyst_module"
        ) as mock_log:
            mock_log.return_value = lambda func_name: func_name
            from tradingagents.agents.analysts.news_analyst import create_news_analyst

            news_analyst = create_news_analyst(mock_llm, mock_toolkit)

    # Assert
    assert news_analyst is not None
    assert callable(news_analyst)


@pytest.mark.unit
def test_news_analyst_basic_execution():
    """测试新闻分析师基本执行"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "session_id": "test_session",
    }

    # Act
    with patch(
        "tradingagents.agents.analysts.news_analyst.create_unified_news_tool"
    ) as mock_create_tool:
        mock_news_tool = Mock()
        mock_news_tool.name = "get_stock_news_unified"
        mock_create_tool.return_value = mock_news_tool

        with patch(
            "tradingagents.agents.analysts.news_analyst.log_analyst_module"
        ) as mock_log:
            mock_log.return_value = lambda func_name: func_name
            with patch(
                "tradingagents.agents.analysts.news_analyst.GoogleToolCallHandler"
            ) as mock_google_handler:
                mock_google_handler.is_google_model.return_value = False

                # Mock LLM result
                mock_result = Mock()
                mock_result.tool_calls = []
                mock_result.content = "新闻分析报告：AAPL的财务状况良好..."
                mock_llm.bind_tools.return_value.invoke.return_value = mock_result

                with patch(
                    "tradingagents.agents.analysts.news_analyst.ChatPromptTemplate"
                ) as mock_prompt_template:
                    mock_prompt_instance = Mock()
                    mock_prompt_instance.partial.return_value = mock_prompt_instance
                    mock_prompt_instance.partial.return_value = mock_prompt_instance
                    mock_prompt_instance.partial.return_value = mock_prompt_instance
                    mock_prompt_template.from_messages.return_value = (
                        mock_prompt_instance
                    )
                    mock_prompt_instance.__or__ = Mock(
                        return_value=mock_llm.bind_tools.return_value
                    )
                    mock_prompt_instance.invoke = Mock(return_value=mock_result)

                    from tradingagents.agents.analysts.news_analyst import (
                        create_news_analyst,
                    )

                    news_analyst = create_news_analyst(mock_llm, mock_toolkit)

                    # Execute
                    result = news_analyst(mock_state)

    # Assert
    assert "messages" in result
    assert "news_report" in result
    assert "news_tool_call_count" in result
    assert isinstance(result["messages"][0], AIMessage)
    assert result["news_tool_call_count"] >= 1


@pytest.mark.unit
def test_news_analyst_tool_call_count_limit():
    """测试工具调用次数限制"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "news_tool_call_count": 3,  # 已达到最大限制
        "session_id": "test_session",
    }

    # Act
    with patch(
        "tradingagents.agents.analysts.news_analyst.create_unified_news_tool"
    ) as mock_create_tool:
        mock_news_tool = Mock()
        mock_news_tool.name = "get_stock_news_unified"
        mock_create_tool.return_value = mock_news_tool

        with patch(
            "tradingagents.agents.analysts.news_analyst.log_analyst_module"
        ) as mock_log:
            mock_log.return_value = lambda func_name: func_name
            with patch(
                "tradingagents.agents.analysts.news_analyst.GoogleToolCallHandler"
            ) as mock_google_handler:
                mock_google_handler.is_google_model.return_value = False

                mock_result = Mock()
                mock_result.tool_calls = []
                mock_result.content = "测试报告"
                mock_llm.bind_tools.return_value.invoke.return_value = mock_result

                with patch(
                    "tradingagents.agents.analysts.news_analyst.ChatPromptTemplate"
                ) as mock_prompt_template:
                    mock_prompt_instance = Mock()
                    mock_prompt_instance.partial.return_value = mock_prompt_instance
                    mock_prompt_template.from_messages.return_value = (
                        mock_prompt_instance
                    )
                    mock_prompt_instance.__or__ = Mock(
                        return_value=mock_llm.bind_tools.return_value
                    )
                    mock_prompt_instance.invoke = Mock(return_value=mock_result)

                    from tradingagents.agents.analysts.news_analyst import (
                        create_news_analyst,
                    )

                    news_analyst = create_news_analyst(mock_llm, mock_toolkit)

                    # Execute
                    result = news_analyst(mock_state)

    # Assert
    # 应该递增工具调用计数
    assert result["news_tool_call_count"] == 4


@pytest.mark.unit
def test_news_analyst_with_china_stock():
    """测试中国股票新闻分析"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_state = {
        "messages": [],
        "company_of_interest": "000001",  # A股代码
        "trade_date": "2025-01-15",
        "session_id": "test_session",
    }

    # Act
    with patch(
        "tradingagents.agents.analysts.news_analyst.create_unified_news_tool"
    ) as mock_create_tool:
        mock_news_tool = Mock()
        mock_news_tool.name = "get_stock_news_unified"
        mock_create_tool.return_value = mock_news_tool

        with patch(
            "tradingagents.agents.analysts.news_analyst.log_analyst_module"
        ) as mock_log:
            mock_log.return_value = lambda func_name: func_name
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

            with patch(
                "tradingagents.agents.analysts.news_analyst.get_company_name"
            ) as mock_get_name:
                mock_get_name.return_value = "平安银行"

            with patch(
                "tradingagents.agents.analysts.news_analyst.GoogleToolCallHandler"
            ) as mock_google_handler:
                mock_google_handler.is_google_model.return_value = False

                mock_result = Mock()
                mock_result.tool_calls = []
                mock_result.content = "中国A股新闻分析报告"
                mock_llm.bind_tools.return_value.invoke.return_value = mock_result

                with patch(
                    "tradingagents.agents.analysts.news_analyst.ChatPromptTemplate"
                ) as mock_prompt_template:
                    mock_prompt_instance = Mock()
                    mock_prompt_instance.partial.return_value = mock_prompt_instance
                    mock_prompt_template.from_messages.return_value = (
                        mock_prompt_instance
                    )
                    mock_prompt_instance.__or__ = Mock(
                        return_value=mock_llm.bind_tools.return_value
                    )
                    mock_prompt_instance.invoke = Mock(return_value=mock_result)

                    from tradingagents.agents.analysts.news_analyst import (
                        create_news_analyst,
                    )

                    news_analyst = create_news_analyst(mock_llm, mock_toolkit)

                    # Execute
                    result = news_analyst(mock_state)

    # Assert
    assert "news_report" in result
    assert len(result["news_report"]) > 0
    assert "平安银行" in result["news_report"] or "000001" in result["news_report"]


@pytest.mark.unit
def test_news_analyst_force_remedy_mechanism():
    """测试强制补救机制"""
    # Arrange
    mock_llm = Mock()
    mock_llm.__class__.__name__ = "ChatOpenAI"
    mock_toolkit = Mock()
    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "session_id": "test_session",
    }

    # Act
    with patch(
        "tradingagents.agents.analysts.news_analyst.create_unified_news_tool"
    ) as mock_create_tool:
        mock_news_tool = Mock()
        mock_news_tool.name = "get_stock_news_unified"
        mock_create_tool.return_value = mock_news_tool

        with patch(
            "tradingagents.agents.analysts.news_analyst.log_analyst_module"
        ) as mock_log:
            mock_log.return_value = lambda func_name: func_name

            with patch(
                "tradingagents.agents.analysts.news_analyst.GoogleToolCallHandler"
            ) as mock_google_handler:
                mock_google_handler.is_google_model.return_value = False

                # 模拟LLM没有调用工具
                mock_result = Mock()
                mock_result.tool_calls = []  # 没有工具调用
                mock_result.content = "我没有调用任何工具"  # 无效响应
                mock_llm.bind_tools.return_value.invoke.return_value = mock_result

                # 模拟强制补救成功
                mock_forced_news = "## 最新新闻\n\nAAPL发布了2024年财报..."
                mock_news_tool.return_value = mock_forced_news

                mock_forced_result = Mock()
                mock_forced_result.content = "基于真实新闻数据的详细分析报告..."
                mock_llm.invoke.return_value = mock_forced_result

                with patch(
                    "tradingagents.agents.analysts.news_analyst.ChatPromptTemplate"
                ) as mock_prompt_template:
                    mock_prompt_instance = Mock()
                    mock_prompt_instance.partial.return_value = mock_prompt_instance
                    mock_prompt_template.from_messages.return_value = (
                        mock_prompt_instance
                    )
                    mock_prompt_instance.__or__ = Mock(
                        return_value=mock_llm.bind_tools.return_value
                    )
                    mock_prompt_instance.invoke = Mock(return_value=mock_result)

                    from tradingagents.agents.analysts.news_analyst import (
                        create_news_analyst,
                    )

                    news_analyst = create_news_analyst(mock_llm, mock_toolkit)

                    # Execute
                    result = news_analyst(mock_state)

    # Assert
    # 应该触发强制补救机制
    assert "news_report" in result
    # 强制补救后应该有分析报告
    assert len(result["news_report"]) > 0


@pytest.mark.unit
def test_news_analyst_with_google_model():
    """测试Google模型特殊处理"""
    # Arrange
    mock_llm = Mock()
    mock_llm.__class__.__name__ = "ChatGoogleGenerativeAI"
    mock_toolkit = Mock()
    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "session_id": "test_session",
    }

    # Act
    with patch(
        "tradingagents.agents.analysts.news_analyst.create_unified_news_tool"
    ) as mock_create_tool:
        mock_news_tool = Mock()
        mock_news_tool.name = "get_stock_news_unified"
        mock_create_tool.return_value = mock_news_tool

        with patch(
            "tradingagents.agents.analysts.news_analyst.log_analyst_module"
        ) as mock_log:
            mock_log.return_value = lambda func_name: func_name
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

            with patch(
                "tradingagents.agents.analysts.news_analyst.get_company_name"
            ) as mock_get_name:
                mock_get_name.return_value = "Apple Inc."

            with patch(
                "tradingagents.agents.analysts.news_analyst.GoogleToolCallHandler"
            ) as mock_google_handler:
                mock_google_handler.is_google_model.return_value = True

                mock_report = "Google模型生成的新闻分析报告"
                mock_messages = [Mock()]
                mock_google_handler.handle_google_tool_calls.return_value = (
                    mock_report,
                    mock_messages,
                )

                mock_result = Mock()
                mock_result.tool_calls = []
                mock_llm.bind_tools.return_value.invoke.return_value = mock_result

                with patch(
                    "tradingagents.agents.analysts.news_analyst.ChatPromptTemplate"
                ) as mock_prompt_template:
                    mock_prompt_instance = Mock()
                    mock_prompt_instance.partial.return_value = mock_prompt_instance
                    mock_prompt_template.from_messages.return_value = (
                        mock_prompt_instance
                    )
                    mock_prompt_instance.__or__ = Mock(
                        return_value=mock_llm.bind_tools.return_value
                    )
                    mock_prompt_instance.invoke = Mock(return_value=mock_result)

                    from tradingagents.agents.analysts.news_analyst import (
                        create_news_analyst,
                    )

                    news_analyst = create_news_analyst(mock_llm, mock_toolkit)

                    # Execute
                    result = news_analyst(mock_state)

    # Assert
    assert "news_report" in result
    assert mock_google_handler.handle_google_tool_calls.called
    assert result["news_report"] == mock_report


@pytest.mark.unit
def test_news_analyst_preprocessing_mode():
    """测试DashScope/DeepSeek模型的预处理模式"""
    # Arrange
    mock_llm = Mock()
    mock_llm.__class__.__name__ = "ChatDashScope"
    mock_llm.model_name = "qwen-max"
    mock_toolkit = Mock()
    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "session_id": "test_session",
    }

    # Act
    with patch(
        "tradingagents.agents.analysts.news_analyst.create_unified_news_tool"
    ) as mock_create_tool:
        mock_news_tool = Mock()
        mock_news_tool.name = "get_stock_news_unified"
        mock_pre_fetched_news = "## 最新新闻数据\n\nAAPL发布新产品..."
        mock_create_tool.return_value = mock_news_tool
        mock_news_tool.return_value = mock_pre_fetched_news

        with patch(
            "tradingagents.agents.analysts.news_analyst.log_analyst_module"
        ) as mock_log:
            mock_log.return_value = lambda func_name: func_name
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

            with patch(
                "tradingagents.agents.analysts.news_analyst.get_company_name"
            ) as mock_get_name:
                mock_get_name.return_value = "Apple Inc."

            mock_preprocessed_result = Mock()
            mock_preprocessed_result.content = "基于预获取新闻数据的分析报告"
            mock_llm.invoke.return_value = mock_preprocessed_result

            from tradingagents.agents.analysts.news_analyst import create_news_analyst

            news_analyst = create_news_analyst(mock_llm, mock_toolkit)

            # Execute
            result = news_analyst(mock_state)

    # Assert
    # 应该使用预处理模式
    assert "news_report" in result
    assert "messages" in result
    # 预处理模式应该直接返回结果,不继续调用工具
    assert len(result["news_report"]) > 0
    # 工具调用计数应该为1（预处理也算一次调用）
    assert result["news_tool_call_count"] == 1


@pytest.mark.unit
def test_news_analyst_hk_stock():
    """测试港股新闻分析"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_state = {
        "messages": [],
        "company_of_interest": "0700.HK",  # 港股代码
        "trade_date": "2025-01-15",
        "session_id": "test_session",
    }

    # Act
    with patch(
        "tradingagents.agents.analysts.news_analyst.create_unified_news_tool"
    ) as mock_create_tool:
        mock_news_tool = Mock()
        mock_news_tool.name = "get_stock_news_unified"
        mock_create_tool.return_value = mock_news_tool

        with patch(
            "tradingagents.agents.analysts.news_analyst.log_analyst_module"
        ) as mock_log:
            mock_log.return_value = lambda func_name: func_name
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

            with patch(
                "tradingagents.agents.analysts.news_analyst.get_company_name"
            ) as mock_get_name:
                mock_get_name.return_value = "腾讯控股"

            with patch(
                "tradingagents.agents.analysts.news_analyst.GoogleToolCallHandler"
            ) as mock_google_handler:
                mock_google_handler.is_google_model.return_value = False

                mock_result = Mock()
                mock_result.tool_calls = []
                mock_result.content = "港股新闻分析报告"
                mock_llm.bind_tools.return_value.invoke.return_value = mock_result

                with patch(
                    "tradingagents.agents.analysts.news_analyst.ChatPromptTemplate"
                ) as mock_prompt_template:
                    mock_prompt_instance = Mock()
                    mock_prompt_instance.partial.return_value = mock_prompt_instance
                    mock_prompt_template.from_messages.return_value = (
                        mock_prompt_instance
                    )
                    mock_prompt_instance.__or__ = Mock(
                        return_value=mock_llm.bind_tools.return_value
                    )
                    mock_prompt_instance.invoke = Mock(return_value=mock_result)

                    from tradingagents.agents.analysts.news_analyst import (
                        create_news_analyst,
                    )

                    news_analyst = create_news_analyst(mock_llm, mock_toolkit)

                    # Execute
                    result = news_analyst(mock_state)

    # Assert
    assert "news_report" in result
    assert "腾讯控股" in result["news_report"] or "0700.HK" in result["news_report"]


@pytest.mark.unit
def test_news_analyst_error_handling():
    """测试错误处理"""
    # Arrange
    mock_llm = Mock()
    mock_llm.__class__.__name__ = "ChatOpenAI"
    mock_toolkit = Mock()
    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "session_id": "test_session",
    }

    # Act
    with patch(
        "tradingagents.agents.analysts.news_analyst.create_unified_news_tool"
    ) as mock_create_tool:
        mock_news_tool = Mock()
        mock_news_tool.name = "get_stock_news_unified"
        mock_create_tool.return_value = mock_news_tool

        with patch(
            "tradingagents.agents.analysts.news_analyst.log_analyst_module"
        ) as mock_log:
            mock_log.return_value = lambda func_name: func_name
            with patch(
                "tradingagents.agents.analysts.news_analyst.GoogleToolCallHandler"
            ) as mock_google_handler:
                mock_google_handler.is_google_model.return_value = False

                # 模拟LLM调用失败
                mock_llm.bind_tools.return_value.invoke.side_effect = Exception(
                    "LLM调用失败"
                )

                # 模拟强制补救也失败
                mock_news_tool.side_effect = Exception("新闻工具调用失败")

                with patch(
                    "tradingagents.agents.analysts.news_analyst.ChatPromptTemplate"
                ) as mock_prompt_template:
                    mock_prompt_instance = Mock()
                    mock_prompt_instance.partial.return_value = mock_prompt_instance
                    mock_prompt_template.from_messages.return_value = (
                        mock_prompt_instance
                    )
                    mock_prompt_instance.__or__ = Mock(
                        return_value=mock_llm.bind_tools.return_value
                    )
                    mock_prompt_instance.invoke = Mock(return_value=Mock())

                    from tradingagents.agents.analysts.news_analyst import (
                        create_news_analyst,
                    )

                    news_analyst = create_news_analyst(mock_llm, mock_toolkit)

                    # Execute & Assert - 应该抛出异常
                    with pytest.raises(Exception):
                        result = news_analyst(mock_state)


@pytest.mark.unit
def test_news_analyst_messages_structure():
    """测试返回消息结构"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": "2025-01-15",
        "session_id": "test_session",
    }

    # Act
    with patch(
        "tradingagents.agents.analysts.news_analyst.create_unified_news_tool"
    ) as mock_create_tool:
        mock_news_tool = Mock()
        mock_news_tool.name = "get_stock_news_unified"
        mock_create_tool.return_value = mock_news_tool

        with patch(
            "tradingagents.agents.analysts.news_analyst.log_analyst_module"
        ) as mock_log:
            mock_log.return_value = lambda func_name: func_name
            with patch(
                "tradingagents.agents.analysts.news_analyst.GoogleToolCallHandler"
            ) as mock_google_handler:
                mock_google_handler.is_google_model.return_value = False

                mock_result = Mock()
                mock_result.tool_calls = []
                mock_result.content = "新闻分析报告"
                mock_llm.bind_tools.return_value.invoke.return_value = mock_result

                with patch(
                    "tradingagents.agents.analysts.news_analyst.ChatPromptTemplate"
                ) as mock_prompt_template:
                    mock_prompt_instance = Mock()
                    mock_prompt_instance.partial.return_value = mock_prompt_instance
                    mock_prompt_template.from_messages.return_value = (
                        mock_prompt_instance
                    )
                    mock_prompt_instance.__or__ = Mock(
                        return_value=mock_llm.bind_tools.return_value
                    )
                    mock_prompt_instance.invoke = Mock(return_value=mock_result)

                    from tradingagents.agents.analysts.news_analyst import (
                        create_news_analyst,
                    )

                    news_analyst = create_news_analyst(mock_llm, mock_toolkit)

                    # Execute
                    result = news_analyst(mock_state)

    # Assert
    assert "messages" in result
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], AIMessage)
    # 清洁消息不应该有tool_calls
    assert (
        not hasattr(result["messages"][0], "tool_calls")
        or len(result["messages"][0].tool_calls) == 0
    )


@pytest.mark.unit
def test_news_analyst_date_handling():
    """测试日期处理"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    test_date = "2025-01-15"
    mock_state = {
        "messages": [],
        "company_of_interest": "AAPL",
        "trade_date": test_date,
        "session_id": "test_session",
    }

    # Act
    with patch(
        "tradingagents.agents.analysts.news_analyst.create_unified_news_tool"
    ) as mock_create_tool:
        mock_news_tool = Mock()
        mock_news_tool.name = "get_stock_news_unified"

        # 验证创建工具时传递了正确的日期
        def verify_tool(toolkit, analysis_date):
            assert analysis_date == test_date, "应该使用state中的trade_date作为分析日期"
            return mock_news_tool

        mock_create_tool.side_effect = verify_tool

        with patch(
            "tradingagents.agents.analysts.news_analyst.log_analyst_module"
        ) as mock_log:
            mock_log.return_value = lambda func_name: func_name
            with patch(
                "tradingagents.agents.analysts.news_analyst.GoogleToolCallHandler"
            ) as mock_google_handler:
                mock_google_handler.is_google_model.return_value = False

                mock_result = Mock()
                mock_result.tool_calls = []
                mock_result.content = "新闻分析报告"
                mock_llm.bind_tools.return_value.invoke.return_value = mock_result

                with patch(
                    "tradingagents.agents.analysts.news_analyst.ChatPromptTemplate"
                ) as mock_prompt_template:
                    mock_prompt_instance = Mock()
                    mock_prompt_instance.partial.return_value = mock_prompt_instance
                    mock_prompt_template.from_messages.return_value = (
                        mock_prompt_instance
                    )
                    mock_prompt_instance.__or__ = Mock(
                        return_value=mock_llm.bind_tools.return_value
                    )
                    mock_prompt_instance.invoke = Mock(return_value=mock_result)

                    from tradingagents.agents.analysts.news_analyst import (
                        create_news_analyst,
                    )

                    news_analyst = create_news_analyst(mock_llm, mock_toolkit)

                    # Execute
                    result = news_analyst(mock_state)

    # Assert
    assert "news_report" in result
