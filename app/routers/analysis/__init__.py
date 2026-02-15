# -*- coding: utf-8 -*-
"""
分析API路由 - 统一导出

保持原有API端点路径不变，确保向后兼容。
"""

# 路由定义（主要导出）
from app.routers.analysis.routes import router

# 数据模型
from app.routers.analysis.schemas import (
    SingleAnalysisRequest,
    BatchAnalysisRequest,
    AnalysisParameters,
    TaskStatusResponse,
    TaskResultResponse,
    ApiResponse,
)

# 服务类
from app.routers.analysis.task_service import get_task_service
from app.routers.analysis.status_service import get_status_service

# 验证工具
from app.routers.analysis.validators import (
    validate_stock_code,
    validate_analysis_date,
    validate_research_depth,
    validate_symbols_list,
)

__all__ = [
    # 路由
    "router",
    # 数据模型
    "SingleAnalysisRequest",
    "BatchAnalysisRequest",
    "AnalysisParameters",
    "TaskStatusResponse",
    "TaskResultResponse",
    "ApiResponse",
    # 服务
    "get_task_service",
    "get_status_service",
    # 验证工具
    "validate_stock_code",
    "validate_analysis_date",
    "validate_research_depth",
    "validate_symbols_list",
]
