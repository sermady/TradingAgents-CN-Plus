# -*- coding: utf-8 -*-
"""
任务管理模块

提供任务查询、暂停、恢复、手动触发等功能
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from apscheduler.job import Job

from tradingagents.utils.logging_manager import get_logger
from app.utils.error_handler import async_handle_errors_empty_list
from .utils import get_utc8_now

logger = get_logger(__name__)


class JobManagerMixin:
    """任务管理混入类"""

    # 这些属性由核心类提供
    scheduler: Any
    _get_db: Any
    _job_to_dict: Any
    _get_job_metadata: Any
    _record_job_action: Any
    _record_job_execution: Any

    @async_handle_errors_empty_list(error_message="获取任务列表失败")
    async def list_jobs(self) -> List[Dict[str, Any]]:
        """
        获取所有定时任务列表

        Returns:
            任务列表
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            job_dict = self._job_to_dict(job)
            # 获取任务元数据（触发器名称和备注）
            metadata = await self._get_job_metadata(job.id)
            if metadata:
                job_dict["display_name"] = metadata.get("display_name")
                job_dict["description"] = metadata.get("description")
            jobs.append(job_dict)

        logger.info(f"📋 获取到 {len(jobs)} 个定时任务")
        return jobs

    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务详情

        Args:
            job_id: 任务ID

        Returns:
            任务详情，如果不存在则返回None
        """
        job = self.scheduler.get_job(job_id)
        if job:
            job_dict = self._job_to_dict(job, include_details=True)
            # 获取任务元数据
            metadata = await self._get_job_metadata(job_id)
            if metadata:
                job_dict["display_name"] = metadata.get("display_name")
                job_dict["description"] = metadata.get("description")
            return job_dict
        return None

    async def _execute_simple_job_action(
        self,
        job_id: str,
        action: str,
        scheduler_method,
        success_log: str,
        error_log_prefix: str
    ) -> bool:
        """执行简单的任务操作（暂停/恢复等）

        用于封装 pause_job、resume_job 等简单操作的通用逻辑，
        统一处理成功/失败日志记录和操作历史。

        Args:
            job_id: 任务ID
            action: 操作名称（如 "pause", "resume"）
            scheduler_method: 调度器方法（如 self.scheduler.pause_job）
            success_log: 成功日志消息模板（如 "任务 {job_id} 已暂停"）
            error_log_prefix: 错误日志前缀（如 "暂停任务"）

        Returns:
            bool: 是否成功
        """
        try:
            scheduler_method(job_id)
            logger.info(success_log.format(job_id=job_id))
            await self._record_job_action(job_id, action, "success")
            return True
        except Exception as e:
            logger.error(f"❌ {error_log_prefix} {job_id} 失败: {e}")
            await self._record_job_action(job_id, action, "failed", str(e))
            return False

    async def pause_job(self, job_id: str) -> bool:
        """
        暂停任务

        Args:
            job_id: 任务ID

        Returns:
            是否成功
        """
        return await self._execute_simple_job_action(
            job_id=job_id,
            action="pause",
            scheduler_method=self.scheduler.pause_job,
            success_log="⏸️ 任务 {job_id} 已暂停",
            error_log_prefix="暂停任务"
        )

    async def resume_job(self, job_id: str) -> bool:
        """
        恢复任务

        Args:
            job_id: 任务ID

        Returns:
            是否成功
        """
        return await self._execute_simple_job_action(
            job_id=job_id,
            action="resume",
            scheduler_method=self.scheduler.resume_job,
            success_log="▶️ 任务 {job_id} 已恢复",
            error_log_prefix="恢复任务"
        )

    async def trigger_job(self, job_id: str, kwargs: Optional[Dict[str, Any]] = None) -> bool:
        """
        手动触发任务执行

        注意：如果任务处于暂停状态，会先临时恢复任务，执行一次后不会自动暂停

        Args:
            job_id: 任务ID
            kwargs: 传递给任务函数的关键字参数（可选）

        Returns:
            是否成功
        """
        try:
            job = self.scheduler.get_job(job_id)
            if not job:
                logger.error(f"❌ 任务 {job_id} 不存在")
                return False

            # 检查任务是否被暂停（next_run_time 为 None 表示暂停）
            was_paused = job.next_run_time is None
            if was_paused:
                logger.warning(f"⚠️ 任务 {job_id} 处于暂停状态，临时恢复以执行一次")
                self.scheduler.resume_job(job_id)
                # 重新获取 job 对象（恢复后状态已改变）
                job = self.scheduler.get_job(job_id)
                logger.info(f"✅ 任务 {job_id} 已临时恢复")

            # 如果提供了 kwargs，合并到任务的 kwargs 中
            if kwargs:
                # 获取任务原有的 kwargs
                original_kwargs = job.kwargs.copy() if job.kwargs else {}
                # 合并新的 kwargs
                merged_kwargs = {**original_kwargs, **kwargs}
                # 修改任务的 kwargs
                job.modify(kwargs=merged_kwargs)
                logger.info(f"📝 任务 {job_id} 参数已更新: {kwargs}")

            # 手动触发任务 - 使用带时区的当前时间
            now = datetime.now(timezone.utc)
            job.modify(next_run_time=now)
            logger.info(f"🚀 手动触发任务 {job_id} (next_run_time={now}, was_paused={was_paused}, kwargs={kwargs})")

            # 记录操作历史
            action_note = f"手动触发执行 (暂停状态: {was_paused}"
            if kwargs:
                action_note += f", 参数: {kwargs}"
            action_note += ")"
            await self._record_job_action(job_id, "trigger", "success", action_note)

            # 立即创建一个"running"状态的执行记录，让用户能看到任务正在执行
            await self._record_job_execution(
                job_id=job_id,
                status="running",
                scheduled_time=get_utc8_now(),
                progress=0,
                is_manual=True
            )

            return True
        except Exception as e:
            logger.error(f"❌ 触发任务 {job_id} 失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            await self._record_job_action(job_id, "trigger", "failed", str(e))
            return False
