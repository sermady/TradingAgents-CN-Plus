# -*- coding: utf-8 -*-

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")

# 导入统一公司名称工具（替换原有的重复代码）
from tradingagents.utils.company_name_utils import get_company_name


def create_bear_researcher(llm, memory):
    def bear_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bear_history = investment_debate_state.get("bear_history", "")

        current_response = investment_debate_state.get("current_response", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        # 获取中国市场分析师报告（如果可用）
        china_market_report = state.get("china_market_report", "")

        # 使用统一的股票类型检测
        ticker = state.get("company_of_interest", "Unknown")
        from tradingagents.utils.stock_utils import StockUtils

        market_info = StockUtils.get_market_info(ticker)
        is_china = market_info["is_china"]

        # 获取公司名称（使用统一工具）
        company_name = get_company_name(ticker, market_info)
        logger.info(f"[空头研究员] 公司名称: {company_name}")
        is_hk = market_info["is_hk"]
        is_us = market_info["is_us"]

        currency = market_info["currency_name"]
        currency_symbol = market_info["currency_symbol"]

        # 构建当前情况，如果是A股则包含中国市场分析师报告
        if is_china and china_market_report:
            curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}\n\n{china_market_report}"
        else:
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

        prompt = f"""你是一位看跌分析师，负责论证不投资股票 {company_name}（股票代码：{ticker}）的理由。
 
⚠️ 重要提醒：当前分析的是 {market_info["market_name"]}，所有价格和估值请使用 {currency}（{currency_symbol}）作为单位。
⚠️ 在你的分析中，请始终使用公司名称"{company_name}"而不是股票代码"{ticker}"来称呼这家公司。
 
🚨 CRITICAL REQUIREMENT - 绝对强制要求：

❌ 严格禁止行为：
1. 绝对禁止编造任何财务数据或风险预测
2. 绝对禁止编造市场地位或竞争劣势
3. 绝对禁止基于常识编造行业趋势
4. 绝对禁止编造负面指标或风险因素
5. 绝对禁止强化基于编造数据的观点
6. 绝对禁止使用常识或训练数据"合理化"编造内容

✅ 强制验证步骤：
1. 你必须批判性地评估前面分析师的报告
2. 如果发现报告中包含编造数据或明显错误，必须明确拒绝该数据
3. 不要使用包含编造数据的论据
4. 如果数据可疑，请在论证中明确说明："该报告的数据不可信，不作为论据"
5. 检查数据是否在合理范围内：
   - PE/PB 比率是否合理？（通常 PE: 5-100, PB: 0.5-5）
   - **🔴【重要】PE指标区分检查**：
     - **PE_TTM（滚动市盈率）**：使用TTM净利润（过去12个月滚动归母净利润）
     - **PE静态**：使用年报归母净利润
     - **⚠️ 常见错误**：不能用年报净利润验算PE_TTM！
     - **示例**：市值268.81亿，PE_TTM 25.7倍 → TTM净利润应为10.46亿（而非7.60亿年报利润）
     - 如果基本面报告同时提到PE_TTM和PE静态，请确认使用正确的利润口径
   - ROE 是否在合理范围？（通常 5%-30%）
   - 增长率是否合理？（通常 0-50%，不包含异常高值）
   - 估值方法是否一致？
   - 是否有矛盾的数据点？
   - ⚠️ 成交量差异是合理设计：技术分析师用日线数据，基本面分析师用实时行情，含义不同不代表矛盾

📊 数据验证清单（重要）：
- [ ] PE/PB 比率是否合理？
- [ ] ROE 是否在合理范围？
- [ ] 增长率是否合理？
- [ ] 估值方法是否一致？
- [ ] 是否有矛盾的数据点？（注意：成交量差异是合理的）
- [ ] 报告是否基于具体数据而非泛泛而谈？

⚠️ 违规后果：
- 如果基于编造数据生成观点，你的论证将被拒绝
- 如果使用不可信的报告作为论据，必须在论证中明确说明
- 必须基于可信数据，否则无法完成论证任务

你的目标是提出合理的论证，强调风险、挑战和负面指标。利用提供的研究和数据来突出潜在的不利因素并有效反驳看涨论点。
 
请用中文回答，重点关注以下几个方面：
 
- 风险和挑战：突出市场饱和、财务不稳定或宏观经济威胁等可能阻碍股票表现的因素
- 竞争劣势：强调市场地位较弱、创新下降或来自竞争对手威胁等脆弱性
- 负面指标：使用财务数据、市场趋势或最近不利消息的证据来支持你的立场
- 反驳看涨观点：用具体数据和合理推理批判性分析看涨论点，揭露弱点或过度乐观的假设
- 参与讨论：以对话风格呈现你的论点，直接回应看涨分析师的观点并进行有效辩论，而不仅仅是列举事实
 
可用资源：
  
市场研究报告：{market_research_report}
社交媒体情绪报告：{sentiment_report}
最新世界事务新闻：{news_report}
公司基本面报告：{fundamentals_report}
{f"A股市场特色分析报告：{china_market_report}" if is_china and china_market_report else ""}
辩论对话历史：{history}
最后的看涨论点：{current_response}
类似情况的反思和经验教训：{past_memory_str}
 
请使用这些信息提供令人信服的看跌论点，反驳看涨声明，并参与动态辩论，展示投资该股票的风险和弱点。你还必须处理反思并从过去的经验教训和错误中学习。
 
请确保所有回答都使用中文。
"""

        response = llm.invoke(prompt)

        argument = f"Bear Analyst: {response.content}"

        new_count = investment_debate_state["count"] + 1
        logger.info(
            f"🐻 [空头研究员] 发言完成，计数: {investment_debate_state['count']} -> {new_count}"
        )

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bear_history": bear_history + "\n" + argument,
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": argument,
            "count": new_count,
        }

        return {"investment_debate_state": new_investment_debate_state}

    return bear_node
