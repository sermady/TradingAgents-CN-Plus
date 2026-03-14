# -*- coding: utf-8 -*-
"""API批量分析模块

提供单股分析和批量分析任务提交功能。
"""

import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, TYPE_CHECKING

from app.models.analysis import (
    AnalysisTask,
    AnalysisResult,
    AnalysisStatus,
    AnalysisBatch,
    BatchStatus,
    SingleAnalysisRequest,
    BatchAnalysisRequest,
    AnalysisParameters,
)
from app.core.database import get_mongo_db
from app.services.config_provider import provider as config_provider
from app.services.queue import (
    DEFAULT_USER_CONCURRENT_LIMIT,
    GLOBAL_CONCURRENT_LIMIT,
    VISIBILITY_TIMEOUT_SECONDS,
)

if TYPE_CHECKING:
    from .core import AnalysisAPIService

logger = logging.getLogger(__name__)


async def _execute_single_analysis_async(
    service: "AnalysisAPIService", task: AnalysisTask
) -> AnalysisResult:
    """异步执行单股分析任务（在后台运行，不阻塞主线程）"""
    from .execution import _execute_analysis_sync_with_progress
    from .status import _update_task_status, _update_task_status_with_tracker, _record_token_usage
    from app.services.simple_analysis_service import get_provider_by_model_name_sync

    progress_tracker = None
    try:
        logger.info(f"🔄 开始执行分析任务: {task.task_id} - {task.symbol}")

        # 创建进度跟踪器
        progress_tracker = service._get_progress_tracker(task)

        # 初始化进度
        progress_tracker.update_progress("🚀 开始股票分析")
        await _update_task_status_with_tracker(
            service, task.task_id, AnalysisStatus.PROCESSING, progress_tracker
        )

        # 在线程池中执行分析，避免阻塞事件循环
        loop = asyncio.get_event_loop()

        # 使用线程池执行器运行同步的分析代码
        with asyncio.ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(
                executor,
                _execute_analysis_sync_with_progress,
                service,
                task,
                progress_tracker,
            )

        # 标记完成
        progress_tracker.mark_completed("✅ 分析完成")
        await _update_task_status_with_tracker(
            service, task.task_id, AnalysisStatus.COMPLETED, progress_tracker, result
        )

        # 记录 token 使用
        try:
            # 获取使用的模型信息
            quick_model = getattr(task.parameters, "quick_analysis_model", None) if task.parameters else None
            deep_model = getattr(task.parameters, "deep_analysis_model", None) if task.parameters else None

            # 优先使用深度分析模型，如果没有则使用快速分析模型
            model_name = deep_model or quick_model or "qwen-plus"

            # 根据模型名称确定供应商
            provider = get_provider_by_model_name(model_name)

            # 记录使用情况
            await _record_token_usage(service, task, result, provider, model_name)
        except Exception as e:
            logger.error(f"⚠️  记录 token 使用失败: {e}")

        logger.info(f"✅ 分析任务完成: {task.task_id}")
        return result

    except Exception as e:
        logger.error(f"❌ 分析任务失败: {task.task_id} - {e}")

        # 标记失败
        if progress_tracker:
            progress_tracker.mark_failed(str(e))
            await _update_task_status_with_tracker(
                service, task.task_id, AnalysisStatus.FAILED, progress_tracker
            )
        else:
            await _update_task_status(
                service, task.task_id, AnalysisStatus.FAILED, 0, str(e)
            )
        # 返回失败结果
        return AnalysisResult(
            analysis_id=str(uuid.uuid4()),
            summary="",
            recommendation="",
            confidence_score=0.0,
            risk_level="未知",
            key_points=[],
            detailed_analysis=None,
            charts=[],
            tokens_used=0,
            execution_time=0.0,
            error_message=str(e),
            model_info=None,
        )
    finally:
        # 清理进度跟踪器缓存
        service._cleanup_progress_tracker(task.task_id)


async def submit_single_analysis(
    service: "AnalysisAPIService", user_id: str, request: SingleAnalysisRequest
) -> Dict[str, Any]:
    """提交单股分析任务"""
    try:
        logger.info(f"📝 开始提交单股分析任务")
        logger.info(f"👤 用户ID: {user_id} (类型: {type(user_id)})")

        # 获取股票代码
        stock_symbol = request.get_symbol()
        logger.info(f"📊 股票代码: {stock_symbol}")
        logger.info(f"⚙️ 分析参数: {request.parameters}")

        # 生成任务ID
        task_id = str(uuid.uuid4())
        logger.info(f"🆔 生成任务ID: {task_id}")

        # 转换用户ID
        converted_user_id = service._convert_user_id(user_id)
        logger.info(
            f"🔄 转换后的用户ID: {converted_user_id} (类型: {type(converted_user_id)})"
        )

        # 创建分析任务
        logger.info(f"🏗️ 开始创建AnalysisTask对象...")

        # 读取合并后的系统设置
        try:
            effective_settings = await config_provider.get_effective_system_settings()
        except Exception:
            effective_settings = {}

        # 填充分析参数中的模型
        params = request.parameters or AnalysisParameters()
        if not getattr(params, "quick_analysis_model", None):
            params.quick_analysis_model = effective_settings.get(
                "quick_analysis_model", "qwen-turbo"
            )
        if not getattr(params, "deep_analysis_model", None):
            params.deep_analysis_model = effective_settings.get(
                "deep_analysis_model", "qwen-max"
            )

        # 应用系统级并发与可见性超时
        try:
            service.queue_service.user_concurrent_limit = int(
                effective_settings.get(
                    "max_concurrent_tasks", DEFAULT_USER_CONCURRENT_LIMIT
                )
            )
            service.queue_service.global_concurrent_limit = int(
                effective_settings.get(
                    "max_concurrent_tasks", GLOBAL_CONCURRENT_LIMIT
                )
            )
            service.queue_service.visibility_timeout = int(
                effective_settings.get(
                    "default_analysis_timeout", VISIBILITY_TIMEOUT_SECONDS
                )
            )
        except Exception:
            pass

        task = AnalysisTask(
            task_id=task_id,
            user_id=converted_user_id,
            symbol=stock_symbol,
            stock_code=stock_symbol,
            parameters=params,
            status=AnalysisStatus.PENDING,
        )
        logger.info(f"✅ AnalysisTask对象创建成功")

        # 保存任务到数据库
        logger.info(f"💾 开始保存任务到数据库...")
        db = get_mongo_db()
        task_dict = task.model_dump(by_alias=True)
        logger.info(f"📄 任务字典: {task_dict}")
        await db.analysis_tasks.insert_one(task_dict)
        logger.info(f"✅ 任务已保存到数据库")

        # 单股分析：直接在后台执行
        logger.info(f"🚀 开始在后台执行分析任务...")

        # 创建后台任务，不等待完成
        background_task = asyncio.create_task(_execute_single_analysis_async(service, task))

        # 不等待任务完成，让它在后台运行
        logger.info(f"✅ 后台任务已启动，任务ID: {task_id}")

        logger.info(f"🎉 单股分析任务提交完成: {task_id} - {stock_symbol}")

        return {
            "task_id": task_id,
            "symbol": stock_symbol,
            "stock_code": stock_symbol,
            "status": AnalysisStatus.PENDING,
            "message": "任务已在后台启动",
        }

    except Exception as e:
        logger.error(f"提交单股分析任务失败: {e}")
        raise


async def submit_batch_analysis(
    service: "AnalysisAPIService", user_id: str, request: BatchAnalysisRequest
) -> Dict[str, Any]:
    """提交批量分析任务"""
    try:
        # 生成批次ID
        batch_id = str(uuid.uuid4())

        # 转换用户ID
        converted_user_id = service._convert_user_id(user_id)

        # 读取系统设置
        try:
            effective_settings = await config_provider.get_effective_system_settings()
        except Exception:
            effective_settings = {}

        params = request.parameters or AnalysisParameters()
        if not getattr(params, "quick_analysis_model", None):
            params.quick_analysis_model = effective_settings.get(
                "quick_analysis_model", "qwen-turbo"
            )
        if not getattr(params, "deep_analysis_model", None):
            params.deep_analysis_model = effective_settings.get(
                "deep_analysis_model", "qwen-max"
            )

        try:
            service.queue_service.user_concurrent_limit = int(
                effective_settings.get(
                    "max_concurrent_tasks", DEFAULT_USER_CONCURRENT_LIMIT
                )
            )
            service.queue_service.global_concurrent_limit = int(
                effective_settings.get(
                    "max_concurrent_tasks", GLOBAL_CONCURRENT_LIMIT
                )
            )
            service.queue_service.visibility_timeout = int(
                effective_settings.get(
                    "default_analysis_timeout", VISIBILITY_TIMEOUT_SECONDS
                )
            )
        except Exception:
            pass

        # 创建批次记录
        stock_symbols = request.get_symbols()

        batch = AnalysisBatch(
            batch_id=batch_id,
            user_id=converted_user_id,
            title=request.title,
            description=request.description,
            total_tasks=len(stock_symbols),
            parameters=params,
            status=BatchStatus.PENDING,
        )

        # 创建任务列表
        tasks = []
        for symbol in stock_symbols:
            task_id = str(uuid.uuid4())
            task = AnalysisTask(
                task_id=task_id,
                batch_id=batch_id,
                user_id=converted_user_id,
                symbol=symbol,
                stock_code=symbol,
                parameters=batch.parameters,
                status=AnalysisStatus.PENDING,
            )
            tasks.append(task)

        # 保存到数据库
        db = get_mongo_db()
        await db.analysis_batches.insert_one(batch.dict(by_alias=True))
        await db.analysis_tasks.insert_many(
            [task.dict(by_alias=True) for task in tasks]
        )

        # 提交任务到队列
        for task in tasks:
            queue_params = task.parameters.dict() if task.parameters else {}

            queue_params.update(
                {
                    "task_id": task.task_id,
                    "symbol": task.symbol,
                    "stock_code": task.symbol,
                    "user_id": str(task.user_id),
                    "batch_id": task.batch_id,
                    "created_at": task.created_at.isoformat()
                    if task.created_at
                    else None,
                }
            )

            await service.queue_service.enqueue_task(
                user_id=str(converted_user_id),
                symbol=task.symbol,
                params=queue_params,
                batch_id=task.batch_id,
            )

        logger.info(f"批量分析任务已提交: {batch_id} - {len(tasks)}个股票")

        return {
            "batch_id": batch_id,
            "total_tasks": len(tasks),
            "status": BatchStatus.PENDING,
            "message": f"已提交{len(tasks)}个分析任务到队列",
        }

    except Exception as e:
        logger.error(f"提交批量分析任务失败: {e}")
        raise


async def execute_analysis_task(
    service: "AnalysisAPIService",
    task: AnalysisTask,
    progress_callback=None,
) -> AnalysisResult:
    """执行单个分析任务（队列系统专用）"""
    return await _execute_single_analysis_async(service, task)
