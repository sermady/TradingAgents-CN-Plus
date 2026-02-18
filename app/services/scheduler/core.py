# -*- coding: utf-8 -*-
"""
调度服务核心模块

整合所有功能模块，提供统一的调度服务接口
"""

from typing import Dict, Any, Optional
from datetime import timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.job import Job

from app.core.database import get_mongo_db
from tradingagents.utils.logging_manager import get_logger
from app.utils.error_handler import async_handle_errors_none

from .utils import get_utc8_now
from .job_manager import JobManagerMixin
from .execution_manager import ExecutionManagerMixin
from .event_handlers import EventHandlerMixin

logger = get_logger(__name__)


class TaskCancelledException(Exception):
    """任务被取消异常"""
    pass


class SchedulerService(JobManagerMixin, ExecutionManagerMixin, EventHandlerMixin):
    """
    定时任务管理服务

    整合任务管理、执行记录管理和事件处理功能
    """

    def __init__(self, scheduler: AsyncIOScheduler):
        """
        初始化服务

        Args:
            scheduler: APScheduler调度器实例
        """
        self.scheduler = scheduler
        self.db = None

        # 添加事件监听器，监控任务执行
        self._setup_event_listeners()

    def _get_db(self):
        """获取数据库连接"""
        if self.db is None:
            self.db = get_mongo_db()
        return self.db

    async def get_stats(self) -> Dict[str, Any]:
        """
        获取调度器统计信息

        Returns:
            统计信息
        """
        jobs = self.scheduler.get_jobs()

        total = len(jobs)
        running = sum(1 for job in jobs if job.next_run_time is not None)
        paused = total - running

        return {
            "total_jobs": total,
            "running_jobs": running,
            "paused_jobs": paused,
            "scheduler_running": self.scheduler.running,
            "scheduler_state": self.scheduler.state
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        调度器健康检查

        Returns:
            健康状态
        """
        return {
            "status": "healthy" if self.scheduler.running else "stopped",
            "running": self.scheduler.running,
            "state": self.scheduler.state,
            "timestamp": get_utc8_now().isoformat()
        }

    def _job_to_dict(self, job: Job, include_details: bool = False) -> Dict[str, Any]:
        """
        将Job对象转换为字典

        Args:
            job: Job对象
            include_details: 是否包含详细信息

        Returns:
            字典表示
        """
        result = {
            "id": job.id,
            "name": job.name or job.id,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "paused": job.next_run_time is None,
            "trigger": str(job.trigger),
        }

        if include_details:
            result.update({
                "func": f"{job.func.__module__}.{job.func.__name__}",
                "args": job.args,
                "kwargs": job.kwargs,
                "misfire_grace_time": job.misfire_grace_time,
                "max_instances": job.max_instances,
            })

        return result

    @async_handle_errors_none(error_message="获取任务元数据失败")
    async def _get_job_metadata(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务元数据（触发器名称和备注）

        Args:
            job_id: 任务ID

        Returns:
            元数据字典，如果不存在则返回None
        """
        db = self._get_db()
        metadata = await db.scheduler_metadata.find_one({"job_id": job_id})
        if metadata:
            metadata.pop("_id", None)
            return metadata
        return None

    @async_handle_errors_none(error_message="更新任务元数据失败")
    async def update_job_metadata(
        self,
        job_id: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None
    ) -> bool:
        """
        更新任务元数据

        Args:
            job_id: 任务ID
            display_name: 触发器名称
            description: 备注

        Returns:
            是否成功
        """
        # 检查任务是否存在
        job = self.scheduler.get_job(job_id)
        if not job:
            logger.error(f"❌ 任务 {job_id} 不存在")
            return False

        db = self._get_db()
        update_data = {
            "job_id": job_id,
            "updated_at": get_utc8_now()
        }

        if display_name is not None:
            update_data["display_name"] = display_name
        if description is not None:
            update_data["description"] = description

        # 使用 upsert 更新或插入
        await db.scheduler_metadata.update_one(
            {"job_id": job_id},
            {"$set": update_data},
            upsert=True
        )

        logger.info(f"✅ 任务 {job_id} 元数据已更新")
        return True
