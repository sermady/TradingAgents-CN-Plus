# -*- coding: utf-8 -*-
"""
报告模板模块

提供统一的报告格式模板，确保所有分析师生成的报告格式一致。
"""

from .report_templates import (
    ReportTemplates,
    format_number,
    format_percentage,
    format_currency,
    get_report_header,
    get_report_footer,
)

__all__ = [
    "ReportTemplates",
    "format_number",
    "format_percentage",
    "format_currency",
    "get_report_header",
    "get_report_footer",
]
