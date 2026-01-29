# -*- coding: utf-8 -*-
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.utils.stock_utils import StockUtils
from tradingagents.utils.company_name_utils import get_company_name
from langchain_core.messages import AIMessage

logger = get_logger("analysts.news")


def create_news_analyst(llm, toolkit=None):
    """
    创建新闻分析师节点

    Args:
        llm: 语言模型实例
        toolkit: 工具包（可选，用于兼容性）

    Returns:
        news_analyst_node: 新闻分析师节点函数
    """

    @log_analyst_module("news")
    def news_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Retrieve pre-fetched data and metadata
        news_data = state.get("news_data", "")
        data_quality_score = state.get("data_quality_score", 0.0)
        data_sources = state.get("data_sources", {})
        sentiment_data = state.get("sentiment_data", "")

        # 检查数据质量
        news_source = data_sources.get("news", "unknown")
        sentiment_source = data_sources.get("sentiment", "unknown")

        if not news_data or "❌" in news_data:
            logger.warning(
                f"[News Analyst] News data unavailable for {ticker} (source: {news_source})"
            )
            news_data = (
                "警告：新闻数据不可用。已尝试获取但失败。\n请检查网络连接或稍后重试。"
            )

        logger.info(
            f"[News Analyst] Analyzing {ticker} on {current_date} (quality: {data_quality_score:.2f}, source: {news_source})"
        )

        market_info = StockUtils.get_market_info(ticker)
        company_name = get_company_name(ticker, market_info)

        # 根据数据质量等级给出不同的分析指导
        data_quality_level = (
            "high"
            if data_quality_score >= 0.8
            else "medium"
            if data_quality_score >= 0.5
            else "low"
        )
        quality_guidance = {
            "high": "数据质量良好，可以进行深入分析。",
            "medium": "数据质量一般，分析时请留意可能存在的信息偏差。",
            "low": "数据质量较差，新闻数据可能不完整或延迟，请谨慎分析。",
        }.get(data_quality_level, "")

        # 舆情数据质量提示
        sentiment_section = ""
        if sentiment_data and "❌" not in sentiment_data:
            sentiment_section = f"""

=== 舆情数据 ===
{sentiment_data}
数据来源: {sentiment_source}
==============="""

        system_message = f"""你是一位专业的财经新闻分析师。
请基于以下**最新新闻数据**对 {company_name} ({ticker}) 进行详细的新闻面分析。

=== 数据质量信息 ===
- 数据质量评分: {data_quality_score:.0%} ({data_quality_level})
- 新闻来源: {news_source}
- 分析日期: {current_date}
- 质量指导: {quality_guidance}

=== 新闻数据 ===
{news_data}
================{sentiment_section}

**分析要求（必须严格遵守）：**
1. **数据来源**：必须严格基于上述提供的新闻数据进行分析，绝对禁止编造新闻。
2. **数据质量意识**：请注意数据质量评分和质量指导，新闻数据可能存在不完整或延迟。
   - 质量等级说明: {quality_guidance}
3. **事件总结**：总结近期的关键新闻事件（财报、并购、政策、产品等）。
4. **影响评估**：评估这些新闻对股价的潜在影响（利好/利空/中性）。
5. **时效性**：关注新闻发布的时间，优先分析最新消息。
6. **舆情分析**：结合舆情数据（如有），分析市场情绪和投资者关注度。
7. **投资建议**：基于消息面给出短期交易建议。

**输出格式要求：**
请使用Markdown格式，包含以下章节：
# **{company_name}（{ticker}）新闻分析报告**
## 一、近期关键新闻摘要
## 二、利好与利空因素分析
## 三、市场情绪与舆情分析
## 四、短期交易建议

⚠️ **重要**：
- 所有分析必须基于提供的数据。如果数据缺失，请明确说明。
- 如果新闻数据较少，请说明数据覆盖的局限性。
- 数据质量评分低于50%时，请在投资建议中提醒用户谨慎参考。
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
