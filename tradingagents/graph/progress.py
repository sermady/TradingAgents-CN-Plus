# -*- coding: utf-8 -*-
# TradingAgents/graph/progress.py
"""
进度更新和回调相关逻辑
"""

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("agents")


class ProgressManager:
    """进度管理器"""

    @staticmethod
    def send_progress_update(chunk, progress_callback):
        """发送进度更新到回调函数

        LangGraph stream 返回的 chunk 格式：{node_name: {...}}
        节点名称示例：
        - "Market Analyst", "Fundamentals Analyst", "News Analyst", "Social Analyst"
        - "tools_market", "tools_fundamentals", "tools_news", "tools_social"
        - "Msg Clear Market", "Msg Clear Fundamentals", "Msg Clear News", etc.
        - "Bull Researcher", "Bear Researcher", "Research Manager"
        - "Trader"
        - "Risky Analyst", "Safe Analyst", "Neutral Analyst", "Risk Judge"
        """
        try:
            # 从chunk中提取当前执行的节点信息
            if not isinstance(chunk, dict):
                return

            # 获取第一个非特殊键作为节点名
            node_name = None
            for key in chunk.keys():
                if not key.startswith("__"):
                    node_name = key
                    break

            if not node_name:
                return

            logger.info(f"🔍 [Progress] 节点名称: {node_name}")

            # 检查是否为结束节点
            if "__end__" in chunk:
                logger.info(f"📊 [Progress] 检测到__end__节点")
                progress_callback("📊 生成报告")
                return

            # 节点名称映射表（匹配 LangGraph 实际节点名）
            node_mapping = {
                # 分析师节点
                "Market Analyst": "📊 市场分析师",
                "Fundamentals Analyst": "💼 基本面分析师",
                "News Analyst": "📰 新闻分析师",
                "Social Analyst": "💬 社交媒体分析师",
                # 工具节点（不发送进度更新，避免重复）
                "tools_market": None,
                "tools_fundamentals": None,
                "tools_news": None,
                "tools_social": None,
                # 消息清理节点（不发送进度更新）
                "Msg Clear Market": None,
                "Msg Clear Fundamentals": None,
                "Msg Clear News": None,
                "Msg Clear Social": None,
                # 研究员节点
                "Bull Researcher": "🐂 看涨研究员",
                "Bear Researcher": "🐻 看跌研究员",
                "Research Manager": "👔 研究经理",
                # 交易员节点
                "Trader": "💼 交易员决策",
                # 风险评估节点
                "Risky Analyst": "🔥 激进风险评估",
                "Safe Analyst": "🛡️ 保守风险评估",
                "Neutral Analyst": "⚖️ 中性风险评估",
                "Risk Judge": "🎯 风险经理",
            }

            # 查找映射的消息
            message = node_mapping.get(node_name)

            if message is None:
                # None 表示跳过（工具节点、消息清理节点）
                logger.debug(f"⏭️ [Progress] 跳过节点: {node_name}")
                return

            if message:
                # 发送进度更新
                logger.info(f"📤 [Progress] 发送进度更新: {message}")
                progress_callback(message)
            else:
                # 未知节点，使用节点名称
                logger.warning(f"⚠️ [Progress] 未知节点: {node_name}")
                progress_callback(f"🔍 {node_name}")

        except Exception as e:
            logger.error(f"❌ 进度更新失败: {e}", exc_info=True)
