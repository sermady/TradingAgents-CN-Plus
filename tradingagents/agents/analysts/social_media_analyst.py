# -*- coding: utf-8 -*-
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.utils.stock_utils import StockUtils
from tradingagents.utils.company_name_utils import get_company_name
from langchain_core.messages import AIMessage

logger = get_logger("analysts.social_media")


def create_social_media_analyst(llm, toolkit):
    @log_analyst_module("social_media")
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Retrieve pre-fetched data
        sentiment_data = state.get("sentiment_data", "")
        if not sentiment_data:
            logger.warning(
                f"[Social Media Analyst] No sentiment data found in state for {ticker}"
            )
            sentiment_data = (
                "Error: No sentiment data available. Please check DataCoordinator logs."
            )

        logger.info(f"[Social Media Analyst] Analyzing {ticker} on {current_date}")

        market_info = StockUtils.get_market_info(ticker)
        company_name = get_company_name(ticker, market_info)

        system_message = f"""你是一位专业的市场情绪分析师。
请基于以下**社交媒体和投资者情绪数据**对 {company_name} ({ticker}) 进行详细的情绪面分析。

=== 情绪数据 ===
{sentiment_data}
================

**分析要求（必须严格遵守）：**
1. **数据来源**：必须严格基于上述提供的即情绪数据进行分析。
2. **情绪概况**：评估当前市场对该股票的整体情绪（贪婪/恐惧/中性）。
3. **散户vs机构**：分析散户讨论热度与可能的机构动向。
4. **舆情风险**：识别潜在的舆情风险点。
5. **投资建议**：基于逆向思维或顺势交易策略给出建议。

**输出格式要求：**
请使用Markdown格式，包含以下章节：
# **{company_name}（{ticker}）市场情绪分析报告**
## 一、投资者情绪概览
## 二、社交媒体热度分析
## 三、潜在舆情风险
## 四、情绪面投资建议

⚠️ **重要**：所有分析必须基于提供的数据。如果数据缺失，请明确说明。
"""

        messages = [
            ("system", system_message),
            ("human", f"请生成 {company_name} ({ticker}) 的情绪分析报告。"),
        ]

        try:
            response = llm.invoke(messages)
            return {"sentiment_report": response.content, "messages": [response]}
        except Exception as e:
            logger.error(f"[Social Media Analyst] LLM调用失败: {e}", exc_info=True)
            return {"sentiment_report": f"❌ 情绪分析失败: {str(e)}", "messages": []}

    return social_media_analyst_node
