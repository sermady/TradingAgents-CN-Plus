#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析结果格式化工具

负责将分析结果格式化为适合显示的格式
"""

from tradingagents.utils.logging_manager import get_logger

logger = get_logger("web.formatter")


def translate_analyst_labels(text):
    """将分析师的英文标签转换为中文"""
    if not text:
        return text

    # 分析师标签翻译映射
    translations = {
        "Bull Analyst:": "看涨分析师:",
        "Bear Analyst:": "看跌分析师:",
        "Risky Analyst:": "激进风险分析师:",
        "Safe Analyst:": "保守风险分析师:",
        "Neutral Analyst:": "中性风险分析师:",
        "Research Manager:": "研究经理:",
        "Portfolio Manager:": "投资组合经理:",
        "Risk Judge:": "风险管理委员会:",
        "Trader:": "交易员:",
    }

    # 替换所有英文标签
    for english, chinese in translations.items():
        text = text.replace(english, chinese)

    return text


def extract_risk_assessment(state):
    """从分析状态中提取风险评估数据"""
    try:
        risk_debate_state = state.get("risk_debate_state", {})

        if not risk_debate_state:
            return None

        # 提取各个风险分析师的观点并进行中文化
        risky_analysis = translate_analyst_labels(
            risk_debate_state.get("risky_history", "")
        )
        safe_analysis = translate_analyst_labels(
            risk_debate_state.get("safe_history", "")
        )
        neutral_analysis = translate_analyst_labels(
            risk_debate_state.get("neutral_history", "")
        )
        judge_decision = translate_analyst_labels(
            risk_debate_state.get("judge_decision", "")
        )

        # 格式化风险评估报告
        risk_assessment = f"""
## ⚠️ 风险评估报告

### 🔴 激进风险分析师观点
{risky_analysis if risky_analysis else "暂无激进风险分析"}

### 🟡 中性风险分析师观点
{neutral_analysis if neutral_analysis else "暂无中性风险分析"}

### 🟢 保守风险分析师观点
{safe_analysis if safe_analysis else "暂无保守风险分析"}

### 🏛️ 风险管理委员会最终决议
{judge_decision if judge_decision else "暂无风险管理决议"}

---
*风险评估基于多角度分析，请结合个人风险承受能力做出投资决策*
        """.strip()

        return risk_assessment

    except Exception as e:
        logger.info(f"提取风险评估数据时出错: {e}")
        return None


def format_analysis_results(results):
    """格式化分析结果用于显示"""

    if not results["success"]:
        return {"error": results["error"], "success": False}

    state = results["state"]
    decision = results["decision"]

    # 提取关键信息
    # decision 可能是字符串（如 "BUY", "SELL", "HOLD"）或字典
    if isinstance(decision, str):
        # 将英文投资建议转换为中文
        action_translation = {
            "BUY": "买入",
            "SELL": "卖出",
            "HOLD": "持有",
            "buy": "买入",
            "sell": "卖出",
            "hold": "持有",
        }
        action = action_translation.get(decision.strip(), decision.strip())

        formatted_decision = {
            "action": action,
            "confidence": 0.7,  # 默认置信度
            "risk_score": 0.3,  # 默认风险分数
            "target_price": None,  # 字符串格式没有目标价格
            "reasoning": f"基于AI分析，建议{decision.strip().upper()}",
        }
    elif isinstance(decision, dict):
        # 处理目标价格 - 确保正确提取数值
        target_price = decision.get("target_price")
        if target_price is not None and target_price != "N/A":
            try:
                # 尝试转换为浮点数
                if isinstance(target_price, str):
                    # 移除货币符号和空格
                    clean_price = (
                        target_price.replace("$", "")
                        .replace("¥", "")
                        .replace("￥", "")
                        .strip()
                    )
                    target_price = (
                        float(clean_price)
                        if clean_price and clean_price != "None"
                        else None
                    )
                elif isinstance(target_price, (int, float)):
                    target_price = float(target_price)
                else:
                    target_price = None
            except (ValueError, TypeError):
                target_price = None
        else:
            target_price = None

        # 将英文投资建议转换为中文
        action_translation = {
            "BUY": "买入",
            "SELL": "卖出",
            "HOLD": "持有",
            "buy": "买入",
            "sell": "卖出",
            "hold": "持有",
        }
        action = decision.get("action", "持有")
        chinese_action = action_translation.get(action, action)

        formatted_decision = {
            "action": chinese_action,
            "confidence": decision.get("confidence", 0.5),
            "risk_score": decision.get("risk_score", 0.3),
            "target_price": target_price,
            "reasoning": decision.get("reasoning", "暂无分析推理"),
        }
    else:
        # 处理其他类型
        formatted_decision = {
            "action": "持有",
            "confidence": 0.5,
            "risk_score": 0.3,
            "target_price": None,
            "reasoning": f"分析结果: {str(decision)}",
        }

    # 格式化状态信息
    formatted_state = {}

    # 处理各个分析模块的结果 - 包含完整的智能体团队分析
    analysis_keys = [
        "market_report",
        "fundamentals_report",
        "sentiment_report",
        "news_report",
        "risk_assessment",
        "investment_plan",
        # 添加缺失的团队决策数据，确保与CLI端一致
        "investment_debate_state",  # 研究团队辩论（多头/空头研究员）
        "trader_investment_plan",  # 交易团队计划
        "risk_debate_state",  # 风险管理团队决策
        "final_trade_decision",  # 最终交易决策
    ]

    # 添加调试信息
    logger.debug(f"🔍 [格式化调试] 原始state中的键: {list(state.keys())}")
    for key in state.keys():
        if isinstance(state[key], str):
            logger.debug(f"🔍 [格式化调试] {key}: 字符串长度 {len(state[key])}")
        elif isinstance(state[key], dict):
            logger.debug(
                f"🔍 [格式化调试] {key}: 字典，包含键 {list(state[key].keys())}"
            )
        else:
            logger.debug(f"🔍 [格式化调试] {key}: {type(state[key])}")

    for key in analysis_keys:
        if key in state:
            # 对文本内容进行中文化处理
            content = state[key]
            if isinstance(content, str):
                content = translate_analyst_labels(content)
                logger.debug(
                    f"🔍 [格式化调试] 处理字符串字段 {key}: 长度 {len(content)}"
                )
            elif isinstance(content, dict):
                logger.debug(
                    f"🔍 [格式化调试] 处理字典字段 {key}: 包含键 {list(content.keys())}"
                )
            formatted_state[key] = content
        elif key == "risk_assessment":
            # 特殊处理：从 risk_debate_state 生成 risk_assessment
            risk_assessment = extract_risk_assessment(state)
            if risk_assessment:
                formatted_state[key] = risk_assessment
        else:
            logger.debug(f"🔍 [格式化调试] 缺失字段: {key}")

    return {
        "stock_symbol": results["stock_symbol"],
        "decision": formatted_decision,
        "state": formatted_state,
        "success": True,
        # 将配置信息放在顶层，供前端直接访问
        "analysis_date": results["analysis_date"],
        "analysts": results["analysts"],
        "research_depth": results["research_depth"],
        "llm_provider": results.get("llm_provider", "dashscope"),
        "llm_model": results["llm_model"],
        "metadata": {
            "analysis_date": results["analysis_date"],
            "analysts": results["analysts"],
            "research_depth": results["research_depth"],
            "llm_provider": results.get("llm_provider", "dashscope"),
            "llm_model": results["llm_model"],
        },
    }
