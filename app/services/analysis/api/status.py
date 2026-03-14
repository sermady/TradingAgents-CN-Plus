# -*- coding: utf-8 -*-
"""API分析状态更新模块

提供任务状态更新和token使用记录功能。
"""

import logging
from typing import Optional, TYPE_CHECKING

from app.models.analysis import AnalysisStatus, AnalysisResult, AnalysisTask

if TYPE_CHECKING:
    from .core import AnalysisAPIService

logger = logging.getLogger(__name__)


async def _update_task_status(
    service: "AnalysisAPIService",
    task_id: str,
    status: AnalysisStatus,
    progress: int,
    message: Optional[str] = None,
):
    """更新任务状态"""
    from app.services.analysis.status_update_utils import perform_update_task_status

    await perform_update_task_status(task_id, status, progress)


async def _update_task_status_with_tracker(
    service: "AnalysisAPIService",
    task_id: str,
    status: AnalysisStatus,
    progress_tracker,
    result: Optional[AnalysisResult] = None,
):
    """使用进度跟踪器更新任务状态"""
    from app.services.analysis.status_update_utils import (
        perform_update_task_status_with_tracker,
    )

    await perform_update_task_status_with_tracker(
        task_id, status, progress_tracker, result
    )


async def _record_token_usage(
    service: "AnalysisAPIService",
    task: AnalysisTask,
    result: AnalysisResult,
    provider: str,
    model_name: str
):
    """记录 token 使用情况"""
    try:
        # 获取使用的 token 数量
        input_tokens = 0
        output_tokens = result.tokens_used

        # 尝试从详细分析中提取更精确的 token 数据
        if result.detailed_analysis and isinstance(result.detailed_analysis, dict):
            if "input_tokens" in result.detailed_analysis:
                input_tokens = result.detailed_analysis.get("input_tokens", 0)
            if "output_tokens" in result.detailed_analysis:
                output_tokens = result.detailed_analysis.get("output_tokens", 0)

        # 使用计费服务记录使用情况
        success = service.billing_service.record_usage(
            provider=provider,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            session_id=task.task_id,
            analysis_type="stock_analysis",
            stock_code=task.symbol,
        )

        if not success:
            logger.warning("⚠️ 记录 token 使用失败")

    except Exception as e:
        logger.error(f"❌ 记录 token 使用失败: {e}")
