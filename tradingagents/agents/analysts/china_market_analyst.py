# -*- coding: utf-8 -*-
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.utils.stock_utils import StockUtils
from tradingagents.utils.company_name_utils import get_company_name

logger = get_logger("analysts.china_market")


def create_china_market_analyst(llm, toolkit):
    @log_analyst_module("china_market")
    def china_market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Retrieve pre-fetched data
        market_data = state.get("market_data", "")
        if not market_data:
            logger.warning(
                f"[China Market Analyst] No market data found in state for {ticker}"
            )
            market_data = (
                "Error: No market data available. Please check DataCoordinator logs."
            )

        logger.info(f"[China Market Analyst] Analyzing {ticker} on {current_date}")

        market_info = StockUtils.get_market_info(ticker)
        company_name = get_company_name(ticker, market_info)

        system_message = f"""你是一位专业的中国股市分析师。
请基于以下**真实市场数据**对 {company_name} ({ticker}) 进行详细的中国市场分析。

=== 市场数据 ===
{market_data}
===============

**分析要求（必须严格遵守）：**
1. **数据来源**：必须严格基于上述提供的市场数据进行分析，绝对禁止编造数据。
2. **中国股市特色**：关注A股市场的涨跌停制度、T+1交易、融资融券等特殊规则。
3. **政策影响**：评估货币政策、财政政策对股市的影响机制。
4. **板块轮动**：分析中国特色的板块轮动规律和热点切换。
5. **监管环境**：了解证监会政策、退市制度、注册制等监管变化。

**技术面分析要点：**
- 分析移动平均线（MA）、MACD、RSI、布林带等技术指标（如果数据中包含）
- 评估价格趋势和支撑/阻力位
- 分析量价配合情况（注意A股单位：手/股）

**基本面分析要点：**
- 分析PE、PB、ROE等估值指标
- 评估盈利能力和成长性
- 结合中国会计准则进行分析

**输出格式要求：**
请使用Markdown格式，包含以下章节：
# **{company_name}（{ticker}）中国市场分析报告**
## 一、股票基本信息
## 二、技术面分析
## 三、基本面分析
## 四、政策面分析
## 五、板块与行业分析
## 六、投资建议

⚠️ **重要**：所有分析必须基于提供的数据。如果数据缺失，请明确说明。
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


def create_china_stock_screener(llm, toolkit):
    """创建中国股票筛选器"""

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
