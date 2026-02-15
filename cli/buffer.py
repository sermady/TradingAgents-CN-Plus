# -*- coding: utf-8 -*-
"""CLI消息缓冲区管理"""

import datetime
from collections import deque
from typing import Optional

# 常量定义
DEFAULT_MESSAGE_BUFFER_SIZE = 100


class MessageBuffer:
    """消息缓冲区：存储和管理分析过程中的消息、工具调用和报告"""

    def __init__(self, max_length: int = DEFAULT_MESSAGE_BUFFER_SIZE):
        """
        初始化消息缓冲区

        Args:
            max_length: 缓冲区最大长度
        """
        self.messages = deque(maxlen=max_length)
        self.tool_calls = deque(maxlen=max_length)
        self.current_report: Optional[str] = None
        self.final_report: Optional[str] = None  # 存储完整的最终报告
        self.agent_status = {
            # 分析师团队 | Analyst Team
            "Market Analyst": "pending",
            "Social Analyst": "pending",
            "News Analyst": "pending",
            "Fundamentals Analyst": "pending",
            # 研究团队 | Research Team
            "Bull Researcher": "pending",
            "Bear Researcher": "pending",
            "Research Manager": "pending",
            # 交易团队 | Trading Team
            "Trader": "pending",
            # 风险管理团队 | Risk Management Team
            "Risky Analyst": "pending",
            "Neutral Analyst": "pending",
            "Safe Analyst": "pending",
            # 投资组合管理团队 | Portfolio Management Team
            "Portfolio Manager": "pending",
        }
        self.current_agent: Optional[str] = None
        self.report_sections = {
            "market_report": None,
            "sentiment_report": None,
            "news_report": None,
            "fundamentals_report": None,
            "investment_plan": None,
            "trader_investment_plan": None,
            "final_trade_decision": None,
        }

    def add_message(self, message_type: str, content) -> None:
        """
        添加消息到缓冲区

        Args:
            message_type: 消息类型（如 "Reasoning", "Tool", "Error"）
            content: 消息内容
        """
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.messages.append((timestamp, message_type, content))

    def add_tool_call(self, tool_name: str, args) -> None:
        """
        添加工具调用记录

        Args:
            tool_name: 工具名称
            args: 工具参数
        """
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.tool_calls.append((timestamp, tool_name, args))

    def update_agent_status(self, agent: str, status: str) -> None:
        """
        更新智能体状态

        Args:
            agent: 智能体名称
            status: 状态（pending/in_progress/completed/error）
        """
        if agent in self.agent_status:
            self.agent_status[agent] = status
            self.current_agent = agent

    def update_report_section(self, section_name: str, content) -> None:
        """
        更新报告章节

        Args:
            section_name: 章节名称（如 "market_report"）
            content: 报告内容
        """
        if section_name in self.report_sections:
            self.report_sections[section_name] = content
            self._update_current_report()

    def _update_current_report(self) -> None:
        """更新当前报告（用于面板显示）"""
        # 对于面板显示，只显示最近更新的章节
        latest_section = None
        latest_content = None

        # 找到最近更新的章节
        for section, content in self.report_sections.items():
            if content is not None:
                latest_section = section
                latest_content = content

        if latest_section and latest_content:
            # 格式化当前章节以供显示
            section_titles = {
                "market_report": "Market Analysis",
                "sentiment_report": "Social Sentiment",
                "news_report": "News Analysis",
                "fundamentals_report": "Fundamentals Analysis",
                "investment_plan": "Research Team Decision",
                "trader_investment_plan": "Trading Team Plan",
                "final_trade_decision": "Portfolio Management Decision",
            }
            self.current_report = (
                f"### {section_titles[latest_section]}\n{latest_content}"
            )

        # 更新完整的最终报告
        self._update_final_report()

    def _update_final_report(self) -> None:
        """更新完整的最终报告"""
        report_parts = []

        # 分析师团队报告 | Analyst Team Reports
        if any(
            self.report_sections[section]
            for section in [
                "market_report",
                "sentiment_report",
                "news_report",
                "fundamentals_report",
            ]
        ):
            report_parts.append("## Analyst Team Reports")
            if self.report_sections["market_report"]:
                report_parts.append(
                    f"### Market Analysis\n{self.report_sections['market_report']}"
                )
            if self.report_sections["sentiment_report"]:
                report_parts.append(
                    f"### Social Sentiment\n{self.report_sections['sentiment_report']}"
                )
            if self.report_sections["news_report"]:
                report_parts.append(
                    f"### News Analysis\n{self.report_sections['news_report']}"
                )
            if self.report_sections["fundamentals_report"]:
                report_parts.append(
                    f"### Fundamentals Analysis\n{self.report_sections['fundamentals_report']}"
                )

        # 研究团队报告 | Research Team Reports
        if self.report_sections["investment_plan"]:
            report_parts.append("## Research Team Decision")
            report_parts.append(f"{self.report_sections['investment_plan']}")

        # 交易团队报告 | Trading Team Reports
        if self.report_sections["trader_investment_plan"]:
            report_parts.append("## Trading Team Plan")
            report_parts.append(f"{self.report_sections['trader_investment_plan']}")

        # 投资组合管理决策 | Portfolio Management Decision
        if self.report_sections["final_trade_decision"]:
            report_parts.append("## Portfolio Management Decision")
            report_parts.append(f"{self.report_sections['final_trade_decision']}")

        self.final_report = "\n\n".join(report_parts) if report_parts else None
