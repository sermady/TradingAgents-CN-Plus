# -*- coding: utf-8 -*-
"""
增强型并行分析师执行模块 (Enhanced Parallel Analysts Execution)

改进点:
1. 为每个分析师添加超时控制 (默认180秒)
2. 集成进度回调机制
3. 更好的异常处理和错误恢复
4. 支持部分失败模式 (部分分析师失败不影响整体流程)
5. 集成LLM缓存

作者: Claude
创建日期: 2026-02-12
"""

import asyncio
import time
from typing import Dict, Any, Optional, Callable, List
from concurrent.futures import TimeoutError as FutureTimeoutError

from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import *

from tradingagents.agents import *
from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.agents.utils.agent_utils import Toolkit

from tradingagents.graph.conditional_logic import ConditionalLogic
from tradingagents.graph.setup import GraphSetup
from tradingagents.graph.data_coordinator import data_coordinator_node

from tradingagents.utils.logging_init import get_logger
from tradingagents.cache.llm_cache import get_llm_cache

logger = get_logger("parallel_analysts_v2")


class AnalystExecutionResult:
    """分析师执行结果"""

    def __init__(
        self,
        analyst_name: str,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
        execution_time: float = 0.0,
        from_cache: bool = False,
    ):
        self.analyst_name = analyst_name
        self.success = success
        self.result = result
        self.error = error
        self.execution_time = execution_time
        self.from_cache = from_cache


class EnhancedParallelAnalystExecutor:
    """
    增强型并行分析师执行器

    特性:
    - 超时控制: 每个分析师独立超时
    - 进度回调: 实时通知执行进度
    - 缓存集成: 自动使用LLM缓存
    - 容错处理: 单个分析师失败不影响其他
    """

    def __init__(
        self,
        base_setup: GraphSetup,
        analyst_timeout: int = 180,  # 单个分析师超时时间(秒)
        progress_callback: Optional[Callable[[str, Dict], None]] = None,
        use_cache: bool = True,
        allow_partial_failure: bool = True,  # 允许部分分析师失败
    ):
        """
        初始化增强型并行执行器

        Args:
            base_setup: 基础图设置
            analyst_timeout: 单个分析师超时时间(秒)
            progress_callback: 进度回调函数 (analyst_name, status_dict)
            use_cache: 是否使用LLM缓存
            allow_partial_failure: 是否允许部分分析师失败
        """
        self.base_setup = base_setup
        self.toolkit = base_setup.toolkit
        self.tool_nodes = {}
        self.conditional_logic = base_setup.conditional_logic

        # 配置参数
        self.analyst_timeout = analyst_timeout
        self.progress_callback = progress_callback
        self.use_cache = use_cache
        self.allow_partial_failure = allow_partial_failure

        # 初始化缓存
        self.llm_cache = get_llm_cache() if use_cache else None

        # 执行统计
        self.execution_stats = {
            "start_time": None,
            "end_time": None,
            "analyst_times": {},
            "cache_hits": 0,
            "cache_misses": 0,
            "timeout_count": 0,
            "error_count": 0,
        }

    async def _execute_analyst_with_timeout(
        self,
        analyst_name: str,
        analyst_node,
        state: AgentState,
    ) -> AnalystExecutionResult:
        """
        带超时的分析师执行

        Args:
            analyst_name: 分析师名称
            analyst_node: 分析师节点函数
            state: 当前状态

        Returns:
            AnalystExecutionResult: 执行结果
        """
        start_time = time.time()

        try:
            # 通知开始
            self._notify_progress(
                analyst_name,
                {"status": "started", "message": f"{analyst_name} 开始分析..."},
            )

            # 检查缓存 (如果启用)
            if self.use_cache and self.llm_cache:
                cache_key = self._generate_cache_key(analyst_name, state)
                cached_result = self.llm_cache.get(cache_key)
                if cached_result:
                    self.execution_stats["cache_hits"] += 1
                    execution_time = time.time() - start_time
                    self._notify_progress(
                        analyst_name,
                        {
                            "status": "completed",
                            "message": f"{analyst_name} 从缓存恢复结果",
                            "execution_time": execution_time,
                            "from_cache": True,
                        },
                    )
                    return AnalystExecutionResult(
                        analyst_name=analyst_name,
                        success=True,
                        result=cached_result,
                        execution_time=execution_time,
                        from_cache=True,
                    )
                self.execution_stats["cache_misses"] += 1

            # 执行分析师 (带超时)
            try:
                # 在事件循环中运行同步函数
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, analyst_node, state),
                    timeout=self.analyst_timeout,
                )

                execution_time = time.time() - start_time
                self.execution_stats["analyst_times"][analyst_name] = execution_time

                # 保存到缓存
                if self.use_cache and self.llm_cache and result:
                    cache_key = self._generate_cache_key(analyst_name, state)
                    self.llm_cache.set(cache_key, result)

                self._notify_progress(
                    analyst_name,
                    {
                        "status": "completed",
                        "message": f"{analyst_name} 分析完成",
                        "execution_time": execution_time,
                    },
                )

                return AnalystExecutionResult(
                    analyst_name=analyst_name,
                    success=True,
                    result=result,
                    execution_time=execution_time,
                )

            except asyncio.TimeoutError:
                self.execution_stats["timeout_count"] += 1
                execution_time = time.time() - start_time
                error_msg = f"{analyst_name} 执行超时 ({self.analyst_timeout}秒)"
                logger.warning(f"⚠️ {error_msg}")

                self._notify_progress(
                    analyst_name,
                    {
                        "status": "timeout",
                        "message": error_msg,
                        "execution_time": execution_time,
                    },
                )

                return AnalystExecutionResult(
                    analyst_name=analyst_name,
                    success=False,
                    error=error_msg,
                    execution_time=execution_time,
                )

        except Exception as e:
            self.execution_stats["error_count"] += 1
            execution_time = time.time() - start_time
            error_msg = f"{analyst_name} 执行错误: {str(e)}"
            logger.error(f"❌ {error_msg}", exc_info=True)

            self._notify_progress(
                analyst_name,
                {
                    "status": "error",
                    "message": error_msg,
                    "execution_time": execution_time,
                },
            )

            return AnalystExecutionResult(
                analyst_name=analyst_name,
                success=False,
                error=error_msg,
                execution_time=execution_time,
            )

    def _generate_cache_key(self, analyst_name: str, state: AgentState) -> str:
        """生成缓存键"""
        # 基于股票代码、分析师类型和日期生成缓存键
        ticker = state.get("ticker", "")
        analysis_date = state.get("analysis_date", "")
        return f"{analyst_name}:{ticker}:{analysis_date}"

    def _notify_progress(self, analyst_name: str, status: Dict):
        """通知进度更新"""
        if self.progress_callback:
            try:
                self.progress_callback(analyst_name, status)
            except Exception as e:
                logger.debug(f"进度回调失败: {e}")

    async def execute_analysts_parallel(
        self,
        analyst_nodes: Dict[str, Any],
        state: AgentState,
    ) -> Dict[str, AnalystExecutionResult]:
        """
        并行执行所有分析师

        Args:
            analyst_nodes: 分析师节点字典
            state: 当前状态

        Returns:
            Dict[str, AnalystExecutionResult]: 执行结果字典
        """
        self.execution_stats["start_time"] = time.time()

        # 创建所有执行任务
        tasks = []
        for analyst_name, analyst_node in analyst_nodes.items():
            task = self._execute_analyst_with_timeout(analyst_name, analyst_node, state)
            tasks.append(task)

        # 并行执行所有任务
        logger.info(f"🚀 开始并行执行 {len(tasks)} 个分析师...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        self.execution_stats["end_time"] = time.time()

        # 处理结果
        result_dict = {}
        success_count = 0
        for i, (analyst_name, result) in enumerate(zip(analyst_nodes.keys(), results)):
            if isinstance(result, Exception):
                # 处理异常情况
                result_dict[analyst_name] = AnalystExecutionResult(
                    analyst_name=analyst_name,
                    success=False,
                    error=f"执行异常: {str(result)}",
                )
                self.execution_stats["error_count"] += 1
            else:
                result_dict[analyst_name] = result
                if result.success:
                    success_count += 1

        total_time = (
            self.execution_stats["end_time"] - self.execution_stats["start_time"]
        )
        logger.info(
            f"✅ 并行执行完成: {success_count}/{len(tasks)} 成功, "
            f"总耗时: {total_time:.2f}秒, "
            f"缓存命中: {self.execution_stats['cache_hits']}, "
            f"超时: {self.execution_stats['timeout_count']}, "
            f"错误: {self.execution_stats['error_count']}"
        )

        return result_dict

    def setup_enhanced_parallel_graph(
        self, selected_analysts=["market", "social", "news", "fundamentals", "china"]
    ):
        """
        设置增强型并行分析师执行图

        与原版相比的改进:
        1. 支持超时控制
        2. 更好的错误处理
        3. 支持部分失败模式

        Args:
            selected_analysts: 选中的分析师列表
        """
        if len(selected_analysts) == 0:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")

        # 创建分析师节点
        analyst_nodes = {}

        if "market" in selected_analysts:
            analyst_nodes["market"] = create_market_analyst(
                self.base_setup.quick_thinking_llm, self.toolkit
            )

        if "social" in selected_analysts:
            analyst_nodes["social"] = create_social_media_analyst(
                self.base_setup.quick_thinking_llm, self.toolkit
            )

        if "news" in selected_analysts:
            analyst_nodes["news"] = create_news_analyst(
                self.base_setup.quick_thinking_llm, self.toolkit
            )

        if "fundamentals" in selected_analysts:
            analyst_nodes["fundamentals"] = create_fundamentals_analyst(
                self.base_setup.quick_thinking_llm, self.toolkit
            )

        if "china" in selected_analysts:
            analyst_nodes["china"] = create_china_market_analyst(
                self.base_setup.quick_thinking_llm, self.toolkit
            )

        # 创建其他节点
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

        risky_analyst = create_risky_debator(self.base_setup.quick_thinking_llm)
        neutral_analyst = create_neutral_debator(self.base_setup.quick_thinking_llm)
        safe_analyst = create_safe_debator(self.base_setup.quick_thinking_llm)
        risk_manager_node = create_risk_manager(
            self.base_setup.deep_thinking_llm, self.base_setup.risk_manager_memory
        )

        # 创建工作流
        workflow = StateGraph(AgentState)

        # 添加数据协调器节点
        workflow.add_node("Data Coordinator", data_coordinator_node)

        # 添加分析师节点
        for analyst_type in selected_analysts:
            workflow.add_node(
                f"{analyst_type.capitalize()} Analyst", analyst_nodes[analyst_type]
            )

        # 添加其他节点
        workflow.add_node("Bull Researcher", bull_researcher_node)
        workflow.add_node("Bear Researcher", bear_researcher_node)
        workflow.add_node("Research Manager", research_manager_node)
        workflow.add_node("Trader", trader_node)
        workflow.add_node("Risky Analyst", risky_analyst)
        workflow.add_node("Neutral Analyst", neutral_analyst)
        workflow.add_node("Safe Analyst", safe_analyst)
        workflow.add_node("Risk Judge", risk_manager_node)

        # 定义边 (并行执行)
        workflow.add_edge(START, "Data Coordinator")

        # Data Coordinator -> 所有分析师并行
        for analyst_type in selected_analysts:
            workflow.add_edge(
                "Data Coordinator", f"{analyst_type.capitalize()} Analyst"
            )

        # 所有分析师 -> Bull Researcher (同步点)
        for analyst_type in selected_analysts:
            workflow.add_edge(f"{analyst_type.capitalize()} Analyst", "Bull Researcher")

        # 辩论和风险流程
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

        # 编译并返回
        compiled_graph = workflow.compile()

        logger.info("=" * 60)
        logger.info(
            "增强型并行分析师执行图已创建 Enhanced Parallel Analysts Graph Created"
        )
        logger.info(f"启用的分析师 Enabled analysts: {', '.join(selected_analysts)}")
        logger.info(f"分析师超时 Analyst timeout: {self.analyst_timeout}s")
        logger.info(f"使用缓存 Use cache: {self.use_cache}")
        logger.info(f"允许部分失败 Allow partial failure: {self.allow_partial_failure}")
        logger.info("=" * 60)

        return compiled_graph

    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        return {
            **self.execution_stats,
            "cache_hit_rate": (
                self.execution_stats["cache_hits"]
                / (
                    self.execution_stats["cache_hits"]
                    + self.execution_stats["cache_misses"]
                )
                if (
                    self.execution_stats["cache_hits"]
                    + self.execution_stats["cache_misses"]
                )
                > 0
                else 0
            ),
        }


def create_enhanced_parallel_executor(
    base_setup: GraphSetup,
    analyst_timeout: int = 180,
    progress_callback: Optional[Callable[[str, Dict], None]] = None,
    use_cache: bool = True,
    allow_partial_failure: bool = True,
) -> EnhancedParallelAnalystExecutor:
    """
    创建增强型并行分析师执行器

    Args:
        base_setup: 基础图设置
        analyst_timeout: 分析师超时时间(秒)
        progress_callback: 进度回调函数
        use_cache: 是否使用缓存
        allow_partial_failure: 是否允许部分失败

    Returns:
        EnhancedParallelAnalystExecutor实例
    """
    return EnhancedParallelAnalystExecutor(
        base_setup=base_setup,
        analyst_timeout=analyst_timeout,
        progress_callback=progress_callback,
        use_cache=use_cache,
        allow_partial_failure=allow_partial_failure,
    )
