# -*- coding: utf-8 -*-
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.utils.stock_utils import StockUtils
from tradingagents.utils.company_name_utils import get_company_name
from langchain_core.messages import AIMessage

logger = get_logger("analysts.market")


def create_market_analyst(llm, toolkit=None):
    """
    创建市场分析师节点

    Args:
        llm: 语言模型实例
        toolkit: 工具包（可选，用于兼容性）

    Returns:
        market_analyst_node: 市场分析师节点函数
    """

    @log_analyst_module("market")
    def market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Retrieve pre-fetched data and metadata
        market_data = state.get("market_data", "")
        data_quality_score = state.get("data_quality_score", 0.0)
        data_sources = state.get("data_sources", {})
        data_issues = state.get("data_issues", {})

        # 检查数据质量
        market_source = data_sources.get("market", "unknown")
        market_issues = data_issues.get("market", [])

        if not market_data or "❌" in market_data:
            logger.warning(
                f"[Market Analyst] Market data unavailable for {ticker} (source: {market_source})"
            )
            market_data = (
                "警告：市场数据不可用。已尝试从多个数据源获取但均失败。\n"
                "请检查网络连接或稍后重试。"
            )

        logger.info(
            f"[Market Analyst] Analyzing {ticker} on {current_date} (quality: {data_quality_score:.2f}, source: {market_source})"
        )

        market_info = StockUtils.get_market_info(ticker)
        company_name = get_company_name(ticker, market_info)

        # 构建数据质量问题提示
        quality_warning = ""
        if market_issues:
            quality_warning = "\n**数据质量警告：**\n"
            for issue in market_issues[:3]:  # 最多显示3个问题
                severity = issue.get("severity", "info")
                message = issue.get("message", "")
                if severity in ["error", "critical"]:
                    quality_warning += f"- ⚠️ {message}\n"
                elif severity == "warning":
                    quality_warning += f"- ℹ️ {message}\n"

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
            "medium": "数据质量一般，分析时请留意可能存在的数据偏差。",
            "low": "数据质量较差，请谨慎分析，重点关注数据可靠性问题。",
        }.get(data_quality_level, "")

        # 获取 metadata 信息（成交量单位等）
        data_metadata = state.get("data_metadata", {})
        volume_unit_info = data_metadata.get("volume_unit_info")

        # 构建 metadata 提示
        metadata_info = ""
        if volume_unit_info:
            metadata_info += f"\n- **成交量单位处理**: {volume_unit_info}"

        system_message = f"""你是一位专业的股票技术分析师。
请基于以下**真实市场数据**对 {company_name} ({ticker}) 进行详细的技术分析。

=== 数据质量信息 ===
- 数据质量评分: {data_quality_score:.0%} ({data_quality_level})
- 数据来源: {market_source}
- 分析日期: {current_date}
- 质量指导: {quality_guidance}
{quality_warning}{metadata_info}

=== 市场数据 ===
{market_data}
================

**分析要求（必须严格遵守）：**
1. **数据来源**：必须严格基于上述提供的市场数据进行分析，绝对禁止编造数据。
2. **数据质量意识**：请注意数据质量评分和任何数据质量警告，在分析中适当考虑数据可靠性。
   - 质量等级说明: {quality_guidance}
3. **技术指标**：分析移动平均线（MA）、MACD、RSI、布林带等指标（如果数据中包含）。
4. **价格趋势**：分析短期和中期价格走势。
5. **成交量**：分析量价配合情况（注意A股成交量已统一转换为"股"）。
6. **数据异常处理**：如果某些指标看起来异常（如成交量数据异常），请在报告中指出。
7. **投资建议**：给出明确的买入/持有/卖出建议。

**输出格式要求：**
请使用Markdown格式，包含以下章节：
# **{company_name}（{ticker}）技术分析报告**
## 一、股票基本信息
## 二、数据质量评估
## 三、技术指标分析
## 四、价格趋势分析
## 五、投资建议

⚠️ **重要**：
- 所有分析必须基于提供的数据。如果数据缺失，请明确说明。
- 如果发现数据异常（如成交量单位问题），请在报告中指出。
- 数据质量评分低于50%时，请在投资建议中提醒用户谨慎参考。
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
