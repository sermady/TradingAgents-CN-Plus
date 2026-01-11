import functools
import time
import json
import re

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger("default")


def validate_trading_decision(content: str, currency_symbol: str, company_name: str) -> dict:
    """
    验证交易决策的有效性

    Args:
        content: LLM返回的交易决策内容
        currency_symbol: 期望的货币符号（如 ¥ 或 $）
        company_name: 股票代码

    Returns:
        dict: 包含验证结果和警告信息
            - is_valid: bool
            - warnings: list of str
            - has_target_price: bool
            - recommendation: str (买入/持有/卖出/未知)
    """
    result = {
        "is_valid": True,
        "warnings": [],
        "has_target_price": False,
        "recommendation": "未知"
    }

    # 1. 检查是否包含投资建议
    recommendation_patterns = [
        r'最终交易建议[：:]\s*\*{0,2}(买入|持有|卖出)\*{0,2}',
        r'投资建议[：:]\s*\*{0,2}(买入|持有|卖出)\*{0,2}',
        r'建议[：:]\s*\*{0,2}(买入|持有|卖出)\*{0,2}',
        r'\*{2}(买入|持有|卖出)\*{2}',
    ]

    for pattern in recommendation_patterns:
        match = re.search(pattern, content)
        if match:
            result["recommendation"] = match.group(1)
            break

    if result["recommendation"] == "未知":
        result["warnings"].append("未找到明确的投资建议（买入/持有/卖出）")

    # 2. 检查是否包含目标价位
    price_patterns = [
        r'目标价[位格]?[：:\s]*[¥\$￥]?\s*(\d+\.?\d*)',
        r'目标[：:\s]*[¥\$￥]?\s*(\d+\.?\d*)',
        r'价格目标[：:\s]*[¥\$￥]?\s*(\d+\.?\d*)',
        r'[¥\$￥]\s*(\d+\.?\d*)\s*[-~到至]\s*[¥\$￥]?\s*(\d+\.?\d*)',  # 价格区间
    ]

    for pattern in price_patterns:
        match = re.search(pattern, content)
        if match:
            result["has_target_price"] = True
            break

    if not result["has_target_price"]:
        result["warnings"].append("未找到具体的目标价位")
        result["is_valid"] = False

    # 3. 检查货币单位是否正确
    if currency_symbol == "¥":
        # A股应该使用人民币
        if "$" in content and "¥" not in content:
            result["warnings"].append(f"A股 {company_name} 应使用人民币(¥)，但检测到使用美元($)")
    elif currency_symbol == "$":
        # 美股/港股应该使用美元
        if "¥" in content and "$" not in content and "￥" not in content:
            result["warnings"].append(f"美股/港股 {company_name} 应使用美元($)，但检测到使用人民币(¥)")

    # 4. 检查是否有"无法确定"等回避语句
    evasive_patterns = [
        r'无法确定',
        r'需要更多信息',
        r'无法提供',
        r'不确定',
        r'暂时无法',
    ]

    for pattern in evasive_patterns:
        if re.search(pattern, content):
            result["warnings"].append(f"检测到回避性语句: '{pattern}'")

    # 5. 检查置信度和风险评分
    confidence_match = re.search(r'置信度[：:\s]*(\d*\.?\d+)', content)
    risk_match = re.search(r'风险评分[：:\s]*(\d*\.?\d+)', content)

    if not confidence_match:
        result["warnings"].append("未找到置信度评分")

    if not risk_match:
        result["warnings"].append("未找到风险评分")

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
        is_china = market_info['is_china']
        is_hk = market_info['is_hk']
        is_us = market_info['is_us']

        # 根据股票类型确定货币单位
        currency = market_info['currency_name']
        currency_symbol = market_info['currency_symbol']

        logger.debug(f"[DEBUG] ===== 交易员节点开始 =====")
        logger.debug(f"[DEBUG] 交易员检测股票类型: {company_name} -> {market_info['market_name']}, 货币: {currency}")
        logger.debug(f"[DEBUG] 货币符号: {currency_symbol}")
        logger.debug(f"[DEBUG] 市场详情: 中国A股={is_china}, 港股={is_hk}, 美股={is_us}")
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
                "content": f"""您是一位专业的交易员，负责分析市场数据并做出投资决策。基于您的分析，请提供具体的买入、卖出或持有建议。

⚠️ 重要提醒：当前分析的股票代码是 {company_name}，请使用正确的货币单位：{currency}（{currency_symbol}）

🔴 严格要求：
- 股票代码 {company_name} 的公司名称必须严格按照基本面报告中的真实数据
- 绝对禁止使用错误的公司名称或混淆不同的股票
- 所有分析必须基于提供的真实数据，不允许假设或编造
- **必须提供具体的目标价位，不允许设置为null或空值**

请在您的分析中包含以下关键信息：
1. **投资建议**: 明确的买入/持有/卖出决策
2. **目标价位**: 基于分析的合理目标价格({currency}) - 🚨 强制要求提供具体数值
   - 买入建议：提供目标价位和预期涨幅
   - 持有建议：提供合理价格区间（如：{currency_symbol}XX-XX）
   - 卖出建议：提供止损价位和目标卖出价
3. **置信度**: 对决策的信心程度(0-1之间)
4. **风险评分**: 投资风险等级(0-1之间，0为低风险，1为高风险)
5. **详细推理**: 支持决策的具体理由

🎯 目标价位计算指导：
- 基于基本面分析中的估值数据（P/E、P/B、DCF等）
- 参考技术分析的支撑位和阻力位
- 考虑行业平均估值水平
- 结合市场情绪和新闻影响
- 即使市场情绪过热，也要基于合理估值给出目标价

特别注意：
- 如果是中国A股（6位数字代码），请使用人民币（¥）作为价格单位
- 如果是美股或港股，请使用美元（$）作为价格单位
- 目标价位必须与当前股价的货币单位保持一致
- 必须使用基本面报告中提供的正确公司名称
- **绝对不允许说"无法确定目标价"或"需要更多信息"**

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

        # 验证交易决策的有效性
        validation = validate_trading_decision(result.content, currency_symbol, company_name)

        if validation["warnings"]:
            logger.warning(f"[Trader] 交易决策验证发现问题:")
            for warning in validation["warnings"]:
                logger.warning(f"  - {warning}")

        if not validation["is_valid"]:
            logger.error(f"[Trader] 交易决策验证失败: 缺少目标价位")

        logger.info(f"[Trader] 决策验证结果: 建议={validation['recommendation']}, "
                   f"目标价={validation['has_target_price']}, 有效={validation['is_valid']}")

        logger.debug(f"[DEBUG] ===== 交易员节点结束 =====")

        return {
            "messages": [result],
            "trader_investment_plan": result.content,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
