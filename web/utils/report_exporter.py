#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告导出工具（向后兼容接口）

此模块保持向后兼容，所有功能已迁移到exporters子模块
"""

# 从新的模块化结构导入所有功能
from .exporters import (
    ReportExporter,
    report_exporter,
    MarkdownExporter,
    WordExporter,
    PDFExporter,
    render_export_buttons,
    save_modular_reports_to_results_dir,
    save_report_to_results_dir,
    save_analysis_report,
    format_team_decision_content,
)

__all__ = [
    "ReportExporter",
    "report_exporter",
    "MarkdownExporter",
    "WordExporter",
    "PDFExporter",
    "render_export_buttons",
    "save_modular_reports_to_results_dir",
    "save_report_to_results_dir",
    "save_analysis_report",
    "format_team_decision_content",
]
