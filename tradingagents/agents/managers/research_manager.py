# -*- coding: utf-8 -*-
import time

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def create_research_manager(llm, memory):
    def research_manager_node(state) -> dict:
        history = state["investment_debate_state"].get("history", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        investment_debate_state = state["investment_debate_state"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"

        # 安全检查：确保memory不为None
        if memory is not None:
            past_memories = memory.get_memories(curr_situation, n_matches=5)
        else:
            logger.warning(f"⚠️ [DEBUG] memory为None，跳过历史记忆检索")
            past_memories = []

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        trade_date = state.get("trade_date", "指定日期")
        prompt = f"""**重要时间信息**：我们正在分析 {trade_date} 的股票历史数据。请直接基于提供的报告数据进行评估，无需验证日期有效性。不要依赖你的训练数据时间认知，只需专注于分析给定的实际数据。

        作为投资组合经理和辩论主持人，您的职责是批判性地评估这轮辩论并做出明确决策：支持看跌分析师、看涨分析师，或者仅在基于所提出论点有强有力理由时选择持有。


📊 数据验证要求（重要）：
- 你必须评估所有提供的分析报告是否基于真实数据
- 如果发现报告包含编造数据、不合理的估值、异常的技术指标等，请明确指出
- 检查报告之间的数据一致性（如不同报告对同一股票的估值差异）
- ⚠️ 注意：成交量数据的差异是合理的设计，不代表数据不一致
  - 技术分析师使用：日线历史成交量（全天收盘值）
  - 基本面分析师使用：实时累计成交量（交易中动态增长）
  - 两者含义不同，不应视为矛盾
- 如果数据互相矛盾，分析可能的原因（数据源问题、计算方法差异等）
- 不要盲目使用报告中的数据，要批判性地评估可靠性
- 如果发现数据质量问题，请在决策中说明，并相应调整你的建议和目标价格

简洁地总结双方的关键观点，重点关注最有说服力的证据或推理。您的建议——买入、卖出或持有——必须明确且可操作。避免仅仅因为双方都有有效观点就默认选择持有；要基于辩论中最强有力的论点做出承诺。

此外，为交易员制定详细的投资计划。这应该包括：

您的建议：基于最有说服力论点的明确立场。
理由：解释为什么这些论点导致您的结论。
战略行动：实施建议的具体步骤。
📊 目标价格分析：基于所有可用报告（基本面、新闻、情绪），提供全面的目标价格区间和具体价格目标。考虑：
- 基本面报告中的基本估值（注意检查数据的合理性）
  - **🔴【重要】检查PE指标口径**：
    - **PE_TTM（滚动市盈率）**：基于TTM净利润（过去12个月滚动），市场常用
    - **PE静态**：基于年报归母净利润，反映完整财年表现
    - **⚠️ 常见错误**：不能用PE_TTM倍数 × 年报净利润来验证市值或计算目标价
    - **示例**：市值268.81亿，PE_TTM 25.7倍 → 对应TTM净利润应为10.46亿（而非7.60亿年报利润）
    - 如果基本面报告同时提到两种PE，请确认估值时使用的是正确的利润口径
- 新闻对价格预期的影响
- 情绪驱动的价格调整
- 技术支撑/阻力位
- 风险调整价格情景（保守、基准、乐观）
- 价格目标的时间范围（1个月、3个月、6个月）
💰 您必须提供具体的目标价格 - 不要回复"无法确定"或"需要更多信息"。

考虑您在类似情况下的过去错误。利用这些见解来完善您的决策制定，确保您在学习和改进。以对话方式呈现您的分析，就像自然说话一样，不使用特殊格式。

以下是您对错误的过去反思：
\"{past_memory_str}\"

以下是综合分析报告：
市场研究：{market_research_report}

情绪分析：{sentiment_report}

新闻分析：{news_report}

基本面分析：{fundamentals_report}

以下是辩论：
辩论历史：
{history}

请用中文撰写所有分析内容和建议。"""

        # 📊 统计 prompt 大小
        prompt_length = len(prompt)
        estimated_tokens = int(prompt_length / 1.8)

        logger.info(f"📊 [Research Manager] Prompt 统计:")
        logger.info(f"   - 辩论历史长度: {len(history)} 字符")
        logger.info(f"   - 总 Prompt 长度: {prompt_length} 字符")
        logger.info(f"   - 估算输入 Token: ~{estimated_tokens} tokens")

        # ⏱️ 记录开始时间
        start_time = time.time()

        response = llm.invoke(prompt)

        # ⏱️ 记录结束时间
        elapsed_time = time.time() - start_time

        # 📊 统计响应信息
        response_length = (
            len(response.content) if response and hasattr(response, "content") else 0
        )
        estimated_output_tokens = int(response_length / 1.8)

        logger.info(f"⏱️ [Research Manager] LLM调用耗时: {elapsed_time:.2f}秒")
        logger.info(
            f"📊 [Research Manager] 响应统计: {response_length} 字符, 估算~{estimated_output_tokens} tokens"
        )

        new_investment_debate_state = {
            "judge_decision": response.content,
            "history": investment_debate_state.get("history", ""),
            "bear_history": investment_debate_state.get("bear_history", ""),
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": response.content,
            "count": investment_debate_state["count"],
        }

        return {
            "investment_debate_state": new_investment_debate_state,
            "investment_plan": response.content,
        }

    return research_manager_node
