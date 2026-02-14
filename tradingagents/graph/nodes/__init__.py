# -*- coding: utf-8 -*-
"""
TradingAgents/graph/nodes

节点定义模块

注意：实际节点创建逻辑在 tradingagents/graph/setup.py 中
此模块提供类型定义和辅助工具
"""

from typing import Dict, Any, Callable

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("agents")


class NodeFactory:
    """节点工厂类"""

    @staticmethod
    def create_analyst_nodes(selected_analysts: list, llm, toolkit):
        """创建分析师节点

        Args:
            selected_analysts: 选定的分析师列表
            llm: 语言模型
            toolkit: 工具包

        Returns:
            分析师节点字典
        """
        from tradingagents.agents import (
            create_market_analyst,
            create_social_media_analyst,
            create_news_analyst,
            create_fundamentals_analyst,
            create_china_market_analyst,
        )

        analyst_nodes = {}

        if "market" in selected_analysts:
            logger.debug(f"📈 [DEBUG] Setup Market Analyst")
            analyst_nodes["market"] = create_market_analyst(llm, toolkit)

        if "social" in selected_analysts:
            logger.debug(f"💬 [DEBUG] Setup Social Media Analyst")
            analyst_nodes["social"] = create_social_media_analyst(llm, toolkit)

        if "news" in selected_analysts:
            logger.debug(f"📰 [DEBUG] Setup News Analyst")
            analyst_nodes["news"] = create_news_analyst(llm, toolkit)

        if "fundamentals" in selected_analysts:
            logger.debug(f"💼 [DEBUG] Setup Fundamentals Analyst")
            analyst_nodes["fundamentals"] = create_fundamentals_analyst(llm, toolkit)

        if "china" in selected_analysts:
            logger.debug(f"🇨🇳 [DEBUG] Setup China Market Analyst")
            analyst_nodes["china"] = create_china_market_analyst(llm, toolkit)

        return analyst_nodes
