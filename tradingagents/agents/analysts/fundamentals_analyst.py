# -*- coding: utf-8 -*-
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.utils.stock_utils import StockUtils
from tradingagents.utils.company_name_utils import get_company_name
from langchain_core.messages import AIMessage

logger = get_logger("analysts.fundamentals")


def create_fundamentals_analyst(llm, toolkit=None):
    """
    创建基本面分析师节点

    Args:
        llm: 语言模型实例
        toolkit: 工具包（可选，用于兼容性）

    Returns:
        fundamentals_analyst_node: 基本面分析师节点函数
    """

    @log_analyst_module("fundamentals")
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Retrieve pre-fetched data and metadata
        financial_data = state.get("financial_data", "")
        data_quality_score = state.get("data_quality_score", 0.0)
        data_sources = state.get("data_sources", {})
        data_issues = state.get("data_issues", {})

        # 检查数据质量
        financial_source = data_sources.get("financial", "unknown")
        financial_issues = data_issues.get("financial", [])

        if not financial_data or "❌" in financial_data:
            logger.warning(
                f"[Fundamentals Analyst] Financial data unavailable for {ticker} (source: {financial_source})"
            )
            financial_data = (
                "警告：财务数据不可用。已尝试从多个数据源获取但均失败。\n"
                "请检查网络连接或稍后重试。"
            )

        logger.info(
            f"[Fundamentals Analyst] Analyzing {ticker} on {current_date} (quality: {data_quality_score:.2f}, source: {financial_source})"
        )

        market_info = StockUtils.get_market_info(ticker)
        company_name = get_company_name(ticker, market_info)

        # 构建数据质量问题提示
        quality_warning = ""
        if financial_issues:
            quality_warning = "\n**数据质量警告：**\n"
            for issue in financial_issues[:3]:  # 最多显示3个问题
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

        # 获取 metadata 信息（PS修正、成交量单位等）
        data_metadata = state.get("data_metadata", {})
        corrected_ps = data_metadata.get("corrected_ps")
        volume_unit_info = data_metadata.get("volume_unit_info")

        # 构建 metadata 提示
        metadata_info = ""
        if corrected_ps:
            metadata_info += f"\n- **PS比率修正**: 数据源报告的PS可能有误，正确值约为 {corrected_ps:.2f}"
        if volume_unit_info:
            metadata_info += f"\n- **成交量单位**: {volume_unit_info}"

        system_message = f"""你是一位专业的股票基本面分析师。
请基于以下**真实财务数据**对 {company_name} ({ticker}) 进行深度的基本面分析。

=== 数据质量信息 ===
- 数据质量评分: {data_quality_score:.0%} ({data_quality_level})
- 数据来源: {financial_source}
- 分析日期: {current_date}
- 质量指导: {quality_guidance}
{quality_warning}{metadata_info}

=== 财务数据 ===
{financial_data}
================

**分析要求（必须严格遵守）：**
1. **数据来源**：必须严格基于上述提供的财务数据进行分析，绝对禁止编造数据。
2. **数据质量意识**：请注意数据质量评分和任何数据质量警告，在分析中适当考虑数据可靠性。
   - 质量等级说明: {quality_guidance}
3. **财务状况**：分析营收、利润、现金流等核心指标。
4. **估值分析**：分析PE、PB、PS、PEG等估值指标，判断当前股价是否低估/高估。
   - ⚠️ **特别注意PS比率**：如果提示中有PS修正值，请使用修正值进行分析。
   - PS 正确计算公式: PS = 总市值 / 总营收
5. **盈利能力**：分析毛利率、净利率、ROE等指标。
6. **数据异常处理**：
   - 如果发现PE、PB、PS等估值指标异常，请使用市值和营收/净利润重新计算验证
   - 如果数据有明显错误，请在报告中指出并说明正确的计算方法
7. **投资建议**：给出基于基本面的买入/持有/卖出建议，并提供合理的目标价位区间。

**输出格式要求：**
请使用Markdown格式，包含以下章节：
# **{company_name}（{ticker}）基本面分析报告**
## 一、公司概况与财务摘要
## 二、数据质量评估
## 三、盈利能力与成长性分析
## 四、估值水平评估
## 五、投资建议与目标价

⚠️ **重要**：
- 所有分析必须基于提供的数据。如果数据缺失，请明确说明。
- 特别关注数据质量警告中的PS修正信息。
- 数据质量评分低于50%时，请在投资建议中提醒用户谨慎参考。
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
