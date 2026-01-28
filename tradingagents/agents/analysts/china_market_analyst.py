# -*- coding: utf-8 -*-
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.utils.stock_utils import StockUtils
from tradingagents.utils.company_name_utils import get_company_name

logger = get_logger("analysts.china_market")


def create_china_market_analyst(llm):
    """
    创建中国市场分析师节点

    Args:
        llm: 语言模型实例

    Returns:
        china_market_analyst_node: 中国市场分析师节点函数
    """
    @log_analyst_module("china_market")
    def china_market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Retrieve pre-fetched data and metadata
        market_data = state.get("market_data", "")
        financial_data = state.get("financial_data", "")
        data_quality_score = state.get("data_quality_score", 0.0)
        data_sources = state.get("data_sources", {})
        data_issues = state.get("data_issues", {})

        # 检查数据质量
        market_source = data_sources.get("market", "unknown")
        financial_source = data_sources.get("financial", "unknown")
        market_issues = data_issues.get("market", [])
        financial_issues = data_issues.get("financial", [])

        if not market_data or "❌" in market_data:
            logger.warning(
                f"[China Market Analyst] Market data unavailable for {ticker} (source: {market_source})"
            )
            market_data = (
                "警告：市场数据不可用。已尝试从多个数据源获取但均失败。\n"
                "请检查网络连接或稍后重试。"
            )

        logger.info(f"[China Market Analyst] Analyzing {ticker} on {current_date} (quality: {data_quality_score:.2f}, source: {market_source})")

        market_info = StockUtils.get_market_info(ticker)
        company_name = get_company_name(ticker, market_info)

        # 构建数据质量问题提示
        quality_warning = ""
        all_issues = market_issues + financial_issues
        if all_issues:
            quality_warning = "\n**数据质量警告：**\n"
            for issue in all_issues[:3]:  # 最多显示3个问题
                severity = issue.get("severity", "info")
                message = issue.get("message", "")
                if severity in ["error", "critical"]:
                    quality_warning += f"- ⚠️ {message}\n"
                elif severity == "warning":
                    quality_warning += f"- ℹ️ {message}\n"

        # 根据数据质量等级给出不同的分析指导
        data_quality_level = "high" if data_quality_score >= 0.8 else "medium" if data_quality_score >= 0.5 else "low"
        quality_guidance = {
            "high": "数据质量良好，可以进行深入分析。",
            "medium": "数据质量一般，分析时请留意可能存在的数据偏差。",
            "low": "数据质量较差，请谨慎分析，重点关注数据可靠性问题。"
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

        # 基本面数据部分
        fundamentals_section = ""
        if financial_data and "❌" not in financial_data:
            fundamentals_section = f"""

=== 基本面数据 ===
{financial_data}
数据来源: {financial_source}
================"""

        system_message = f"""你是一位专业的中国股市分析师，专注于A股市场分析。
请基于以下**真实市场数据**对 {company_name} ({ticker}) 进行详细的中国市场分析。

=== 数据质量信息 ===
- 数据质量评分: {data_quality_score:.0%} ({data_quality_level})
- 市场数据来源: {market_source}
- 基本面数据来源: {financial_source}
- 分析日期: {current_date}
- 质量指导: {quality_guidance}
{quality_warning}{metadata_info}

=== 市场数据 ===
{market_data}
================{fundamentals_section}

**A股特色分析要求（必须严格遵守）：**
1. **数据来源**：必须严格基于上述提供的市场数据进行分析，绝对禁止编造数据。
2. **数据质量意识**：请注意数据质量评分和任何数据质量警告，在分析中适当考虑数据可靠性。
   - 质量等级说明: {quality_guidance}
3. **特别关注PS修正**: 如果提示中有PS修正值，请在估值分析中使用修正值。

**A股市场特色分析要点：**
1. **涨跌停制度分析**：
   - 检查是否触及涨停（+10% for 主板/ST: +5%）或跌停
   - 分析封板强度和封单量（如果数据可用）
   - 评估涨停/跌停的持续性

2. **换手率分析**：
   - 换手率 < 3%：交易清淡，关注较低
   - 换手率 3-7%：交易活跃，正常范围
   - 换手率 7-10%：高度活跃，需关注
   - 换手率 > 10%：异常活跃，可能有重大消息
   - 换手率 > 20%：极度活跃，高风险高机会
   - 注意：成交量已统一转换为"股"

3. **量比分析**（如果数据包含）：
   - 量比 > 1.5：放量，资金关注
   - 量比 < 0.8：缩量，交易清淡

4. **政策面分析**：
   - 关注证监会政策、退市制度、注册制变化
   - 评估行业政策对公司的影响
   - 北向资金流向（如果数据可用）

5. **技术面分析**：
   - 分析移动平均线（MA）、MACD、RSI、布林带等指标
   - 评估价格趋势和支撑/阻力位
   - 分析量价配合情况（成交量单位已统一为"股"）

6. **基本面分析**：
   - 分析PE、PB、PS、ROE等估值指标
   - ⚠️ **特别注意PS比率**：如果提示中有PS修正值，请使用修正值
   - PS 正确计算公式: PS = 总市值 / 总营收
   - 评估盈利能力和成长性

**输出格式要求：**
请使用Markdown格式，包含以下章节：
# **{company_name}（{ticker}）A股市场分析报告**
## 一、股票基本信息与数据质量评估
## 二、A股市场特色指标分析（涨跌停、换手率、量比）
## 三、技术面分析
## 四、基本面与估值分析
## 五、政策面与行业分析
## 六、投资建议与风险提示

⚠️ **重要**：
- 所有分析必须基于提供的数据。如果数据缺失，请明确说明。
- 特别关注A股特色指标（涨跌停、换手率等）的分析。
- 如发现PS比率问题，请在报告中指出并说明修正后的合理值。
- 数据质量评分低于50%时，请在投资建议中提醒用户谨慎参考。
"""

        messages = [
            ("system", system_message),
            ("human", f"请生成 {company_name} ({ticker}) 的中国市场分析报告。"),
        ]

        try:
            response = llm.invoke(messages)
            return {"china_market_report": response.content, "messages": [response]}
        except Exception as e:
            logger.error(f"[China Market Analyst] LLM调用失败: {e}", exc_info=True)
            return {
                "china_market_report": f"❌ 中国市场分析失败: {str(e)}",
                "messages": [],
            }

    return china_market_analyst_node


def create_china_stock_screener(llm):
    """创建中国股票筛选器

    Args:
        llm: 语言模型实例
    """

    @log_analyst_module("china_stock_screener")
    def china_stock_screener_node(state):
        current_date = state["trade_date"]

        # Note: 股票筛选器通常不针对单个股票，因此不从 state 读取特定股票数据
        # 如果需要市场概况数据，可以添加 state.get("market_overview", "")

        logger.info(
            f"[China Stock Screener] Generating stock screening recommendations on {current_date}"
        )

        system_message = f"""你是一位专业的中国股票筛选专家，负责从A股市场中筛选出具有投资价值的股票。

筛选维度包括：
1. **基本面筛选**: 
   - 财务指标：ROE、ROA、净利润增长率、营收增长率
   - 估值指标：PE、PB、PEG、PS比率
   - 财务健康：资产负债率、流动比率、速动比率

2. **技术面筛选**:
   - 趋势指标：均线系统、MACD、KDJ
   - 动量指标：RSI、威廉指标、CCI
   - 成交量指标：量价关系、换手率

3. **市场面筛选**:
   - 资金流向：主力资金净流入、北向资金偏好
   - 机构持仓：基金重仓、社保持仓、QFII持仓
   - 市场热度：概念板块活跃度、题材炒作程度

4. **政策面筛选**:
   - 政策受益：国家政策扶持行业
   - 改革红利：国企改革、混改标的
   - 监管影响：监管政策变化的影响

筛选策略：
- **价值投资**: 低估值、高分红、稳定增长
- **成长投资**: 高增长、新兴行业、技术创新
- **主题投资**: 政策驱动、事件催化、概念炒作
- **周期投资**: 经济周期、行业周期、季节性

**输出格式要求：**
请使用Markdown格式，包含以下章节：
# **中国A股股票筛选报告**
## 一、当前市场环境分析
## 二、筛选策略说明
## 三、重点推荐板块
## 四、个股推荐（如有）
## 五、风险提示

请基于当前市场环境和政策背景，提供专业的股票筛选建议。
当前分析日期：{current_date}。
"""

        messages = [
            ("system", system_message),
            ("human", f"请生成 {current_date} 的中国A股股票筛选报告。"),
        ]

        try:
            response = llm.invoke(messages)
            return {"stock_screening_report": response.content, "messages": [response]}
        except Exception as e:
            logger.error(f"[China Stock Screener] LLM调用失败: {e}", exc_info=True)
            return {
                "stock_screening_report": f"❌ 股票筛选失败: {str(e)}",
                "messages": [],
            }

    return china_stock_screener_node
