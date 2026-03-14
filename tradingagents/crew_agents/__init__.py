# -*- coding: utf-8 -*-
"""
CrewAI 多智能体模块

整合自 a_share_investment_system 项目，提供：
- 多智能体协作编排 (crew.py)
- SMART 模式 LLM 分配 (llm/)
- 智能协调器 (coordination/)
- 智能体日志 (agent_logging/)
"""

from .crew import AShareInvestmentCrew

__all__ = ["AShareInvestmentCrew"]