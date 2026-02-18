#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票分析核心运行器

负责执行股票分析的主要逻辑
"""

import sys
import os
import uuid
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger, get_logger_manager

logger = get_logger("web.core_runner")

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 确保环境变量正确加载
load_dotenv(project_root / ".env", override=True)

# 导入统一日志系统
from tradingagents.utils.logging_init import setup_web_logging

logger = setup_web_logging()

# 添加配置管理器
try:
    from tradingagents.config.config_manager import token_tracker

    TOKEN_TRACKING_ENABLED = True
    logger.info("✅ Token跟踪功能已启用")
except ImportError:
    TOKEN_TRACKING_ENABLED = False
    logger.warning("⚠️ Token跟踪功能未启用")

# 导入格式化工具
from .formatter import extract_risk_assessment


def run_stock_analysis(
    stock_symbol,
    analysis_date=None,
    analysts=None,
    research_depth=3,
    llm_provider="dashscope",
    llm_model="qwen-plus",
    market_type="美股",
    use_realtime=True,
    progress_callback=None,
):
    """执行股票分析

    Args:
        stock_symbol: 股票代码
        analysis_date: 分析日期 (默认今天)
        analysts: 分析师列表 (默认全部)
        research_depth: 研究深度 (默认3-标准分析)
        llm_provider: LLM提供商 (dashscope/deepseek/google)
        llm_model: 大模型名称
        market_type: 市场类型 (A股/港股/美股)
        use_realtime: 是否使用实时行情 (仅今天有效，默认True)
        progress_callback: 进度回调函数，用于更新UI状态

    Returns:
        dict: 分析结果字典，包含success, state, decision等字段
    """
    # 处理默认值
    if analysis_date is None:
        analysis_date = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"📅 未指定分析日期，默认使用今天: {analysis_date}")

    if analysts is None:
        analysts = ["market", "fundamentals", "news", "social"]
        logger.info(f"📊 未指定分析师，默认使用全部: {analysts}")

    def update_progress(message, step=None, total_steps=None):
        """更新进度"""
        if progress_callback:
            progress_callback(message, step, total_steps)
        logger.info(f"[进度] {message}")

    # 生成会话ID用于Token跟踪和日志关联
    session_id = (
        f"analysis_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )

    # 1. 数据预获取和验证阶段
    update_progress("🔍 验证股票代码并预获取数据...", 1, 10)

    try:
        from tradingagents.utils.stock_validator import prepare_stock_data

        # 预获取股票数据（默认30天历史数据）
        preparation_result = prepare_stock_data(
            stock_code=stock_symbol,
            market_type=market_type,
            period_days=30,  # 可以根据research_depth调整
            analysis_date=analysis_date,
        )

        if not preparation_result.is_valid:
            error_msg = f"❌ 股票数据验证失败: {preparation_result.error_message}"
            update_progress(error_msg)
            logger.error(f"[{session_id}] {error_msg}")

            return {
                "success": False,
                "error": preparation_result.error_message,
                "suggestion": preparation_result.suggestion,
                "stock_symbol": stock_symbol,
                "analysis_date": analysis_date,
                "session_id": session_id,
            }

        # 数据预获取成功
        success_msg = f"✅ 数据准备完成: {preparation_result.stock_name} ({preparation_result.market_type})"
        update_progress(success_msg)  # 使用智能检测，不再硬编码步骤
        logger.info(f"[{session_id}] {success_msg}")
        logger.info(f"[{session_id}] 缓存状态: {preparation_result.cache_status}")

        # 2. 实时行情获取（仅当 use_realtime=True 且分析日期是今天时）
        realtime_quote = None
        if use_realtime:
            try:
                from tradingagents.dataflows.data_source_manager import (
                    get_data_source_manager,
                )

                dsm = get_data_source_manager()

                if dsm.should_use_realtime_data(analysis_date, market_type):
                    update_progress("📈 获取实时行情数据...")
                    realtime_quote = dsm.get_realtime_quote(stock_symbol, market_type)
                    if realtime_quote:
                        price = realtime_quote.get("price", "N/A")
                        change_pct = realtime_quote.get("change_pct", 0)
                        market_status = realtime_quote.get("market_status_desc", "未知")
                        logger.info(
                            f"📈 [实时行情] {stock_symbol}: 价格={price}, 涨跌幅={change_pct}%, 市场状态={market_status}"
                        )
                        update_progress(
                            f"📈 实时行情: ¥{price} ({change_pct:+.2f}%) - {market_status}"
                        )
                    else:
                        logger.warning(f"⚠️ [实时行情] 获取失败，将使用历史数据")
                        update_progress("⚠️ 实时行情获取失败，使用历史数据")
                else:
                    logger.info(
                        f"📅 [实时行情] 分析日期非今天或非交易时段，使用历史数据"
                    )
            except Exception as rt_error:
                logger.warning(f"⚠️ [实时行情] 获取异常: {rt_error}")
                # 实时行情获取失败不影响后续分析

    except Exception as e:
        error_msg = f"❌ 数据预获取过程中发生错误: {str(e)}"
        update_progress(error_msg)
        logger.error(f"[{session_id}] {error_msg}")

        return {
            "success": False,
            "error": error_msg,
            "suggestion": "请检查网络连接或稍后重试",
            "stock_symbol": stock_symbol,
            "analysis_date": analysis_date,
            "session_id": session_id,
        }

    # 记录分析开始的详细日志
    logger_manager = get_logger_manager()
    analysis_start_time = time.time()

    logger_manager.log_analysis_start(
        logger, stock_symbol, "comprehensive_analysis", session_id
    )

    logger.info(
        f"🚀 [分析开始] 股票分析启动",
        extra={
            "stock_symbol": stock_symbol,
            "analysis_date": analysis_date,
            "analysts": analysts,
            "research_depth": research_depth,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "market_type": market_type,
            "session_id": session_id,
            "event_type": "web_analysis_start",
        },
    )

    update_progress("🚀 开始股票分析...")

    # 估算Token使用（用于成本预估）
    if TOKEN_TRACKING_ENABLED:
        estimated_input = 2000 * len(analysts)  # 估算每个分析师2000个输入token
        estimated_output = 1000 * len(analysts)  # 估算每个分析师1000个输出token
        estimated_cost_result = token_tracker.estimate_cost(
            llm_provider, llm_model, estimated_input, estimated_output
        )

        # estimate_cost 返回 tuple (cost, currency)
        if isinstance(estimated_cost_result, tuple):
            estimated_cost, currency = estimated_cost_result
        else:
            estimated_cost = estimated_cost_result
            currency = "CNY"

        update_progress(f"💰 预估分析成本: ¥{estimated_cost:.4f}")

    # 验证环境变量
    update_progress("检查环境变量配置...")
    dashscope_key = os.getenv("DASHSCOPE_API_KEY")
    finnhub_key = os.getenv("FINNHUB_API_KEY")

    logger.info(f"环境变量检查:")
    logger.info(f"  DASHSCOPE_API_KEY: {'已设置' if dashscope_key else '未设置'}")
    logger.info(f"  FINNHUB_API_KEY: {'已设置' if finnhub_key else '未设置'}")

    if not dashscope_key:
        raise ValueError("DASHSCOPE_API_KEY 环境变量未设置")
    if not finnhub_key:
        raise ValueError("FINNHUB_API_KEY 环境变量未设置")

    update_progress("环境变量验证通过")

    try:
        # 导入必要的模块
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG

        # 创建配置
        update_progress("配置分析参数...")
        config = DEFAULT_CONFIG.copy()
        config["llm_provider"] = llm_provider
        config["deep_think_llm"] = llm_model
        config["quick_think_llm"] = llm_model

        # 根据研究深度调整配置
        config = _configure_by_research_depth(
            config, research_depth, llm_provider, market_type
        )

        # 根据LLM提供商设置不同的配置
        config = _configure_by_llm_provider(config, llm_provider, research_depth)

        # 修复路径问题 - 优先使用环境变量配置
        config = _configure_paths(config, project_root)

        # 确保目录存在
        update_progress("📁 创建必要的目录...")
        os.makedirs(config["data_dir"], exist_ok=True)
        os.makedirs(config["results_dir"], exist_ok=True)
        os.makedirs(config["data_cache_dir"], exist_ok=True)

        logger.info(f"📁 目录配置:")
        logger.info(f"  - 数据目录: {config['data_dir']}")
        logger.info(f"  - 结果目录: {config['results_dir']}")
        logger.info(f"  - 缓存目录: {config['data_cache_dir']}")
        logger.info(
            f"  - 环境变量 TRADINGAGENTS_RESULTS_DIR: {os.getenv('TRADINGAGENTS_RESULTS_DIR', '未设置')}"
        )

        logger.info(f"使用配置: {config}")
        logger.info(f"分析师列表: {analysts}")
        logger.info(f"股票代码: {stock_symbol}")
        logger.info(f"分析日期: {analysis_date}")

        # 根据市场类型调整股票代码格式
        logger.debug(f"🔍 [RUNNER DEBUG] ===== 股票代码格式化 =====")
        logger.debug(f"🔍 [RUNNER DEBUG] 原始股票代码: '{stock_symbol}'")
        logger.debug(f"🔍 [RUNNER DEBUG] 市场类型: '{market_type}'")

        formatted_symbol = _format_stock_symbol(stock_symbol, market_type)

        logger.debug(
            f"🔍 [RUNNER DEBUG] 最终传递给分析引擎的股票代码: '{formatted_symbol}'"
        )

        # 初始化交易图
        update_progress("🔧 初始化分析引擎...")
        graph = TradingAgentsGraph(analysts, config=config, debug=False)

        # 执行分析
        update_progress(f"📊 开始分析 {formatted_symbol} 股票，这可能需要几分钟时间...")
        logger.debug(f"🔍 [RUNNER DEBUG] ===== 调用graph.propagate =====")
        logger.debug(f"🔍 [RUNNER DEBUG] 传递给graph.propagate的参数:")
        logger.debug(f"🔍 [RUNNER DEBUG]   symbol: '{formatted_symbol}'")
        logger.debug(f"🔍 [RUNNER DEBUG]   date: '{analysis_date}'")

        state, decision = graph.propagate(formatted_symbol, analysis_date)

        # 调试信息
        logger.debug(f"🔍 [DEBUG] 分析完成，decision类型: {type(decision)}")
        logger.debug(f"🔍 [DEBUG] decision内容: {decision}")

        # 格式化结果
        update_progress("📋 分析完成，正在整理结果...")

        # 确保 state 不为 None
        if state is None:
            state = {}

        # 提取风险评估数据
        risk_assessment = extract_risk_assessment(state)

        # 将风险评估添加到状态中
        if risk_assessment:
            state["risk_assessment"] = risk_assessment

        # 记录Token使用（实际使用量，这里使用估算值）
        if TOKEN_TRACKING_ENABLED:
            # 在实际应用中，这些值应该从LLM响应中获取
            # 这里使用基于分析师数量和研究深度的估算
            actual_input_tokens = len(analysts) * (
                1500
                if research_depth == "快速"
                else 2500
                if research_depth == "标准"
                else 4000
            )
            actual_output_tokens = len(analysts) * (
                800
                if research_depth == "快速"
                else 1200
                if research_depth == "标准"
                else 2000
            )

            usage_record = token_tracker.track_usage(
                provider=llm_provider,
                model_name=llm_model,
                input_tokens=actual_input_tokens,
                output_tokens=actual_output_tokens,
                session_id=session_id,
                analysis_type=f"{market_type}_analysis",
            )

            if usage_record:
                update_progress(f"💰 记录使用成本: ¥{usage_record.cost:.4f}")

        # 从决策中提取模型信息
        model_info = (
            decision.get("model_info", "Unknown")
            if isinstance(decision, dict)
            else "Unknown"
        )

        results = {
            "stock_symbol": stock_symbol,
            "analysis_date": analysis_date,
            "analysts": analysts,
            "research_depth": research_depth,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "model_info": model_info,  # 🔥 添加模型信息字段
            "market_type": market_type,  # 添加市场类型
            "use_realtime": use_realtime,  # 添加是否使用实时行情标志
            "realtime_quote": realtime_quote,  # 添加实时行情数据
            "state": state,
            "decision": decision,
            "success": True,
            "error": None,
            "session_id": session_id if TOKEN_TRACKING_ENABLED else None,
        }

        # 记录分析完成的详细日志
        analysis_duration = time.time() - analysis_start_time

        # 计算总成本（如果有Token跟踪）
        total_cost = 0.0
        if TOKEN_TRACKING_ENABLED:
            try:
                total_cost = token_tracker.get_session_cost(session_id)
            except:
                pass

        logger_manager.log_analysis_complete(
            logger,
            stock_symbol,
            "comprehensive_analysis",
            session_id,
            analysis_duration,
            total_cost,
        )

        logger.info(
            f"✅ [分析完成] 股票分析成功完成",
            extra={
                "stock_symbol": stock_symbol,
                "session_id": session_id,
                "duration": analysis_duration,
                "total_cost": total_cost,
                "analysts_used": analysts,
                "success": True,
                "event_type": "web_analysis_complete",
            },
        )

        # 保存分析报告到本地和MongoDB
        try:
            update_progress("💾 正在保存分析报告...")
            from web.utils.report_exporter import (
                save_analysis_report,
                save_modular_reports_to_results_dir,
            )

            # 1. 保存分模块报告到本地目录
            logger.info(f"📁 [本地保存] 开始保存分模块报告到本地目录")
            local_files = save_modular_reports_to_results_dir(results, stock_symbol)
            if local_files:
                logger.info(f"✅ [本地保存] 已保存 {len(local_files)} 个本地报告文件")
                for module, path in local_files.items():
                    logger.info(f"  - {module}: {path}")
            else:
                logger.warning(f"⚠️ [本地保存] 本地报告文件保存失败")

            # 2. 保存分析报告到MongoDB
            logger.info(f"🗄️ [MongoDB保存] 开始保存分析报告到MongoDB")
            save_success = save_analysis_report(
                stock_symbol=stock_symbol, analysis_results=results
            )

            if save_success:
                logger.info(f"✅ [MongoDB保存] 分析报告已成功保存到MongoDB")
                update_progress("✅ 分析报告已保存到数据库和本地文件")
            else:
                logger.warning(f"⚠️ [MongoDB保存] MongoDB报告保存失败")
                if local_files:
                    update_progress("✅ 本地报告已保存，但数据库保存失败")
                else:
                    update_progress("⚠️ 报告保存失败，但分析已完成")

        except Exception as save_error:
            logger.error(f"❌ [报告保存] 保存分析报告时发生错误: {str(save_error)}")
            update_progress("⚠️ 报告保存出错，但分析已完成")

        update_progress("✅ 分析成功完成！")
        return results

    except Exception as e:
        # 记录分析失败的详细日志
        analysis_duration = time.time() - analysis_start_time

        logger_manager.log_module_error(
            logger,
            "comprehensive_analysis",
            stock_symbol,
            session_id,
            analysis_duration,
            str(e),
        )

        logger.error(
            f"❌ [分析失败] 股票分析执行失败",
            extra={
                "stock_symbol": stock_symbol,
                "session_id": session_id,
                "duration": analysis_duration,
                "error": str(e),
                "error_type": type(e).__name__,
                "analysts_used": analysts,
                "success": False,
                "event_type": "web_analysis_error",
            },
            exc_info=True,
        )

        # 如果真实分析失败，返回错误信息而不是误导性演示数据
        return {
            "stock_symbol": stock_symbol,
            "analysis_date": analysis_date,
            "analysts": analysts,
            "research_depth": research_depth,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "state": {},  # 空状态，将显示占位符
            "decision": {},  # 空决策
            "success": False,
            "error": str(e),
            "is_demo": False,
            "error_reason": f"分析失败: {str(e)}",
        }


def _configure_by_research_depth(config, research_depth, llm_provider, market_type):
    """根据研究深度调整配置"""
    # 根据研究深度调整配置
    if research_depth == 1:  # 1级 - 快速分析
        config["max_debate_rounds"] = 1
        config["max_risk_discuss_rounds"] = 1
        # 禁用记忆以加速
        config["memory_enabled"] = False

        # 统一使用在线工具，避免离线工具的各种问题
        config["online_tools"] = True  # 所有市场都使用统一工具
        logger.info(
            f"🔧 [快速分析] {market_type}使用统一工具，确保数据源正确和稳定性"
        )
        if llm_provider == "dashscope":
            config["quick_think_llm"] = "qwen-turbo"  # 使用最快模型
            config["deep_think_llm"] = "qwen-plus"
        elif llm_provider == "deepseek":
            config["quick_think_llm"] = "deepseek-chat"  # DeepSeek只有一个模型
            config["deep_think_llm"] = "deepseek-chat"
    elif research_depth == 2:  # 2级 - 基础分析
        config["max_debate_rounds"] = 1
        config["max_risk_discuss_rounds"] = 1
        config["memory_enabled"] = True
        config["online_tools"] = True
        if llm_provider == "dashscope":
            config["quick_think_llm"] = "qwen-plus"
            config["deep_think_llm"] = "qwen-plus"
        elif llm_provider == "deepseek":
            config["quick_think_llm"] = "deepseek-chat"
            config["deep_think_llm"] = "deepseek-chat"
        elif llm_provider == "openai":
            config["quick_think_llm"] = llm_model
            config["deep_think_llm"] = llm_model
    elif research_depth == 3:  # 3级 - 标准分析 (默认)
        config["max_debate_rounds"] = 1
        config["max_risk_discuss_rounds"] = 2
        config["memory_enabled"] = True
        config["online_tools"] = True
        if llm_provider == "dashscope":
            config["quick_think_llm"] = "qwen-plus"
            config["deep_think_llm"] = "qwen3-max"
        elif llm_provider == "deepseek":
            config["quick_think_llm"] = "deepseek-chat"
            config["deep_think_llm"] = "deepseek-chat"
    elif research_depth == 4:  # 4级 - 深度分析
        config["max_debate_rounds"] = 2
        config["max_risk_discuss_rounds"] = 2
        config["memory_enabled"] = True
        config["online_tools"] = True
        if llm_provider == "dashscope":
            config["quick_think_llm"] = "qwen-plus"
            config["deep_think_llm"] = "qwen3-max"
        elif llm_provider == "deepseek":
            config["quick_think_llm"] = "deepseek-chat"
            config["deep_think_llm"] = "deepseek-chat"
    else:  # 5级 - 全面分析
        config["max_debate_rounds"] = 3
        config["max_risk_discuss_rounds"] = 3
        config["memory_enabled"] = True
        config["online_tools"] = True
        if llm_provider == "dashscope":
            config["quick_think_llm"] = "qwen3-max"
            config["deep_think_llm"] = "qwen3-max"
        elif llm_provider == "deepseek":
            config["quick_think_llm"] = "deepseek-chat"
            config["deep_think_llm"] = "deepseek-chat"

    return config


def _configure_by_llm_provider(config, llm_provider, research_depth):
    """根据LLM提供商设置不同的配置"""
    if llm_provider == "dashscope":
        config["backend_url"] = "https://dashscope.aliyuncs.com/api/v1"
    elif llm_provider == "deepseek":
        config["backend_url"] = "https://api.deepseek.com"
    elif llm_provider == "qianfan":
        # 千帆（文心一言）配置
        config["backend_url"] = "https://aip.baidubce.com"
        # 根据研究深度设置千帆模型
        if research_depth <= 2:  # 快速和基础分析
            config["quick_think_llm"] = "ernie-3.5-8k"
            config["deep_think_llm"] = "ernie-3.5-8k"
        elif research_depth <= 4:  # 标准和深度分析
            config["quick_think_llm"] = "ernie-3.5-8k"
            config["deep_think_llm"] = "ernie-4.0-turbo-8k"
        else:  # 全面分析
            config["quick_think_llm"] = "ernie-4.0-turbo-8k"
            config["deep_think_llm"] = "ernie-4.0-turbo-8k"

        logger.info(f"🤖 [千帆] 快速模型: {config['quick_think_llm']}")
        logger.info(f"🤖 [千帆] 深度模型: {config['deep_think_llm']}")
    elif llm_provider == "google":
        # Google AI不需要backend_url，使用默认的OpenAI格式
        config["backend_url"] = "https://api.openai.com/v1"

        # 根据研究深度优化Google模型选择
        if research_depth == 1:  # 快速分析 - 使用最快模型
            config["quick_think_llm"] = (
                "gemini-2.5-flash-lite-preview-06-17"  # 1.45s
            )
            config["deep_think_llm"] = "gemini-2.0-flash"  # 1.87s
        elif research_depth == 2:  # 基础分析 - 使用快速模型
            config["quick_think_llm"] = "gemini-2.0-flash"  # 1.87s
            config["deep_think_llm"] = "gemini-1.5-pro"  # 2.25s
        elif research_depth == 3:  # 标准分析 - 平衡性能
            config["quick_think_llm"] = "gemini-1.5-pro"  # 2.25s
            config["deep_think_llm"] = "gemini-2.5-flash"  # 2.73s
        elif research_depth == 4:  # 深度分析 - 使用强大模型
            config["quick_think_llm"] = "gemini-2.5-flash"  # 2.73s
            config["deep_think_llm"] = "gemini-2.5-pro"  # 16.68s
        else:  # 全面分析 - 使用最强模型
            config["quick_think_llm"] = "gemini-2.5-pro"  # 16.68s
            config["deep_think_llm"] = "gemini-2.5-pro"  # 16.68s

        logger.info(f"🤖 [Google AI] 快速模型: {config['quick_think_llm']}")
        logger.info(f"🤖 [Google AI] 深度模型: {config['deep_think_llm']}")
    elif llm_provider == "openai":
        # OpenAI官方API
        config["backend_url"] = "https://api.openai.com/v1"
        logger.info(f"🤖 [OpenAI] 使用模型: {config['llm_model']}")
        logger.info(f"🤖 [OpenAI] API端点: https://api.openai.com/v1")
    elif llm_provider == "openrouter":
        # OpenRouter使用OpenAI兼容API
        config["backend_url"] = "https://openrouter.ai/api/v1"
        logger.info(f"🌐 [OpenRouter] 使用模型: {config['llm_model']}")
        logger.info(f"🌐 [OpenRouter] API端点: https://openrouter.ai/api/v1")
    elif llm_provider == "siliconflow":
        config["backend_url"] = "https://api.siliconflow.cn/v1"
        logger.info(f"🌐 [SiliconFlow] 使用模型: {config['llm_model']}")
        logger.info(f"🌐 [SiliconFlow] API端点: https://api.siliconflow.cn/v1")

    return config


def _configure_paths(config, project_root):
    """配置数据路径"""
    # 数据目录：优先使用环境变量，否则使用默认路径
    if not config.get("data_dir") or config["data_dir"] == "./data":
        env_data_dir = os.getenv("TRADINGAGENTS_DATA_DIR")
        if env_data_dir:
            # 如果环境变量是相对路径，相对于项目根目录解析
            if not os.path.isabs(env_data_dir):
                config["data_dir"] = str(project_root / env_data_dir)
            else:
                config["data_dir"] = env_data_dir
        else:
            config["data_dir"] = str(project_root / "data")

    # 结果目录：优先使用环境变量，否则使用默认路径
    if not config.get("results_dir") or config["results_dir"] == "./results":
        env_results_dir = os.getenv("TRADINGAGENTS_RESULTS_DIR")
        if env_results_dir:
            # 如果环境变量是相对路径，相对于项目根目录解析
            if not os.path.isabs(env_results_dir):
                config["results_dir"] = str(project_root / env_results_dir)
            else:
                config["results_dir"] = env_results_dir
        else:
            config["results_dir"] = str(project_root / "results")

    # 缓存目录：优先使用环境变量，否则使用默认路径
    if not config.get("data_cache_dir"):
        env_cache_dir = os.getenv("TRADINGAGENTS_CACHE_DIR")
        if env_cache_dir:
            # 如果环境变量是相对路径，相对于项目根目录解析
            if not os.path.isabs(env_cache_dir):
                config["data_cache_dir"] = str(project_root / env_cache_dir)
            else:
                config["data_cache_dir"] = env_cache_dir
        else:
            config["data_cache_dir"] = str(
                project_root / "tradingagents" / "dataflows" / "data_cache"
            )

    return config


def _format_stock_symbol(stock_symbol, market_type):
    """根据市场类型格式化股票代码"""
    if market_type == "A股":
        # A股代码不需要特殊处理，保持原样
        formatted_symbol = stock_symbol
        logger.debug(f"🔍 [FORMAT DEBUG] A股代码保持原样: '{formatted_symbol}'")
    elif market_type == "港股":
        # 港股代码转为大写，确保.HK后缀
        formatted_symbol = stock_symbol.upper()
        if not formatted_symbol.endswith(".HK"):
            # 如果是纯数字，添加.HK后缀
            if formatted_symbol.isdigit():
                formatted_symbol = f"{formatted_symbol.zfill(4)}.HK"
    else:
        # 美股代码转为大写
        formatted_symbol = stock_symbol.upper()
        logger.debug(
            f"🔍 [FORMAT DEBUG] 美股代码转大写: '{stock_symbol}' -> '{formatted_symbol}'"
        )

    return formatted_symbol
