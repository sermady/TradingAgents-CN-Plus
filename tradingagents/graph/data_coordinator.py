# -*- coding: utf-8 -*-
"""
数据协调器节点 - 负责预获取所有必要的数据（仅限A股）
绕过 LLM 工具绑定，直接调用统一数据获取方法
"""

from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.utils.logging_init import get_logger

logger = get_logger("data_coordinator")


def data_coordinator_node(state: AgentState):
    """
    Data Coordinator Node - 集中式数据预取节点

    负责预获取所有 A 股必要的数据（Market, Fundamentals, News, Sentiment）
    并存储在 AgentState 中供下游分析师使用。

    这种集中式方法可以避免：
    1. 重复的 API 调用
    2. 分析师节点无限循环尝试调用工具
    3. 工具失败时产生幻觉

    ⚡ 关键改进：绕过 LLM 工具绑定，直接调用数据获取方法

    注意：当前仅支持 A 股分析
    """
    logger.info("🔄 [Data Coordinator] 开始集中式数据预取...")

    company = state.get("company_of_interest", "")
    trade_date = state.get("trade_date", "")

    if not company:
        logger.error("❌ [Data Coordinator] 股票代码为空")
        return {
            "market_data": "❌ 错误：股票代码为空",
            "financial_data": "❌ 错误：股票代码为空",
            "news_data": "❌ 错误：股票代码为空",
            "sentiment_data": "❌ 错误：股票代码为空",
        }

    # 🔧 检测股票市场类型
    from tradingagents.utils.stock_utils import StockUtils

    market_info = StockUtils.get_market_info(company)
    is_china = market_info.get("is_china", False)

    if not is_china:
        logger.warning(
            f"⚠️ [Data Coordinator] 非A股市场（{market_info.get('market_name', 'Unknown')}），跳过数据预取"
        )
        logger.info(f"💡 提示：分析师将使用原有的工具调用流程获取数据")
        # 返回空数据，让分析师使用原有工具流程
        return {
            "market_data": "",
            "financial_data": "",
            "news_data": "",
            "sentiment_data": "",
        }

    # 仅支持 A 股数据预取
    logger.info(f"📊 目标: {company}, 交易日期: {trade_date} (A 股)")
    logger.info("📌 注意：当前 Data Coordinator 仅支持 A 股数据预取")

    # 初始化结果
    updates = {
        "market_data": "",
        "financial_data": "",
        "news_data": "",
        "sentiment_data": "",
    }

    # 1. 获取 A 股市场数据
    try:
        logger.info("📈 正在获取 A 股市场数据...")
        # 🔥 绕过 LLM 工具绑定，直接调用数据获取方法
        from tradingagents.dataflows.interface import get_china_stock_data_unified

        market_data = get_china_stock_data_unified(company, trade_date, trade_date)

        updates["market_data"] = market_data
        logger.info(f"✅ A 股市场数据获取成功，长度: {len(market_data)}")
    except Exception as e:
        logger.error(f"❌ [Data Coordinator] A 股市场数据获取失败: {e}", exc_info=True)
        updates["market_data"] = f"❌ A 股市场数据获取失败: {str(e)}"

    # 2. 获取 A 股基本面数据
    try:
        logger.info("💰 正在获取 A 股基本面数据...")
        # 🔥 绕过 LLM 工具绑定，直接调用数据获取方法
        from tradingagents.agents.utils.agent_utils import Toolkit

        financial_data = Toolkit.get_stock_fundamentals_unified.func(
            ticker=company,
            start_date=trade_date,
            end_date=trade_date,
            curr_date=trade_date,
        )

        updates["financial_data"] = financial_data
        logger.info(f"✅ A 股基本面数据获取成功，长度: {len(financial_data)}")
    except Exception as e:
        logger.error(
            f"❌ [Data Coordinator] A 股基本面数据获取失败: {e}", exc_info=True
        )
        updates["financial_data"] = f"❌ A 股基本面数据获取失败: {str(e)}"

    # 3. 获取 A 股新闻数据
    try:
        logger.info("📰 正在获取 A 股新闻数据...")
        # 🔥 绕过 LLM 工具绑定，直接调用数据获取方法
        from tradingagents.agents.utils.agent_utils import Toolkit

        news_data = Toolkit.get_stock_news_unified.func(
            ticker=company, curr_date=trade_date
        )

        updates["news_data"] = news_data
        logger.info(f"✅ A 股新闻数据获取成功，长度: {len(news_data)}")
    except Exception as e:
        logger.error(f"❌ [Data Coordinator] A 股新闻数据获取失败: {e}", exc_info=True)
        updates["news_data"] = f"❌ A 股新闻数据获取失败: {str(e)}"

    # 4. 获取 A 股舆情数据
    try:
        logger.info("😊 正在获取 A 股舆情数据...")
        # 🔥 绕过 LLM 工具绑定，直接调用数据获取方法
        from tradingagents.dataflows.interface import get_chinese_social_sentiment

        sentiment_data = get_chinese_social_sentiment(company, trade_date)

        updates["sentiment_data"] = sentiment_data
        logger.info(f"✅ A 股舆情数据获取成功，长度: {len(sentiment_data)}")
    except Exception as e:
        logger.error(f"❌ [Data Coordinator] A 股舆情数据获取失败: {e}", exc_info=True)
        updates["sentiment_data"] = f"❌ A 股舆情数据获取失败: {str(e)}"

    logger.info("✅ [Data Coordinator] 所有 A 股数据预取完成")

    return updates
