# -*- coding: utf-8 -*-
# TradingAgents/graph/setup.py

from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import *  # ToolNode 已弃用，预加载模式使用 DataCoordinator

from tradingagents.agents import *
from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.agents.utils.agent_utils import Toolkit

from .conditional_logic import ConditionalLogic
from .data_coordinator import data_coordinator_node

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        quick_thinking_llm: ChatOpenAI,
        deep_thinking_llm: ChatOpenAI,
        toolkit: Toolkit,
        bull_memory,
        bear_memory,
        trader_memory,
        invest_judge_memory,
        risk_manager_memory,
        conditional_logic: ConditionalLogic,
        # DEPRECATED: tool_nodes 已弃用
        # 统一预加载模式下，DataCoordinator 负责预加载数据，分析师直接从 state 获取
        # 此参数保留用于向后兼容，实际不再使用
        tool_nodes: Dict = None,
        config: Dict[str, Any] = None,
        react_llm=None,
    ):
        """Initialize with required components."""
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.toolkit = toolkit
        # DEPRECATED: tool_nodes 已弃用，保留空字典以保持兼容
        self.tool_nodes = tool_nodes or {}
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.trader_memory = trader_memory
        self.invest_judge_memory = invest_judge_memory
        self.risk_manager_memory = risk_manager_memory
        self.conditional_logic = conditional_logic
        self.config = config or {}
        self.react_llm = react_llm

    def setup_graph(
        self, selected_analysts=["market", "social", "news", "fundamentals", "china"]
    ):
        """Set up and compile the agent workflow graph.

        Args:
            selected_analysts (list): List of analyst types to include. Options are:
                - "market": Market analyst
                - "social": Social media analyst
                - "news": News analyst
                - "fundamentals": Fundamentals analyst
                - "china": China market analyst (A-share specific)
        """
        if len(selected_analysts) == 0:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")

        # Create analyst nodes
        analyst_nodes = {}

        # 注意：ToolNode 已弃用，分析师使用 DataCoordinator 预加载的数据
        # 分析流程：DataCoordinator 预加载 → Analyst 直接从 state 获取数据 → 生成报告
        # 注意：并行执行模式下不再使用 Msg Clear 节点，避免消息删除冲突

        if "market" in selected_analysts:
            logger.debug(f"📈 [DEBUG] Setup Market Analyst")
            analyst_nodes["market"] = create_market_analyst(
                self.quick_thinking_llm, self.toolkit
            )

        if "social" in selected_analysts:
            logger.debug(f"💬 [DEBUG] Setup Social Media Analyst")
            analyst_nodes["social"] = create_social_media_analyst(
                self.quick_thinking_llm, self.toolkit
            )

        if "news" in selected_analysts:
            logger.debug(f"📰 [DEBUG] Setup News Analyst")
            analyst_nodes["news"] = create_news_analyst(
                self.quick_thinking_llm, self.toolkit
            )

        if "fundamentals" in selected_analysts:
            logger.debug(f"💼 [DEBUG] Setup Fundamentals Analyst")
            analyst_nodes["fundamentals"] = create_fundamentals_analyst(
                self.quick_thinking_llm, self.toolkit
            )

        if "china" in selected_analysts:
            logger.debug(f"🇨🇳 [DEBUG] Setup China Market Analyst")
            analyst_nodes["china"] = create_china_market_analyst(
                self.quick_thinking_llm, self.toolkit
            )

        # Create researcher and manager nodes
        bull_researcher_node = create_bull_researcher(
            self.quick_thinking_llm, self.bull_memory
        )
        bear_researcher_node = create_bear_researcher(
            self.quick_thinking_llm, self.bear_memory
        )
        research_manager_node = create_research_manager(
            self.deep_thinking_llm, self.invest_judge_memory
        )
        trader_node = create_trader(self.quick_thinking_llm, self.trader_memory)

        # Create risk analysis nodes
        risky_analyst = create_risky_debator(self.quick_thinking_llm)
        neutral_analyst = create_neutral_debator(self.quick_thinking_llm)
        safe_analyst = create_safe_debator(self.quick_thinking_llm)
        risk_manager_node = create_risk_manager(
            self.deep_thinking_llm, self.risk_manager_memory
        )

        # Create workflow
        workflow = StateGraph(AgentState)

        # Add Data Coordinator node (New Entry Point)
        workflow.add_node("Data Coordinator", data_coordinator_node)

        # Add analyst nodes to the graph
        for analyst_type, node in analyst_nodes.items():
            workflow.add_node(f"{analyst_type.capitalize()} Analyst", node)
            # 注意：并行执行模式下不使用 Msg Clear 节点

        # Add other nodes
        workflow.add_node("Bull Researcher", bull_researcher_node)
        workflow.add_node("Bear Researcher", bear_researcher_node)
        workflow.add_node("Research Manager", research_manager_node)
        workflow.add_node("Trader", trader_node)
        workflow.add_node("Risky Analyst", risky_analyst)
        workflow.add_node("Neutral Analyst", neutral_analyst)
        workflow.add_node("Safe Analyst", safe_analyst)
        workflow.add_node("Risk Judge", risk_manager_node)

        # Define edges

        # 1. START -> Data Coordinator
        workflow.add_edge(START, "Data Coordinator")

        # 2. Data Coordinator -> All Analysts in PARALLEL
        # 所有选中的分析师并行执行，提高效率
        for analyst_type in selected_analysts:
            workflow.add_edge(
                "Data Coordinator", f"{analyst_type.capitalize()} Analyst"
            )

        # 3. Connect analysts directly to Bull Researcher (parallel -> sync point)
        # 所有分析师并行执行完成后，直接汇聚到 Bull Researcher
        # 注意：不在此处清理消息，避免并行冲突
        for analyst_type in selected_analysts:
            current_analyst = f"{analyst_type.capitalize()} Analyst"
            workflow.add_edge(current_analyst, "Bull Researcher")

        # 4. Add remaining edges (Debate and Risk flows)
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
        return workflow.compile()
