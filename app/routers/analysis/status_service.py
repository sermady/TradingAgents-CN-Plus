# -*- coding: utf-8 -*-
"""
任务状态查询服务

提取自 analysis.py 的状态查询逻辑，包括：
- 任务状态查询
- 任务结果获取
- 从内存/MongoDB恢复数据
"""
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from app.routers.analysis.schemas import TaskStatusResponse, TaskResultResponse
from app.services.simple_analysis_service import get_simple_analysis_service

logger = logging.getLogger(__name__)


class StatusService:
    """任务状态查询服务"""

    def __init__(self):
        self._analysis_service = None

    @property
    def analysis_service(self):
        from app.services.simple_analysis_service import get_simple_analysis_service
        if self._analysis_service is None:
            self._analysis_service = get_simple_analysis_service()
        return self._analysis_service

    async def get_task_status(
        self,
        task_id: str,
        user: Optional[Dict[str, Any]] = None,
    ) -> Optional[TaskStatusResponse]:
        """获取任务状态"""
        try:
            logger.info(f"查询任务状态: {task_id}")

            # 1. 尝试从内存获取
            result = await self.analysis_service.get_task_status(task_id)

            if result:
                logger.info(f"从内存获取到任务状态")
                return TaskStatusResponse(**result)

            # 2. 尝试从 MongoDB 获取
            from app.core.database import get_mongo_db
            db = get_mongo_db()

            # 从 analysis_tasks 查找（进行中的任务）
            task_result = await db.analysis_tasks.find_one({"task_id": task_id})

            if task_result:
                logger.info(f"从 MongoDB analysis_tasks 找到任务")
                return self._build_status_from_db(task_result, "mongodb_tasks")

            # 从 analysis_reports 查找（已完成的任务）
            report_result = await db.analysis_reports.find_one({"task_id": task_id})

            if report_result:
                logger.info(f"从 MongoDB analysis_reports 找到任务")
                return self._build_status_from_db(report_result, "mongodb_reports")

            logger.warning(f"未找到任务: {task_id}")
            return None

        except Exception as e:
            logger.error(f"获取任务状态失败: {e}", exc_info=True)
            raise

    async def get_task_result(
        self,
        task_id: str,
        user: Optional[Dict[str, Any]] = None,
    ) -> Optional[TaskResultResponse]:
        """获取任务结果"""
        try:
            logger.info(f"获取任务结果: {task_id}")

            # 1. 尝试从内存获取
            task_status = await self.analysis_service.get_task_status(task_id)

            result_data = None
            if task_status and task_status.get("status") == "completed":
                result_data = task_status.get("result_data")
                logger.info(f"从内存获取到结果数据")

            # 2. 尝试从 MongoDB 获取
            if not result_data:
                from app.core.database import get_mongo_db
                db = get_mongo_db()

                mongo_result = await db.analysis_reports.find_one({"task_id": task_id})

                if mongo_result:
                    logger.info(f"从 MongoDB 找到结果")
                    result_data = self._build_result_from_db(mongo_result)

            if not result_data:
                logger.warning(f"未找到任务结果: {task_id}")
                return None

            return TaskResultResponse(**result_data)

        except Exception as e:
            logger.error(f"获取任务结果失败: {e}", exc_info=True)
            raise

    def _build_status_from_db(
        self,
        db_record: Dict[str, Any],
        source: str,
    ) -> TaskStatusResponse:
        """从数据库记录构建状态响应"""
        start_time = db_record.get("started_at") or db_record.get("created_at")
        end_time = db_record.get("completed_at") or db_record.get("updated_at")
        current_time = datetime.utcnow()

        elapsed_time = 0
        if start_time:
            elapsed_time = (current_time - start_time).total_seconds()

        return TaskStatusResponse(
            task_id=db_record.get("task_id"),
            status=db_record.get("status", "unknown"),
            progress=db_record.get("progress", 0),
            message=f"任务{db_record.get('status', 'unknown')}中...",
            current_step=db_record.get("status"),
            start_time=start_time,
            end_time=end_time,
            elapsed_time=elapsed_time,
            remaining_time=0,
            estimated_total_time=0,
            symbol=db_record.get("symbol") or db_record.get("stock_code"),
            stock_code=db_record.get("stock_code"),
            stock_symbol=db_record.get("symbol") or db_record.get("stock_code"),
            analysts=db_record.get("analysts"),
            research_depth=db_record.get("research_depth"),
            source=source,
        )

    def _build_result_from_db(
        self,
        db_record: Dict[str, Any],
    ) -> Dict[str, Any]:
        """从数据库记录构建结果响应"""
        return {
            "analysis_id": db_record.get("analysis_id"),
            "stock_symbol": db_record.get("stock_symbol"),
            "stock_code": db_record.get("stock_symbol"),
            "analysis_date": db_record.get("analysis_date"),
            "summary": db_record.get("summary", ""),
            "recommendation": db_record.get("recommendation", ""),
            "confidence_score": db_record.get("confidence_score", 0.0),
            "risk_level": db_record.get("risk_level", "中等"),
            "key_points": db_record.get("key_points", []),
            "execution_time": db_record.get("execution_time", 0),
            "tokens_used": db_record.get("tokens_used", 0),
            "analysts": db_record.get("analysts", []),
            "research_depth": db_record.get("research_depth", "快速"),
            "reports": db_record.get("reports", {}),
            "created_at": db_record.get("created_at"),
            "updated_at": db_record.get("updated_at"),
            "status": db_record.get("status", "completed"),
            "decision": db_record.get("decision", {}),
            "source": "mongodb",
            "state": db_record.get("state"),
            "detailed_analysis": db_record.get("detailed_analysis"),
        }


_status_service: Optional[StatusService] = None


def get_status_service() -> StatusService:
    """获取状态查询服务实例（单例模式）"""
    global _status_service
    if _status_service is None:
        _status_service = StatusService()
    return _status_service
