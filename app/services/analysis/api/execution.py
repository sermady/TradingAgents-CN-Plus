# -*- coding: utf-8 -*-
"""API分析执行模块

提供同步和异步分析执行逻辑。
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, TYPE_CHECKING, Callable

from tradingagents.utils.logging_init import init_logging, get_logger

from app.models.analysis import AnalysisTask, AnalysisResult, AnalysisStatus
from app.services.redis_progress_tracker import RedisProgressTracker
from app.core.unified_config_service import get_config_manager
from app.services.simple_analysis_service import create_analysis_config

if TYPE_CHECKING:
    from .core import AnalysisAPIService

logger = logging.getLogger(__name__)


def _execute_analysis_sync_with_progress(
    service: "AnalysisAPIService",
    task: AnalysisTask,
    progress_tracker: RedisProgressTracker
) -> AnalysisResult:
    """同步执行分析任务（在线程池中运行，带进度跟踪）"""
    try:
        # 在线程中重新初始化日志系统
        init_logging()
        thread_logger = get_logger("analysis_thread")

        thread_logger.info(
            f"🔄 [线程池] 开始执行分析任务: {task.task_id} - {task.symbol}"
        )
        logger.info(f"🔄 [线程池] 开始执行分析任务: {task.task_id} - {task.symbol}")

        # 环境检查
        progress_tracker.update_progress("🔧 检查环境配置")

        # 使用统一配置管理器
        config_mgr = get_config_manager()
        quick_model = (
            getattr(task.parameters, "quick_analysis_model", None)
            or config_mgr.get_quick_analysis_model()
        )
        deep_model = (
            getattr(task.parameters, "deep_analysis_model", None)
            or config_mgr.get_deep_analysis_model()
        )

        # 从 MongoDB 读取模型配置
        quick_model_config = None
        deep_model_config = None

        try:
            from pymongo import MongoClient
            from app.core.config import settings

            client = MongoClient(settings.MONGO_URI)
            db = client[settings.MONGO_DB]
            collection = db.system_configs

            doc = collection.find_one({"is_active": True}, sort=[("version", -1)])

            if doc and "llm_configs" in doc:
                llm_configs = doc["llm_configs"]
                logger.info(f"✅ 从 MongoDB 读取到 {len(llm_configs)} 个模型配置")

                for llm_config in llm_configs:
                    if llm_config.get("model_name") == quick_model:
                        quick_model_config = {
                            "max_tokens": llm_config.get("max_tokens", 4000),
                            "temperature": llm_config.get("temperature", 0.7),
                            "timeout": llm_config.get("timeout", 180),
                            "retry_times": llm_config.get("retry_times", 3),
                            "api_base": llm_config.get("api_base"),
                        }
                        logger.info(f"✅ 读取快速模型配置: {quick_model}")

                    if llm_config.get("model_name") == deep_model:
                        deep_model_config = {
                            "max_tokens": llm_config.get("max_tokens", 4000),
                            "temperature": llm_config.get("temperature", 0.7),
                            "timeout": llm_config.get("timeout", 180),
                            "retry_times": llm_config.get("retry_times", 3),
                            "api_base": llm_config.get("api_base"),
                        }
                        logger.info(
                            f"✅ 读取深度模型配置: {deep_model}"
                        )
            else:
                logger.warning("⚠️ MongoDB 中没有找到系统配置，将使用默认参数")
        except Exception as e:
            logger.warning(f"⚠️ 从 MongoDB 读取模型配置失败: {e}，将使用默认参数")

        # 成本估算
        progress_tracker.update_progress("💰 预估分析成本")

        llm_provider = "dashscape"

        # 参数配置
        progress_tracker.update_progress("⚙️ 配置分析参数")

        config = create_analysis_config(
            research_depth=task.parameters.research_depth if task.parameters else "标准",
            selected_analysts=task.parameters.selected_analysts
            if task.parameters and hasattr(task.parameters, 'selected_analysts')
            else ["market", "fundamentals"],
            quick_model=quick_model,
            deep_model=deep_model,
            llm_provider=llm_provider,
            market_type=getattr(task.parameters, "market_type", "A股") if task.parameters else "A股",
            quick_model_config=quick_model_config,
            deep_model_config=deep_model_config,
        )

        # 启动引擎
        progress_tracker.update_progress("🚀 初始化AI分析引擎")

        # 获取TradingAgents实例
        trading_graph = service._get_trading_graph(config)

        # 执行分析
        start_time = datetime.now(timezone.utc)
        if task.parameters and task.parameters.analysis_date:
            if isinstance(task.parameters.analysis_date, datetime):
                analysis_date = task.parameters.analysis_date.strftime("%Y-%m-%d")
            else:
                analysis_date = str(task.parameters.analysis_date)
        else:
            analysis_date = datetime.now().strftime("%Y-%m-%d")

        # 创建进度回调函数
        def progress_callback(message: str):
            progress_tracker.update_progress(message)

        # 调用分析方法
        _, decision = trading_graph.propagate(
            task.symbol, analysis_date, progress_callback
        )

        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        # 生成报告
        progress_tracker.update_progress("📊 生成分析报告")

        # 从决策中提取模型信息
        model_info = (
            decision.get("model_info", "Unknown")
            if isinstance(decision, dict)
            else "Unknown"
        )

        # 构建结果
        result = AnalysisResult(
            analysis_id=str(uuid.uuid4()),
            summary=decision.get("summary", ""),
            recommendation=decision.get("recommendation", ""),
            confidence_score=decision.get("confidence_score", 0.0),
            risk_level=decision.get("risk_level", "中等"),
            key_points=decision.get("key_points", []),
            detailed_analysis=decision,
            execution_time=execution_time,
            tokens_used=decision.get("tokens_used", 0),
            model_info=model_info,
        )

        logger.info(
            f"✅ [线程池] 分析任务完成: {task.task_id} - 耗时{execution_time:.2f}秒"
        )
        return result

    except Exception as e:
        logger.error(f"❌ [线程池] 执行分析任务失败: {task.task_id} - {e}")
        raise


def _execute_analysis_sync(
    service: "AnalysisAPIService",
    task: AnalysisTask
) -> AnalysisResult:
    """同步执行分析任务（在线程池中运行）"""
    try:
        logger.info(f"🔄 [线程池] 开始执行分析任务: {task.task_id} - {task.symbol}")

        # 使用统一配置管理器
        config_mgr = get_config_manager()
        quick_model = (
            getattr(task.parameters, "quick_analysis_model", None)
            or config_mgr.get_quick_analysis_model()
        )
        deep_model = (
            getattr(task.parameters, "deep_analysis_model", None)
            or config_mgr.get_deep_analysis_model()
        )

        # 从 MongoDB 读取模型配置
        quick_model_config = None
        deep_model_config = None

        try:
            from pymongo import MongoClient
            from app.core.config import settings

            client = MongoClient(settings.MONGO_URI)
            db = client[settings.MONGO_DB]
            collection = db.system_configs

            doc = collection.find_one({"is_active": True}, sort=[("version", -1)])

            if doc and "llm_configs" in doc:
                llm_configs = doc["llm_configs"]

                for llm_config in llm_configs:
                    if llm_config.get("model_name") == quick_model:
                        quick_model_config = {
                            "max_tokens": llm_config.get("max_tokens", 4000),
                            "temperature": llm_config.get("temperature", 0.7),
                            "timeout": llm_config.get("timeout", 180),
                            "retry_times": llm_config.get("retry_times", 3),
                            "api_base": llm_config.get("api_base"),
                        }

                    if llm_config.get("model_name") == deep_model:
                        deep_model_config = {
                            "max_tokens": llm_config.get("max_tokens", 4000),
                            "temperature": llm_config.get("temperature", 0.7),
                            "timeout": llm_config.get("timeout", 180),
                            "retry_times": llm_config.get("retry_times", 3),
                            "api_base": llm_config.get("api_base"),
                        }
        except Exception as e:
            logger.warning(f"⚠️ 从 MongoDB 读取模型配置失败: {e}")

        llm_provider = "dashscope"
        selected_analysts = (["market", "fundamentals"]
                          if not task.parameters or not hasattr(task.parameters, 'selected_analysts') or not task.parameters.selected_analysts
                          else task.parameters.selected_analysts)
        market_type = ("A股"
                    if not task.parameters or not hasattr(task.parameters, 'market_type')
                    else task.parameters.market_type)

        config = create_analysis_config(
            research_depth=task.parameters.research_depth if task.parameters and hasattr(task.parameters, 'research_depth') else "标准",
            selected_analysts=selected_analysts,
            quick_model=quick_model,
            deep_model=deep_model,
            llm_provider=llm_provider,
            market_type=market_type,
            quick_model_config=quick_model_config,
            deep_model_config=deep_model_config,
        )

        # 获取TradingAgents实例
        trading_graph = service._get_trading_graph(config)

        # 执行分析
        start_time = datetime.now(timezone.utc)
        if task.parameters and task.parameters.analysis_date:
            if isinstance(task.parameters.analysis_date, datetime):
                analysis_date = task.parameters.analysis_date.strftime("%Y-%m-%d")
            else:
                analysis_date = str(task.parameters.analysis_date)
        else:
            analysis_date = datetime.now().strftime("%Y-%m-%d")

        # 调用分析方法
        _, decision = trading_graph.propagate(task.symbol, analysis_date)

        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        # 从决策中提取模型信息
        model_info = (
            decision.get("model_info", "Unknown")
            if isinstance(decision, dict)
            else "Unknown"
        )

        # 构建结果
        result = AnalysisResult(
            analysis_id=str(uuid.uuid4()),
            summary=decision.get("summary", ""),
            recommendation=decision.get("recommendation", ""),
            confidence_score=decision.get("confidence_score", 0.0),
            risk_level=decision.get("risk_level", "中等"),
            key_points=decision.get("key_points", []),
            detailed_analysis=decision,
            execution_time=execution_time,
            tokens_used=decision.get("tokens_used", 0),
            model_info=model_info,
        )

        logger.info(
            f"✅ [线程池] 分析任务完成: {task.task_id} - 耗时{execution_time:.2f}秒"
        )
        return result

    except Exception as e:
        logger.error(f"❌ [线程池] 执行分析任务失败: {task.task_id} - {e}")
        raise
