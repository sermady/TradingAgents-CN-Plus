# -*- coding: utf-8 -*-
"""简化的股票分析服务 - 向后兼容入口

⚠️ 注意：此文件已拆分至 app/services/analysis/ 目录

原有功能已拆分为以下模块：
- base_analysis_service.py: 基础功能（股票名称解析、用户ID转换等）
- task_management_service.py: 任务管理（创建、查询、清理）
- analysis_execution_service.py: 分析执行（后台执行、同步分析）
- model_provider_service.py: 模型和提供商查询
- report_generation_service.py: 报告生成和保存
- simple_analysis_service.py: 统一门面类（在 analysis/ 目录中）

此文件仅用于向后兼容，所有导入都会转发到新的位置。
"""

# 从新的位置重新导出所有内容，保持完全向后兼容
from app.services.analysis.simple_analysis_service import (
    SimpleAnalysisService,
    get_simple_analysis_service,
)
from app.services.analysis.model_provider_service import (
    get_provider_by_model_name,
    get_provider_by_model_name_sync,
    get_provider_and_url_by_model_sync,
    create_analysis_config,
    RESEARCH_DEPTH_CONFIG,
    RESEARCH_DEPTH_TO_DEBATE_ROUNDS,
)

# 保持向后兼容的常量导出
STATUS_MAPPING = {
    "processing": "running",
    "pending": "pending",
    "completed": "completed",
    "failed": "failed",
    "cancelled": "cancelled",
}

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
    "STATUS_MAPPING",
]
