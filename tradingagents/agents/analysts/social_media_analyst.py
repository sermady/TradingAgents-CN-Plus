# -*- coding: utf-8 -*-
"""
市场情绪与资金流向分析师

P1-3: 替换原有的死节点社交媒体分析师。
基于真实的市场资金流向数据（龙虎榜、北向资金、融资融券、大宗交易）
分析市场参与者行为和资金动向，作为情绪面分析的核心依据。
"""

from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.utils.stock_utils import StockUtils
from tradingagents.utils.company_name_utils import get_company_name

logger = get_logger("analysts.social_media")


def create_social_media_analyst(llm, toolkit):
    @log_analyst_module("social_media")
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Retrieve pre-fetched data and metadata
        sentiment_data = state.get("sentiment_data", "")
        data_quality_score = state.get("data_quality_score", 0.0)
        data_sources = state.get("data_sources", {})
        data_issues = state.get("data_issues", {})

        # 检查数据质量
        sentiment_source = data_sources.get("sentiment", "unknown")
        sentiment_issues = data_issues.get("sentiment", [])

        market_info = StockUtils.get_market_info(ticker)
        company_name = get_company_name(ticker, market_info)

        # 检查数据是否为有效的资金流向数据 (P1-3: 新判断逻辑)
        has_flow_data = sentiment_data and any(
            kw in sentiment_data
            for kw in ["龙虎榜", "北向资金", "融资融券", "大宗交易", "市场资金流向"]
        )

        data_unavailable = not sentiment_data or (
            "❌" in sentiment_data
            and not has_flow_data
        )

        if data_unavailable:
            logger.warning(
                f"[Social Media Analyst] All data unavailable for {ticker} (source: {sentiment_source}), "
                f"generating default report"
            )
            default_report = _build_default_report(company_name, ticker, current_date, sentiment_source)
            return {"sentiment_report": default_report, "messages": []}

        logger.info(
            f"[Social Media Analyst] Analyzing {ticker} on {current_date} "
            f"(quality: {data_quality_score:.2f}, source: {sentiment_source}, "
            f"has_flow_data: {has_flow_data})"
        )

        # 记录数据质量问题到日志
        if sentiment_issues:
            for issue in sentiment_issues[:3]:
                logger.warning(
                    f"[Social Media Analyst] Data issue for {ticker}: {issue.get('message', '')}"
                )

        # 根据数据类型选择 prompt
        if has_flow_data:
            system_message = _build_flow_analysis_prompt(
                company_name, ticker, current_date, sentiment_source, sentiment_data
            )
        else:
            system_message = _build_sentiment_analysis_prompt(
                company_name, ticker, current_date, sentiment_source, sentiment_data
            )

        messages = [
            ("system", system_message),
            ("human", f"请生成 {company_name} ({ticker}) 的市场情绪与资金流向分析报告。"),
        ]

        try:
            response = llm.invoke(messages)
            return {"sentiment_report": response.content, "messages": [response]}
        except Exception as e:
            logger.error(f"[Social Media Analyst] LLM调用失败: {e}", exc_info=True)
            return {"sentiment_report": f"❌ 情绪分析失败: {str(e)}", "messages": []}

    return social_media_analyst_node


def _build_flow_analysis_prompt(
    company_name: str,
    ticker: str,
    current_date: str,
    source: str,
    data: str,
) -> str:
    """构建资金流向分析 prompt (P1-3 核心 prompt)"""
    return f"""你是一位专业的市场情绪与资金流向分析师。
请基于以下**真实市场数据**对 {company_name} ({ticker}) 进行详细的资金流向和市场情绪分析。

=== 数据信息 ===
- 数据来源: {source}
- 数据日期: {current_date}

=== 市场资金流向数据 ===
{data}
================

**分析要求（必须严格遵守）：**
1. **数据来源**：必须严格基于上述提供的资金流向数据进行分析，绝对禁止编造数据。
2. **龙虎榜分析**（如有数据）：
   - 判断机构/游资的买卖方向和力度
   - 分析上榜原因及其对后市的含义
   - 关注"机构专用"席位的买卖行为（机构买入通常更有参考价值）
3. **北向资金分析**（如有数据）：
   - 判断外资近期的流入/流出趋势
   - 结合大盘走势分析北向资金的择时信号
   - 注意：北向资金是市场层面数据，需结合个股分析
4. **融资融券分析**（如有数据）：
   - 融资余额变化反映杠杆资金情绪
   - 融券余额变化反映做空力量
   - 融资/融券比例变化判断多空力量对比
5. **大宗交易分析**（如有数据）：
   - 折价/溢价率反映机构对后市的态度
   - 折价大宗交易可能暗示减持压力
   - 溢价大宗交易可能暗示看好后市
6. **综合资金面判断**：
   - 综合多个资金流向指标，给出整体资金面偏多/偏空/中性的判断
   - 不同资金信号冲突时，说明原因并给出权重判断
7. **投资建议规范**：
   - 避免使用绝对化表述
   - 使用"倾向于"、"大概率"、"预计"等谨慎表述
   - 提供明确的理由和依据

**输出格式要求：**
请使用Markdown格式，包含以下章节：
# **{company_name}（{ticker}）市场情绪与资金流向分析报告**
## 一、资金流向综合概览
## 二、机构行为分析（龙虎榜/大宗交易）
## 三、资金面信号分析（北向资金/融资融券）
## 四、情绪面投资建议

⚠️ **重要**：所有分析必须基于提供的数据。如果某类数据缺失，请明确说明并基于可用数据分析。"""


def _build_sentiment_analysis_prompt(
    company_name: str,
    ticker: str,
    current_date: str,
    source: str,
    data: str,
) -> str:
    """构建传统舆情分析 prompt (兜底路径)"""
    return f"""你是一位专业的市场情绪分析师。
请基于以下**社交媒体和投资者情绪数据**对 {company_name} ({ticker}) 进行详细的情绪面分析。

=== 数据信息 ===
- 数据来源: {source}
- 数据日期: {current_date}

=== 情绪数据 ===
{data}
================

**分析要求（必须严格遵守）：**
1. **数据来源**：必须严格基于上述提供的情绪数据进行分析，绝对禁止编造数据。
2. **情绪概况**：评估当前市场对该股票的整体情绪（贪婪/恐惧/中性）。
3. **散户vs机构**：分析散户讨论热度与可能的机构动向。
4. **舆情风险**：识别潜在的舆情风险点。
5. **数据异常处理**：如果情绪数据看起来异常，请在报告中指出。
6. **投资建议**：基于逆向思维或顺势交易策略给出建议。

**输出格式要求：**
请使用Markdown格式，包含以下章节：
# **{company_name}（{ticker}）市场情绪分析报告**
## 一、投资者情绪概览
## 二、社交媒体热度分析
## 三、潜在舆情风险
## 四、情绪面投资建议

⚠️ **重要**：所有分析必须基于提供的数据。如果数据缺失或异常，请明确说明。"""


def _build_default_report(
    company_name: str,
    ticker: str,
    current_date: str,
    source: str,
) -> str:
    """生成默认报告 (所有数据源均不可用时)"""
    return f"""# **{company_name}（{ticker}）市场情绪分析报告**

## 一、数据获取状态

⚠️ **数据获取受限**：市场资金流向和社交媒体数据均不可用。

数据源状态：**{source}**

**可能原因**：
- AKShare 接口限制或版本变化
- 网络连接问题
- 非交易日无数据

## 二、替代分析建议

由于资金流向数据不可用，建议投资者通过以下途径了解市场情绪：

1. **关注技术面信号**
   - 成交量变化是最直接的市场情绪指标
   - 换手率反映交易活跃度和市场关注度
   - 量比指标显示资金关注度变化

2. **参考基本面变化**
   - 业绩预期和实际表现驱动情绪长期走向
   - 机构研报评级变化反映专业投资者看法

3. **结合新闻分析**
   - 财经新闻中的市场情绪评估
   - 政策面变化对投资者信心的影响

---

*⚠️ 注：本报告因数据获取限制未能提供完整的资金流向分析。建议结合其他分析报告进行综合判断。*

*数据时间: {current_date}*"""
