# -*- coding: utf-8 -*-
"""分析执行服务模块

提供分析任务执行的核心功能，包括:
- 后台分析执行
- 进度跟踪管理
- 结果构建与保存
- 风控验证

使用方法:
    from app.services.analysis.execution import AnalysisExecutionService

    service = AnalysisExecutionService()
    await service.execute_analysis_background(task_id, user_id, request)
"""

from app.services.analysis.execution.constants import NODE_PROGRESS_MAP
from app.services.analysis.execution.core import AnalysisExecutionService

__all__ = [
    "AnalysisExecutionService",
    "NODE_PROGRESS_MAP",
]
