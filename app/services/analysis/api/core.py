# -*- coding: utf-8 -*-
"""API分析服务核心模块

提供AnalysisAPIService核心类和基础功能。
"""

import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# 初始化TradingAgents日志系统
from tradingagents.utils.logging_init import init_logging

init_logging()

from tradingagents.graph.trading_graph import TradingAgentsGraph
from app.models.user import PyObjectId
from bson import ObjectId
from app.core.config import settings
from app.core.redis_client import get_redis
from app.services.queue_service import QueueService
from app.services.redis_progress_tracker import RedisProgressTracker
from app.services.usage_statistics_service import UsageStatisticsService
from app.services.progress_manager import get_progress_manager
from app.services.billing_service import get_billing_service

logger = logging.getLogger(__name__)


class AnalysisAPIService:
    """股票分析API服务类"""

    def __init__(self):
        # 获取Redis客户端
        redis_client = get_redis()
        self.queue_service = QueueService(redis_client)
        # 初始化服务
        self.usage_service = UsageStatisticsService()
        self.progress_manager = get_progress_manager()
        self.billing_service = get_billing_service()
        self._trading_graph_cache = {}
        self._progress_trackers = {}  # 进度跟踪器缓存

    def _convert_user_id(self, user_id: str) -> PyObjectId:
        """将字符串用户ID转换为PyObjectId"""
        try:
            logger.info(f"🔄 开始转换用户ID: {user_id} (类型: {type(user_id)})")

            # 如果是admin用户，使用配置的ObjectId
            if user_id == "admin":
                admin_object_id = ObjectId(settings.ADMIN_USER_ID)
                logger.info(f"🔄 转换admin用户ID: {user_id} -> {admin_object_id}")
                return PyObjectId(admin_object_id)
            else:
                # 尝试将字符串转换为ObjectId
                object_id = ObjectId(user_id)
                logger.info(f"🔄 转换用户ID: {user_id} -> {object_id}")
                return PyObjectId(object_id)
        except Exception as e:
            logger.error(f"❌ 用户ID转换失败: {user_id} -> {e}")
            # 如果转换失败，生成一个新的ObjectId
            new_object_id = ObjectId()
            logger.warning(f"⚠️ 生成新的用户ID: {new_object_id}")
            return PyObjectId(new_object_id)

    def _get_trading_graph(self, config: Dict[str, Any]) -> TradingAgentsGraph:
        """获取或创建TradingAgents图实例（带缓存）"""
        config_key = json.dumps(config, sort_keys=True)

        if config_key not in self._trading_graph_cache:
            self._trading_graph_cache[config_key] = TradingAgentsGraph(
                selected_analysts=config.get(
                    "selected_analysts", ["market", "fundamentals"]
                ),
                debug=config.get("debug", False),
                config=config,
            )

            logger.info(
                f"创建新的TradingAgents实例: {config.get('llm_provider', 'default')}"
            )

        return self._trading_graph_cache[config_key]

    def _get_progress_tracker(self, task) -> RedisProgressTracker:
        """创建或获取进度跟踪器"""
        from app.models.analysis import AnalysisTask

        if task.task_id in self._progress_trackers:
            return self._progress_trackers[task.task_id]

        progress_tracker = RedisProgressTracker(
            task_id=task.task_id,
            analysts=task.parameters.selected_analysts
            if task.parameters and hasattr(task.parameters, 'selected_analysts')
            else ["market", "fundamentals"],
            research_depth=task.parameters.research_depth
            if task.parameters and hasattr(task.parameters, 'research_depth')
            else "标准",
            llm_provider="dashscope",
        )
        self._progress_trackers[task.task_id] = progress_tracker
        return progress_tracker

    def _cleanup_progress_tracker(self, task_id: str) -> None:
        """清理进度跟踪器缓存"""
        if task_id in self._progress_trackers:
            del self._progress_trackers[task_id]
