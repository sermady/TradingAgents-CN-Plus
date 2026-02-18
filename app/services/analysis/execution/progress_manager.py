# -*- coding: utf-8 -*-
"""进度管理模块

负责分析任务进度跟踪、更新和模拟
"""

import asyncio
import logging
import threading
import time
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from app.services.analysis.execution.constants import (
    DEBATE_ROUNDS,
    DEFAULT_ANALYSTS,
    DEFAULT_RESEARCH_DEPTH,
    NODE_PROGRESS_MAP,
)
from app.services.memory_state_manager import TaskStatus

if TYPE_CHECKING:
    from app.services.redis_progress_tracker import RedisProgressTracker

logger = logging.getLogger(__name__)


class ProgressManagerMixin:
    """进度管理混入类"""

    def __init__(self):
        self._progress_trackers: dict[str, "RedisProgressTracker"] = {}

    async def _create_progress_tracker(
        self, task_id: str, request
    ) -> "RedisProgressTracker":
        """创建Redis进度跟踪器

        Args:
            task_id: 任务ID
            request: 分析请求对象

        Returns:
            RedisProgressTracker 实例
        """
        from app.models.analysis import AnalysisParameters
        from app.services.redis_progress_tracker import RedisProgressTracker

        parameters = request.parameters or AnalysisParameters()

        def create_tracker():
            return RedisProgressTracker(
                task_id=task_id,
                analysts=parameters.selected_analysts or DEFAULT_ANALYSTS,
                research_depth=parameters.research_depth or DEFAULT_RESEARCH_DEPTH,
                llm_provider="dashscope",
            )

        return await asyncio.to_thread(create_tracker)

    async def _initialize_progress(
        self, task_id: str, progress_tracker: "RedisProgressTracker"
    ):
        """初始化任务进度

        Args:
            task_id: 任务ID
            progress_tracker: 进度跟踪器
        """
        from app.models.analysis import AnalysisStatus
        from app.services.analysis.task_management_service import TaskManagementService

        await asyncio.to_thread(
            progress_tracker.update_progress,
            {"progress_percentage": 10, "last_message": "🚀 开始股票分析"},
        )

        await self.memory_manager.update_task_status(
            task_id=task_id,
            status=TaskStatus.RUNNING,
            progress=10,
            message="分析开始...",
            current_step="initialization",
        )

        # 更新MongoDB状态
        task_service = TaskManagementService()
        await task_service.update_task_status(task_id, AnalysisStatus.PROCESSING, 10)

    def _update_progress_sync(
        self,
        task_id: str,
        progress: int,
        message: str,
        step: str,
        progress_tracker: Optional["RedisProgressTracker"] = None,
    ):
        """在线程池中同步更新进度

        Args:
            task_id: 任务ID
            progress: 进度百分比
            message: 进度消息
            step: 当前步骤
            progress_tracker: 进度跟踪器
        """
        try:
            if progress_tracker:
                progress_tracker.update_progress(
                    {"progress_percentage": progress, "last_message": message}
                )

            # 更新内存中的任务状态
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    self.memory_manager.update_task_status(
                        task_id=task_id,
                        status=TaskStatus.RUNNING,
                        progress=progress,
                        message=message,
                        current_step=step,
                    )
                )
            finally:
                loop.close()

            # 更新 MongoDB
            from pymongo import MongoClient
            from app.core.config import settings

            sync_client = MongoClient(settings.MONGO_URI)
            sync_db = sync_client[settings.MONGO_DB]

            sync_db.analysis_tasks.update_one(
                {"task_id": task_id},
                {
                    "$set": {
                        "progress": progress,
                        "current_step": step,
                        "message": message,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
            sync_client.close()

        except Exception as e:
            logger.warning(f"⚠️ 进度更新失败: {e}")

    def _create_progress_callback(self, task_id: str, progress_tracker):
        """创建进度回调函数

        Args:
            task_id: 任务ID
            progress_tracker: 进度跟踪器

        Returns:
            回调函数
        """

        def callback(message: str):
            try:
                logger.info(f"🎯🎯🎯 [Graph进度回调被调用] message={message}")
                if not progress_tracker:
                    return

                progress_pct = NODE_PROGRESS_MAP.get(message)
                if progress_pct is not None:
                    current_progress = progress_tracker.progress_data.get(
                        "progress_percentage", 0
                    )

                    if int(progress_pct) > current_progress:
                        progress_tracker.update_progress(
                            {
                                "progress_percentage": int(progress_pct),
                                "last_message": message,
                            }
                        )
                        logger.info(
                            f"📊 [Graph进度] 进度已更新: {current_progress}% → {int(progress_pct)}% - {message}"
                        )

                        # 同时更新内存和 MongoDB
                        self._sync_progress_to_db(task_id, int(progress_pct), message)
                    else:
                        progress_tracker.update_progress({"last_message": message})
                else:
                    logger.warning(f"⚠️ [Graph进度] 未知节点: {message}")
                    progress_tracker.update_progress({"last_message": message})

            except Exception as e:
                logger.error(f"❌ Graph进度回调失败: {e}", exc_info=True)

        return callback

    def _sync_progress_to_db(self, task_id: str, progress: int, message: str):
        """同步进度到数据库

        Args:
            task_id: 任务ID
            progress: 进度百分比
            message: 进度消息
        """
        try:
            import asyncio
            from pymongo import MongoClient
            from app.core.config import settings

            # 创建同步 MongoDB 客户端
            sync_client = MongoClient(settings.MONGO_URI)
            sync_db = sync_client[settings.MONGO_DB]

            sync_db.analysis_tasks.update_one(
                {"task_id": task_id},
                {
                    "$set": {
                        "progress": progress,
                        "current_step": message,
                        "message": message,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
            sync_client.close()

            # 异步更新内存
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    self.memory_manager.update_task_status(
                        task_id=task_id,
                        status=TaskStatus.RUNNING,
                        progress=progress,
                        message=message,
                        current_step=message,
                    )
                )
            finally:
                loop.close()

        except Exception as e:
            logger.warning(f"⚠️ [Graph进度] 同步更新失败: {e}")

    def _start_progress_simulation(
        self, request, progress_tracker: Optional["RedisProgressTracker"]
    ) -> threading.Thread:
        """启动进度模拟线程

        Args:
            request: 分析请求对象
            progress_tracker: 进度跟踪器

        Returns:
            模拟线程
        """

        def simulate_progress():
            try:
                if not progress_tracker:
                    return

                analysts = (
                    request.parameters.selected_analysts
                    if request.parameters
                    else DEFAULT_ANALYSTS
                )

                # 模拟分析师执行
                for i, analyst in enumerate(analysts):
                    time.sleep(15)
                    if analyst == "market":
                        progress_tracker.update_progress("📊 市场分析师正在分析")
                    elif analyst == "fundamentals":
                        progress_tracker.update_progress("💼 基本面分析师正在分析")
                    elif analyst == "news":
                        progress_tracker.update_progress("📰 新闻分析师正在分析")
                    elif analyst == "social":
                        progress_tracker.update_progress("💬 社交媒体分析师正在分析")

                # 研究团队阶段
                time.sleep(10)
                progress_tracker.update_progress("🐂 看涨研究员构建论据")

                time.sleep(8)
                progress_tracker.update_progress("🐻 看跌研究员识别风险")

                # 辩论阶段
                research_depth = (
                    request.parameters.research_depth
                    if request.parameters
                    else DEFAULT_RESEARCH_DEPTH
                )
                debate_rounds = DEBATE_ROUNDS.get(research_depth, 1)

                for round_num in range(debate_rounds):
                    time.sleep(12)
                    progress_tracker.update_progress(f"🎯 研究辩论 第{round_num + 1}轮")

                time.sleep(8)
                progress_tracker.update_progress("👔 研究经理形成共识")

                # 交易员阶段
                time.sleep(10)
                progress_tracker.update_progress("💼 交易员制定策略")

                # 风险管理阶段
                time.sleep(8)
                progress_tracker.update_progress("🔥 激进风险评估")

                time.sleep(6)
                progress_tracker.update_progress("🛡️ 保守风险评估")

                time.sleep(6)
                progress_tracker.update_progress("⚖️ 中性风险评估")

                time.sleep(8)
                progress_tracker.update_progress("🎯 风险经理制定策略")

                # 最终阶段
                time.sleep(5)
                progress_tracker.update_progress("📡 信号处理")

            except Exception as e:
                logger.warning(f"⚠️ 进度模拟失败: {e}")

        progress_thread = threading.Thread(target=simulate_progress, daemon=True)
        progress_thread.start()
        return progress_thread
