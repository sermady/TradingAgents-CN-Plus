# -*- coding: utf-8 -*-
"""
中国市场分析师 - A股特色专家

职责:
- 分析A股市场特色指标（涨跌停、换手率、量比）
- 政策面分析（证监会、退市制度、注册制）
- A股投资者结构和市场情绪特征

不重复其他分析师的工作:
- ❌ 技术面分析（由市场分析师负责）
- ❌ 基本面分析（由基本面分析师负责）
- ❌ 新闻分析（由新闻分析师负责）
- ❌ 社交媒体情绪（由社交媒体分析师负责）
"""

from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.utils.stock_utils import StockUtils
from tradingagents.utils.company_name_utils import get_company_name

logger = get_logger("analysts.china_market")


def create_china_market_analyst(llm, toolkit=None):
    """
    创建中国市场分析师节点

    Args:
        llm: 语言模型实例
        toolkit: 工具包（可选，用于兼容性）

    Returns:
        china_market_analyst_node: 中国市场分析师节点函数
    """

    @log_analyst_module("china_market")
    def china_market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Retrieve pre-fetched data and metadata
        china_market_data = state.get("china_market_data", "")
        data_quality_score = state.get("data_quality_score", 0.0)
        data_sources = state.get("data_sources", {})
        data_issues = state.get("data_issues", {})
        china_market_source = data_sources.get("china_market", "unknown")
        china_market_issues = data_issues.get("china_market", [])

        if not china_market_data or "❌" in china_market_data:
            logger.warning(
                f"[China Market Analyst] China market data unavailable for {ticker} (source: {china_market_source})"
            )
            china_market_data = (
                "警告：A股市场特色数据不可用。已尝试获取但失败。\n"
                "请检查网络连接或稍后重试。"
            )

        logger.info(
            f"[China Market Analyst] Analyzing {ticker} on {current_date} (quality: {data_quality_score:.2f}, source: {china_market_source})"
        )

        market_info = StockUtils.get_market_info(ticker)
        company_name = get_company_name(ticker, market_info)

        # 记录数据质量问题到日志（不在提示词中显示）
        if china_market_issues:
            for issue in china_market_issues[:3]:
                logger.warning(
                    f"[China Market Analyst] Data issue for {ticker}: {issue.get('message', '')}"
                )

        # 获取 metadata 信息（如有）
        # data_metadata 可包含：PS修正标记、数据单位说明等
        # 目前为空，保留结构以备将来扩展
        data_metadata = state.get("data_metadata", {})

        # 构建 metadata 提示（可扩展：成交量单位、数据修正说明等）
        metadata_info = ""  # 中国市场分析师暂无特殊 metadata

        system_message = f"""你是一位专业的中国股市分析师，专注于A股市场特色分析。
请基于以下**A股特色数据**对 {company_name} ({ticker}) 进行详细的A股市场分析。

=== 数据信息 ===
- 数据来源: {china_market_source}
- 数据日期: {current_date}（历史数据）
{metadata_info}

=== A股特色数据 ===
{china_market_data}
================

**分析要求（必须严格遵守）：**

1. **数据来源**：必须严格基于上述提供的A股特色数据进行分析，绝对禁止编造数据。

2. **涨跌停制度分析**：
   - 检查是否触及涨停（主板+10%，ST+5%）或跌停
   - 分析封板强度和持续性
   - 评估涨跌停对交易的影响

3. **换手率深度分析**：
   - 换手率 < 3%：交易清淡，关注较低
   - 换手率 3-7%：交易活跃，正常范围
   - 换手率 7-10%：高度活跃，需关注
   - 换手率 > 10%：异常活跃，可能有重大消息
   - 换手率 > 20%：极度活跃，高风险高机会
   - 结合价格走势分析换手率变化的意义

4. **量比分析**（如果数据包含）：
   - 量比 > 1.5：放量，资金关注
   - 量比 < 0.8：缩量，交易清淡
   - 结合换手率判断资金流向

5. **A股投资者结构特征**：
   - 散户与机构行为差异
   - 北向资金流向（如果提及）
   - 主力资金动向判断

6. **政策面分析**：
   - 证监会监管政策影响
   - 退市制度风险评估
   - 注册制改革影响
   - 行业政策导向

7. **投资建议**：基于A股特色给出针对性的交易建议，包括：
   - 适合A股市场的操作策略
   - 风险控制要点（A股特色）
   - 买卖时机判断

**输出格式要求：**
请使用Markdown格式，包含以下章节：
# **{company_name}（{ticker}）A股市场特色分析报告**
## 一、A股交易特征分析（涨跌停、换手率、量比）
## 二、投资者结构与资金流向
## 三、政策面与监管环境影响
## 四、A股特色投资策略建议

⚠️ **重要**：
- 所有分析必须基于提供的数据
- 不要重复技术面分析（已由市场分析师完成）
- 不要重复基本面分析（已由基本面分析师完成）
- 专注于A股市场特有的交易制度和投资者行为
"""

        messages = [
            ("system", system_message),
            ("human", f"请生成 {company_name} ({ticker}) 的A股市场特色分析报告。"),
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
