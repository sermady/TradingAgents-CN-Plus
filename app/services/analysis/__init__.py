# -*- coding: utf-8 -*-
"""分析服务模块

将原有的 simple_analysis_service.py 拆分为多个独立模块：
- BaseAnalysisService: 分析服务基类，包含通用功能
- TaskManagementService: 任务管理相关功能
- AnalysisExecutionService: 分析执行核心逻辑
- ModelProviderService: 模型和提供商查询
- ReportGenerationService: 报告生成和保存

保持向后兼容：所有原有导入仍然有效。
"""

from app.services.analysis.base_analysis_service import BaseAnalysisService
from app.services.analysis.task_management_service import TaskManagementService
from app.services.analysis.analysis_execution_service import AnalysisExecutionService
from app.services.analysis.model_provider_service import (
    ModelProviderService,
    get_provider_by_model_name,
    get_provider_by_model_name_sync,
    get_provider_and_url_by_model_sync,
    create_analysis_config,
)
from app.services.analysis.report_generation_service import ReportGenerationService

# 为了保持向后兼容，导出原有的 SimpleAnalysisService
# 它现在继承自各个拆分后的服务类
from app.services.analysis.simple_analysis_service import SimpleAnalysisService
from app.services.analysis.simple_analysis_service import get_simple_analysis_service

__all__ = [
    # 拆分后的服务类
    "BaseAnalysisService",
    "TaskManagementService",
    "AnalysisExecutionService",
    "ModelProviderService",
    "ReportGenerationService",
    # 向后兼容
    "SimpleAnalysisService",
    "get_simple_analysis_service",
    # 工具函数
    "get_provider_by_model_name",
    "get_provider_by_model_name_sync",
    "get_provider_and_url_by_model_sync",
    "create_analysis_config",
]
