# -*- coding: utf-8 -*-
# TradingAgents/graph/performance.py
"""
性能统计和报告相关逻辑
"""

from typing import Dict, Any, List, Tuple

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("agents")


class PerformanceTracker:
    """性能追踪器"""

    @staticmethod
    def build_performance_data(
        node_timings: Dict[str, float], total_elapsed: float, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """构建性能数据结构

        Args:
            node_timings: 每个节点的执行时间字典
            total_elapsed: 总执行时间
            config: 配置字典

        Returns:
            性能数据字典
        """
        # 节点分类（注意：风险管理节点要先于分析师节点判断，因为它们也包含'Analyst'）
        analyst_nodes = {}
        tool_nodes = {}
        msg_clear_nodes = {}
        research_nodes = {}
        trader_nodes = {}
        risk_nodes = {}
        other_nodes = {}

        for node_name, elapsed in node_timings.items():
            # 优先匹配风险管理团队（因为它们也包含'Analyst'）
            if (
                "Risky" in node_name
                or "Safe" in node_name
                or "Neutral" in node_name
                or "Risk Judge" in node_name
            ):
                risk_nodes[node_name] = elapsed
            # 然后匹配分析师团队
            elif "Analyst" in node_name:
                analyst_nodes[node_name] = elapsed
            # 工具节点
            elif node_name.startswith("tools_"):
                tool_nodes[node_name] = elapsed
            # 消息清理节点
            elif node_name.startswith("Msg Clear"):
                msg_clear_nodes[node_name] = elapsed
            # 研究团队
            elif "Researcher" in node_name or "Research Manager" in node_name:
                research_nodes[node_name] = elapsed
            # 交易团队
            elif "Trader" in node_name:
                trader_nodes[node_name] = elapsed
            # 其他节点
            else:
                other_nodes[node_name] = elapsed

        # 计算统计数据
        slowest_node = (
            max(node_timings.items(), key=lambda x: x[1]) if node_timings else (None, 0)
        )
        fastest_node = (
            min(node_timings.items(), key=lambda x: x[1]) if node_timings else (None, 0)
        )
        avg_time = sum(node_timings.values()) / len(node_timings) if node_timings else 0

        return {
            "total_time": round(total_elapsed, 2),
            "total_time_minutes": round(total_elapsed / 60, 2),
            "node_count": len(node_timings),
            "average_node_time": round(avg_time, 2),
            "slowest_node": {
                "name": slowest_node[0],
                "time": round(slowest_node[1], 2),
            }
            if slowest_node[0]
            else None,
            "fastest_node": {
                "name": fastest_node[0],
                "time": round(fastest_node[1], 2),
            }
            if fastest_node[0]
            else None,
            "node_timings": {k: round(v, 2) for k, v in node_timings.items()},
            "category_timings": {
                "analyst_team": {
                    "nodes": {k: round(v, 2) for k, v in analyst_nodes.items()},
                    "total": round(sum(analyst_nodes.values()), 2),
                    "percentage": round(
                        sum(analyst_nodes.values()) / total_elapsed * 100, 1
                    )
                    if total_elapsed > 0
                    else 0,
                },
                "tool_calls": {
                    "nodes": {k: round(v, 2) for k, v in tool_nodes.items()},
                    "total": round(sum(tool_nodes.values()), 2),
                    "percentage": round(
                        sum(tool_nodes.values()) / total_elapsed * 100, 1
                    )
                    if total_elapsed > 0
                    else 0,
                },
                "message_clearing": {
                    "nodes": {k: round(v, 2) for k, v in msg_clear_nodes.items()},
                    "total": round(sum(msg_clear_nodes.values()), 2),
                    "percentage": round(
                        sum(msg_clear_nodes.values()) / total_elapsed * 100, 1
                    )
                    if total_elapsed > 0
                    else 0,
                },
                "research_team": {
                    "nodes": {k: round(v, 2) for k, v in research_nodes.items()},
                    "total": round(sum(research_nodes.values()), 2),
                    "percentage": round(
                        sum(research_nodes.values()) / total_elapsed * 100, 1
                    )
                    if total_elapsed > 0
                    else 0,
                },
                "trader_team": {
                    "nodes": {k: round(v, 2) for k, v in trader_nodes.items()},
                    "total": round(sum(trader_nodes.values()), 2),
                    "percentage": round(
                        sum(trader_nodes.values()) / total_elapsed * 100, 1
                    )
                    if total_elapsed > 0
                    else 0,
                },
                "risk_management_team": {
                    "nodes": {k: round(v, 2) for k, v in risk_nodes.items()},
                    "total": round(sum(risk_nodes.values()), 2),
                    "percentage": round(
                        sum(risk_nodes.values()) / total_elapsed * 100, 1
                    )
                    if total_elapsed > 0
                    else 0,
                },
                "other": {
                    "nodes": {k: round(v, 2) for k, v in other_nodes.items()},
                    "total": round(sum(other_nodes.values()), 2),
                    "percentage": round(
                        sum(other_nodes.values()) / total_elapsed * 100, 1
                    )
                    if total_elapsed > 0
                    else 0,
                },
            },
            "llm_config": {
                "provider": config.get("llm_provider", "unknown"),
                "deep_think_model": config.get("deep_think_llm", "unknown"),
                "quick_think_model": config.get("quick_think_llm", "unknown"),
            },
        }

    @staticmethod
    def print_timing_summary(
        node_timings: Dict[str, float], total_elapsed: float, config: Dict[str, Any]
    ):
        """打印详细的时间统计报告

        Args:
            node_timings: 每个节点的执行时间字典
            total_elapsed: 总执行时间
            config: 配置字典
        """
        logger.info("🔍 [_print_timing_summary] 方法被调用")
        logger.info(f"🔍 [_print_timing_summary] node_timings 数量: " + str(len(node_timings)))
        logger.info("🔍 [_print_timing_summary] total_elapsed: " + str(total_elapsed))

        logger.info("=" * 80)
        logger.info("⏱️  分析性能统计报告")
        logger.info("=" * 80)

        # 节点分类（注意：风险管理节点要先于分析师节点判断，因为它们也包含'Analyst'）
        analyst_nodes = []
        tool_nodes = []
        msg_clear_nodes = []
        research_nodes = []
        trader_nodes = []
        risk_nodes = []
        other_nodes = []

        for node_name, elapsed in node_timings.items():
            # 优先匹配风险管理团队（因为它们也包含'Analyst'）
            if (
                "Risky" in node_name
                or "Safe" in node_name
                or "Neutral" in node_name
                or "Risk Judge" in node_name
            ):
                risk_nodes.append((node_name, elapsed))
            # 然后匹配分析师团队
            elif "Analyst" in node_name:
                analyst_nodes.append((node_name, elapsed))
            # 工具节点
            elif node_name.startswith("tools_"):
                tool_nodes.append((node_name, elapsed))
            # 消息清理节点
            elif node_name.startswith("Msg Clear"):
                msg_clear_nodes.append((node_name, elapsed))
            # 研究团队
            elif "Researcher" in node_name or "Research Manager" in node_name:
                research_nodes.append((node_name, elapsed))
            # 交易团队
            elif "Trader" in node_name:
                trader_nodes.append((node_name, elapsed))
            # 其他节点
            else:
                other_nodes.append((node_name, elapsed))

        # 打印分类统计
        def print_category(title: str, nodes: List[Tuple[str, float]]):
            if not nodes:
                return
            logger.info(f"\n📊 {title}")
            logger.info("-" * 80)
            total_category_time = sum(t for _, t in nodes)
            for node_name, elapsed in sorted(nodes, key=lambda x: x[1], reverse=True):
                percentage = (elapsed / total_elapsed * 100) if total_elapsed > 0 else 0
                logger.info(
                    f"  • {node_name:40s} {elapsed:8.2f}秒  ({percentage:5.1f}%)"
                )
            logger.info(
                f"  {'小计':40s} {total_category_time:8.2f}秒  ({total_category_time / total_elapsed * 100:5.1f}%)"
            )

        print_category("分析师团队", analyst_nodes)
        print_category("工具调用", tool_nodes)
        print_category("消息清理", msg_clear_nodes)
        print_category("研究团队", research_nodes)
        print_category("交易团队", trader_nodes)
        print_category("风险管理团队", risk_nodes)
        print_category("其他节点", other_nodes)

        # 打印总体统计
        logger.info("\n" + "=" * 80)
        logger.info(
            f"🎯 总执行时间: {total_elapsed:.2f}秒 ({total_elapsed / 60:.2f}分钟)"
        )
        logger.info(f"📈 节点总数: {len(node_timings)}")
        if node_timings:
            avg_time = sum(node_timings.values()) / len(node_timings)
            logger.info(f"⏱️  平均节点耗时: {avg_time:.2f}秒")
            slowest_node = max(node_timings.items(), key=lambda x: x[1])
            logger.info(f"🐌 最慢节点: {slowest_node[0]} ({slowest_node[1]:.2f}秒)")
            fastest_node = min(node_timings.items(), key=lambda x: x[1])
            logger.info(f"⚡ 最快节点: {fastest_node[0]} ({fastest_node[1]:.2f}秒)")

        # 打印LLM配置信息
        logger.info(f"\n🤖 LLM配置:")
        logger.info(f"  • 提供商: {config.get('llm_provider', 'unknown')}")
        logger.info(f"  • 深度思考模型: {config.get('deep_think_llm', 'unknown')}")
        logger.info(
            f"  • 快速思考模型: {config.get('quick_think_llm', 'unknown')}"
        )
        logger.info("=" * 80)
