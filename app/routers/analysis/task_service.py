# -*- coding: utf-8 -*-
"""
任务管理服务

提取自 analysis.py 的任务管理逻辑
"""
from typing import Dict, Any, Optional
import logging
import uuid

from app.routers.analysis.schemas import (
    SingleAnalysisRequest,
    BatchAnalysisRequest,
)

logger = logging.getLogger(__name__)


class TaskService:
    """任务管理服务"""

    def __init__(self):
        self._queue_service = None
        self._analysis_service = None

    @property
    def queue_service(self):
        from app.services.queue_service import get_queue_service
        if self._queue_service is None:
            self._queue_service = get_queue_service()
        return self._queue_service

    @property
    def analysis_service(self):
        from app.services.simple_analysis_service import get_simple_analysis_service
        if self._analysis_service is None:
            self._analysis_service = get_simple_analysis_service()
        return self._analysis_service

    async def submit_single_task(
        self,
        request: SingleAnalysisRequest,
        user: Dict[str, Any],
    ) -> Dict[str, Any]:
        """提交单股分析任务"""
        try:
            symbol = request.get_symbol()
            if not symbol:
                raise ValueError("股票代码不能为空")

            logger.info(f"提交单股分析任务: {symbol}")
            logger.info(f"用户: {user.get('id')}")

            result = await self.analysis_service.create_analysis_task(
                user_id=user["id"],
                request=request,
            )

            task_id = result.get("task_id")
            logger.info(f"分析任务已创建: {task_id}")

            return {
                "success": True,
                "data": result,
                "message": "分析任务已提交",
            }

        except ValueError as e:
            logger.error(f"参数验证失败: {e}")
            raise
        except Exception as e:
            logger.error(f"提交单股分析任务失败: {e}", exc_info=True)
            raise


_task_service: Optional[TaskService] = None


def get_task_service() -> TaskService:
    """获取任务管理服务实例（单例模式）"""
    global _task_service
    if _task_service is None:
        _task_service = TaskService()
    return _task_service
