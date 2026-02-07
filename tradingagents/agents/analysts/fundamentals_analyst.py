# -*- coding: utf-8 -*-
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

        # 记录数据质量问题到日志（不在提示词中显示）
        if financial_issues:
            for issue in financial_issues[:3]:
                logger.warning(
                    f"[Fundamentals Analyst] Data issue for {ticker}: {issue.get('message', '')}"
                )

        # 获取 metadata 信息（如有）
        data_metadata = state.get("data_metadata", {})

        # 构建 metadata 提示
        # 注意：PS修正信息已由 Data Coordinator 添加到 financial_data 中，这里不再重复添加
        metadata_info = "\n- **成交量单位**: 手 (1手=100股)"

        system_message = f"""你是一位专业的股票基本面分析师。
请基于以下**真实财务数据**对 {company_name} ({ticker}) 进行深度的基本面分析。

=== 数据信息 ===
- 数据来源: {financial_source}
- 数据日期: {current_date}（历史数据）
{metadata_info}

=== 财务数据 ===
{financial_data}
================

**分析要求（必须严格遵守）：**
1. **数据来源**：必须严格基于上述提供的财务数据进行分析，绝对禁止编造数据。
2. **财务状况**：分析营收、利润、现金流等核心指标。
3. **估值分析**：分析PE、PB、PS、PEG等估值指标，判断当前股价是否低估/高估。
   - ⚠️ **特别注意PS比率**：如果财务数据中有PS修正标记（"⚠️ **PS比率修正**"），请使用修正后的PS值进行分析。
    - **估值指标计算公式（必须严格遵守）：**
      - **PE（静态市盈率）**：PE = 总市值 / 净利润
        - ⚠️ **注意**：Tushare等数据源的PE字段可能使用不同口径的净利润（如TTM净利润、最新季度净利润等），不一定与年报净利润一致
        - 如果报告中的PE值与"总市值/年报净利润"计算结果不一致，说明PE使用的是其他口径的净利润，这是正常现象
      - **PE_TTM（滚动市盈率）**：PE_TTM = 总市值 / TTM净利润（过去12个月滚动归母净利润）
      - **PB（市净率）**：PB = 总市值 / 归母净资产
      - **PS（市销率）**：PS = 总市值 / 总营收
4. **盈利能力**：分析毛利率、净利率、ROE等指标。
5. **数据异常处理**：
    - ⚠️ **PE验算注意事项**：
      - 如果Tushare等数据源的PE值与"总市值/年报净利润"计算结果不一致，这是正常现象
      - Tushare的PE字段可能使用TTM净利润、最新季度净利润或其他口径
      - 验算时，如果PE值与年报净利润不一致，请标注"数据来源为Tushare官方计算，使用的净利润口径可能与年报不同"
      - 不需要强制将PE值修改为与年报净利润一致
    - 其他指标验算：
      - PE_TTM 必须用 TTM净利润验算，不能用单期归母净利润验算
      - PB 用净资产验算
      - PS 用营收验算
    - 如果发现PB、PS等估值指标异常，请使用**正确口径**的市值和营收/净利润重新计算验证
   - **验算格式要求**：使用清晰的文本格式展示验算过程，不要使用复杂的LaTeX公式
     - ✅ **推荐格式**：
       ```
       PS计算：
         • 总市值：XX亿元
         • 营业收入：XX亿元
         • 计算：XX ÷ XX = XX倍
         • 报告PS值：XX倍
         • 结果：✓ 一致
       ```
   - 如果数据有明显错误，请在报告中指出并说明正确的计算方法
6. **投资建议规范**：
   - 建议等级：使用"强烈买入/买入/谨慎买入/持有/谨慎卖出/卖出/强烈卖出/中性观望"之一
   - 避免使用绝对化表述（如"必须"、"务必"、"绝对"、"坚决"）
   - 提供合理的目标价位区间，并说明估值依据
   - 给出明确的投资理由和风险评估

**输出格式要求：**
请使用Markdown格式，包含以下章节：
# **{company_name}（{ticker}）基本面分析报告**
## 一、公司概况与财务摘要
## 二、盈利能力与成长性分析
## 三、估值水平评估
## 四、投资建议与目标价

⚠️ **重要**：所有分析必须基于提供的数据。如果数据缺失或异常，请明确说明。
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
