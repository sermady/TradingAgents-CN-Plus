# -*- coding: utf-8 -*-
"""
Analysis Progress Manager
封装分析进度追踪相关的业务逻辑
"""

import logging
from typing import Optional, Dict, Any
from app.services.redis_progress_tracker import RedisProgressTracker, AnalysisStep
from app.core.database import get_redis_client

logger = logging.getLogger(__name__)


class ProgressManager:
    """
    分析进度管理器

    负责管理分析任务的进度追踪,包括:
    - 创建进度跟踪器
    - 更新进度
    - 获取进度信息
    - 销毁进度跟踪器
    """

    def __init__(self):
        """初始化进度管理器"""
        self._trackers: Dict[str, RedisProgressTracker] = {}
        self._redis_client = get_redis_client()

    def create_tracker(
        self,
        task_id: str,
        analysts: list,
        research_depth: str,
        llm_provider: str = "dashscope",
    ) -> RedisProgressTracker:
        """
        创建进度跟踪器

        Args:
            task_id: 任务ID
            analysts: 分析师列表
            research_depth: 研究深度
            llm_provider: LLM提供商

        Returns:
            RedisProgressTracker实例
        """
        tracker = RedisProgressTracker(
            task_id=task_id,
            analysts=analysts,
            research_depth=research_depth,
            llm_provider=llm_provider,
        )

        # 缓存跟踪器
        self._trackers[task_id] = tracker

        logger.info(
            f"✅ 创建进度跟踪器: {task_id} (分析师: {len(analysts)}, 深度: {research_depth})"
        )
        return tracker

    def get_tracker(self, task_id: str) -> Optional[RedisProgressTracker]:
        """
        获取进度跟踪器

        Args:
            task_id: 任务ID

        Returns:
            RedisProgressTracker实例,如果不存在则返回None
        """
        return self._trackers.get(task_id)

    def update_progress(self, task_id: str, message: str):
        """
        更新分析进度

        Args:
            task_id: 任务ID
            message: 进度消息
        """
        tracker = self.get_tracker(task_id)
        if tracker:
            tracker.update_progress(message)
        else:
            logger.warning(f"⚠️ 进度跟踪器不存在: {task_id}")

    def complete_analysis(self, task_id: str, success: bool = True, reason: str = ""):
        """
        标记分析完成

        Args:
            task_id: 任务ID
            success: 是否成功
            reason: 失败原因(可选)
        """
        tracker = self.get_tracker(task_id)
        if tracker:
            if success:
                tracker.mark_completed()
            else:
                tracker.mark_failed(reason)
        else:
            logger.warning(f"⚠️ 进度跟踪器不存在: {task_id}")

    def destroy_tracker(self, task_id: str):
        """
        销毁进度跟踪器

        Args:
            task_id: 任务ID
        """
        if task_id in self._trackers:
            del self._trackers[task_id]
            logger.info(f"🗑️ 销毁进度跟踪器: {task_id}")

    def cleanup_old_trackers(self, max_age_hours: int = 24):
        """
        清理旧的进度跟踪器

        Args:
            max_age_hours: 最大保留时间(小时)
        """
        import time
        from datetime import datetime, timedelta

        current_time = datetime.now()
        expired_ids = []

        for task_id, tracker in self._trackers.items():
            # 检查是否超时(使用progress_data中的start_time)
            if (
                hasattr(tracker, "progress_data")
                and "start_time" in tracker.progress_data
            ):
                start_time = datetime.fromtimestamp(tracker.progress_data["start_time"])
                age = current_time - start_time
                if age > timedelta(hours=max_age_hours):
                    expired_ids.append(task_id)

        # 销毁过期的跟踪器
        for task_id in expired_ids:
            self.destroy_tracker(task_id)

        if expired_ids:
            logger.info(f"🗑️ 清理了 {len(expired_ids)} 个过期进度跟踪器")


# 全局进度管理器实例(延迟初始化)
_progress_manager: Optional[ProgressManager] = None


def get_progress_manager() -> ProgressManager:
    """获取全局进度管理器实例"""
    global _progress_manager
    if _progress_manager is None:
        _progress_manager = ProgressManager()
    return _progress_manager
