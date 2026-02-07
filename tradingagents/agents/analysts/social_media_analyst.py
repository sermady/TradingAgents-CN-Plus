# -*- coding: utf-8 -*-
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.utils.stock_utils import StockUtils
from tradingagents.utils.company_name_utils import get_company_name
from langchain_core.messages import AIMessage

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

        # 检查情绪数据是否可用
        data_unavailable = (
            not sentiment_data or "❌" in sentiment_data or "警告" in sentiment_data
        )

        if data_unavailable:
            logger.warning(
                f"[Social Media Analyst] Sentiment data unavailable for {ticker} (source: {sentiment_source}), "
                f"generating default report instead of calling LLM"
            )
            # 生成默认报告，避免LLM生成空内容
            default_report = f"""# **{company_name}（{ticker}）市场情绪分析报告**

## 一、投资者情绪概览

⚠️ **数据获取状态**：由于中国社交媒体平台API限制，无法获取实时社交媒体情绪数据。

当前可用的数据源：**{sentiment_source}**

**数据限制说明**：
- 微博、雪球等平台的公开API已关闭或限制访问
- 东方财富等财经网站的数据抓取受到反爬虫机制限制
- 当前仅能通过财经新闻间接了解市场情绪

## 二、社交媒体热度分析

**数据缺失** - 无法获取以下指标：
- 股吧/雪球讨论热度
- 微博提及量和情绪倾向
- 散户情绪指数
- 大V观点汇总

## 三、潜在舆情风险

基于新闻分析的舆情风险评估（详细内容请参考新闻分析报告）：
- 请查看 `news_report.md` 了解最新舆情动态
- 关注监管政策变化对投资者情绪的影响
- 注意行业热点切换对资金流向的影响

## 四、情绪面投资建议

由于社交媒体情绪数据不可用，建议投资者：

1. **关注新闻舆情**
   - 参考新闻分析报告中的市场情绪评估
   - 关注主流媒体对公司和行业的报道倾向

2. **分析技术面信号**
   - 成交量变化可能反映市场情绪
   - 资金流向数据可作为情绪替代指标

3. **重视基本面分析**
   - 业绩预期和实际表现是情绪的根基
   - 机构研报评级变化反映专业投资者看法

4. **参考A股特色指标**
   - 换手率反映交易活跃度
   - 量比指标显示资金关注度

---

*⚠️ 注：本报告因数据获取限制未能提供完整的社交媒体情绪分析。建议结合其他分析报告进行综合判断。*

*数据时间: {current_date}*
"""
            return {"sentiment_report": default_report, "messages": []}

        logger.info(
            f"[Social Media Analyst] Analyzing {ticker} on {current_date} (quality: {data_quality_score:.2f}, source: {sentiment_source})"
        )

        # 记录数据质量问题到日志（不在提示词中显示）
        if sentiment_issues:
            for issue in sentiment_issues[:3]:
                logger.warning(
                    f"[Social Media Analyst] Data issue for {ticker}: {issue.get('message', '')}"
                )

        # 获取 metadata 信息（如有）
        # data_metadata 可包含：PS修正标记、数据单位说明等
        # 目前为空，保留结构以备将来扩展
        data_metadata = state.get("data_metadata", {})

        # 构建 metadata 提示（可扩展：成交量单位、数据修正说明等）
        metadata_info = ""  # 社交媒体分析师暂无特殊 metadata

        system_message = f"""你是一位专业的市场情绪分析师。
请基于以下**社交媒体和投资者情绪数据**对 {company_name} ({ticker}) 进行详细的情绪面分析。

=== 数据信息 ===
- 数据来源: {sentiment_source}
- 数据日期: {current_date}（历史数据）
{metadata_info}

=== 情绪数据 ===
{sentiment_data}
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

⚠️ **重要**：所有分析必须基于提供的数据。如果数据缺失或异常，请明确说明。
"""

        messages = [
            ("system", system_message),
            ("human", f"请生成 {company_name} ({ticker}) 的情绪分析报告。"),
        ]

        try:
            response = llm.invoke(messages)
            return {"sentiment_report": response.content, "messages": [response]}
        except Exception as e:
            logger.error(f"[Social Media Analyst] LLM调用失败: {e}", exc_info=True)
            return {"sentiment_report": f"❌ 情绪分析失败: {str(e)}", "messages": []}

    return social_media_analyst_node
