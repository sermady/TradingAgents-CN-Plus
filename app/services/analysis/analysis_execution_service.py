# -*- coding: utf-8 -*-
"""分析执行服务

⚠️ 此文件已模块化拆分，现在作为兼容性层存在

实际实现已迁移至 app/services/analysis/execution/ 目录:
- core.py: 核心执行逻辑
- config_builder.py: 配置构建
- progress_manager.py: 进度管理
- result_builder.py: 结果构建
- constants.py: 常量定义
"""

from app.services.analysis.execution import AnalysisExecutionService
from app.services.analysis.execution.constants import NODE_PROGRESS_MAP

__all__ = ["AnalysisExecutionService", "NODE_PROGRESS_MAP"]
