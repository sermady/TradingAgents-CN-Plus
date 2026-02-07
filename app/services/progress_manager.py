# -*- coding: utf-8 -*-
"""
Analysis Progress Manager
封装分析进度追踪相关的业务逻辑

借鉴上游 TradingAgents 项目设计思想:
- 统一状态转换逻辑 (update_analyst_statuses)
- 标准化分析师顺序 (ANALYST_ORDER)
- 支持消息去重
"""

import logging
from typing import Optional, Dict, Any, List
from app.services.redis_progress_tracker import RedisProgressTracker, AnalysisStep
from app.core.database import get_redis_client
from app.services.progress.constants import (
    ANALYST_ORDER,
    ANALYST_DISPLAY_NAMES,
    ANALYST_REPORT_MAP,
    AnalystStatus,
)

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

    def update_analyst_statuses(
        self,
        task_id: str,
        analyst_reports: Dict[str, Any],
        selected_analysts: List[str],
    ) -> Dict[str, str]:
        """
        统一更新所有分析师状态

        借鉴上游 TradingAgents 项目设计思想:
        - 根据报告存在性自动判断状态
        - 第一个无报告的分析师设为 in_progress
        - 其余无报告的分析师设为 pending
        - 有报告的分析师设为 completed

        Args:
            task_id: 任务ID
            analyst_reports: 分析师报告字典 {report_key: report_content}
            selected_analysts: 选中的分析师列表

        Returns:
            Dict[str, str]: 分析师状态映射 {analyst_key: status}
        """
        tracker = self.get_tracker(task_id)
        if not tracker:
            logger.warning(f"⚠️ 更新分析师状态失败: 跟踪器不存在 {task_id}")
            return {}

        status_map = {}
        found_active = False

        # 按照 ANALYST_ORDER 顺序处理，确保状态一致性
        selected_set = set(selected_analysts)

        for analyst_key in ANALYST_ORDER:
            if analyst_key not in selected_set:
                continue

            report_key = ANALYST_REPORT_MAP.get(analyst_key)
            has_report = bool(report_key and analyst_reports.get(report_key))
            analyst_name = ANALYST_DISPLAY_NAMES.get(analyst_key, analyst_key)

            if has_report:
                # 有报告 = 已完成
                status_map[analyst_key] = AnalystStatus.COMPLETED
                tracker.update_agent_status(analyst_name, AnalystStatus.COMPLETED)
            elif not found_active:
                # 第一个无报告的 = 执行中
                status_map[analyst_key] = AnalystStatus.IN_PROGRESS
                tracker.update_agent_status(analyst_name, AnalystStatus.IN_PROGRESS)
                found_active = True
            else:
                # 其余无报告的 = 等待中
                status_map[analyst_key] = AnalystStatus.PENDING
                tracker.update_agent_status(analyst_name, AnalystStatus.PENDING)

        # 当所有分析师完成时，更新研究团队状态
        if not found_active and selected_analysts:
            logger.info(f"✅ 所有分析师完成，准备进入研究团队阶段: {task_id}")
            # 可以在这里触发研究团队状态更新

        logger.debug(f"📊 分析师状态更新: {task_id} - {status_map}")
        return status_map

    def normalize_analyst_order(self, selected_analysts: List[str]) -> List[str]:
        """
        标准化分析师顺序

        按照 ANALYST_ORDER 中定义的顺序返回分析师列表，
        确保执行顺序的一致性。

        Args:
            selected_analysts: 选中的分析师列表

        Returns:
            List[str]: 按标准顺序排列的分析师列表
        """
        selected_set = set(selected_analysts)
        ordered = [a for a in ANALYST_ORDER if a in selected_set]

        # 检查是否有未定义的分析师
        undefined = selected_set - set(ANALYST_ORDER)
        if undefined:
            logger.warning(f"⚠️ 未定义的分析师类型: {undefined}")
            ordered.extend(sorted(undefined))

        return ordered

    def get_next_pending_analyst(
        self, status_map: Dict[str, str], selected_analysts: List[str]
    ) -> Optional[str]:
        """
        获取下一个等待中的分析师

        Args:
            status_map: 分析师状态映射
            selected_analysts: 选中的分析师列表

        Returns:
            Optional[str]: 下一个等待中的分析师key，如果没有则返回None
        """
        for analyst in self.normalize_analyst_order(selected_analysts):
            if status_map.get(analyst) == AnalystStatus.PENDING:
                return analyst
        return None


# 全局进度管理器实例(延迟初始化)
_progress_manager: Optional[ProgressManager] = None


def get_progress_manager() -> ProgressManager:
    """获取全局进度管理器实例"""
    global _progress_manager
    if _progress_manager is None:
        _progress_manager = ProgressManager()
    return _progress_manager
