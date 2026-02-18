# -*- coding: utf-8 -*-
"""
事件处理模块

提供APScheduler事件监听和任务执行记录功能
"""

import asyncio
from typing import Any
from datetime import datetime, timedelta

from apscheduler.events import (
    EVENT_JOB_EXECUTED,
    EVENT_JOB_ERROR,
    EVENT_JOB_MISSED,
    JobExecutionEvent
)

from tradingagents.utils.logging_manager import get_logger
from .utils import get_utc8_now

logger = get_logger(__name__)


class EventHandlerMixin:
    """事件处理混入类"""

    # 这些属性由核心类提供
    scheduler: Any
    _get_db: Any

    def _setup_event_listeners(self):
        """设置APScheduler事件监听器"""
        # 监听任务执行成功事件
        self.scheduler.add_listener(
            self._on_job_executed,
            EVENT_JOB_EXECUTED
        )

        # 监听任务执行失败事件
        self.scheduler.add_listener(
            self._on_job_error,
            EVENT_JOB_ERROR
        )

        # 监听任务错过执行事件
        self.scheduler.add_listener(
            self._on_job_missed,
            EVENT_JOB_MISSED
        )

        logger.info("✅ APScheduler事件监听器已设置")

        # 添加定时任务，检测僵尸任务
        self.scheduler.add_job(
            self._check_zombie_tasks,
            'interval',
            minutes=5,
            id='check_zombie_tasks',
            name='检测僵尸任务',
            replace_existing=True
        )
        logger.info("✅ 僵尸任务检测定时任务已添加")

    async def _check_zombie_tasks(self):
        """检测僵尸任务（长时间处于running状态的任务）"""
        try:
            db = self._get_db()

            # 查找超过30分钟仍处于running状态的任务
            threshold_time = get_utc8_now() - timedelta(minutes=30)

            zombie_tasks = await db.scheduler_executions.find({
                "status": "running",
                "timestamp": {"$lt": threshold_time}
            }).to_list(length=100)

            for task in zombie_tasks:
                # 更新为failed状态
                await db.scheduler_executions.update_one(
                    {"_id": task["_id"]},
                    {
                        "$set": {
                            "status": "failed",
                            "error_message": "任务执行超时或进程异常终止",
                            "updated_at": get_utc8_now()
                        }
                    }
                )
                logger.warning(f"⚠️ 检测到僵尸任务: {task.get('job_name', task.get('job_id'))}")

            if zombie_tasks:
                logger.info(f"✅ 已标记 {len(zombie_tasks)} 个僵尸任务为失败状态")

        except Exception as e:
            logger.error(f"❌ 检测僵尸任务失败: {e}")

    def _on_job_executed(self, event: JobExecutionEvent):
        """任务执行成功回调"""
        # 计算执行时间
        execution_time = None
        if event.scheduled_run_time:
            now = datetime.now(event.scheduled_run_time.tzinfo)
            execution_time = (now - event.scheduled_run_time).total_seconds()

        asyncio.create_task(self._record_job_execution(
            job_id=event.job_id,
            status="success",
            scheduled_time=event.scheduled_run_time,
            execution_time=execution_time,
            return_value=str(event.retval) if event.retval else None,
            progress=100
        ))

    def _on_job_error(self, event: JobExecutionEvent):
        """任务执行失败回调"""
        # 计算执行时间
        execution_time = None
        if event.scheduled_run_time:
            now = datetime.now(event.scheduled_run_time.tzinfo)
            execution_time = (now - event.scheduled_run_time).total_seconds()

        asyncio.create_task(self._record_job_execution(
            job_id=event.job_id,
            status="failed",
            scheduled_time=event.scheduled_run_time,
            execution_time=execution_time,
            error_message=str(event.exception) if event.exception else None,
            traceback=event.traceback if hasattr(event, 'traceback') else None,
            progress=None
        ))

    def _on_job_missed(self, event: JobExecutionEvent):
        """任务错过执行回调"""
        asyncio.create_task(self._record_job_execution(
            job_id=event.job_id,
            status="missed",
            scheduled_time=event.scheduled_run_time,
            progress=None
        ))

    async def _record_job_execution(
        self,
        job_id: str,
        status: str,
        scheduled_time: datetime = None,
        execution_time: float = None,
        return_value: str = None,
        error_message: str = None,
        traceback: str = None,
        progress: int = None,
        is_manual: bool = False
    ):
        """
        记录任务执行历史

        Args:
            job_id: 任务ID
            status: 状态 (running/success/failed/missed)
            scheduled_time: 计划执行时间
            execution_time: 实际执行时长（秒）
            return_value: 返回值
            error_message: 错误信息
            traceback: 错误堆栈
            progress: 执行进度（0-100）
            is_manual: 是否手动触发
        """
        try:
            db = self._get_db()

            # 获取任务名称
            job = self.scheduler.get_job(job_id)
            job_name = job.name if job else job_id

            # 如果是完成状态，先查找是否有对应的 running 记录
            if status in ["success", "failed"]:
                five_minutes_ago = get_utc8_now() - timedelta(minutes=5)
                existing_record = await db.scheduler_executions.find_one(
                    {
                        "job_id": job_id,
                        "status": "running",
                        "timestamp": {"$gte": five_minutes_ago}
                    },
                    sort=[("timestamp", -1)]
                )

                if existing_record:
                    # 更新现有记录
                    update_data = {
                        "status": status,
                        "execution_time": execution_time,
                        "updated_at": get_utc8_now()
                    }

                    if return_value:
                        update_data["return_value"] = return_value
                    if error_message:
                        update_data["error_message"] = error_message
                    if traceback:
                        update_data["traceback"] = traceback
                    if progress is not None:
                        update_data["progress"] = progress

                    await db.scheduler_executions.update_one(
                        {"_id": existing_record["_id"]},
                        {"$set": update_data}
                    )

                    if status == "success":
                        logger.info(f"✅ [任务执行] {job_name} 执行成功")
                    elif status == "failed":
                        logger.error(f"❌ [任务执行] {job_name} 执行失败: {error_message}")

                    return

            # 如果没有找到 running 记录，插入新记录
            scheduled_time_naive = None
            if scheduled_time:
                if scheduled_time.tzinfo is not None:
                    from .utils import UTC_8
                    scheduled_time_naive = scheduled_time.astimezone(UTC_8).replace(tzinfo=None)
                else:
                    scheduled_time_naive = scheduled_time

            execution_record = {
                "job_id": job_id,
                "job_name": job_name,
                "status": status,
                "scheduled_time": scheduled_time_naive,
                "execution_time": execution_time,
                "timestamp": get_utc8_now(),
                "is_manual": is_manual
            }

            if return_value:
                execution_record["return_value"] = return_value
            if error_message:
                execution_record["error_message"] = error_message
            if traceback:
                execution_record["traceback"] = traceback
            if progress is not None:
                execution_record["progress"] = progress

            await db.scheduler_executions.insert_one(execution_record)

            if status == "success":
                logger.info(f"✅ [任务执行] {job_name} 执行成功")
            elif status == "failed":
                logger.error(f"❌ [任务执行] {job_name} 执行失败: {error_message}")
            elif status == "missed":
                logger.warning(f"⚠️ [任务执行] {job_name} 错过执行时间")
            elif status == "running":
                trigger_type = "手动触发" if is_manual else "自动触发"
                logger.info(f"🔄 [任务执行] {job_name} 开始执行 ({trigger_type})")

        except Exception as e:
            logger.error(f"❌ 记录任务执行历史失败: {e}")

    async def _record_job_action(
        self,
        job_id: str,
        action: str,
        status: str,
        error_message: str = None
    ):
        """
        记录任务操作历史

        Args:
            job_id: 任务ID
            action: 操作类型 (pause/resume/trigger)
            status: 状态 (success/failed)
            error_message: 错误信息
        """
        try:
            db = self._get_db()
            await db.scheduler_history.insert_one({
                "job_id": job_id,
                "action": action,
                "status": status,
                "error_message": error_message,
                "timestamp": get_utc8_now()
            })
        except Exception as e:
            logger.error(f"❌ 记录任务操作历史失败: {e}")
