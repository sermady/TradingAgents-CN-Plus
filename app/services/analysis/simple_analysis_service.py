# -*- coding: utf-8 -*-
"""简化的股票分析服务 - 门面类

这是拆分后的统一入口，继承所有子服务的功能：
- BaseAnalysisService: 基础功能（股票名称解析、用户ID转换等）
- TaskManagementService: 任务管理（创建、查询、清理）
- AnalysisExecutionService: 分析执行（后台执行、同步分析）
- ReportGenerationService: 报告生成和保存

原有的 simple_analysis_service.py 中的模型查询功能已移至 model_provider_service.py

保持向后兼容：所有原有 API 和导入路径不变。
"""

import logging
from typing import Dict, Any, Optional, List

# 导入子服务
from app.services.analysis.base_analysis_service import BaseAnalysisService
from app.services.analysis.task_management_service import TaskManagementService
from app.services.analysis.analysis_execution_service import AnalysisExecutionService
from app.services.analysis.report_generation_service import ReportGenerationService

# 重新导出模型查询函数以保持向后兼容
from app.services.analysis.model_provider_service import (
    get_provider_by_model_name,
    get_provider_by_model_name_sync,
    get_provider_and_url_by_model_sync,
    create_analysis_config,
    RESEARCH_DEPTH_CONFIG,
    RESEARCH_DEPTH_TO_DEBATE_ROUNDS,
)

logger = logging.getLogger(__name__)

# 全局服务实例
_analysis_service = None


class SimpleAnalysisService(
    BaseAnalysisService,
    TaskManagementService,
    AnalysisExecutionService,
    ReportGenerationService,
):
    """简化的股票分析服务类 - 统一门面

    通过多重继承组合所有子服务的功能：
    - BaseAnalysisService: _resolve_stock_name, _enrich_stock_names, _convert_user_id, _get_trading_graph
    - TaskManagementService: create_analysis_task, get_task_status, list_user_tasks, list_all_tasks, cleanup_zombie_tasks
    - AnalysisExecutionService: execute_analysis_background, _execute_analysis_sync, _run_analysis_sync
    - ReportGenerationService: save_analysis_result, save_analysis_result_web_style, save_analysis_results_complete
    """

    def __init__(self):
        # 初始化所有父类
        BaseAnalysisService.__init__(self)
        TaskManagementService.__init__(self)
        AnalysisExecutionService.__init__(self)
        ReportGenerationService.__init__(self)

        # 设置 WebSocket 管理器
        try:
            from app.services.websocket_manager import get_websocket_manager
            self.memory_manager.set_websocket_manager(get_websocket_manager())
        except ImportError:
            logger.warning("⚠️ WebSocket 管理器不可用")

        logger.info(f"🔧 [服务初始化] SimpleAnalysisService 实例ID: {id(self)}")
        logger.info(f"🔧 [服务初始化] 内存管理器实例ID: {id(self.memory_manager)}")
        logger.info(f"🔧 [服务初始化] 线程池最大并发数: 3")

    # 为了保持完全向后兼容，保留一些别名方法
    async def _update_task_status(
        self,
        task_id: str,
        status,
        progress: int,
        error_message: str = None,
    ):
        """更新任务状态（向后兼容别名）"""
        return await self.update_task_status(task_id, status, progress, error_message)

    async def _save_analysis_result(self, task_id: str, result: Dict[str, Any]):
        """保存分析结果（向后兼容别名）"""
        return await self.save_analysis_result(task_id, result)

    async def _save_analysis_result_web_style(self, task_id: str, result: Dict[str, Any]):
        """保存分析结果web风格（向后兼容别名）"""
        return await self.save_analysis_result_web_style(task_id, result)

    async def _save_analysis_results_complete(self, task_id: str, result: Dict[str, Any]):
        """完整保存分析结果（向后兼容别名）"""
        return await self.save_analysis_results_complete(task_id, result)

    async def _save_modular_reports_to_data_dir(
        self, result: Dict[str, Any], stock_symbol: str
    ) -> Dict[str, str]:
        """保存分模块报告到数据目录（向后兼容别名）"""
        return await self.save_modular_reports_to_data_dir(result, stock_symbol)

    async def _update_progress_async(self, task_id: str, progress: int, message: str):
        """异步更新进度（向后兼容别名）"""
        try:
            from app.models.analysis import AnalysisStatus
            from app.services.memory_state_manager import TaskStatus

            # 更新内存
            await self.memory_manager.update_task_status(
                task_id=task_id,
                status=TaskStatus.RUNNING,
                progress=progress,
                message=message,
                current_step=message,
            )

            # 更新 MongoDB
            from app.core.database import get_mongo_db
            from datetime import datetime

            db = get_mongo_db()
            await db.analysis_tasks.update_one(
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
            logger.debug(f"✅ [异步更新] 已更新内存和MongoDB: {progress}%")
        except Exception as e:
            logger.warning(f"⚠️ [异步更新] 失败: {e}")


def get_simple_analysis_service() -> SimpleAnalysisService:
    """获取分析服务实例"""
    global _analysis_service
    if _analysis_service is None:
        logger.info("🔧 [单例] 创建新的 SimpleAnalysisService 实例")
        _analysis_service = SimpleAnalysisService()
    else:
        logger.info(
            f"🔧 [单例] 返回现有的 SimpleAnalysisService 实例: {id(_analysis_service)}"
        )
    return _analysis_service


# 向后兼容：保留原有的配置常量
__all__ = [
    # 主要类
    "SimpleAnalysisService",
    "get_simple_analysis_service",
    # 工具函数
    "get_provider_by_model_name",
    "get_provider_by_model_name_sync",
    "get_provider_and_url_by_model_sync",
    "create_analysis_config",
    # 常量
    "RESEARCH_DEPTH_CONFIG",
    "RESEARCH_DEPTH_TO_DEBATE_ROUNDS",
]
