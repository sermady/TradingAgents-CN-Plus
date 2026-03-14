# -*- coding: utf-8 -*-
"""API分析服务主类

整合所有API分析功能的主服务类。
"""

import logging
from typing import Dict, Any, Optional, Callable

from .core import AnalysisAPIService as CoreAnalysisAPIService
from .batch import (
    submit_single_analysis,
    submit_batch_analysis,
    execute_analysis_task,
    _execute_single_analysis_async,
)

logger = logging.getLogger(__name__)


class AnalysisAPIService(CoreAnalysisAPIService):
    """
    股票分析API服务类

    提供完整的股票分析API功能，包括：
    - 单股分析提交
    - 批量分析提交
    - 任务执行管理
    - 进度跟踪
    """

    async def submit_single_analysis(
        self, user_id: str, request
    ) -> Dict[str, Any]:
        """提交单股分析任务"""
        return await submit_single_analysis(self, user_id, request)

    async def submit_batch_analysis(
        self, user_id: str, request
    ) -> Dict[str, Any]:
        """提交批量分析任务"""
        return await submit_batch_analysis(self, user_id, request)

    async def execute_analysis_task(
        self,
        task,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ):
        """执行单个分析任务（队列系统专用）"""
        return await execute_analysis_task(self, task, progress_callback)

    async def _execute_single_analysis_async(self, task):
        """异步执行单股分析任务"""
        return await _execute_single_analysis_async(self, task)


# 全局分析服务实例（延迟初始化）
_analysis_api_service_instance: Optional[AnalysisAPIService] = None


def get_analysis_api_service() -> AnalysisAPIService:
    """获取API分析服务实例（延迟初始化）"""
    global _analysis_api_service_instance
    if _analysis_api_service_instance is None:
        _analysis_api_service_instance = AnalysisAPIService()
    return _analysis_api_service_instance


# 向后兼容
get_analysis_service = get_analysis_api_service
AnalysisService = AnalysisAPIService
