# -*- coding: utf-8 -*-
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.utils.stock_utils import StockUtils
from tradingagents.utils.company_name_utils import get_company_name
from langchain_core.messages import AIMessage

logger = get_logger("analysts.fundamentals")


def create_fundamentals_analyst(llm, toolkit):
    @log_analyst_module("fundamentals")
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Retrieve pre-fetched data
        financial_data = state.get("financial_data", "")
        if not financial_data:
            logger.warning(
                f"[Fundamentals Analyst] No financial data found in state for {ticker}"
            )
            financial_data = (
                "Error: No financial data available. Please check DataCoordinator logs."
            )

        logger.info(f"[Fundamentals Analyst] Analyzing {ticker} on {current_date}")

        market_info = StockUtils.get_market_info(ticker)
        company_name = get_company_name(ticker, market_info)

        system_message = f"""你是一位专业的股票基本面分析师。
请基于以下**真实财务数据**对 {company_name} ({ticker}) 进行深度的基本面分析。

=== 财务数据 ===
{financial_data}
================

**分析要求（必须严格遵守）：**
1. **数据来源**：必须严格基于上述提供的财务数据进行分析，绝对禁止编造数据。
2. **财务状况**：分析营收、利润、现金流等核心指标。
3. **估值分析**：分析PE、PB、PEG等估值指标，判断当前股价是否低估/高估。
4. **盈利能力**：分析毛利率、净利率、ROE等指标。
5. **投资建议**：给出基于基本面的买入/持有/卖出建议，并提供合理的目标价位区间。

**输出格式要求：**
请使用Markdown格式，包含以下章节：
# **{company_name}（{ticker}）基本面分析报告**
## 一、公司概况与财务摘要
## 二、盈利能力与成长性分析
## 三、估值水平评估
## 四、投资建议与目标价

⚠️ **重要**：所有分析必须基于提供的数据。如果数据缺失，请明确说明。
"""

        messages = [
            ("system", system_message),
            ("human", f"请生成 {company_name} ({ticker}) 的基本面分析报告。"),
        ]

        try:
            response = llm.invoke(messages)
            return {"fundamentals_report": response.content, "messages": [response]}
        except Exception as e:
            logger.error(f"[Fundamentals Analyst] LLM调用失败: {e}", exc_info=True)
            return {
                "fundamentals_report": f"❌ 基本面分析失败: {str(e)}",
                "messages": [],
            }

    return fundamentals_analyst_node
