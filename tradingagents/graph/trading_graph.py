# -*- coding: utf-8 -*-
# TradingAgents/graph/trading_graph.py

import os
import time
from datetime import datetime
from typing import Dict, Any

from langchain_openai import ChatOpenAI

from tradingagents.agents import *
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.agents.utils.memory import FinancialSituationMemory
from tradingagents.agents.utils.agent_states import (
    AgentState,
)
from tradingagents.dataflows.interfaces.base_interface import set_config
from tradingagents.agents.utils.agent_utils import Toolkit

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("agents")

# 导入拆分后的子模块
from .base import create_llm_by_provider
from .llm_init import LLMInitializer
from .quality import QualityChecker
from .performance import PerformanceTracker
from .progress import ProgressManager
from .state_logging import StateLogger
from .conditional_logic import ConditionalLogic
from .setup import GraphSetup
from .propagation import Propagator
from .reflection import Reflector
from .signal_processing import SignalProcessor


class TradingAgentsGraph:
    """Main class that orchestrates trading agents framework.

    这是一个 Facade 类，将复杂的多模块逻辑封装为简单接口。
    """

    def __init__(
        self,
        selected_analysts=["market", "social", "news", "fundamentals", "china"],
        debug=False,
        config: Dict[str, Any] = None,
    ):
        """Initialize trading agents graph and components.

        Args:
            selected_analysts: List of analyst types to include
            debug: Whether to run in debug mode
            config: Configuration dictionary. If None, uses default config
        """
        self.debug = debug
        self.config = config or DEFAULT_CONFIG
        self.selected_analysts = selected_analysts  # 保存分析师选择列表

        # Update interface's config
        set_config(self.config)

        # Create necessary directories
        os.makedirs(
            os.path.join(self.config["project_dir"], "dataflows/data_cache"),
            exist_ok=True,
        )

        # Initialize LLMs
        self.quick_thinking_llm, self.deep_thinking_llm = LLMInitializer.initialize_llms(
            self.config
        )

        self.toolkit = Toolkit(config=self.config)

        # Initialize memories (如果启用)
        memory_enabled = self.config.get("memory_enabled", True)
        if memory_enabled:
            # 使用单例ChromaDB管理器，避免并发创建冲突
            self.bull_memory = FinancialSituationMemory("bull_memory", self.config)
            self.bear_memory = FinancialSituationMemory("bear_memory", self.config)
            self.trader_memory = FinancialSituationMemory("trader_memory", self.config)
            self.invest_judge_memory = FinancialSituationMemory(
                "invest_judge_memory", self.config
            )
            self.risk_manager_memory = FinancialSituationMemory(
                "risk_manager_memory", self.config
            )
        else:
            # 创建空的内存对象
            self.bull_memory = None
            self.bear_memory = None
            self.trader_memory = None
            self.invest_judge_memory = None
            self.risk_manager_memory = None

        # Create tool nodes - 统一预加载模式，不再需要 ToolNode
        # 保留空字典以保持向后兼容
        self.tool_nodes = {}

        # Initialize components
        # 🔥 [修复] 从配置中读取辩论轮次参数
        self.conditional_logic = ConditionalLogic(
            max_debate_rounds=self.config.get("max_debate_rounds", 1),
            max_risk_discuss_rounds=self.config.get("max_risk_discuss_rounds", 1),
        )
        logger.info(f"🔧 [ConditionalLogic] 初始化完成:")
        logger.info(
            f"   - max_debate_rounds: {self.conditional_logic.max_debate_rounds}"
        )
        logger.info(
            f"   - max_risk_discuss_rounds: {self.conditional_logic.max_risk_discuss_rounds}"
        )

        self.graph_setup = GraphSetup(
            self.quick_thinking_llm,
            self.deep_thinking_llm,
            self.toolkit,
            self.bull_memory,
            self.bear_memory,
            self.trader_memory,
            self.invest_judge_memory,
            self.risk_manager_memory,
            self.conditional_logic,
            self.tool_nodes,  # DEPRECATED: 已弃用，但保留兼容
            self.config,
            getattr(self, "react_llm", None),
        )

        self.propagator = Propagator()
        self.reflector = Reflector(self.quick_thinking_llm)
        self.signal_processor = SignalProcessor(self.quick_thinking_llm)

        # State tracking
        self.curr_state = None
        self.ticker = None
        self.state_logger = None

        # Set up graph
        self.graph = self.graph_setup.setup_graph(selected_analysts)

    def _create_tool_nodes(self) -> Dict:
        """[已弃用] 创建工具节点

        注意：统一预加载模式下，Data Coordinator 负责预加载数据，
        分析师节点直接从 state 获取数据，不再需要动态工具调用。

        此方法保留用于向后兼容，返回空字典。
        """
        return {}

    def propagate(self, company_name, trade_date, progress_callback=None, task_id=None):
        """Run trading agents graph for a company on a specific date.

        Args:
            company_name: Company name or stock symbol
            trade_date: Date for analysis
            progress_callback: Optional callback function for progress updates
            task_id: Optional task ID for tracking performance data
        """
        # 添加详细的接收日志
        logger.debug(
            f"🔍 [GRAPH DEBUG] ===== TradingAgentsGraph.propagate 接收参数 ====="
        )
        logger.debug(
            f"🔍 [GRAPH DEBUG] 接收到的company_name: '{company_name}' (类型: {type(company_name)})"
        )
        logger.debug(
            f"🔍 [GRAPH DEBUG] 接收到的trade_date: '{trade_date}' (类型: {type(trade_date)})"
        )
        logger.debug(f"🔍 [GRAPH DEBUG] 接收到的task_id: '{task_id}'")

        # 🔧修复：从配置中读取selected_analysts，而不是使用默认值
        config_selected_analysts = self.config.get(
            "selected_analysts", self.selected_analysts
        )
        if config_selected_analysts != self.selected_analysts:
            logger.info(
                f"🔍 [GRAPH] 使用配置中的selected_analysts: {config_selected_analysts}"
            )
            logger.info(
                f"🔍 [GRAPH] 覆盖默认的selected_analysts: {self.selected_analysts}"
            )
            self.selected_analysts = config_selected_analysts

        # 🔧修复：同步日期到全局配置，确保所有工具都能获取正确的分析日期
        if trade_date is not None:
            Toolkit._config["trade_date"] = str(trade_date)
            Toolkit._config["analysis_date"] = str(trade_date)
            logger.info(f"📅 [GRAPH] 已同步分析日期到全局配置: {trade_date}")
        else:
            logger.warning(f"⚠️  [GRAPH] trade_date 为 None，跳过日期同步")

        self.ticker = company_name
        logger.debug(f"🔍 [GRAPH DEBUG] 设置self.ticker: '{self.ticker}'")

        # Initialize state
        logger.debug(
            f"🔍 [GRAPH DEBUG] 创建初始状态，传递参数: company_name='{company_name}', trade_date='{trade_date}'"
        )

        init_agent_state = self.propagator.create_initial_state(
            company_name, trade_date
        )
        logger.debug(
            f"🔍 [GRAPH DEBUG] 初始状态中的company_of_interest: '{init_agent_state.get('company_of_interest', 'NOT_FOUND')}'"
        )
        logger.debug(
            f"🔍 [GRAPH DEBUG] 初始状态中的trade_date: '{init_agent_state.get('trade_date', 'NOT_FOUND')}'"
        )

        # 初始化计时器
        node_timings = {}  # 记录每个节点的执行时间
        total_start_time = time.time()  # 总体开始时间
        current_node_start = None  # 当前节点开始时间
        current_node_name = None  # 当前节点名称

        # 保存task_id用于后续保存性能数据
        self._current_task_id = task_id

        # 统一的执行模式 - 简化并发处理逻辑
        # 移除原来的3种模式（Debug/Standard/Invoke），统一为单一模式
        args = self.propagator.get_graph_args(
            use_progress_callback=bool(progress_callback)
        )

        final_state = None
        for chunk in self.graph.stream(init_agent_state, **args):
            # 记录节点计时（所有模式都需要）
            for node_name in chunk.keys():
                if not node_name.startswith("__"):
                    if current_node_name and current_node_start:
                        elapsed = time.time() - current_node_start
                        node_timings[current_node_name] = elapsed
                        if self.debug:
                            logger.info(
                                f"⏱️ [{current_node_name}] 耗时: {elapsed:.2f}秒"
                            )
                            logger.info(
                                f"🔍 [TIMING] 节点切换: {current_node_name} → {node_name}"
                            )
                        else:
                            logger.info(
                                f"⏱️ [{current_node_name}] 耗时: {elapsed:.2f}秒"
                            )

                    current_node_name = node_name
                    current_node_start = time.time()
                    if self.debug:
                        logger.info(f"🔍 [TIMING] 开始计时: {node_name}")
                    break

            # 发送进度更新（如果有回调）
            if progress_callback:
                ProgressManager.send_progress_update(chunk, progress_callback)

            # 累积状态更新（所有模式都需要）
            if final_state is None:
                final_state = init_agent_state.copy()
            for node_name, node_update in chunk.items():
                if not node_name.startswith("__"):
                    final_state.update(node_update)

            # Debug模式：打印消息
            if self.debug and len(chunk.get("messages", [])) > 0:
                chunk["messages"][-1].pretty_print()

        # 记录最后一个节点的时间
        if current_node_name and current_node_start:
            elapsed = time.time() - current_node_start
            node_timings[current_node_name] = elapsed
            logger.info(f"⏱️ [{current_node_name}] 耗时: {elapsed:.2f}秒")

        # 计算总时间
        total_elapsed = time.time() - total_start_time

        # 调试日志
        logger.info(f"🔍 [TIMING DEBUG] 节点计时数量: {len(node_timings)}")
        logger.info(f"🔍 [TIMING DEBUG] 总耗时: {total_elapsed:.2f}秒")
        logger.info(f"🔍 [TIMING DEBUG] 节点列表: {list(node_timings.keys())}")

        # 打印详细的时间统计
        logger.info("🔍 [TIMING DEBUG] 准备调用 _print_timing_summary")
        PerformanceTracker.print_timing_summary(node_timings, total_elapsed, self.config)
        logger.info("🔍 [TIMING DEBUG] _print_timing_summary 调用完成")

        # 构建性能数据
        performance_data = PerformanceTracker.build_performance_data(
            node_timings, total_elapsed, self.config
        )

        # 将性能数据添加到状态中
        if final_state is not None:
            final_state["performance_metrics"] = performance_data

        # Store current state for reflection
        self.curr_state = final_state

        # Log state
        if self.state_logger is None:
            self.state_logger = StateLogger(self.ticker)
        self.state_logger.log_state(trade_date, final_state)

        # 获取模型信息
        model_info = ""
        try:
            if hasattr(self.deep_thinking_llm, "model_name"):
                model_info = f"{self.deep_thinking_llm.__class__.__name__}:{self.deep_thinking_llm.model_name}"
            else:
                model_info = self.deep_thinking_llm.__class__.__name__
        except Exception:
            model_info = "Unknown"

        # ========== 报告质量检查集成 ==========
        # 在处理决策之前执行质量检查，以便根据质量调整置信度
        if final_state is not None:
            QualityChecker.run_quality_checks(final_state)

        # 处理决策并添加模型信息
        if final_state is not None:
            decision = self.process_signal(
                final_state.get("final_trade_decision", {}), company_name
            )
        else:
            decision = {}
        decision["model_info"] = model_info

        # 将质量检查结果添加到决策中
        QualityChecker.apply_quality_results_to_decision(final_state, decision)

        # Return decision and processed signal
        return final_state, decision

    def reflect_and_remember(self, returns_losses):
        """Reflect on decisions and update memory based on returns."""
        self.reflector.reflect_bull_researcher(
            self.curr_state, returns_losses, self.bull_memory
        )
        self.reflector.reflect_bear_researcher(
            self.curr_state, returns_losses, self.bear_memory
        )
        self.reflector.reflect_trader(
            self.curr_state, returns_losses, self.trader_memory
        )
        self.reflector.reflect_invest_judge(
            self.curr_state, returns_losses, self.invest_judge_memory
        )
        self.reflector.reflect_risk_manager(
            self.curr_state, returns_losses, self.risk_manager_memory
        )

    def process_signal(self, full_signal, stock_symbol=None):
        """Process a signal to extract core decision."""
        return self.signal_processor.process_signal(full_signal, stock_symbol)
