# -*- coding: utf-8 -*-
"""
基本面分析师 - 统一工具架构版本
使用统一工具自动识别股票类型并调用相应数据源

重构说明：
- 将原始的单一巨型函数拆分为多个职责单一的小函数
- 提取重复代码到辅助函数
- 改善代码结构和可读性
- 保持所有现有功能不变
"""

from datetime import datetime, timedelta
from typing import Any

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, ToolMessage

from tradingagents.utils.tool_logging import log_analyst_module
from tradingagents.utils.logging_init import get_logger
from tradingagents.agents.utils.google_tool_handler import GoogleToolCallHandler
# 导入统一公司名称工具（替换原有的重复代码）
from tradingagents.utils.company_name_utils import get_company_name

logger = get_logger("default")


# =============================================================================
# 辅助函数
# =============================================================================

def _get_tool_names(tools: list) -> list[str]:
    """
    从工具列表中安全地获取工具名称

    Args:
        tools: 工具列表

    Returns:
        工具名称列表
    """
    tool_names = []
    for tool in tools:
        if hasattr(tool, 'name'):
            tool_names.append(tool.name)
        elif hasattr(tool, '__name__'):
            tool_names.append(tool.__name__)
        else:
            tool_names.append(str(tool))
    return tool_names


def _calculate_date_range(current_date: str, days: int = 10) -> tuple[str, str]:
    """
    计算分析的日期范围

    基本面分析主要依赖财务数据（PE、PB、ROE等），只需要当前股价。
    获取指定天数的数据是为了保证能拿到数据（处理周末/节假日/数据延迟），
    但实际分析只使用最近几天的数据。

    Args:
        current_date: 当前日期，格式 YYYY-MM-DD
        days: 向前获取的天数，默认10天

    Returns:
        (start_date, end_date) 元组
    """
    try:
        end_date_dt = datetime.strptime(current_date, "%Y-%m-%d")
        start_date_dt = end_date_dt - timedelta(days=days)
        start_date = start_date_dt.strftime("%Y-%m-%d")
        logger.info(f"[基本面分析师] 数据范围: {start_date} 至 {current_date} (固定{days}天)")
        return start_date, current_date
    except Exception as e:
        logger.warning(f"[基本面分析师] 日期解析失败，使用默认范围: {e}")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return start_date, current_date


def _count_tool_messages(messages: list) -> int:
    """
    统计消息历史中的工具消息数量

    Args:
        messages: 消息列表

    Returns:
        ToolMessage 的数量
    """
    return sum(1 for msg in messages if isinstance(msg, ToolMessage))


def _has_tool_result(messages: list) -> bool:
    """
    检查消息历史中是否已有工具返回结果

    Args:
        messages: 消息列表

    Returns:
        是否存在 ToolMessage
    """
    return any(isinstance(msg, ToolMessage) for msg in messages)


def _has_valid_analysis_content(result: Any, min_length: int = 500) -> bool:
    """
    检查LLM返回是否包含有效的分析内容

    Args:
        result: LLM返回结果
        min_length: 最小内容长度阈值

    Returns:
        是否包含有效分析内容
    """
    if not hasattr(result, 'content') or not result.content:
        return False
    content_length = len(str(result.content))
    return content_length > min_length


# =============================================================================
# 提示词构建函数
# =============================================================================

def _build_system_message(
    ticker: str,
    company_name: str,
    market_info: dict,
    start_date: str,
    current_date: str
) -> str:
    """
    构建系统提示词

    Args:
        ticker: 股票代码
        company_name: 公司名称
        market_info: 市场信息
        start_date: 开始日期
        current_date: 当前日期

    Returns:
        系统提示词字符串
    """
    return (
        f"你是一位专业的股票基本面分析师。"
        f"任务：分析{company_name}（股票代码：{ticker}，{market_info['market_name']}）"
        f"立即调用 get_stock_fundamentals_unified 工具"
        f"参数：ticker='{ticker}', start_date='{start_date}', end_date='{current_date}', curr_date='{current_date}'"
        "分析要求："
        "- 基于真实数据进行深度基本面分析"
        f"- 计算并提供合理价位区间（使用{market_info['currency_name']}{market_info['currency_symbol']}）"
        "- 分析当前股价是否被低估或高估"
        "- 提供基于基本面的目标价位建议"
        "- 包含PE、PB、PEG等估值指标分析"
        "- 结合市场特点进行分析"
        "语言和货币要求："
        "- 所有分析内容必须使用中文"
        "- 投资建议必须使用中文：买入、持有、卖出"
        "- 绝对不允许使用英文：buy、hold、sell"
        f"- 货币单位使用：{market_info['currency_name']}（{market_info['currency_symbol']}）"
        "严格禁止："
        "- 不允许说'我将调用工具'"
        "- 不允许假设任何数据"
        "- 不允许编造公司信息"
        "- 不允许直接回答而不调用工具"
        "- 不允许回复'无法确定价位'或'需要更多信息'"
        "- 不允许使用英文投资建议（buy/hold/sell）"
        "你必须："
        "- 立即调用统一基本面分析工具"
        "- 等待工具返回真实数据"
        "- 基于真实数据进行分析"
        "- 提供具体的价位区间和目标价"
        "- 使用中文投资建议（买入/持有/卖出）"
        "现在立即开始调用工具！不要说任何其他话！"
    )


def _build_system_prompt_template() -> str:
    """
    构建系统提示模板

    Returns:
        系统提示模板字符串
    """
    return (
        "强制要求：你必须调用工具获取真实数据！"
        "绝对禁止：不允许假设、编造或直接回答任何问题！"
        "工作流程："
        "1. 【第一次调用】如果消息历史中没有工具结果（ToolMessage），立即调用 get_stock_fundamentals_unified 工具"
        "2. 【收到数据后】如果消息历史中已经有工具结果（ToolMessage），绝对禁止再次调用工具！"
        "3. 【生成报告】收到工具数据后，必须立即生成完整的基本面分析报告，包含："
        "   - 公司基本信息和财务数据分析"
        "   - PE、PB、PEG等估值指标分析"
        "   - 当前股价是否被低估或高估的判断"
        "   - 合理价位区间和目标价位建议"
        "   - 基于基本面的投资建议（买入/持有/卖出）"
        "4. 重要：工具只需调用一次！一次调用返回所有需要的数据！不要重复调用！"
        "5. 如果你已经看到ToolMessage，说明工具已经返回数据，直接生成报告，不要再调用工具！"
        "可用工具：{tool_names}。\n{system_message}"
        "当前日期：{current_date}。"
        "分析目标：{company_name}（股票代码：{ticker}）。"
        "请确保在分析中正确区分公司名称和股票代码。"
    )


def _build_force_report_prompt(ticker: str, company_name: str) -> str:
    """
    构建强制生成报告的提示词（当LLM已有工具结果但仍尝试调用工具时使用）

    Args:
        ticker: 股票代码
        company_name: 公司名称

    Returns:
        强制生成报告的提示词
    """
    return (
        f"你是专业的股票基本面分析师。"
        f"你已经收到了股票 {company_name}（代码：{ticker}）的基本面数据。"
        f"现在你必须基于这些数据生成完整的基本面分析报告！\n\n"
        f"报告必须包含以下内容：\n"
        f"1. 公司基本信息和财务数据分析\n"
        f"2. PE、PB、PEG等估值指标分析\n"
        f"3. 当前股价是否被低估或高估的判断\n"
        f"4. 合理价位区间和目标价位建议\n"
        f"5. 基于基本面的投资建议（买入/持有/卖出）\n\n"
        f"要求：\n"
        f"- 使用中文撰写报告\n"
        f"- 基于消息历史中的真实数据进行分析\n"
        f"- 分析要详细且专业\n"
        f"- 投资建议必须明确（买入/持有/卖出）"
    )


def _build_analysis_prompt(
    ticker: str,
    company_name: str,
    combined_data: str,
    market_info: dict
) -> str:
    """
    构建基于数据的分析提示词

    Args:
        ticker: 股票代码
        company_name: 公司名称
        combined_data: 工具返回的数据
        market_info: 市场信息

    Returns:
        分析提示词
    """
    currency_info = f"{market_info['currency_name']}（{market_info['currency_symbol']}）"

    return f"""基于以下真实数据，对{company_name}（股票代码：{ticker}）进行详细的基本面分析：

{combined_data}

请提供：
1. 公司基本信息分析（{company_name}，股票代码：{ticker}）
2. 财务状况评估
3. 盈利能力分析
4. 估值分析（使用{currency_info}）
5. 投资建议（买入/持有/卖出）

要求：
- 基于提供的真实数据进行分析
- 正确使用公司名称"{company_name}"和股票代码"{ticker}"
- 价格使用{currency_info}
- 投资建议使用中文
- 分析要详细且专业"""


# =============================================================================
# 日志函数
# =============================================================================

def _log_llm_input(
    system_message: str,
    tool_names: list[str],
    current_date: str,
    ticker: str,
    company_name: str,
    messages: list,
    tools: list
) -> None:
    """
    打印提交给LLM的完整输入内容（调试用）

    Args:
        system_message: 系统提示词
        tool_names: 工具名称列表
        current_date: 当前日期
        ticker: 股票代码
        company_name: 公司名称
        messages: 消息历史
        tools: 工具列表
    """
    logger.info("=" * 80)
    logger.info("[提示词调试] 开始打印提交给大模型的完整内容")
    logger.info("=" * 80)

    # 1. 系统提示词
    logger.info("[提示词调试] 1 系统提示词 (System Message):")
    logger.info("-" * 80)
    logger.info(system_message)
    logger.info("-" * 80)

    # 2. 完整的提示模板
    logger.info("[提示词调试] 2 完整提示模板 (Prompt Template):")
    logger.info("-" * 80)
    logger.info(f"工具名称: {', '.join(tool_names)}")
    logger.info(f"当前日期: {current_date}")
    logger.info(f"股票代码: {ticker}")
    logger.info(f"公司名称: {company_name}")
    logger.info("-" * 80)

    # 3. 消息历史
    logger.info("[提示词调试] 3 消息历史 (Message History):")
    logger.info("-" * 80)
    for i, msg in enumerate(messages):
        msg_type = type(msg).__name__
        if hasattr(msg, 'content'):
            content_full = str(msg.content)
            logger.info(f"消息 {i+1} [{msg_type}]:")
            logger.info(f"  内容长度: {len(content_full)} 字符")
            logger.info(f"  内容: {content_full}")
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            logger.info(f"  工具调用: {[tc.get('name', 'unknown') for tc in msg.tool_calls]}")
        if hasattr(msg, 'name'):
            logger.info(f"  工具名称: {msg.name}")
        logger.info("-" * 40)
    logger.info("-" * 80)

    # 4. 绑定的工具信息
    logger.info("[提示词调试] 4 绑定的工具 (Bound Tools):")
    logger.info("-" * 80)
    for i, tool in enumerate(tools):
        tool_name = getattr(tool, 'name', None) or getattr(tool, '__name__', 'unknown')
        tool_desc = getattr(tool, 'description', 'No description')
        logger.info(f"工具 {i+1}: {tool_name}")
        logger.info(f"  描述: {tool_desc}")
        if hasattr(tool, 'args_schema'):
            logger.info(f"  参数: {tool.args_schema}")
        logger.info("-" * 40)
    logger.info("-" * 80)

    logger.info("=" * 80)
    logger.info("[提示词调试] 完整内容打印结束，开始调用LLM")
    logger.info("=" * 80)


def _log_llm_result(result: Any, analyst_name: str = "基本面分析师") -> None:
    """
    打印LLM返回结果的详细信息

    Args:
        result: LLM返回结果
        analyst_name: 分析师名称（用于日志标识）
    """
    logger.info(f"[{analyst_name}] ===== LLM返回结果分析 =====")
    logger.info(f"[{analyst_name}] - 结果类型: {type(result).__name__}")
    logger.info(f"[{analyst_name}] - 是否有tool_calls属性: {hasattr(result, 'tool_calls')}")

    if hasattr(result, 'content'):
        content_preview = str(result.content)[:200] if result.content else "None"
        logger.info(f"[{analyst_name}] - 内容长度: {len(str(result.content)) if result.content else 0}")
        logger.info(f"[{analyst_name}] - 内容预览: {content_preview}...")
        if result.content:
            logger.info(f"[{analyst_name}] - 完整内容:")
            logger.info(f"{result.content}")

    if hasattr(result, 'tool_calls'):
        logger.info(f"[{analyst_name}] - tool_calls数量: {len(result.tool_calls)}")
        if result.tool_calls:
            logger.info(f"[{analyst_name}] 检测到 {len(result.tool_calls)} 个工具调用:")
            for i, tc in enumerate(result.tool_calls):
                logger.info(f"[{analyst_name}] - 工具调用 {i+1}: {tc.get('name', 'unknown')} (ID: {tc.get('id', 'unknown')})")
                if 'args' in tc:
                    logger.info(f"[{analyst_name}] - 参数: {tc['args']}")
        else:
            logger.info(f"[{analyst_name}] tool_calls为空列表")
    else:
        logger.info(f"[{analyst_name}] 无tool_calls属性")

    logger.info(f"[{analyst_name}] ===== LLM返回结果分析结束 =====")


def _log_message_history_summary(messages: list) -> None:
    """
    打印消息历史摘要信息

    Args:
        messages: 消息列表
    """
    ai_message_count = sum(1 for msg in messages if isinstance(msg, AIMessage))
    tool_message_count = sum(1 for msg in messages if isinstance(msg, ToolMessage))

    logger.info(f"[消息历史] 当前消息总数: {len(messages)}")
    logger.info(f"[消息历史] AIMessage数量: {ai_message_count}, ToolMessage数量: {tool_message_count}")

    recent_messages = messages[-5:] if len(messages) >= 5 else messages
    logger.info(f"[消息历史] 最近{len(recent_messages)}条消息类型: {[type(msg).__name__ for msg in recent_messages]}")


def _log_stock_code_trace(ticker: str) -> None:
    """记录股票代码追踪日志"""
    logger.info(f"[股票代码追踪] 基本面分析师接收到的原始股票代码: '{ticker}' (类型: {type(ticker)})")
    logger.info(f"[股票代码追踪] 股票代码长度: {len(str(ticker))}")
    logger.info(f"[股票代码追踪] 股票代码字符: {list(str(ticker))}")


def _log_market_info(ticker: str, market_info: dict, toolkit) -> None:
    """记录市场信息日志"""
    logger.info(f"[股票代码追踪] StockUtils.get_market_info 返回的市场信息: {market_info}")
    logger.debug(f"[基本面分析师] 股票类型检查: {ticker} -> {market_info['market_name']} ({market_info['currency_name']})")
    logger.debug(f"[基本面分析师] 详细市场信息: is_china={market_info['is_china']}, is_hk={market_info['is_hk']}, is_us={market_info['is_us']}")
    logger.debug(f"[基本面分析师] 工具配置检查: online_tools={toolkit.config['online_tools']}")


# =============================================================================
# LLM处理函数
# =============================================================================

def _create_fresh_llm(llm: Any) -> Any:
    """
    为阿里百炼模型创建新实例以避免工具缓存问题

    Args:
        llm: 原始LLM实例

    Returns:
        新的LLM实例（阿里百炼模型）或原始实例（其他模型）
    """
    if not (hasattr(llm, '__class__') and 'DashScope' in llm.__class__.__name__):
        return llm

    logger.debug("[基本面分析师] 检测到阿里百炼模型，创建新实例以避免工具缓存")
    from tradingagents.llm_adapters import ChatDashScopeOpenAI

    original_base_url = getattr(llm, 'openai_api_base', None)
    original_api_key = getattr(llm, 'openai_api_key', None)

    fresh_llm = ChatDashScopeOpenAI(
        model=llm.model_name,
        api_key=original_api_key,
        base_url=original_base_url if original_base_url else None,
        temperature=llm.temperature,
        max_tokens=getattr(llm, 'max_tokens', 2000)
    )

    if original_base_url:
        logger.debug(f"[基本面分析师] 新实例使用原始 base_url: {original_base_url}")
    if original_api_key:
        logger.debug("[基本面分析师] 新实例使用原始 API Key（来自数据库配置）")

    return fresh_llm


def _create_prompt_template(
    system_message: str,
    tool_names: list[str],
    current_date: str,
    ticker: str,
    company_name: str
) -> ChatPromptTemplate:
    """
    创建提示模板

    Args:
        system_message: 系统提示词
        tool_names: 工具名称列表
        current_date: 当前日期
        ticker: 股票代码
        company_name: 公司名称

    Returns:
        配置好的提示模板
    """
    system_prompt = _build_system_prompt_template()

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
    ])

    prompt = prompt.partial(system_message=system_message)
    prompt = prompt.partial(tool_names=", ".join(tool_names))
    prompt = prompt.partial(current_date=current_date)
    prompt = prompt.partial(ticker=ticker)
    prompt = prompt.partial(company_name=company_name)

    return prompt


# =============================================================================
# 核心处理逻辑函数
# =============================================================================

def _force_tool_invocation(
    tools: list,
    ticker: str,
    start_date: str,
    current_date: str
) -> str:
    """
    强制调用工具获取数据

    Args:
        tools: 工具列表
        ticker: 股票代码
        start_date: 开始日期
        current_date: 当前日期

    Returns:
        工具返回的数据字符串
    """
    logger.debug("[基本面分析师] 强制调用 get_stock_fundamentals_unified...")

    # 查找统一基本面分析工具
    unified_tool = None
    for tool in tools:
        tool_name = getattr(tool, 'name', None) or getattr(tool, '__name__', None)
        if tool_name == 'get_stock_fundamentals_unified':
            unified_tool = tool
            break

    if not unified_tool:
        logger.debug("[基本面分析师] 统一工具未找到")
        return "统一基本面分析工具不可用"

    try:
        logger.info("[工具调用] 找到统一工具，准备强制调用")
        logger.info(f"[工具调用] 传入参数 - ticker: '{ticker}', start_date: {start_date}, end_date: {current_date}")

        combined_data = unified_tool.invoke({
            'ticker': ticker,
            'start_date': start_date,
            'end_date': current_date,
            'curr_date': current_date
        })

        logger.info("[工具调用] 统一工具调用成功")
        logger.info(f"[工具调用] 返回数据长度: {len(combined_data)}字符")

        # 记录返回数据预览
        _log_tool_data_preview(combined_data)

        return combined_data

    except Exception as e:
        logger.error(f"[基本面分析师] 统一工具调用异常: {e}")
        return f"统一基本面分析工具调用失败: {e}"


def _log_tool_data_preview(combined_data: Any) -> None:
    """
    记录工具返回数据的预览信息

    Args:
        combined_data: 工具返回的数据
    """
    try:
        if isinstance(combined_data, (dict, list)):
            import json
            preview = json.dumps(combined_data, ensure_ascii=False, default=str)
        else:
            preview = str(combined_data)

        preview_truncated = preview[:6000] + ("..." if len(preview) > 6000 else "")
        logger.info(f"[基本面分析师] 统一工具返回数据预览(前6000字符):\n{preview_truncated}")
        logger.debug(f"[基本面分析师] 统一工具返回完整数据:\n{preview}")

    except Exception as log_err:
        logger.warning(f"[基本面分析师] 记录统一工具数据时出错: {log_err}")


def _generate_analysis_report(
    fresh_llm: Any,
    ticker: str,
    company_name: str,
    combined_data: str,
    market_info: dict
) -> str:
    """
    生成基于数据的分析报告

    Args:
        fresh_llm: LLM实例
        ticker: 股票代码
        company_name: 公司名称
        combined_data: 工具返回的数据
        market_info: 市场信息

    Returns:
        分析报告字符串
    """
    analysis_prompt = _build_analysis_prompt(ticker, company_name, combined_data, market_info)

    try:
        analysis_prompt_template = ChatPromptTemplate.from_messages([
            ("system", "你是专业的股票基本面分析师，基于提供的真实数据进行分析。"),
            ("human", "{analysis_request}")
        ])

        analysis_chain = analysis_prompt_template | fresh_llm
        analysis_result = analysis_chain.invoke({"analysis_request": analysis_prompt})

        if hasattr(analysis_result, 'content'):
            report = analysis_result.content
        else:
            report = str(analysis_result)

        logger.info(f"[基本面分析师] 强制工具调用完成，报告长度: {len(report)}")
        return report

    except Exception as e:
        logger.error(f"[基本面分析师] 强制工具调用分析失败: {e}")
        return f"基本面分析失败：{str(e)}"


def _handle_tool_calls_present(
    result: Any,
    state: dict,
    fresh_llm: Any,
    ticker: str,
    company_name: str,
    tool_call_count: int,
    max_tool_calls: int
) -> dict:
    """
    处理LLM返回包含工具调用的情况

    Args:
        result: LLM返回结果
        state: 当前状态
        fresh_llm: LLM实例
        ticker: 股票代码
        company_name: 公司名称
        tool_call_count: 当前工具调用计数
        max_tool_calls: 最大工具调用次数

    Returns:
        更新后的状态字典
    """
    messages = state.get("messages", [])
    has_tool = _has_tool_result(messages)

    if has_tool:
        # 已有工具结果，强制生成报告
        logger.warning("[强制生成报告] 工具已返回数据，但LLM仍尝试调用工具，强制基于现有数据生成报告")
        return _force_generate_report(fresh_llm, messages, ticker, company_name, tool_call_count)

    if tool_call_count >= max_tool_calls:
        # 达到最大调用次数但没有工具结果
        logger.warning(f"[异常情况] 达到最大工具调用次数 {max_tool_calls}，但没有工具结果")
        fallback_report = f"基本面分析（股票代码：{ticker}）\n\n由于达到最大工具调用次数限制，使用简化分析模式。建议检查数据源连接或降低分析复杂度。"
        return {
            "messages": [result],
            "fundamentals_report": fallback_report,
            "fundamentals_tool_call_count": tool_call_count
        }

    # 第一次调用工具，正常流程
    logger.info("[正常流程] ===== LLM第一次调用工具 =====")
    tool_calls_info = [tc['name'] for tc in result.tool_calls]
    logger.info(f"[正常流程] LLM请求调用工具: {tool_calls_info}")
    logger.info(f"[正常流程] 工具调用数量: {len(tool_calls_info)}")
    logger.info("[正常流程] 返回状态，等待工具执行")

    return {"messages": [result]}


def _force_generate_report(
    fresh_llm: Any,
    messages: list,
    ticker: str,
    company_name: str,
    tool_call_count: int
) -> dict:
    """
    强制生成报告（当已有工具结果但LLM仍尝试调用工具时）

    Args:
        fresh_llm: LLM实例
        messages: 消息历史
        ticker: 股票代码
        company_name: 公司名称
        tool_call_count: 工具调用计数

    Returns:
        包含报告的状态字典
    """
    force_system_prompt = _build_force_report_prompt(ticker, company_name)

    force_prompt = ChatPromptTemplate.from_messages([
        ("system", force_system_prompt),
        MessagesPlaceholder(variable_name="messages"),
    ])

    force_chain = force_prompt | fresh_llm

    logger.info("[强制生成报告] 使用专门的提示词重新调用LLM...")
    force_result = force_chain.invoke({"messages": messages})

    report = str(force_result.content) if hasattr(force_result, 'content') else "基本面分析完成"
    logger.info(f"[强制生成报告] 成功生成报告，长度: {len(report)}字符")

    return {
        "fundamentals_report": report,
        "messages": [force_result],
        "fundamentals_tool_call_count": tool_call_count
    }


def _handle_no_tool_calls(
    result: Any,
    state: dict,
    fresh_llm: Any,
    tools: list,
    ticker: str,
    company_name: str,
    start_date: str,
    current_date: str,
    market_info: dict,
    tool_call_count: int
) -> dict:
    """
    处理LLM未返回工具调用的情况

    Args:
        result: LLM返回结果
        state: 当前状态
        fresh_llm: LLM实例
        tools: 工具列表
        ticker: 股票代码
        company_name: 公司名称
        start_date: 开始日期
        current_date: 当前日期
        market_info: 市场信息
        tool_call_count: 工具调用计数

    Returns:
        更新后的状态字典
    """
    logger.info("[基本面分析师] ===== 强制工具调用检查开始 =====")

    messages = state.get("messages", [])
    _log_message_history_summary(messages)

    has_tool = _has_tool_result(messages)
    has_analysis = _has_valid_analysis_content(result)

    # 记录内容检查详情
    if hasattr(result, 'content') and result.content:
        content_length = len(str(result.content))
        logger.info(f"[内容检查] LLM返回内容长度: {content_length}字符")
        if has_analysis:
            logger.info(f"[内容检查] LLM已返回分析内容 (长度: {content_length}字符 > 500字符阈值)")
        else:
            logger.info(f"[内容检查] LLM返回内容较短 (长度: {content_length}字符 < 500字符阈值)")
    else:
        logger.info("[内容检查] LLM未返回内容或内容为空")

    logger.info(f"[检查结果] 是否有工具返回结果: {has_tool}")
    logger.info(f"[统计] 历史工具调用次数: {tool_call_count}")
    logger.info(f"[重复调用检查] 汇总 - 工具结果数: {tool_call_count}, 已有工具结果: {has_tool}, 已有分析内容: {has_analysis}")
    logger.info("[基本面分析师] ===== 强制工具调用检查结束 =====")

    # 关键逻辑：必须有工具结果才能跳过强制调用
    if has_tool:
        return _use_existing_analysis(result, tool_call_count)

    if has_analysis:
        logger.warning("[警告] LLM返回了分析内容但未调用工具，可能是编造数据，强制调用工具获取真实数据")

    # 执行强制工具调用
    return _execute_force_tool_call(
        fresh_llm, tools, ticker, company_name,
        start_date, current_date, market_info, tool_call_count
    )


def _use_existing_analysis(result: Any, tool_call_count: int) -> dict:
    """
    使用现有的分析结果（当已有工具结果时）

    Args:
        result: LLM返回结果
        tool_call_count: 工具调用计数

    Returns:
        包含报告的状态字典
    """
    logger.info("[决策] ===== 跳过强制工具调用 =====")
    logger.info(f"[决策原因] 检测到已有 {tool_call_count} 次工具调用结果，避免重复调用")

    report = str(result.content) if hasattr(result, 'content') else "基本面分析完成"
    logger.info(f"[返回结果] 使用LLM返回的分析内容，报告长度: {len(report)}字符")
    logger.info(f"[返回结果] 报告预览(前200字符): {report[:200]}...")
    logger.info("[决策] 基本面分析完成，跳过重复调用成功")

    return {
        "fundamentals_report": report,
        "messages": [result],
        "fundamentals_tool_call_count": tool_call_count
    }


def _execute_force_tool_call(
    fresh_llm: Any,
    tools: list,
    ticker: str,
    company_name: str,
    start_date: str,
    current_date: str,
    market_info: dict,
    tool_call_count: int
) -> dict:
    """
    执行强制工具调用并生成报告

    Args:
        fresh_llm: LLM实例
        tools: 工具列表
        ticker: 股票代码
        company_name: 公司名称
        start_date: 开始日期
        current_date: 当前日期
        market_info: 市场信息
        tool_call_count: 工具调用计数

    Returns:
        包含报告的状态字典
    """
    logger.info("[决策] ===== 执行强制工具调用 =====")
    logger.info("[决策原因] 未检测到工具结果或分析内容，需要获取基本面数据")
    logger.info("[决策] 启用强制工具调用模式")

    # 强制调用工具
    combined_data = _force_tool_invocation(tools, ticker, start_date, current_date)

    # 生成分析报告
    report = _generate_analysis_report(fresh_llm, ticker, company_name, combined_data, market_info)

    return {
        "fundamentals_report": report,
        "fundamentals_tool_call_count": tool_call_count
    }


def _handle_google_model_result(
    result: Any,
    fresh_llm: Any,
    tools: list,
    state: dict,
    ticker: str,
    company_name: str
) -> dict:
    """
    处理Google模型的结果

    Args:
        result: LLM返回结果
        fresh_llm: LLM实例
        tools: 工具列表
        state: 当前状态
        ticker: 股票代码
        company_name: 公司名称

    Returns:
        包含报告的状态字典
    """
    logger.info("[基本面分析师] 检测到Google模型，使用统一工具调用处理器")

    analysis_prompt_template = GoogleToolCallHandler.create_analysis_prompt(
        ticker=ticker,
        company_name=company_name,
        analyst_type="基本面分析",
        specific_requirements="重点关注财务数据、盈利能力、估值指标、行业地位等基本面因素。"
    )

    report, messages = GoogleToolCallHandler.handle_google_tool_calls(
        result=result,
        llm=fresh_llm,
        tools=tools,
        state=state,
        analysis_prompt_template=analysis_prompt_template,
        analyst_name="基本面分析师"
    )

    return {"fundamentals_report": report}


def _handle_standard_model_result(
    result: Any,
    state: dict,
    fresh_llm: Any,
    tools: list,
    ticker: str,
    company_name: str,
    start_date: str,
    current_date: str,
    market_info: dict,
    tool_call_count: int,
    max_tool_calls: int
) -> dict:
    """
    处理标准模型（非Google）的结果

    Args:
        result: LLM返回结果
        state: 当前状态
        fresh_llm: LLM实例
        tools: 工具列表
        ticker: 股票代码
        company_name: 公司名称
        start_date: 开始日期
        current_date: 当前日期
        market_info: 市场信息
        tool_call_count: 工具调用计数
        max_tool_calls: 最大工具调用次数

    Returns:
        更新后的状态字典
    """
    logger.debug(f"[基本面分析师] 非Google模型 ({fresh_llm.__class__.__name__})，使用标准处理逻辑")

    current_tool_calls = len(result.tool_calls) if hasattr(result, 'tool_calls') else 0
    logger.debug(f"[基本面分析师] 当前消息的工具调用数量: {current_tool_calls}")
    logger.debug(f"[基本面分析师] 累计工具调用次数: {tool_call_count}/{max_tool_calls}")

    if current_tool_calls > 0:
        return _handle_tool_calls_present(
            result, state, fresh_llm, ticker, company_name,
            tool_call_count, max_tool_calls
        )

    return _handle_no_tool_calls(
        result, state, fresh_llm, tools, ticker, company_name,
        start_date, current_date, market_info, tool_call_count
    )


def _update_tool_call_count(state: dict, messages: list) -> int:
    """
    更新工具调用计数器

    Args:
        state: 当前状态
        messages: 消息列表

    Returns:
        更新后的工具调用计数
    """
    tool_message_count = _count_tool_messages(messages)
    tool_call_count = state.get("fundamentals_tool_call_count", 0)

    if tool_message_count > tool_call_count:
        tool_call_count = tool_message_count
        logger.info(f"[工具调用计数] 检测到新的工具结果，更新计数器: {tool_call_count}")

    return tool_call_count


# =============================================================================
# 公共接口
# =============================================================================

def create_fundamentals_analyst(llm, toolkit):
    """
    创建基本面分析师节点

    Args:
        llm: LLM实例
        toolkit: 工具包实例

    Returns:
        基本面分析师节点函数
    """

    @log_analyst_module("fundamentals")
    def fundamentals_analyst_node(state: dict) -> dict:
        """基本面分析师节点主函数"""
        logger.debug("[基本面分析师] ===== 节点开始 =====")

        # 1. 初始化和状态检查
        messages = state.get("messages", [])
        tool_call_count = _update_tool_call_count(state, messages)
        max_tool_calls = 1

        logger.info(f"[工具调用计数] 当前工具调用次数: {tool_call_count}/{max_tool_calls}")

        # 2. 获取基本参数
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        start_date, end_date = _calculate_date_range(current_date)

        logger.debug(f"[基本面分析师] 输入参数: ticker={ticker}, date={current_date}")
        logger.debug(f"[基本面分析师] 当前状态中的消息数量: {len(messages)}")
        logger.debug(f"[基本面分析师] 现有基本面报告: {state.get('fundamentals_report', 'None')}")

        # 3. 获取市场信息和公司名称
        from tradingagents.utils.stock_utils import StockUtils
        logger.info(f"[基本面分析师] 正在分析股票: {ticker}")

        _log_stock_code_trace(ticker)

        market_info = StockUtils.get_market_info(ticker)
        _log_market_info(ticker, market_info, toolkit)

        company_name = get_company_name(ticker, market_info)
        logger.info(f"[基本面分析师] 公司名称: {company_name}")

        # 4. 准备工具和提示词
        tools = [toolkit.get_stock_fundamentals_unified]
        tool_names = _get_tool_names(tools)

        logger.info(f"[基本面分析师] 使用统一基本面分析工具，自动识别股票类型")
        logger.info(f"[基本面分析师] 绑定的工具: {tool_names}")
        logger.info(f"[基本面分析师] 目标市场: {market_info['market_name']}")

        system_message = _build_system_message(
            ticker, company_name, market_info, start_date, current_date
        )

        # 5. 创建LLM链
        fresh_llm = _create_fresh_llm(llm)
        prompt = _create_prompt_template(system_message, tool_names, current_date, ticker, company_name)

        logger.debug(f"[基本面分析师] 创建LLM链，工具数量: {len(tools)}")
        logger.debug(f"[基本面分析师] 绑定的工具列表: {tool_names}")
        logger.debug(f"[基本面分析师] 创建工具链，让模型自主决定是否调用工具")

        logger.info(f"[基本面分析师] LLM类型: {fresh_llm.__class__.__name__}")
        logger.info(f"[基本面分析师] LLM模型: {getattr(fresh_llm, 'model_name', 'unknown')}")
        logger.info(f"[基本面分析师] 消息历史数量: {len(messages)}")

        try:
            chain = prompt | fresh_llm.bind_tools(tools)
            logger.info(f"[基本面分析师] 工具绑定成功，绑定了 {len(tools)} 个工具")
        except Exception as e:
            logger.error(f"[基本面分析师] 工具绑定失败: {e}")
            raise e

        # 6. 调用LLM
        logger.info("[基本面分析师] 开始调用LLM...")
        logger.info(f"[股票代码追踪] LLM调用前，ticker参数: '{ticker}'")
        logger.info(f"[股票代码追踪] 传递给LLM的消息数量: {len(messages)}")

        _log_llm_input(system_message, tool_names, current_date, ticker, company_name, messages, tools)

        result = chain.invoke({"messages": messages})
        logger.info("[基本面分析师] LLM调用完成")

        _log_llm_result(result)

        # 7. 处理结果
        if GoogleToolCallHandler.is_google_model(fresh_llm):
            return _handle_google_model_result(
                result, fresh_llm, tools, state, ticker, company_name
            )

        return _handle_standard_model_result(
            result, state, fresh_llm, tools, ticker, company_name,
            start_date, current_date, market_info, tool_call_count, max_tool_calls
        )

    return fundamentals_analyst_node
