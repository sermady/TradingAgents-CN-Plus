# -*- coding: utf-8 -*-
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
import traceback

# 导入分析模块日志装饰器
from tradingagents.utils.tool_logging import log_analyst_module

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")

# 导入Google工具调用处理器
from tradingagents.agents.utils.google_tool_handler import GoogleToolCallHandler

# 导入统一公司名称工具（替换原有的重复代码）
from tradingagents.utils.company_name_utils import get_company_name


def create_market_analyst(llm, toolkit):
    def market_analyst_node(state):
        logger.debug(f"📈 [DEBUG] ===== 市场分析师节点开始 =====")

        # 🔧 工具调用计数器 - 防止无限循环
        tool_call_count = state.get("market_tool_call_count", 0)
        max_tool_calls = 3  # 最大工具调用次数
        logger.info(
            f"🔧 [死循环修复] 当前工具调用次数: {tool_call_count}/{max_tool_calls}"
        )

        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        logger.debug(f"📈 [DEBUG] 输入参数: ticker={ticker}, date={current_date}")
        logger.debug(
            f"📈 [DEBUG] 当前状态中的消息数量: {len(state.get('messages', []))}"
        )
        logger.debug(f"📈 [DEBUG] 现有市场报告: {state.get('market_report', 'None')}")

        # 根据股票代码格式选择数据源
        from tradingagents.utils.stock_utils import StockUtils

        market_info = StockUtils.get_market_info(ticker)

        logger.debug(
            f"📈 [DEBUG] 股票类型检查: {ticker} -> {market_info['market_name']} ({market_info['currency_name']})"
        )

        # 获取公司名称（使用统一工具）
        company_name = get_company_name(ticker, market_info)
        logger.info(f"[市场分析师] 公司名称: {company_name}")

        # 统一使用 get_stock_market_data_unified 工具
        # 该工具内部会自动识别股票类型（A股/港股/美股）并调用相应的数据源
        logger.info(f"📊 [市场分析师] 使用统一市场数据工具，自动识别股票类型")
        tools = [toolkit.get_stock_market_data_unified]

        # 安全地获取工具名称用于调试
        tool_names_debug = []
        for tool in tools:
            if hasattr(tool, "name"):
                tool_names_debug.append(tool.name)
            elif hasattr(tool, "__name__"):
                tool_names_debug.append(tool.__name__)
            else:
                tool_names_debug.append(str(tool))
        logger.info(f"📊 [市场分析师] 绑定的工具: {tool_names_debug}")
        logger.info(f"📊 [市场分析师] 目标市场: {market_info['market_name']}")

        # 🔥 优化：将输出格式要求放在系统提示的开头，确保LLM遵循格式
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一位专业的股票技术分析师，与其他分析师协作。\n"
                    "\n"
                    "🚨 CRITICAL REQUIREMENT - 绝对强制要求：\n"
                    "\n"
                    "❌ 严格禁止行为：\n"
                    "1. 绝对禁止在没有调用工具的情况下直接回答\n"
                    "2. 绝对禁止编造任何技术指标数据（MA、MACD、RSI、布林带等）\n"
                    "3. 绝对禁止编造价格、成交量等市场数据\n"
                    "4. 绝对禁止基于推测、假设或常识生成分析内容\n"
                    "5. 绝对禁止说'我无法获取数据'、'需要更多信息'等借口\n"
                    "\n"
                    "✅ 强制执行步骤：\n"
                    "1. 您的第一个动作必须是调用 get_stock_market_data_unified 工具\n"
                    "2. 等待工具返回真实数据\n"
                    "3. 基于工具返回的真实数据进行分析\n"
                    "4. 报告中必须明确说明数据来源（基于工具返回的数据）\n"
                    "5. 所有技术指标数值必须使用工具返回的实际数据\n"
                    "\n"
                    "⚠️ 违规后果：\n"
                    "- 不调用工具的回答将被视为无效\n"
                    "- 基于编造数据的分析将被拒绝\n"
                    "- 必须基于工具返回的数据，否则无法完成分析任务\n"
                    "- 没有例外，没有借口，必须调用工具\n"
                    "\n"
                    "📋 **分析对象：**\n"
                    "- 公司名称：{company_name}\n"
                    "- 股票代码：{ticker}\n"
                    "- 所属市场：{market_name}\n"
                    "- 计价货币：{currency_name}（{currency_symbol}）\n"
                    "- 分析日期：{current_date}\n"
                    "- ⚠️ 成交量单位特别说明：A股市场成交量通常以'股'或'手'（1手=100股）为单位。请根据数值大小智能判断（如数值为百万级通常为股，万级可能是手），并在报告中明确标注单位。\n"
                    "\n"
                    "🔧 **工具使用：**\n"
                    "你可以使用以下工具：{tool_names}\n"
                    "⚠️ 重要工作流程：\n"
                    "1. 如果消息历史中没有工具结果，立即调用 get_stock_market_data_unified 工具\n"
                    "   - ticker: {ticker}\n"
                    "   - start_date: {current_date}\n"
                    "   - end_date: {current_date}\n"
                    "   注意：系统会自动扩展到365天历史数据，你只需要传递当前分析日期即可\n"
                    "2. 如果消息历史中已经有工具结果（ToolMessage），立即基于工具数据生成最终分析报告\n"
                    "3. 不要重复调用工具！一次工具调用就足够了！\n"
                    "4. 接收到工具数据后，必须立即生成完整的技术分析报告，不要再调用任何工具\n"
                    "\n"
                    "📝 **输出格式要求（必须严格遵守）：**\n"
                    "\n"
                    "## 📊 股票基本信息\n"
                    "- 公司名称：{company_name}\n"
                    "- 股票代码：{ticker}\n"
                    "- 所属市场：{market_name}\n"
                    "\n"
                    "## 📈 技术指标分析\n"
                    "[在这里分析移动平均线、MACD、RSI、布林带等技术指标，提供具体数值]\n"
                    "\n"
                    "## 📉 价格趋势分析\n"
                    "[在这里分析价格趋势，考虑{market_name}市场特点]\n"
                    "\n"
                    "## 💭 投资建议\n"
                    "[在这里给出明确的投资建议：买入/持有/卖出]\n"
                    "\n"
                    "⚠️ **重要提醒：**\n"
                    "- 必须使用上述格式输出，不要自创标题格式\n"
                    "- 所有价格数据使用{currency_name}（{currency_symbol}）表示\n"
                    '- 确保在分析中正确使用公司名称"{company_name}"和股票代码"{ticker}"\n'
                    '- 不要在标题中使用"技术分析报告"等自创标题\n'
                    "- 如果你有明确的技术面投资建议（买入/持有/卖出），请在投资建议部分明确标注\n"
                    "- 不要使用'最终交易建议'前缀，因为最终决策需要综合所有分析师的意见\n"
                    "\n"
                    "请使用中文，基于真实数据进行分析。",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        # 安全地获取工具名称，处理函数和工具对象
        tool_names = []
        for tool in tools:
            if hasattr(tool, "name"):
                tool_names.append(tool.name)
            elif hasattr(tool, "__name__"):
                tool_names.append(tool.__name__)
            else:
                tool_names.append(str(tool))

        # 🔥 设置所有模板变量
        prompt = prompt.partial(tool_names=", ".join(tool_names))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)
        prompt = prompt.partial(company_name=company_name)
        prompt = prompt.partial(market_name=market_info["market_name"])
        prompt = prompt.partial(currency_name=market_info["currency_name"])
        prompt = prompt.partial(currency_symbol=market_info["currency_symbol"])

        # 添加详细日志
        logger.info(f"📊 [市场分析师] LLM类型: {llm.__class__.__name__}")
        logger.info(f"📊 [市场分析师] LLM模型: {getattr(llm, 'model_name', 'unknown')}")
        logger.info(f"📊 [市场分析师] 消息历史数量: {len(state['messages'])}")
        logger.info(f"📊 [市场分析师] 公司名称: {company_name}")
        logger.info(f"📊 [市场分析师] 股票代码: {ticker}")

        # 打印提示词模板信息
        logger.info("📊 [市场分析师] ========== 提示词模板信息 ==========")
        logger.info(
            f"📊 [市场分析师] 模板变量已设置: company_name={company_name}, ticker={ticker}, market={market_info['market_name']}"
        )
        logger.info("📊 [市场分析师] ==========================================")

        # 打印实际传递给LLM的消息
        logger.info(f"📊 [市场分析师] ========== 传递给LLM的消息 ==========")
        for i, msg in enumerate(state["messages"]):
            msg_type = type(msg).__name__
            # 🔥 修复：更安全地提取消息内容
            if hasattr(msg, "content"):
                msg_content = str(msg.content)[:500]  # 增加到500字符以便查看完整内容
            elif isinstance(msg, tuple) and len(msg) >= 2:
                # 处理旧格式的元组消息 ("human", "content")
                msg_content = f"[元组消息] 类型={msg[0]}, 内容={str(msg[1])[:500]}"
            else:
                msg_content = str(msg)[:500]
            logger.info(
                f"📊 [市场分析师] 消息[{i}] 类型={msg_type}, 内容={msg_content}"
            )
        logger.info(f"📊 [市场分析师] ========== 消息列表结束 ==========")

        chain = prompt | llm.bind_tools(tools)

        logger.info(f"📊 [市场分析师] 开始调用LLM...")
        # 修复：传递字典而不是直接传递消息列表，以便 ChatPromptTemplate 能正确处理所有变量
        result = chain.invoke({"messages": state["messages"]})
        logger.info(f"📊 [市场分析师] LLM调用完成")

        # 打印LLM响应
        logger.info(f"📊 [市场分析师] ========== LLM响应开始 ==========")
        logger.info(f"📊 [市场分析师] 响应类型: {type(result).__name__}")
        logger.info(f"📊 [市场分析师] 响应内容: {str(result.content)[:1000]}...")
        if hasattr(result, "tool_calls") and result.tool_calls:
            logger.info(f"📊 [市场分析师] 工具调用: {result.tool_calls}")
        logger.info(f"📊 [市场分析师] ========== LLM响应结束 ==========")

        # 使用统一的Google工具调用处理器
        if GoogleToolCallHandler.is_google_model(llm):
            logger.info(f"📊 [市场分析师] 检测到Google模型，使用统一工具调用处理器")

            # 创建分析提示词
            analysis_prompt_template = GoogleToolCallHandler.create_analysis_prompt(
                ticker=ticker,
                company_name=company_name,
                analyst_type="市场分析",
                specific_requirements="重点关注市场数据、价格走势、交易量变化等市场指标。",
            )

            # 处理Google模型工具调用
            report, messages = GoogleToolCallHandler.handle_google_tool_calls(
                result=result,
                llm=llm,
                tools=tools,
                state=state,
                analysis_prompt_template=analysis_prompt_template,
                analyst_name="市场分析师",
            )

            # 🔧 更新工具调用计数器
            return {
                "messages": [result],
                "market_report": report,
                "market_tool_call_count": tool_call_count + 1,
            }
        else:
            # 非Google模型的处理逻辑
            logger.info(
                f"📊 [市场分析师] 非Google模型 ({llm.__class__.__name__})，使用标准处理逻辑"
            )
            logger.info(f"📊 [市场分析师] 检查LLM返回结果...")
            logger.info(
                f"📊 [市场分析师] - 是否有tool_calls: {hasattr(result, 'tool_calls')}"
            )
            if hasattr(result, "tool_calls"):
                logger.info(
                    f"📊 [市场分析师] - tool_calls数量: {len(result.tool_calls)}"
                )
                if result.tool_calls:
                    for i, tc in enumerate(result.tool_calls):
                        logger.info(
                            f"📊 [市场分析师] - tool_call[{i}]: {tc.get('name', 'unknown')}"
                        )

            # 处理市场分析报告
            if len(result.tool_calls) == 0:
                logger.warning(
                    f"📊 [市场分析师] ⚠️ {llm.__class__.__name__} 没有调用任何工具，启动补救机制..."
                )
                logger.warning(
                    f"📊 [市场分析师] 📄 LLM原始响应内容 (前500字符): {result.content[:500] if hasattr(result, 'content') else 'No content'}"
                )

                try:
                    # 强制调用工具获取市场数据
                    logger.info(
                        f"📊 [市场分析师] 🔧 强制调用 get_stock_market_data_unified 工具获取市场数据..."
                    )
                    logger.info(f"📊 [市场分析师] 📊 尝试调用第一个工具")

                    # 尝试第一个工具（get_stock_market_data_unified）
                    tool_to_call = tools[0] if tools else None

                    if tool_to_call:
                        # 计算合理的历史日期范围（过去一年）
                        from datetime import datetime, timedelta

                        try:
                            end_date = datetime.strptime(current_date, "%Y%m%d")
                            start_date = end_date - timedelta(days=365)
                        except ValueError:
                            logger.warning(
                                f"📊 [市场分析师] ⚠️ 无法解析日期格式: {current_date}，使用默认日期范围"
                            )
                            end_date = datetime.now()
                            start_date = end_date - timedelta(days=365)

                        forced_data = tool_to_call.invoke(
                            {
                                "ticker": ticker,
                                "start_date": start_date.strftime("%Y%m%d"),
                                "end_date": end_date.strftime("%Y%m%d"),
                            }
                        )

                        logger.info(
                            f"📊 [市场分析师] 📋 强制获取返回结果长度: {len(str(forced_data)) if forced_data else 0} 字符"
                        )
                        logger.info(
                            f"📊 [市场分析师] 📄 强制获取返回结果预览 (前500字符): {str(forced_data)[:500] if forced_data else 'None'}"
                        )

                        # 类型安全的强制数据检查
                        forced_data_str = ""
                        if forced_data is not None:
                            if isinstance(forced_data, str):
                                forced_data_str = forced_data.strip()
                            else:
                                # 尝试导入 pandas 并检查是否为 DataFrame
                                try:
                                    import pandas as pd

                                    if isinstance(forced_data, pd.DataFrame):
                                        forced_data_str = str(forced_data)
                                    elif isinstance(forced_data, (dict, list)):
                                        forced_data_str = json.dumps(
                                            forced_data, ensure_ascii=False, indent=2
                                        )
                                    else:
                                        forced_data_str = str(forced_data)
                                except ImportError:
                                    # pandas 不可用时，直接转换为字符串
                                    if isinstance(forced_data, (dict, list)):
                                        forced_data_str = json.dumps(
                                            forced_data, ensure_ascii=False, indent=2
                                        )
                                    else:
                                        forced_data_str = str(forced_data)

                        if forced_data_str and len(forced_data_str) > 100:
                            logger.info(
                                f"📊 [市场分析师] ✅ 强制获取市场数据成功: {len(forced_data_str)} 字符"
                            )

                        # ========== 数据验证开始 ==========
                        try:
                            from tradingagents.utils.validation import (
                                validate_market_data,
                            )
                            import json

                            market_data = {}
                            if isinstance(forced_data, dict):
                                market_data = forced_data
                            elif isinstance(forced_data, str):
                                try:
                                    market_data = json.loads(forced_data)
                                except:
                                    pass

                            if market_data:
                                validation_report = validate_market_data(market_data)

                                if validation_report.get("alerts"):
                                    logger.warning(
                                        f"[数据验证] 发现关键告警: {validation_report['alerts']}"
                                    )

                                if validation_report.get("issues"):
                                    logger.error(
                                        f"[数据验证] 数据质量问题: {validation_report['issues']}"
                                    )

                                if validation_report["overall_status"] == "pass":
                                    logger.info(f"[数据验证] 数据验证通过")
                                else:
                                    logger.warning(
                                        f"[数据验证] 数据状态: {validation_report['overall_status']}"
                                    )

                        except Exception as e:
                            logger.debug(f"[数据验证] 验证过程跳过: {e}")
                            # ========== 数据验证结束 ==========

                            # 基于真实数据重新生成分析
                            forced_prompt = f"""
你是一位专业的股票技术分析师。请基于以下最新获取的市场数据，对股票 {ticker}（{company_name}）进行详细的技术分析：

=== 最新市场数据 ===
{forced_data_str}

=== 分析要求 ===
🚨 CRITICAL REQUIREMENT - 绝对强制要求：
❌ 严格禁止行为：
- 绝对禁止在没有调用工具的情况下直接回答
- 绝对禁止编造任何技术指标数据（MA、MACD、RSI、布林带等）
- 绝对禁止编造价格、成交量等市场数据
- ⚠️ A股成交量单位特别说明：必须明确区分'股'和'手'，避免数量级错误
- 绝对禁止基于推测、假设或常识生成分析内容
- 绝对禁止说'我无法获取数据'、'需要更多信息'等借口

✅ 强制执行步骤：
1. 你必须基于上述真实数据进行分析
2. 所有技术指标数值必须使用工具返回的实际数据
3. 如果工具数据不完整，必须明确说明
4. 不允许编造任何数值或信息

⚠️ 违规后果：
- 基于编造数据的分析将被拒绝
- 必须使用工具返回的真实数据
- 没有例外，没有借口

输出格式要求：
## {company_name}（{ticker}）技术分析报告

### 一、股票基本信息
- **公司名称**：{company_name}
- **股票代码**：{ticker}
- **所属市场**：{market_info["market_name"]}

### 二、技术指标分析（必须使用工具返回的数据）
#### 1. 移动平均线（MA）
[从工具数据中提取并分析MA5、MA10、MA20、MA60，包括：
- 当前各均线数值
- 均线排列形态（多头/空头）
- 价格与均线的位置关系
- 均线交叉信号]

#### 2. MACD指标
[从工具数据中提取并分析MACD，包括：
- DIF、DEA、MACD柱状图当前数值
- 金叉/死叉信号
- 背离现象]

#### 3. RSI相对强弱指标
[从工具数据中提取并分析RSI，包括：
- RSI当前数值
- ⚠️ 重要：如果RSI6连续3天≥80，必须明确标注极端超买信号，这是3年罕见的风险信号
- 超买/超卖区域判断（70以上为超买，30以下为超卖）
- 背离信号]

#### 4. 布林带（BOLL）
[从工具数据中提取并分析布林带，包括：
- 上轨、中轨、下轨数值
- 价格在布林带中的位置
- 带宽变化趋势
- 突破信号]

### 三、价格趋势分析
#### 1. 短期趋势（5-10个交易日）
[分析短期价格走势，包括支撑位、压力位、关键价格区间]

#### 2. 中期趋势（20-60个交易日）
[分析中期价格走势，结合均线系统判断趋势方向]

#### 3. 成交量分析
[分析成交量变化，量价配合情况]

### 四、投资建议
#### 1. 综合评估
[基于上述技术指标，给出综合评估]

#### 2. 操作建议
- **投资评级**：买入/持有/卖出
- **目标价位**：[给出具体价格区间] {market_info["currency_symbol"]}
- **止损位**：[给出止损价格] {market_info["currency_symbol"]}
- **风险提示**：[列出主要风险因素]

⚠️ 重要提醒：
- 所有技术指标必须使用工具返回的真实数据
- 不允许编造任何数值
- 如果工具数据不完整，必须明确说明
- 使用中文撰写报告
- 使用 {market_info["currency_name"]}（{market_info["currency_symbol"]}）表示价格
"""

                            logger.info(
                                f"📊 [市场分析师] 🔄 基于强制获取的市场数据重新生成完整分析..."
                            )
                            logger.info(
                                f"📊 [市场分析师] 📝 强制提示词长度: {len(forced_prompt)} 字符"
                            )

                            forced_result = llm.invoke(
                                [{"role": "user", "content": forced_prompt}]
                            )

                            if (
                                hasattr(forced_result, "content")
                                and forced_result.content
                            ):
                                report = forced_result.content
                                logger.info(
                                    f"📊 [市场分析师] ✅ 强制补救成功，生成基于真实数据的报告，长度: {len(report)} 字符"
                                )
                                logger.info(
                                    f"📊 [市场分析师] 📄 报告预览 (前300字符): {report[:300]}"
                                )
                            else:
                                logger.warning(
                                    f"📊 [市场分析师] ⚠️ 强制补救LLM返回为空，使用原始结果"
                                )
                                report = (
                                    result.content if hasattr(result, "content") else ""
                                )
                        else:
                            logger.warning(
                                f"📊 [市场分析师] ⚠️ 工具获取失败或内容过短（{len(forced_data_str) if forced_data_str else 0}字符），使用原始结果"
                            )
                            if forced_data_str:
                                logger.warning(
                                    f"📊 [市场分析师] 📄 失败的市场内容: {forced_data_str[:500]}"
                                )
                            report = (
                                result.content if hasattr(result, "content") else ""
                            )
                    else:
                        logger.error(f"📊 [市场分析师] ❌ 没有可用的工具，强制补救失败")
                        report = result.content if hasattr(result, "content") else ""

                except Exception as e:
                    logger.error(f"📊 [市场分析师] ❌ 强制补救过程失败: {e}")
                    import traceback

                    logger.error(
                        f"📊 [市场分析师] 📋 异常堆栈: {traceback.format_exc()}"
                    )
                    report = result.content if hasattr(result, "content") else ""
            else:
                # 有工具调用，执行工具并生成完整分析报告
                logger.info(
                    f"📊 [市场分析师] 🔧 检测到工具调用: {[call.get('name', 'unknown') for call in result.tool_calls]}"
                )

                try:
                    # 执行工具调用
                    from langchain_core.messages import ToolMessage, HumanMessage

                    tool_messages = []
                    for tool_call in result.tool_calls:
                        tool_name = tool_call.get("name")
                        tool_args = tool_call.get("args", {})
                        tool_id = tool_call.get("id")

                        logger.debug(
                            f"📊 [DEBUG] 执行工具: {tool_name}, 参数: {tool_args}"
                        )

                        # 找到对应的工具并执行
                        tool_result = None
                        for tool in tools:
                            # 安全地获取工具名称进行比较
                            current_tool_name = None
                            if hasattr(tool, "name"):
                                current_tool_name = tool.name
                            elif hasattr(tool, "__name__"):
                                current_tool_name = tool.__name__

                            if current_tool_name == tool_name:
                                try:
                                    if tool_name == "get_china_stock_data":
                                        # 中国股票数据工具
                                        tool_result = tool.invoke(tool_args)
                                    else:
                                        # 其他工具
                                        tool_result = tool.invoke(tool_args)
                                    logger.debug(
                                        f"📊 [DEBUG] 工具执行成功，结果长度: {len(str(tool_result))}"
                                    )
                                    break
                                except Exception as tool_error:
                                    logger.error(
                                        f"❌ [DEBUG] 工具执行失败: {tool_error}"
                                    )
                                    tool_result = f"工具执行失败: {str(tool_error)}"

                        if tool_result is None:
                            tool_result = f"未找到工具: {tool_name}"

                        # 创建工具消息
                        tool_message = ToolMessage(
                            content=str(tool_result), tool_call_id=tool_id
                        )
                        tool_messages.append(tool_message)

                    # 基于工具结果生成完整分析报告
                    # 🔥 重要：这里必须包含公司名称和输出格式要求，确保LLM生成正确的报告标题
                    analysis_prompt = f"""现在请基于上述工具获取的数据，生成详细的技术分析报告。

**分析对象：**
- 公司名称：{company_name}
- 股票代码：{ticker}
- 所属市场：{market_info["market_name"]}
- 计价货币：{market_info["currency_name"]}（{market_info["currency_symbol"]}）

**输出格式要求（必须严格遵守）：**

请按照以下专业格式输出报告，不要使用emoji符号（如📊📈📉💭等），使用纯文本标题：

# **{company_name}（{ticker}）技术分析报告**
**分析日期：[当前日期]**

---

## 一、股票基本信息

- **公司名称**：{company_name}
- **股票代码**：{ticker}
- **所属市场**：{market_info["market_name"]}
- **当前价格**：[从工具数据中获取] {market_info["currency_symbol"]}
- **涨跌幅**：[从工具数据中获取]
- **成交量**：[从工具数据中获取]（⚠️必须注明单位：股/手/万股/万手）

---

## 二、技术指标分析

### 1. 移动平均线（MA）分析

[分析MA5、MA10、MA20、MA60等均线系统，包括：]
- 当前各均线数值
- 均线排列形态（多头/空头）
- 价格与均线的位置关系
- 均线交叉信号

### 2. MACD指标分析

[分析MACD指标，包括：]
- DIF、DEA、MACD柱状图当前数值
- 金叉/死叉信号
- 背离现象
- 趋势强度判断

### 3. RSI相对强弱指标

[分析RSI指标，包括：]
- RSI当前数值
- 超买/超卖区域判断
- 背离信号
- 趋势确认

### 4. 布林带（BOLL）分析

[分析布林带指标，包括：]
- 上轨、中轨、下轨数值
- 价格在布林带中的位置
- 带宽变化趋势
- 突破信号

---

## 三、价格趋势分析

### 1. 短期趋势（5-10个交易日）

[分析短期价格走势，包括支撑位、压力位、关键价格区间]

### 2. 中期趋势（20-60个交易日）

[分析中期价格走势，结合均线系统判断趋势方向]

### 3. 成交量分析

[分析成交量变化，量价配合情况。⚠️注意：如果是A股，请确认成交量单位是'手'还是'股'，避免数量级错误]

---

## 四、投资建议

### 1. 综合评估

[基于上述技术指标，给出综合评估]

### 2. 操作建议

- **投资评级**：买入/持有/卖出
- **目标价位**：[给出具体价格区间] {market_info["currency_symbol"]}
- **止损位**：[给出止损价格] {market_info["currency_symbol"]}
- **风险提示**：[列出主要风险因素]

### 3. 关键价格区间

- **支撑位**：[具体价格]
- **压力位**：[具体价格]
- **突破买入价**：[具体价格]
- **跌破卖出价**：[具体价格]

---

**重要提醒：**
- 必须严格按照上述格式输出，使用标准的Markdown标题（#、##、###）
- 不要使用emoji符号（📊📈📉💭等）
- 所有价格数据使用{market_info["currency_name"]}（{market_info["currency_symbol"]}）表示
- 确保在分析中正确使用公司名称"{company_name}"和股票代码"{ticker}"
- 报告标题必须是：# **{company_name}（{ticker}）技术分析报告**
- 报告必须基于工具返回的真实数据进行分析
- 包含具体的技术指标数值和专业分析
- 提供明确的投资建议和风险提示
- 报告长度不少于800字
- 使用中文撰写
- 使用表格展示数据时，确保格式规范"""

                    # 构建完整的消息序列
                    messages = (
                        state["messages"]
                        + [result]
                        + tool_messages
                        + [HumanMessage(content=analysis_prompt)]
                    )

                    # 生成最终分析报告
                    final_result = llm.invoke(messages)
                    report = final_result.content

                    logger.info(
                        f"📊 [市场分析师] 生成完整分析报告，长度: {len(report)}"
                    )

                    # 返回包含工具调用和最终分析的完整消息序列
                    # 🔧 更新工具调用计数器
                    return {
                        "messages": [result] + tool_messages + [final_result],
                        "market_report": report,
                        "market_tool_call_count": tool_call_count + 1,
                    }

                except Exception as e:
                    logger.error(f"❌ [市场分析师] 工具执行或分析生成失败: {e}")
                    logger.error(
                        f"📊 [市场分析师] 📋 异常堆栈: {traceback.format_exc()}"
                    )

                    # 降级处理：返回工具调用信息
                    report = f"市场分析师调用了工具但分析生成失败: {[call.get('name', 'unknown') for call in result.tool_calls]}"

                    # 🔧 更新工具调用计数器
                    return {
                        "messages": [result],
                        "market_report": report,
                        "market_tool_call_count": tool_call_count + 1,
                    }

            # 🔧 更新工具调用计数器
            return {
                "messages": [result],
                "market_report": report,
                "market_tool_call_count": tool_call_count + 1,
            }

    return market_analyst_node
