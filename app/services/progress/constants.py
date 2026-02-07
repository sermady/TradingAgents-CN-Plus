# -*- coding: utf-8 -*-
"""
分析进度管理常量定义

定义分析师执行顺序、状态转换规则等常量
借鉴上游 TradingAgents 项目设计思想:
- 统一状态转换逻辑
- 标准化分析师顺序
- 支持消息去重
"""

from typing import List, Dict, Set

# ==================== 分析师顺序定义 ====================

# 标准分析师执行顺序
# 注意：虽然是并行执行，但顺序用于：
# 1. 状态显示的一致性
# 2. 进度计算的优先级
# 3. 报告生成的顺序
ANALYST_ORDER: List[str] = [
    "market",       # 市场分析师 - 技术分析
    "social",       # 社交媒体分析师 - 情绪分析
    "news",         # 新闻分析师 - 消息面分析
    "fundamentals", # 基本面分析师 - 财务分析
    "china",        # 中国市场分析师 - A股特色指标
]

# 分析师显示名称映射
ANALYST_DISPLAY_NAMES: Dict[str, str] = {
    "market": "市场分析师",
    "social": "社交媒体分析师",
    "news": "新闻分析师",
    "fundamentals": "基本面分析师",
    "china": "中国市场分析师",
}

# 分析师报告字段映射
ANALYST_REPORT_MAP: Dict[str, str] = {
    "market": "market_report",
    "social": "sentiment_report",
    "news": "news_report",
    "fundamentals": "fundamentals_report",
    "china": "china_market_report",
}

# 研究团队顺序
RESEARCH_TEAM_ORDER: List[str] = [
    "bull_researcher",    # 看涨研究员
    "bear_researcher",    # 看跌研究员
    "research_manager",   # 研究经理
]

# 风险管理团队顺序
RISK_TEAM_ORDER: List[str] = [
    "risky_analyst",      # 激进分析师
    "safe_analyst",       # 保守分析师
    "neutral_analyst",    # 中性分析师
    "risk_manager",       # 风险经理
]

# 完整的分析流程顺序
ANALYSIS_PHASES: List[str] = [
    "data_coordination",  # 数据协调
    "analyst_team",       # 分析师团队
    "research_debate",    # 研究辩论
    "trader_decision",    # 交易员决策
    "risk_debate",        # 风险辩论
    "final_decision",     # 最终决策
]

# ==================== 状态定义 ====================

# 分析师状态
class AnalystStatus:
    PENDING = "pending"       # 等待执行
    IN_PROGRESS = "in_progress"  # 执行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败

# 任务状态
class TaskStatus:
    PENDING = "pending"       # 等待中
    RUNNING = "running"       # 运行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"   # 已取消

# ==================== 消息去重配置 ====================

# 消息去重缓存大小（最近N条消息）
MESSAGE_DEDUP_CACHE_SIZE: int = 100

# 消息去重时间窗口（秒）
MESSAGE_DEDUP_WINDOW: int = 60

# 需要检查重复的字段
MESSAGE_DEDUP_FIELDS: Set[str] = {
    "id",
    "timestamp",
    "content_hash",
}
