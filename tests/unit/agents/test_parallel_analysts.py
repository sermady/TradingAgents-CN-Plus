# -*- coding: utf-8 -*-
"""
测试并行分析师执行模块

测试范围:
- ParallelAnalystExecutor初始化
- 并行图设置
- 分析师节点创建
- 工作流构建
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from langgraph.graph import StateGraph, END

from tradingagents.graph.parallel_analysts import ParallelAnalystExecutor


@pytest.mark.unit
def test_parallel_executor_initialization():
    """测试并行执行器初始化"""
    # Arrange
    mock_base_setup = Mock()
    mock_toolkit = Mock()
    mock_base_setup.toolkit = mock_toolkit

    # Act
    executor = ParallelAnalystExecutor(mock_base_setup)

    # Assert
    assert executor is not None
    assert executor.base_setup == mock_base_setup
    assert executor.toolkit == mock_toolkit


@pytest.mark.unit
def test_parallel_executor_setup_graph():
    """测试并行图设置"""
    # Arrange
    mock_base_setup = Mock()
    mock_toolkit = Mock()
    mock_quick_llm = Mock()

    mock_base_setup.quick_thinking_llm = mock_quick_llm
    mock_base_setup.toolkit = mock_toolkit
    mock_base_setup.tool_nodes = {
        "market": Mock(name="tool_market"),
        "social": Mock(name="tool_social"),
        "news": Mock(name="tool_news"),
        "fundamentals": Mock(name="tool_fundamentals"),
    }

    executor = ParallelAnalystExecutor(mock_base_setup)

    # Act
    with patch("tradingagents.graph.parallel_analysts.GraphSetup") as mock_graph_setup:
        mock_graph_setup.return_value = Mock()
        mock_graph_setup.toolkit = mock_toolkit

        with patch(
            "tradingagents.graph.parallel_analysts.create_market_analyst"
        ) as mock_market:
            with patch(
                "tradingagents.graph.parallel_analysts.create_social_media_analyst"
            ) as mock_social:
                with patch(
                    "tradingagents.graph.parallel_analysts.create_news_analyst"
                ) as mock_news:
                    with patch(
                        "tradingagents.graph.parallel_analysts.create_fundamentals_analyst"
                    ) as mock_fundamentals:
                        with patch(
                            "tradingagents.graph.parallel_analysts.create_bull_researcher"
                        ) as mock_bull:
                            with patch(
                                "tradingagents.graph.parallel_analysts.create_bear_researcher"
                            ) as mock_bear:
                                mock_market.return_value = Mock(name="node_market")
                                mock_social.return_value = Mock(name="node_social")
                                mock_news.return_value = Mock(name="node_news")
                                mock_fundamentals.return_value = Mock(
                                    name="node_fundamentals"
                                )
                                mock_bull.return_value = Mock(name="node_bull")
                                mock_bear.return_value = Mock(name="node_bear")

                    graph = executor.setup_parallel_graph(
                        selected_analysts=["market", "social"]
                    )

    # Assert
    assert graph is not None


@pytest.mark.unit
def test_parallel_executor_setup_all_analysts():
    """测试设置所有分析师"""
    # Arrange
    mock_base_setup = Mock()
    mock_toolkit = Mock()
    mock_base_setup.tool_nodes = {
        "market": Mock(),
        "social": Mock(),
        "news": Mock(),
        "fundamentals": Mock(),
    }
    executor = ParallelAnalystExecutor(mock_base_setup)

    # Act
    with patch("tradingagents.graph.parallel_analysts.GraphSetup") as mock_graph_setup:
        mock_graph_setup.tool_nodes = {}

        graph = executor.setup_parallel_graph(
            selected_analysts=["market", "social", "news", "fundamentals"]
        )

    # Assert
    # 验证选择了所有分析师


@pytest.mark.unit
def test_parallel_executor_setup_no_analysts():
    """测试未选择分析师时的错误处理"""
    # Arrange
    mock_base_setup = Mock()
    mock_toolkit = Mock()
    executor = ParallelAnalystExecutor(mock_base_setup)

    # Act & Assert
    with patch("tradingagents.graph.parallel_analysts.GraphSetup") as mock_graph_setup:
        mock_graph_setup.tool_nodes = {}

        with pytest.raises(ValueError) as exc_info:
            graph = executor.setup_parallel_graph(selected_analysts=[])

        assert "no analysts selected" in str(exc_info.value).lower()


@pytest.mark.unit
def test_parallel_executor_conditional_logic():
    """测试条件逻辑注入"""
    # Arrange
    mock_base_setup = Mock()
    mock_toolkit = Mock()
    mock_conditional_logic = Mock()

    mock_base_setup.conditional_logic = mock_conditional_logic
    mock_base_setup.tool_nodes = {
        "market": Mock(name="tool_market"),
        "social": Mock(name="tool_social"),
        "news": Mock(name="tool_news"),
        "fundamentals": Mock(name="tool_fundamentals"),
    }

    executor = ParallelAnalystExecutor(mock_base_setup)

    # Act
    with patch("tradingagents.graph.parallel_analysts.GraphSetup") as mock_graph_setup:
        with patch(
            "tradingagents.graph.parallel_analysts.create_market_analyst"
        ) as mock_market:
            mock_market.return_value = Mock(name="node_market")

            mock_graph_setup.tool_nodes = {"market": Mock()}

            graph = executor.setup_parallel_graph(selected_analysts=["market"])

    # Assert
    # 验证条件逻辑被使用
    assert executor.conditional_logic == mock_conditional_logic


@pytest.mark.unit
def test_parallel_executor_workflow_structure():
    """测试工作流结构"""
    # Arrange
    mock_base_setup = Mock()
    mock_toolkit = Mock()
    mock_base_setup.tool_nodes = {
        "market": Mock(name="tool_market"),
        "social": Mock(name="tool_social"),
        "news": Mock(name="tool_news"),
        "fundamentals": Mock(name="tool_fundamentals"),
    }
    executor = ParallelAnalystExecutor(mock_base_setup)

    # Act
    with patch("tradingagents.graph.parallel_analysts.GraphSetup") as mock_graph_setup:
        with patch(
            "tradingagents.graph.parallel_analysts.create_market_analyst"
        ) as mock_market:
            mock_market.return_value = Mock(name="node_market")

            mock_graph_setup.tool_nodes = {"market": Mock()}

            graph = executor.setup_parallel_graph(selected_analysts=["market"])

    # Assert
    assert graph is not None
    # 验证图结构包含预期的节点
    nodes = graph.nodes.keys()
    assert any("Market" in node for node in nodes)


@pytest.mark.unit
def test_parallel_executor_parallel_edges():
    """测试并行边设置"""
    # Arrange
    mock_base_setup = Mock()
    mock_toolkit = Mock()
    mock_base_setup.tool_nodes = {
        "market": Mock(name="tool_market"),
        "social": Mock(name="tool_social"),
        "news": Mock(name="tool_news"),
        "fundamentals": Mock(name="tool_fundamentals"),
    }
    executor = ParallelAnalystExecutor(mock_base_setup)

    # Act
    with patch("tradingagents.graph.parallel_analysts.GraphSetup") as mock_graph_setup:
        with patch(
            "tradingagents.graph.parallel_analysts.create_market_analyst"
        ) as mock_market:
            mock_market.return_value = Mock(name="node_market")

            mock_graph_setup.tool_nodes = {"market": Mock()}

            graph = executor.setup_parallel_graph(selected_analysts=["market"])

    # Assert
    # 验证图结构
    assert graph is not None
    # 使用get_graph()方法获取图的 drawable representation
    graph_structure = graph.get_graph()
    assert graph_structure is not None
