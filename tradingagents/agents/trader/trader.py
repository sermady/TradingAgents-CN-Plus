# -*- coding: utf-8 -*-
import functools
import time
import json
import re
from typing import Optional, Tuple

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.time_utils import get_chinese_date

logger = get_logger("default")


def extract_trading_decision(
    content: str,
    current_price: Optional[float] = None,
    data_quality_score: float = 100.0,
) -> dict:
    """
    从交易决策内容中提取结构化信息，并自动填充缺失字段

    Args:
        content: LLM返回的交易决策内容
        current_price: 当前股价（用于自动计算目标价）
        data_quality_score: 数据质量评分 (0-100)，低质量数据会降低置信度 (Phase 1.1)

    Returns:
        dict: 包含提取的结构化信息
            - recommendation: str (买入/持有/卖出/未知)
            - target_price: float or None
            - target_price_range: str or None
            - confidence: float or None
            - risk_score: float or None
            - warnings: list of str
    """
    result = {
        "recommendation": "未知",
        "target_price": None,
        "target_price_range": None,
        "confidence": None,
        "risk_score": None,
        "warnings": [],
    }

    # 1. 提取投资建议
    recommendation_patterns = [
        r"最终交易建议[：:\s]*\*{0,2}(买入|持有|卖出)\*{0,2}",
        r"投资建议[：:\s]*\*{0,2}(买入|持有|卖出)\*{0,2}",
        r"建议[：:\s]*\*{0,2}(买入|持有|卖出)\*{0,2}",
        r"\*{2}(买入|持有|卖出)\*{2}",
        r"决策[：:\s]*\*{0,2}(买入|持有|卖出)\*{0,2}",
    ]

    for pattern in recommendation_patterns:
        match = re.search(pattern, content)
        if match:
            result["recommendation"] = match.group(1)
            break

    if result["recommendation"] == "未知":
        result["warnings"].append("未找到明确的投资建议")

    # 2. 提取目标价位
    price_patterns = [
        r"目标价[位格]?[：:\s]*[¥\$￥]?\s*(\d+\.?\d*)",
        r"目标[：:\s]*[¥\$￥]?\s*(\d+\.?\d*)",
        r"价格目标[：:\s]*[¥\$￥]?\s*(\d+\.?\d*)",
        r"[¥\$￥]\s*(\d+\.?\d*)\s*[-~到至]\s*[¥\$￥]?\s*(\d+\.?\d*)",  # 价格区间
    ]

    for pattern in price_patterns:
        match = re.search(pattern, content)
        if match:
            if len(match.groups()) >= 2 and match.group(2):
                # 价格区间
                result["target_price_range"] = f"¥{match.group(1)}-{match.group(2)}"
            else:
                result["target_price"] = float(match.group(1))
            break

    # 如果没有找到目标价但有当前股价，自动计算
    if (
        result["target_price"] is None
        and result["target_price_range"] is None
        and current_price
    ):
        if result["recommendation"] == "买入":
            # 买入时，目标价通常比当前价高 10-30%
            result["target_price"] = round(current_price * 1.15, 2)
            result["warnings"].append(
                f"自动计算目标价（买入）: {result['target_price']}"
            )
        elif result["recommendation"] == "卖出":
            # 卖出时，目标价通常比当前价低 10-20%
            result["target_price"] = round(current_price * 0.9, 2)
            result["warnings"].append(
                f"自动计算目标价（卖出）: {result['target_price']}"
            )
        elif result["recommendation"] == "持有":
            # 持有时，给出价格区间
            low = round(current_price * 0.95, 2)
            high = round(current_price * 1.05, 2)
            result["target_price_range"] = f"¥{low}-{high}"
            result["warnings"].append(
                f"自动计算目标区间（持有）: {result['target_price_range']}"
            )

    # 3. 提取置信度 - 支持多种格式
    confidence_patterns = [
        # 标准格式
        r"置信度[：:\s]*(\d*\.?\d+)",
        r"信心程度[：:\s]*(\d*\.?\d+)",
        r"confidence[：:\s]*(\d*\.?\d+)",
        # 百分比格式
        r"置信度[：:\s]*(\d+)%",
        r"信心程度[：:\s]*(\d+)%",
        r"confidence[：:\s]*(\d+)%",
        # 带百分号的浮点数
        r"置信度[：:\s]*(\d+\.\d+)%",
        # Markdown格式
        r"\*\*置信度\*\*[：:\s]*(\d*\.?\d+)",
        r"\*\*confidence\*\*[：:\s]*(\d*\.?\d+)",
        # 表格格式
        r"\|\s*置信度\s*\|\s*(\d*\.?\d+)\s*\|",
        r"\|\s*confidence\s*\|\s*(\d*\.?\d+)\s*\|",
    ]

    for pattern in confidence_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            val = float(match.group(1))
            if 0 <= val <= 1:
                result["confidence"] = val
                break
            elif val > 1 and val <= 100:
                # 可能是百分比形式
                result["confidence"] = val / 100
                break

    # 如果没有找到置信度，使用默认值
    if result["confidence"] is None:
        if result["recommendation"] == "买入":
            result["confidence"] = 0.7
        elif result["recommendation"] == "卖出":
            result["confidence"] = 0.65
        else:
            result["confidence"] = 0.5
        result["warnings"].append(f"使用默认置信度: {result['confidence']}")

    # ========== Phase 1.1: 根据数据质量评分调整置信度 ==========
    original_confidence = result["confidence"]
    if data_quality_score < 60:  # F级
        result["confidence"] = result["confidence"] * 0.8  # 降低20%
        result["warnings"].append(
            f"数据质量评分低({data_quality_score:.1f}分，F级)，置信度从{original_confidence:.2f}调整为{result['confidence']:.2f}"
        )
    elif data_quality_score < 70:  # D级
        result["confidence"] = result["confidence"] * 0.9  # 降低10%
        result["warnings"].append(
            f"数据质量评分边缘({data_quality_score:.1f}分，D级)，置信度从{original_confidence:.2f}调整为{result['confidence']:.2f}"
        )
    elif data_quality_score >= 90:  # A级
        # 高质量数据可以略微提升置信度，但不超过0.95
        result["confidence"] = min(result["confidence"] * 1.05, 0.95)

    # 4. 提取风险评分 - 支持多种格式
    risk_patterns = [
        # 标准格式
        r"风险评分[：:\s]*(\d*\.?\d+)",
        r"风险等级[：:\s]*(\d*\.?\d+)",
        r"risk[：:\s]*(\d*\.?\d+)",
        # 百分比格式
        r"风险评分[：:\s]*(\d+)%",
        r"风险等级[：:\s]*(\d+)%",
        r"risk[：:\s]*(\d+)%",
        # 带百分号的浮点数
        r"风险评分[：:\s]*(\d+\.\d+)%",
        # Markdown格式
        r"\*\*风险评分\*\*[：:\s]*(\d*\.?\d+)",
        r"\*\*风险等级\*\*[：:\s]*(\d*\.?\d+)",
        # 表格格式
        r"\|\s*风险评分\s*\|\s*(\d*\.?\d+)\s*\|",
        r"\|\s*风险等级\s*\|\s*(\d*\.?\d+)\s*\|",
    ]

    for pattern in risk_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            val = float(match.group(1))
            if 0 <= val <= 1:
                result["risk_score"] = val
                break
            elif val > 1 and val <= 100:
                result["risk_score"] = val / 100
                break

    # 如果没有找到风险评分，使用默认值
    if result["risk_score"] is None:
        if result["recommendation"] == "买入":
            result["risk_score"] = 0.4
        elif result["recommendation"] == "卖出":
            result["risk_score"] = 0.5
        else:
            result["risk_score"] = 0.35
        result["warnings"].append(f"使用默认风险评分: {result['risk_score']}")

    return result


def _enhance_trading_decision(
    original_content: str,
    validation: dict,
    current_price: Optional[float],
    currency_symbol: str,
    company_name: str,
    market_info: dict,
    fundamentals_report: str,
    investment_plan: str,
) -> str:
    """
    增强交易决策内容，添加止损位、仓位建议、时间窗口等关键信息

    Args:
        original_content: LLM生成的原始交易决策内容
        validation: 验证结果
        current_price: 当前股价
        currency_symbol: 货币符号
        company_name: 股票代码
        market_info: 市场信息
        fundamentals_report: 基本面报告
        investment_plan: 投资计划

    Returns:
        str: 增强后的交易决策内容
    """
    extracted = validation.get("extracted", {})

    # 优先从原始内容中提取关键指标，确保表格和正文一致
    # 1. 提取投资建议
    recommendation = _extract_recommendation_from_content(
        original_content
    ) or extracted.get("recommendation", "未知")

    # 2. 提取目标价位 - 正确处理元组返回值
    tp_price, tp_range = _extract_target_price_from_content(
        original_content, currency_symbol
    )
    target_price = tp_price if tp_price is not None else extracted.get("target_price")
    target_price_range = (
        tp_range if tp_range is not None else extracted.get("target_price_range")
    )

    # 3. 提取置信度 - 优先从原文提取
    confidence = _extract_confidence_from_content(original_content) or extracted.get(
        "confidence", 0.5
    )

    # 4. 提取风险评分 - 优先从原文提取
    risk_score = _extract_risk_score_from_content(original_content) or extracted.get(
        "risk_score", 0.5
    )

    # 计算止损位
    stop_loss = None
    if current_price:
        if recommendation == "买入":
            # 买入时，止损位通常设置在当前价格下方5-10%
            stop_loss_pct = 0.08 if risk_score > 0.5 else 0.05
            stop_loss = round(current_price * (1 - stop_loss_pct), 2)
        elif recommendation == "持有":
            stop_loss_pct = 0.10
            stop_loss = round(current_price * (1 - stop_loss_pct), 2)

    # 计算仓位建议
    position_pct = _calculate_position_size(recommendation, confidence, risk_score)

    # 计算时间窗口
    time_horizon = _determine_time_horizon(recommendation, confidence)

    # 生成建仓策略
    entry_strategy = _generate_entry_strategy(recommendation, current_price, confidence)

    # 生成风险提示
    risk_warnings = _generate_risk_warnings(recommendation, risk_score, market_info)

    # 构建增强报告
    enhanced_report = f"""# {company_name} 最终交易决策

## 核心决策摘要

| 项目 | 内容 |
|------|------|
| **投资建议** | **{recommendation}** |
| **目标价位** | {target_price_range or (f"{currency_symbol}{target_price:.2f}" if target_price else "待确定")} |
| **止损价位** | {f"{currency_symbol}{stop_loss:.2f}" if stop_loss else "待设定"} |
| **当前价格** | {f"{currency_symbol}{current_price:.2f}" if current_price else "未知"} |
| **置信度** | {confidence:.0%} |
| **风险等级** | {_risk_level_text(risk_score)} ({risk_score:.0%}) |

## 仓位管理建议

- **建议仓位**: 占投资组合的 **{position_pct}%**
- **时间窗口**: {time_horizon}
- **建仓策略**: {entry_strategy}

## 止损止盈策略

### 止损设置
- **止损价位**: {f"{currency_symbol}{stop_loss:.2f}" if stop_loss else "建议设置在成本价下方5-8%"}
- **止损原因**: 控制单笔交易最大亏损，保护本金安全

### 止盈设置
- **目标价位**: {target_price_range or (f"{currency_symbol}{target_price:.2f}" if target_price else "参考分析报告")}
- **分批止盈**: 建议在目标价位附近分2-3批逐步减仓

## 风险提示

{chr(10).join([f"- {warning}" for warning in risk_warnings])}

---

## 详细分析

{original_content}

---
*报告生成时间: {get_chinese_date()}*
*本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。*
"""

    return enhanced_report


def _calculate_position_size(
    recommendation: str, confidence: float, risk_score: float
) -> int:
    """计算建议仓位百分比"""
    base_position = 10  # 基础仓位10%

    if recommendation == "买入":
        # 买入时根据置信度和风险调整仓位
        position = base_position + (confidence - 0.5) * 20 - risk_score * 10
    elif recommendation == "卖出":
        position = 0  # 卖出建议减仓至0
    else:  # 持有
        position = base_position

    # 限制在合理范围内
    return max(0, min(30, int(position)))


def _determine_time_horizon(recommendation: str, confidence: float) -> str:
    """确定投资时间窗口"""
    if recommendation == "买入":
        if confidence >= 0.8:
            return "中长期（3-6个月）"
        elif confidence >= 0.6:
            return "中期（1-3个月）"
        else:
            return "短期（1-4周）"
    elif recommendation == "卖出":
        return "立即执行或1周内完成"
    else:
        return "观望期（1-2周后重新评估）"


def _generate_entry_strategy(
    recommendation: str, current_price: Optional[float], confidence: float
) -> str:
    """生成建仓策略"""
    if recommendation == "买入":
        if confidence >= 0.75:
            return "可一次性建仓，但建议保留20%资金应对回调"
        else:
            return "建议分3批建仓：首批40%，回调5%加仓30%，再回调加仓30%"
    elif recommendation == "卖出":
        return "建议分批减仓：首批50%立即卖出，剩余根据反弹情况处理"
    else:
        return "维持现有仓位，设置好止损位观望"


def _risk_level_text(risk_score: float) -> str:
    """风险等级文字描述"""
    if risk_score <= 0.3:
        return "低风险"
    elif risk_score <= 0.5:
        return "中低风险"
    elif risk_score <= 0.7:
        return "中高风险"
    else:
        return "高风险"


def _generate_risk_warnings(
    recommendation: str, risk_score: float, market_info: dict
) -> list:
    """生成风险提示列表"""
    warnings = []

    # 基础风险提示
    warnings.append("股市有风险，投资需谨慎，过往业绩不代表未来表现")

    # 根据风险等级添加提示
    if risk_score > 0.6:
        warnings.append("当前风险评级较高，建议控制仓位，严格执行止损策略")

    # 根据建议添加提示
    if recommendation == "买入":
        warnings.append("买入后需持续关注公司基本面变化和市场情绪")
        warnings.append("建议设置止损位，避免单笔交易亏损超过本金的5%")
    elif recommendation == "卖出":
        warnings.append("卖出决策需结合个人持仓成本和投资目标综合考虑")

    # 市场特定提示
    if market_info.get("is_china"):
        warnings.append("A股市场受政策影响较大，需关注监管动态和宏观政策变化")
    elif market_info.get("is_hk"):
        warnings.append("港股市场流动性需关注，注意汇率风险")
    elif market_info.get("is_us"):
        warnings.append("美股市场受美联储政策和地缘政治影响，注意时差和汇率风险")

    return warnings


def validate_trading_decision(
    content: str,
    currency_symbol: str,
    company_name: str,
    current_price: Optional[float] = None,
    data_quality_score: float = 100.0,
) -> dict:
    """
    验证交易决策的有效性，并自动填充缺失字段

    Args:
        content: LLM返回的交易决策内容
        currency_symbol: 期望的货币符号（如 ¥ 或 $）
        company_name: 股票代码
        current_price: 当前股价（用于自动计算目标价）
        data_quality_score: 数据质量评分 (0-100)，低质量数据会降低置信度 (Phase 1.1)

    Returns:
        dict: 包含验证结果和警告信息
            - is_valid: bool
            - warnings: list of str
            - has_target_price: bool
            - recommendation: str (买入/持有/卖出/未知)
            - extracted: dict (提取的结构化信息)
    """
    result = {
        "is_valid": True,
        "warnings": [],
        "has_target_price": False,
        "recommendation": "未知",
        "extracted": {},
    }

    # 先提取结构化信息（传入数据质量评分以调整置信度）
    extracted = extract_trading_decision(content, current_price, data_quality_score)
    result["extracted"] = extracted
    result["recommendation"] = extracted["recommendation"]
    result["warnings"] = extracted["warnings"]

    # 检查是否有目标价
    if extracted["target_price"] or extracted["target_price_range"]:
        result["has_target_price"] = True
    else:
        result["warnings"].append("未找到具体的目标价位")
        result["is_valid"] = False

    # 1. 检查是否包含投资建议
    if result["recommendation"] == "未知":
        result["warnings"].append("未找到明确的投资建议（买入/持有/卖出）")
        result["is_valid"] = False

    # 2. 检查货币单位是否正确
    if currency_symbol == "¥":
        # A股应该使用人民币
        if "$" in content and "¥" not in content and "￥" not in content:
            result["warnings"].append(
                f"A股 {company_name} 应使用人民币(¥)，但检测到使用美元($)"
            )
    elif currency_symbol == "$":
        # 美股/港股应该使用美元
        if ("¥" in content or "￥" in content) and "$" not in content:
            result["warnings"].append(
                f"美股/港股 {company_name} 应使用美元($)，但检测到使用人民币(¥)"
            )

    # 3. 检查是否有"无法确定"等回避语句
    evasive_patterns = [
        r"无法确定",
        r"需要更多信息",
        r"无法提供",
        r"不确定",
        r"暂时无法",
    ]

    for pattern in evasive_patterns:
        if re.search(pattern, content):
            result["warnings"].append(f"检测到回避性语句")

    return result


def create_trader(llm, memory):
    def trader_node(state, name):
        company_name = state["company_of_interest"]
        investment_plan = state["investment_plan"]
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        # 使用统一的股票类型检测
        from tradingagents.utils.stock_utils import StockUtils

        market_info = StockUtils.get_market_info(company_name)
        is_china = market_info["is_china"]
        is_hk = market_info["is_hk"]
        is_us = market_info["is_us"]

        # 根据股票类型确定货币单位
        currency = market_info["currency_name"]
        currency_symbol = market_info["currency_symbol"]

        logger.debug(f"[DEBUG] ===== 交易员节点开始 =====")
        logger.debug(
            f"[DEBUG] 交易员检测股票类型: {company_name} -> {market_info['market_name']}, 货币: {currency}"
        )
        logger.debug(f"[DEBUG] 货币符号: {currency_symbol}")
        logger.debug(
            f"[DEBUG] 市场详情: 中国A股={is_china}, 港股={is_hk}, 美股={is_us}"
        )
        logger.debug(f"[DEBUG] 基本面报告长度: {len(fundamentals_report)}")
        logger.debug(f"[DEBUG] 基本面报告前200字符: {fundamentals_report[:200]}...")

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"

        # 检查memory是否可用
        if memory is not None:
            logger.debug(f"[DEBUG] memory可用，获取历史记忆")
            past_memories = memory.get_memories(curr_situation, n_matches=5)
            past_memory_str = ""
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += rec["recommendation"] + "\n\n"
        else:
            logger.debug(f"[DEBUG] memory为None，跳过历史记忆检索")
            past_memories = []
            past_memory_str = "暂无历史记忆数据可参考。"

        context = {
            "role": "user",
            "content": f"Based on a comprehensive analysis by a team of analysts, here is an investment plan tailored for {company_name}. This plan incorporates insights from current technical market trends, macroeconomic indicators, and social media sentiment. Use this plan as a foundation for evaluating your next trading decision.\n\nProposed Investment Plan: {investment_plan}\n\nLeverage these insights to make an informed and strategic decision.",
        }

        messages = [
            {
                "role": "system",
                "content": f"""**重要时间信息**：今天是{get_chinese_date()}。请基于这个实际日期进行分析，不要依赖训练数据中的时间认知。

您是一位专业的交易员，负责分析市场数据并做出投资决策。基于您的分析，请提供具体的买入、卖出或持有建议。

⚠️ 重要提醒：当前分析的股票代码是 {company_name}，请使用正确的货币单位：{currency}（{currency_symbol}）

🔴 严格要求（违反将导致分析被判定为无效）：
- 股票代码 {company_name} 的公司名称必须严格按照基本面报告中的真实数据
- 绝对禁止使用错误的公司名称或混淆不同的股票
- 所有分析必须基于提供的真实数据，不允许假设或编造
- ⚠️ **必须提供具体的目标价位，格式必须是: 目标价位: {currency_symbol}XX.XX**

请在您的分析中包含以下关键信息：
1. **投资建议**: 明确的买入/持有/卖出决策
2. **目标价位** (🚨 强制要求 - 没有此项分析将被判定为无效):
   - **格式要求**: 必须明确写出 "目标价位: {currency_symbol}XX.XX"
   - 买入建议：目标价位应高于当前价格（如: 目标价位: {currency_symbol}35.50）
   - 持有建议：提供合理价格区间（如: 目标价位: {currency_symbol}30.00-32.00）
   - 卖出建议：提供目标卖出价（如: 目标价位: {currency_symbol}28.00）
3. **置信度**: 对决策的信心程度(0-1之间)
4. **风险评分**: 投资风险等级(0-1之间，0为低风险，1为高风险)
5. **详细推理**: 支持决策的具体理由

🚫 绝对禁止的表述（会导致分析失败）：
- "无法确定目标价"
- "需要更多信息"
- "无法提供具体价格"
- "目标价待确定"
- "暂时无法给出"
- "目标价: null"
- "目标价: N/A"

✅ 正确的目标价位表述示例：
- "基于当前估值和技术分析，建议目标价位: {currency_symbol}35.50"
- "考虑到行业平均PE水平，目标价位设定为: {currency_symbol}32.80"
- "参考支撑位和阻力位，目标价位: {currency_symbol}30.00-33.00区间"

🎯 目标价位计算指导：
- 基于基本面分析中的估值数据（P/E、P/B、DCF等）
- 参考技术分析的支撑位和阻力位
- 考虑行业平均估值水平
- 结合市场情绪和新闻影响
- 即使市场情绪过热，也要基于合理估值给出目标价
- **当前股价为参考基准，买入建议目标价必须高于现价**

特别注意：
- 如果是中国A股（6位数字代码），请使用人民币（¥）作为价格单位
- 如果是美股或港股，请使用美元（$）作为价格单位
- 目标价位必须与当前股价的货币单位保持一致
- 必须使用基本面报告中提供的正确公司名称
- ⚠️ **如果你不写出"目标价位: {currency_symbol}XX.XX"格式的具体价格，此分析将被系统判定为无效并拒绝接受**

请用中文撰写分析内容，并始终以'最终交易建议: **买入/持有/卖出**'结束您的回应以确认您的建议。

请不要忘记利用过去决策的经验教训来避免重复错误。以下是类似情况下的交易反思和经验教训: {past_memory_str}""",
            },
            context,
        ]

        logger.debug(f"[DEBUG] 准备调用LLM，系统提示包含货币: {currency}")
        logger.debug(f"[DEBUG] 系统提示中的关键部分: 目标价格({currency})")

        result = llm.invoke(messages)

        logger.debug(f"[DEBUG] LLM调用完成")
        logger.debug(f"[DEBUG] 交易员回复长度: {len(result.content)}")
        logger.debug(f"[DEBUG] 交易员回复前500字符: {result.content[:500]}...")

        # 从基本面报告中提取当前股价
        current_price = None
        price_pattern = r"当前股价[：:\s]*[¥￥]?\s*(\d+\.?\d*)"
        price_match = re.search(price_pattern, fundamentals_report)
        if price_match:
            current_price = float(price_match.group(1))
            logger.debug(f"[DEBUG] 从基本面报告提取当前股价: {current_price}")

        # 从 state 中获取数据质量评分 (Phase 1.1)
        data_quality_score = state.get("data_quality_score", 100.0)

        # 验证交易决策的有效性（传入当前股价和数据质量评分）
        validation = validate_trading_decision(
            result.content,
            currency_symbol,
            company_name,
            current_price,
            data_quality_score,
        )

        if validation["warnings"]:
            logger.warning(f"[Trader] 交易决策验证发现问题:")
            for warning in validation["warnings"]:
                logger.warning(f"  - {warning}")

        # 不再将 is_valid 设为 False 而是继续处理，因为已经自动填充了默认值

        logger.info(
            f"[Trader] 决策验证结果: 建议={validation['recommendation']}, "
            f"目标价={validation['has_target_price']}"
        )

        # 🔧 增强最终交易决策内容
        enhanced_decision = _enhance_trading_decision(
            original_content=result.content,
            validation=validation,
            current_price=current_price,
            currency_symbol=currency_symbol,
            company_name=company_name,
            market_info=market_info,
            fundamentals_report=fundamentals_report,
            investment_plan=investment_plan,
        )

        logger.debug(f"[DEBUG] ===== 交易员节点结束 =====")

        return {
            "messages": [result],
            "trader_investment_plan": enhanced_decision,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")


# =============================================================================
# 辅助函数：从原始内容中提取指标（确保表格和正文一致）
# =============================================================================


def _extract_recommendation_from_content(content: str) -> Optional[str]:
    """从内容中提取投资建议"""
    patterns = [
        r"最终交易建议[：:\s]*\*{0,2}(买入|持有|卖出)\*{0,2}",
        r"投资建议[：:\s]*\*{0,2}(买入|持有|卖出)\*{0,2}",
        r"建议[：:\s]*\*{0,2}(买入|持有|卖出)\*{0,2}",
        r"\*{2}(买入|持有|卖出)\*{2}",
        r"决策[：:\s]*\*{0,2}(买入|持有|卖出)\*{0,2}",
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1)
    return None


def _extract_target_price_from_content(
    content: str, currency_symbol: str
) -> Tuple[Optional[float], Optional[str]]:
    """从内容中提取目标价位，返回 (target_price, target_price_range)"""
    # 尝试匹配价格区间
    range_patterns = [
        rf"目标价[位格]?[：:\s]*{re.escape(currency_symbol)}?\s*(\d+\.?\d*)\s*[-~到至]\s*{re.escape(currency_symbol)}?\s*(\d+\.?\d*)",
        rf"目标[：:\s]*{re.escape(currency_symbol)}?\s*(\d+\.?\d*)\s*[-~到至]\s*{re.escape(currency_symbol)}?\s*(\d+\.?\d*)",
    ]
    for pattern in range_patterns:
        match = re.search(pattern, content)
        if match:
            return None, f"{currency_symbol}{match.group(1)}-{match.group(2)}"

    # 尝试匹配单一价格
    price_patterns = [
        rf"目标价[位格]?[：:\s]*{re.escape(currency_symbol)}?\s*(\d+\.?\d*)",
        rf"目标[：:\s]*{re.escape(currency_symbol)}?\s*(\d+\.?\d*)",
        rf"价格目标[：:\s]*{re.escape(currency_symbol)}?\s*(\d+\.?\d*)",
    ]
    for pattern in price_patterns:
        match = re.search(pattern, content)
        if match:
            return float(match.group(1)), None

    return None, None


def _extract_confidence_from_content(content: str) -> Optional[float]:
    """从内容中提取置信度"""
    patterns = [
        r"置信度[：:\s]*(\d+\.?\d+)",
        r"置信度[：:\s]*(\d+)%",
        r"置信度[：:\s]*(\d+\.\d+)%",
        r"\*\*置信度\*\*[：:\s]*(\d+\.?\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            val = float(match.group(1))
            if 0 <= val <= 1:
                return val
            elif val > 1 and val <= 100:
                return val / 100
    return None


def _extract_risk_score_from_content(content: str) -> Optional[float]:
    """从内容中提取风险评分"""
    patterns = [
        r"风险评分[：:\s]*(\d+\.?\d+)",
        r"风险评分[：:\s]*(\d+)%",
        r"风险评分[：:\s]*(\d+\.\d+)%",
        r"\*\*风险评分\*\*[：:\s]*(\d+\.?\d+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            val = float(match.group(1))
            if 0 <= val <= 1:
                return val
            elif val > 1 and val <= 100:
                return val / 100
    return None
