# -*- coding: utf-8 -*-
"""
股票分析执行工具

此模块保持向后兼容，所有功能已迁移到analysis子模块
"""

# 从新的模块化结构导入所有功能
from .analysis import (
    run_stock_analysis,
    validate_analysis_params,
    format_analysis_results,
    translate_analyst_labels,
    extract_risk_assessment,
    get_supported_stocks,
)

__all__ = [
    "run_stock_analysis",
    "validate_analysis_params",
    "format_analysis_results",
    "translate_analyst_labels",
    "extract_risk_assessment",
    "get_supported_stocks",
]

# 注意：generate_demo_results_deprecated 函数已删除
# 原因：该函数已弃用且会生成误导性演示数据
