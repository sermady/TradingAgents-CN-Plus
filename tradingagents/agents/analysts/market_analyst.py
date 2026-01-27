# -*- coding: utf-8 -*-
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.utils.stock_utils import StockUtils
from tradingagents.utils.company_name_utils import get_company_name
from langchain_core.messages import AIMessage

logger = get_logger("analysts.market")


def create_market_analyst(llm, toolkit):
    @log_analyst_module("market")
    def market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Retrieve pre-fetched data
        market_data = state.get("market_data", "")
        if not market_data:
            logger.warning(
                f"[Market Analyst] No market data found in state for {ticker}"
            )
            market_data = (
                "Error: No market data available. Please check DataCoordinator logs."
            )

        logger.info(f"[Market Analyst] Analyzing {ticker} on {current_date}")

        market_info = StockUtils.get_market_info(ticker)
        company_name = get_company_name(ticker, market_info)

        system_message = f"""你是一位专业的股票技术分析师。
请基于以下**真实市场数据**对 {company_name} ({ticker}) 进行详细的技术分析。

=== 市场数据 ===
{market_data}
================

**分析要求（必须严格遵守）：**
1. **数据来源**：必须严格基于上述提供的市场数据进行分析，绝对禁止编造数据。
2. **技术指标**：分析移动平均线（MA）、MACD、RSI、布林带等指标（如果数据中包含）。
3. **价格趋势**：分析短期和中期价格走势。
4. **成交量**：分析量价配合情况（注意A股单位：手/股）。
5. **投资建议**：给出明确的买入/持有/卖出建议。

**输出格式要求：**
请使用Markdown格式，包含以下章节：
# **{company_name}（{ticker}）技术分析报告**
## 一、股票基本信息
## 二、技术指标分析
## 三、价格趋势分析
## 四、投资建议

⚠️ **重要**：所有分析必须基于提供的数据。如果数据缺失，请明确说明。
"""

        messages = [
            ("system", system_message),
            ("human", f"请生成 {company_name} ({ticker}) 的技术分析报告。"),
        ]

        try:
            response = llm.invoke(messages)
            return {"market_report": response.content, "messages": [response]}
        except Exception as e:
            logger.error(f"[Market Analyst] LLM调用失败: {e}", exc_info=True)
            return {"market_report": f"❌ 技术分析失败: {str(e)}", "messages": []}

    return market_analyst_node
