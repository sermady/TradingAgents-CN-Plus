# -*- coding: utf-8 -*-
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.utils.stock_utils import StockUtils
from tradingagents.utils.company_name_utils import get_company_name
from langchain_core.messages import AIMessage

logger = get_logger("analysts.news")


def create_news_analyst(llm, toolkit):
    @log_analyst_module("news")
    def news_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Retrieve pre-fetched data
        news_data = state.get("news_data", "")
        if not news_data:
            logger.warning(f"[News Analyst] No news data found in state for {ticker}")
            news_data = (
                "Error: No news data available. Please check DataCoordinator logs."
            )

        logger.info(f"[News Analyst] Analyzing {ticker} on {current_date}")

        market_info = StockUtils.get_market_info(ticker)
        company_name = get_company_name(ticker, market_info)

        system_message = f"""你是一位专业的财经新闻分析师。
请基于以下**最新新闻数据**对 {company_name} ({ticker}) 进行详细的新闻面分析。

=== 新闻数据 ===
{news_data}
================

**分析要求（必须严格遵守）：**
1. **数据来源**：必须严格基于上述提供的新闻数据进行分析，绝对禁止编造新闻。
2. **事件总结**：总结近期的关键新闻事件（财报、并购、政策、产品等）。
3. **影响评估**：评估这些新闻对股价的潜在影响（利好/利空/中性）。
4. **时效性**：关注新闻发布的时间，优先分析最新消息。
5. **投资建议**：基于消息面给出短期交易建议。

**输出格式要求：**
请使用Markdown格式，包含以下章节：
# **{company_name}（{ticker}）新闻分析报告**
## 一、近期关键新闻摘要
## 二、利好与利空因素分析
## 三、市场情绪与潜在影响
## 四、短期交易建议

⚠️ **重要**：所有分析必须基于提供的数据。如果数据缺失，请明确说明。
"""

        messages = [
            ("system", system_message),
            ("human", f"请生成 {company_name} ({ticker}) 的新闻分析报告。"),
        ]

        try:
            response = llm.invoke(messages)
            return {"news_report": response.content, "messages": [response]}
        except Exception as e:
            logger.error(f"[News Analyst] LLM调用失败: {e}", exc_info=True)
            return {"news_report": f"❌ 新闻分析失败: {str(e)}", "messages": []}

    return news_analyst_node
