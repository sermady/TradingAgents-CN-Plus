# -*- coding: utf-8 -*-
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json

# 导入统一日志系统和分析模块日志装饰器
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_analyst_module

logger = get_logger("analysts.social_media")

# 导入Google工具调用处理器
from tradingagents.agents.utils.google_tool_handler import GoogleToolCallHandler

# 导入统一公司名称工具（替换原有的重复代码）
from tradingagents.utils.company_name_utils import get_company_name


def create_social_media_analyst(llm, toolkit):
    @log_analyst_module("social_media")
    def social_media_analyst_node(state):
        # 🔧 工具调用计数器 - 防止无限循环
        tool_call_count = state.get("sentiment_tool_call_count", 0)
        max_tool_calls = 3  # 最大工具调用次数
        logger.info(
            f"🔧 [死循环修复] 当前工具调用次数: {tool_call_count}/{max_tool_calls}"
        )

        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # 获取股票市场信息
        from tradingagents.utils.stock_utils import StockUtils

        market_info = StockUtils.get_market_info(ticker)

        # 获取公司名称（使用统一工具）
        company_name = get_company_name(ticker, market_info)
        logger.info(f"[社交媒体分析师] 公司名称: {company_name}")

        # 统一使用 get_stock_sentiment_unified 工具
        # 该工具内部会自动识别股票类型并调用相应的情绪数据源
        logger.info(f"[社交媒体分析师] 使用统一情绪分析工具，自动识别股票类型")
        tools = [toolkit.get_stock_sentiment_unified]

        system_message = """您是一位专业的中国市场社交媒体和投资情绪分析师，负责分析中国投资者对特定股票的讨论和情绪变化。

您的主要职责包括：
1. 分析中国主要财经平台的投资者情绪（如雪球、东方财富股吧等）
2. 监控财经媒体和新闻对股票的报道倾向
3. 识别影响股价的热点事件和市场传言
4. 评估散户与机构投资者的观点差异
5. 分析政策变化对投资者情绪的影响
6. 评估情绪变化对股价的潜在影响

重点关注平台：
- 财经新闻：财联社、新浪财经、东方财富、腾讯财经
- 投资社区：雪球、东方财富股吧、同花顺
- 社交媒体：微博财经大V、知乎投资话题
- 专业分析：各大券商研报、财经自媒体

分析要点：
- 投资者情绪的变化趋势和原因
- 关键意见领袖(KOL)的观点和影响力
- 热点事件对股价预期的影响
- 政策解读和市场预期变化
- 散户情绪与机构观点的差异
 
 📊 数据验证要求（重要）：
- 情绪指数评分是否合理？（通常 1-10 分）
- 情绪变化趋势是否符合实际数据？
- 投资者情绪分析是否基于具体讨论内容？
- KOL观点是否有实际引用？
- 是否有矛盾的情绪数据点？
- 所有情绪评分必须使用工具返回的实际数据，不允许编造

📊 情绪影响分析要求（必须基于工具数据）：
- 量化投资者情绪强度（乐观/悲观程度）和情绪变化趋势（使用工具返回的数值）
- 评估情绪变化对短期市场反应的影响（1-5天）
- 分析散户情绪与市场走势的相关性
- 识别情绪极端点和可能的情绪反转信号
- 提供基于情绪分析的市场预期和投资建议
- 评估市场情绪对投资者信心和决策的影响程度
- 不允许回复'无法评估情绪影响'或'需要更多数据'
 
💰 必须包含（基于工具返回数据）：
- 情绪指数评分（1-10分）- 必须使用工具返回的数值
- 预期价格波动幅度
- 基于情绪的交易时机建议

请撰写详细的中文分析报告，并在报告末尾附上Markdown表格总结关键发现。
注意：由于中国社交媒体API限制，如果数据获取受限，请明确说明并提供替代分析建议。"""

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "您是一位有用的AI助手，与其他助手协作。"
                    " 使用提供的工具来推进回答问题。"
                    " 如果您无法完全回答，没关系；具有不同工具的其他助手"
                    " 将从您停下的地方继续帮助。执行您能做的以取得进展。"
                    " 如果您或任何其他助手有最终交易提案：**买入/持有/卖出**或可交付成果，"
                    " 请在您的回应前加上最终交易提案：**买入/持有/卖出**，以便团队知道停止。"
                    " 您可以访问以下工具：{tool_names}。\n{system_message}"
                    "供您参考，当前日期是{current_date}。我们要分析的当前公司是{ticker}。请用中文撰写所有分析内容。",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        # 安全地获取工具名称，处理函数和工具对象
        tool_names = []
        for tool in tools:
            if hasattr(tool, "name"):
                tool_names.append(tool.name)
            elif hasattr(tool, "__name__"):
                tool_names.append(tool.__name__)
            else:
                tool_names.append(str(tool))

        prompt = prompt.partial(tool_names=", ".join(tool_names))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        chain = prompt | llm.bind_tools(tools)

        # 修复：传递字典而不是直接传递消息列表，以便 ChatPromptTemplate 能正确处理所有变量
        result = chain.invoke({"messages": state["messages"]})

        # 使用统一的Google工具调用处理器
        if GoogleToolCallHandler.is_google_model(llm):
            logger.info(f"📊 [社交媒体分析师] 检测到Google模型，使用统一工具调用处理器")

            # 创建分析提示词
            analysis_prompt_template = GoogleToolCallHandler.create_analysis_prompt(
                ticker=ticker,
                company_name=company_name,
                analyst_type="社交媒体情绪分析",
                specific_requirements="重点关注投资者情绪、社交媒体讨论热度、舆论影响等。",
            )

            # 处理Google模型工具调用
            report, messages = GoogleToolCallHandler.handle_google_tool_calls(
                result=result,
                llm=llm,
                tools=tools,
                state=state,
                analysis_prompt_template=analysis_prompt_template,
                analyst_name="社交媒体分析师",
            )
        else:
            # 非Google模型的处理逻辑
            logger.debug(
                f"📊 [DEBUG] 非Google模型 ({llm.__class__.__name__})，使用标准处理逻辑"
            )

            report = ""
            if len(result.tool_calls) == 0:
                report = result.content
            else:
                # 有工具调用但未处理，执行工具并生成报告
                logger.info(f"[社交媒体分析师] 非Google模型有 {len(result.tool_calls)} 个工具调用，手动执行")
                tool_results = []
                for tool_call in result.tool_calls:
                    tool_name = tool_call.get('name', '')
                    tool_args = tool_call.get('args', {})
                    for tool in tools:
                        current_name = getattr(tool, 'name', getattr(tool, '__name__', ''))
                        if current_name == tool_name:
                            try:
                                if hasattr(tool, 'invoke'):
                                    tool_result = tool.invoke(tool_args)
                                else:
                                    tool_result = tool(**tool_args)
                                tool_results.append(str(tool_result))
                            except Exception as e:
                                logger.error(f"[社交媒体分析师] 工具执行失败: {e}")
                                tool_results.append(f"工具执行失败: {e}")
                            break
                if tool_results:
                    report = "\n\n".join(tool_results)

        # 🔧 降级机制：如果报告仍为空，生成默认报告
        if not report or len(report.strip()) == 0:
            logger.warning(f"[社交媒体分析师] 报告为空，启用降级机制")
            report = f"""# {ticker} 情绪分析报告

## 分析概况
**股票代码**: {ticker}
**公司名称**: {company_name}
**分析日期**: {current_date}

## 情绪分析结果

### 数据获取状态
由于社交媒体数据源限制或API调用异常，未能获取到完整的情绪数据。

### 建议关注渠道
- **雪球**: https://xueqiu.com/S/{ticker}
- **东方财富股吧**: https://guba.eastmoney.com/
- **同花顺社区**: https://t.10jqka.com.cn/

### 替代分析建议
1. 手动查看上述平台的投资者讨论热度
2. 关注财经媒体对该股票的报道倾向
3. 监控机构研报的评级变化

### 情绪指标（待验证）
| 指标 | 数值 | 说明 |
|------|------|------|
| 整体情绪 | 中性 | 待数据验证 |
| 讨论热度 | 待分析 | 需手动确认 |
| 投资者信心 | 待评估 | 建议参考其他来源 |

---
*注：本报告为降级报告，建议结合其他数据源进行综合分析*
"""
            logger.info(f"[社交媒体分析师] 生成降级报告，长度: {len(report)}")

        # 🔧 更新工具调用计数器
        return {
            "messages": [result],
            "sentiment_report": report,
            "sentiment_tool_call_count": tool_call_count + 1,
        }

    return social_media_analyst_node
