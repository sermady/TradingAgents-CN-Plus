# -*- coding: utf-8 -*-
from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict
from tradingagents.agents import *
from langgraph.graph import MessagesState

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


# Researcher team state
class InvestDebateState(TypedDict):
    bull_history: Annotated[
        str, "Bullish Conversation history"
    ]  # Bullish Conversation history
    bear_history: Annotated[
        str, "Bearish Conversation history"
    ]  # Bullish Conversation history
    history: Annotated[str, "Conversation history"]  # Conversation history
    current_response: Annotated[str, "Latest response"]  # Last response
    judge_decision: Annotated[str, "Final judge decision"]  # Last response
    count: Annotated[int, "Length of the current conversation"]  # Conversation length
    # Phase 2.2: 证据强度和数据引用跟踪
    evidence_strength: Annotated[float, "Overall evidence strength (0-1)"]  # 证据强度评分
    citations: Annotated[
        list, "List of data citations with source and confidence"
    ]  # 数据引用列表


# Risk management team state
class RiskDebateState(TypedDict):
    risky_history: Annotated[
        str, "Risky Agent's Conversation history"
    ]  # Conversation history
    safe_history: Annotated[
        str, "Safe Agent's Conversation history"
    ]  # Conversation history
    neutral_history: Annotated[
        str, "Neutral Agent's Conversation history"
    ]  # Conversation history
    history: Annotated[str, "Conversation history"]  # Conversation history
    latest_speaker: Annotated[str, "Analyst that spoke last"]
    current_risky_response: Annotated[
        str, "Latest response by the risky analyst"
    ]  # Last response
    current_safe_response: Annotated[
        str, "Latest response by the safe analyst"
    ]  # Last response
    current_neutral_response: Annotated[
        str, "Latest response by the neutral analyst"
    ]  # Last response
    judge_decision: Annotated[str, "Judge's decision"]
    count: Annotated[int, "Length of the current conversation"]  # Conversation length
    # Phase P1-4: 辩论质量评估
    argument_quality: Annotated[float, "Cumulative argument quality score (0-1)"]  # 累积论点质量


class AgentState(MessagesState):
    company_of_interest: Annotated[str, "Company that we are interested in trading"]
    trade_date: Annotated[str, "What date we are trading at"]

    sender: Annotated[str, "Agent that sent this message"]

    # Centralized Data Store (Pre-fetched by DataCoordinator)
    # 文本数据通道 (向后兼容，供分析师 LLM 使用)
    market_data: Annotated[str, "Raw technical analysis data"]
    financial_data: Annotated[str, "Raw fundamental data"]
    news_data: Annotated[str, "Raw aggregated news data"]
    sentiment_data: Annotated[str, "Raw social sentiment data"]
    china_market_data: Annotated[str, "Raw China A-share market features data"]

    # 结构化数据通道 (P0-1: 供 Trader/SignalProcessor/QualityChecker 精确使用)
    # 这些字段存储从 DataFrame 解析出的结构化数值，避免 text→LLM→regex 的精度丢失
    market_data_structured: Annotated[
        Dict[str, Any], "Parsed market data (prices, indicators, volume)"
    ] = {}
    financial_data_structured: Annotated[
        Dict[str, Any], "Parsed fundamental data (PE, PB, PS, margins)"
    ] = {}
    china_market_data_structured: Annotated[
        Dict[str, Any], "Parsed China market features (turnover, volume_ratio)"
    ] = {}

    # 数据源和问题跟踪 (从 DataCoordinator 传递)
    data_sources: Annotated[
        Dict[str, str], "Data source used for each data type"
    ] = {}
    data_issues: Annotated[
        Dict[str, List[Dict[str, Any]]], "Quality issues per data type"
    ] = {}
    data_metadata: Annotated[
        Dict[str, Any], "Additional metadata (PS correction, volume unit, etc.)"
    ] = {}

    # P1-2: 量化风险指标 (由 DataCoordinator 计算并注入)
    quant_risk_metrics: Annotated[
        Dict[str, Any], "Quantitative risk metrics (VaR, CVaR, MDD, Vol, Beta, Sharpe)"
    ] = {}
    quant_risk_text: Annotated[
        str, "Formatted risk metrics text for injection into debate prompts"
    ] = ""

    # research step
    market_report: Annotated[str, "Report from the Market Analyst"]
    sentiment_report: Annotated[str, "Report from the Social Media Analyst"]
    news_report: Annotated[
        str, "Report from the News Researcher of current world affairs"
    ]
    fundamentals_report: Annotated[str, "Report from the Fundamentals Researcher"]
    china_market_report: Annotated[str, "Report from the China Market Analyst"]

    # 🔧 死循环防护: 工具调用计数器
    # 注：虽然重构后分析师使用 Data Coordinator 预取数据，不再直接调用工具，
    # 但保留这些字段作为安全防护机制，防止意外情况下的无限循环
    # 这些字段由 conditional_logic.py 中的死循环检测逻辑使用
    market_tool_call_count: Annotated[
        int, "Market analyst tool call counter (safety mechanism)"
    ] = 0
    news_tool_call_count: Annotated[
        int, "News analyst tool call counter (safety mechanism)"
    ] = 0
    sentiment_tool_call_count: Annotated[
        int, "Social media analyst tool call counter (safety mechanism)"
    ] = 0
    fundamentals_tool_call_count: Annotated[
        int, "Fundamentals analyst tool call counter (safety mechanism)"
    ] = 0

    # researcher team discussion step
    investment_debate_state: Annotated[
        InvestDebateState, "Current state of the debate on if to invest or not"
    ]
    investment_plan: Annotated[str, "Plan generated by the Analyst"]

    trader_investment_plan: Annotated[str, "Plan generated by the Trader"]

    # risk management team discussion step
    risk_debate_state: Annotated[
        RiskDebateState, "Current state of the debate on evaluating risk"
    ]
    final_trade_decision: Annotated[str, "Final decision made by the Risk Analysts"]

    # ========== 数据质量风控字段 (Phase 1.1/1.4) ==========
    data_quality_score: Annotated[
        float, "Data quality score (0.0-1.0)"
    ] = 1.0  # 默认满分
    data_quality_grade: Annotated[
        str, "Data quality grade (A/B/C/D/F)"
    ] = "A"  # 默认A级
    data_quality_issues: Annotated[
        List[str], "List of data quality issues"
    ] = []  # 默认无问题

    # P2-3: 技术信号预计算摘要 (由 DataCoordinator 计算, 注入分析师 prompt)
    technical_signals: Annotated[
        Dict[str, Any], "Pre-computed technical signals (trend, signals list, summary)"
    ] = {}
    technical_signals_text: Annotated[
        str, "Formatted technical signals text for analyst prompt injection"
    ] = ""
