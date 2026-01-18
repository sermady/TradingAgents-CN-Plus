# -*- coding: utf-8 -*-
"""
并行分析师执行模块
Parallel Analysts Execution Module

实现分析师并行执行，提升分析速度（预计 3x 速度提升）。
Implements parallel analyst execution to improve analysis speed (expected 3x speedup).

作者 Author: Claude
创建日期 Created: 2026-01-18
"""

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

from tradingagents.agents import *
from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.agents.utils.agent_utils import Toolkit

from tradingagents.graph.conditional_logic import ConditionalLogic
from tradingagents.graph.setup import GraphSetup

from tradingagents.utils.logging_init import get_logger

logger = get_logger("parallel_analysts")


class ParallelAnalystExecutor:
    """并行分析师执行器 - 实现分析师并行执行"""

    def __init__(
        self,
        base_setup: GraphSetup,
    ):
        """初始化并行执行器 Initialize parallel executor"""
        self.base_setup = base_setup
        self.toolkit = base_setup.toolkit
        self.tool_nodes = base_setup.tool_nodes
        self.conditional_logic = base_setup.conditional_logic

    def setup_parallel_graph(
        self, selected_analysts=["market", "social", "news", "fundamentals"]
    ):
        """设置并行分析师执行图 Setup parallel analyst execution graph

        Args:
            selected_analysts (list): List of analyst types to include
        """
        if len(selected_analysts) == 0:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")

        # Create analyst nodes
        analyst_nodes = {}
        delete_nodes = {}
        tool_nodes = {}

        if "market" in selected_analysts:
            analyst_nodes["market"] = create_market_analyst(
                self.base_setup.quick_thinking_llm, self.toolkit
            )
            delete_nodes["market"] = create_msg_delete()
            tool_nodes["market"] = self.tool_nodes["market"]

        if "social" in selected_analysts:
            analyst_nodes["social"] = create_social_media_analyst(
                self.base_setup.quick_thinking_llm, self.toolkit
            )
            delete_nodes["social"] = create_msg_delete()
            tool_nodes["social"] = self.tool_nodes["social"]

        if "news" in selected_analysts:
            analyst_nodes["news"] = create_news_analyst(
                self.base_setup.quick_thinking_llm, self.toolkit
            )
            delete_nodes["news"] = create_msg_delete()
            tool_nodes["news"] = self.tool_nodes["news"]

        if "fundamentals" in selected_analysts:
            analyst_nodes["fundamentals"] = create_fundamentals_analyst(
                self.base_setup.quick_thinking_llm, self.toolkit
            )
            delete_nodes["fundamentals"] = create_msg_delete()
            tool_nodes["fundamentals"] = self.tool_nodes["fundamentals"]

        # Create researcher and manager nodes
        bull_researcher_node = create_bull_researcher(
            self.base_setup.quick_thinking_llm, self.base_setup.bull_memory
        )
        bear_researcher_node = create_bear_researcher(
            self.base_setup.quick_thinking_llm, self.base_setup.bear_memory
        )
        research_manager_node = create_research_manager(
            self.base_setup.deep_thinking_llm, self.base_setup.invest_judge_memory
        )
        trader_node = create_trader(
            self.base_setup.quick_thinking_llm, self.base_setup.trader_memory
        )

        # Create risk analysis nodes
        risky_analyst = create_risky_debator(self.base_setup.quick_thinking_llm)
        neutral_analyst = create_neutral_debator(self.base_setup.quick_thinking_llm)
        safe_analyst = create_safe_debator(self.base_setup.quick_thinking_llm)
        risk_manager_node = create_risk_manager(
            self.base_setup.deep_thinking_llm, self.base_setup.risk_manager_memory
        )

        # Create workflow
        workflow = StateGraph(AgentState)

        # Add analyst nodes to graph
        for analyst_type, node in analyst_nodes.items():
            workflow.add_node(f"{analyst_type.capitalize()} Analyst", node)
            workflow.add_node(
                f"Msg Clear {analyst_type.capitalize()}", delete_nodes[analyst_type]
            )
            workflow.add_node(f"tools_{analyst_type}", tool_nodes[analyst_type])

        # Add other nodes
        workflow.add_node("Bull Researcher", bull_researcher_node)
        workflow.add_node("Bear Researcher", bear_researcher_node)
        workflow.add_node("Research Manager", research_manager_node)
        workflow.add_node("Trader", trader_node)
        workflow.add_node("Risky Analyst", risky_analyst)
        workflow.add_node("Neutral Analyst", neutral_analyst)
        workflow.add_node("Safe Analyst", safe_analyst)
        workflow.add_node("Risk Judge", risk_manager_node)

        # === 关键改动：并行执行所有分析师 ===
        # Start edge: Connect START to all analysts (并行开始）
        for analyst_type in selected_analysts:
            workflow.add_edge(START, f"{analyst_type.capitalize()} Analyst")

        # Add conditional edges for each analyst (并行执行）
        for analyst_type in selected_analysts:
            current_analyst = f"{analyst_type.capitalize()} Analyst"
            current_tools = f"tools_{analyst_type}"
            current_clear = f"Msg Clear {analyst_type.capitalize()}"

            # 添加条件边
            workflow.add_conditional_edges(
                current_analyst,
                getattr(self.conditional_logic, f"should_continue_{analyst_type}"),
                [current_tools, current_clear],
            )
            workflow.add_edge(current_tools, current_analyst)

        # Wait for all analysts to complete, then proceed to Bull Researcher
        # 使用同步节点等待所有分析师完成
        if selected_analysts:
            # 将所有分析师的清理节点连接到 Bull Researcher
            for analyst_type in selected_analysts:
                current_clear = f"Msg Clear {analyst_type.capitalize()}"
                workflow.add_edge(current_clear, "Bull Researcher")

        # Add remaining edges (保持原有逻辑）
        workflow.add_conditional_edges(
            "Bull Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bear Researcher": "Bear Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_conditional_edges(
            "Bear Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bull Researcher": "Bull Researcher",
                "Research Manager": "Research Manager",
            },
        )
        workflow.add_edge("Research Manager", "Trader")
        workflow.add_edge("Trader", "Risky Analyst")
        workflow.add_conditional_edges(
            "Risky Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Safe Analyst": "Safe Analyst",
                "Risk Judge": "Risk Judge",
            },
        )
        workflow.add_conditional_edges(
            "Safe Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Neutral Analyst": "Neutral Analyst",
                "Risk Judge": "Risk Judge",
            },
        )
        workflow.add_conditional_edges(
            "Neutral Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {
                "Risky Analyst": "Risky Analyst",
                "Risk Judge": "Risk Judge",
            },
        )

        workflow.add_edge("Risk Judge", END)

        # Compile and return
        compiled_graph = workflow.compile()

        logger.info("=" * 60)
        logger.info("并行分析师执行图已创建 Parallel Analysts Graph Created")
        logger.info(f"启用的分析师 Enabled analysts: {', '.join(selected_analysts)}")
        logger.info(f"并行执行模式 Parallel execution: YES")
        logger.info("=" * 60)

        return compiled_graph


def create_parallel_executor(
    base_setup: GraphSetup,
) -> ParallelAnalystExecutor:
    """创建并行分析师执行器 Create parallel analyst executor

    Args:
        base_setup: Base graph setup with LLMs and toolkit

    Returns:
        ParallelAnalystExecutor instance
    """
    return ParallelAnalystExecutor(base_setup)
