# -*- coding: utf-8 -*-
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.utils.stock_utils import StockUtils
from tradingagents.utils.company_name_utils import get_company_name

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

        # 记录数据质量问题到日志（不在提示词中显示）
        if market_issues:
            for issue in market_issues[:3]:
                logger.warning(
                    f"[Market Analyst] Data issue for {ticker}: {issue.get('message', '')}"
                )

        # 获取 metadata 信息（如有）
        data_metadata = state.get("data_metadata", {})

        # 构建 metadata 提示
        metadata_info = "\n- **成交量单位**: 手 (1手=100股)"

        # P2-3: 获取预计算技术信号摘要 (已含 === 分隔符, 无需额外包装)
        tech_signals_text = state.get("technical_signals_text", "")
        tech_signals_block = f"\n{tech_signals_text}\n" if tech_signals_text else ""

        system_message = f"""你是一位专业的股票技术分析师。
请基于以下**真实市场数据**对 {company_name} ({ticker}) 进行详细的技术分析。

=== 数据信息 ===
- 数据来源: {market_source}
- 数据日期: {current_date}（历史数据）
{metadata_info}
{tech_signals_block}
=== 市场数据 ===
{market_data}
================

**分析要求（必须严格遵守）：**
1. **数据来源**：必须严格基于上述提供的市场数据进行分析，绝对禁止编造数据。
2. **核心技术指标**：分析以下指标（如果数据中包含）：
   - **趋势类**：移动平均线（MA5/10/20/60）、MACD（DIF/DEA/柱状图）
   - **动量类**：RSI（6日超短期、14日标准）、KDJ（K/D/J值及金叉死叉）
   - **波动类**：布林带（价格相对上中下轨位置）、ATR（14日平均真实波幅，衡量波动强度）
   - **量价类**：OBV（能量潮，判断资金流向）、成交量趋势
   - **超买超卖**：Williams %R（-20以上超买，-80以下超卖）、CCI（+100以上超买，-100以下超卖）
3. **价格趋势**：分析短期和中期价格走势。
4. **成交量分析**：
   - 关注单日成交量与5日均量的关系
   - 量比>=2.0为"巨量"，>=1.5为"放量"，<0.8为"缩量"
   - 结合OBV趋势判断主力资金动向
   - 结合价格走势分析量价配合（放量上涨、缩量下跌等）
5. **多指标交叉验证**：综合多个指标的信号进行交叉验证，避免单一指标误判。例如：
   - RSI超买 + KDJ高位死叉 + Williams %R超买 = 强卖出信号
   - MACD金叉 + OBV上升 + 布林带中轨上方 = 偏多信号
6. **数据异常处理**：如果某些指标看起来异常（如成交量数据异常），请在报告中指出。
7. **投资建议规范**：
   - 建议等级：使用"强烈买入/买入/谨慎买入/持有/谨慎卖出/卖出/强烈卖出/中性观望"之一
   - 避免使用绝对化表述（如"必须"、"务必"、"绝对"、"一定"、"坚决"）
   - 建议使用"倾向于"、"大概率"、"预计"等更谨慎的表述
   - 提供明确的理由和依据

**输出格式要求：**
请使用Markdown格式，包含以下章节：
# **{company_name}（{ticker}）技术分析报告**
## 一、股票基本信息
## 二、技术指标分析（含趋势、动量、波动、量价指标）
## 三、多指标交叉验证与信号判断
## 四、价格趋势分析
## 五、投资建议

⚠️ **重要**：所有分析必须基于提供的数据。如果数据缺失或异常，请明确说明。
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
