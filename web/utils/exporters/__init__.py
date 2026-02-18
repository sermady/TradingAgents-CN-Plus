#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告导出模块
提供统一的报告导出接口，支持多种格式
"""

import streamlit as st
import logging
from typing import Dict, Any, Optional
from tradingagents.utils.logging_manager import get_logger

# 导入各个导出器
from .markdown_exporter import MarkdownExporter
from .word_exporter import WordExporter
from .pdf_exporter import PDFExporter

logger = get_logger('web.exporters')

# 尝试导入Docker适配器
try:
    from ..docker_pdf_adapter import (
        is_docker_environment,
        get_docker_status_info
    )
    DOCKER_ADAPTER_AVAILABLE = True
except ImportError:
    DOCKER_ADAPTER_AVAILABLE = False
    logger.warning("⚠️ Docker适配器不可用")


class ReportExporter:
    """统一报告导出器"""

    def __init__(self):
        """初始化导出器"""
        self.markdown_exporter = MarkdownExporter()
        self.word_exporter = WordExporter()
        self.pdf_exporter = PDFExporter()

        self.export_available = self.markdown_exporter.export_available
        self.pandoc_available = self.markdown_exporter.pandoc_available
        self.is_docker = DOCKER_ADAPTER_AVAILABLE and is_docker_environment()

        # 记录初始化状态
        logger.info("📋 ReportExporter初始化:")
        logger.info(f"  - export_available: {self.export_available}")
        logger.info(f"  - pandoc_available: {self.pandoc_available}")
        logger.info(f"  - is_docker: {self.is_docker}")
        logger.info(f"  - docker_adapter_available: {DOCKER_ADAPTER_AVAILABLE}")

        # Docker环境初始化
        if self.is_docker:
            logger.info("🐳 检测到Docker环境，初始化PDF支持...")
            try:
                from ..docker_pdf_adapter import setup_xvfb_display
                setup_xvfb_display()
            except Exception as e:
                logger.warning(f"⚠️ Docker环境初始化失败: {e}")

    def export_report(self, results: Dict[str, Any], format_type: str) -> Optional[bytes]:
        """导出报告为指定格式"""

        logger.info(f"🚀 开始导出报告: format={format_type}")
        logger.info(f"📊 导出状态检查:")
        logger.info(f"  - export_available: {self.export_available}")
        logger.info(f"  - pandoc_available: {self.pandoc_available}")
        logger.info(f"  - is_docker: {self.is_docker}")

        if not self.export_available:
            logger.error("❌ 导出功能不可用")
            st.error("❌ 导出功能不可用，请安装必要的依赖包")
            return None

        try:
            logger.info(f"🔄 开始生成{format_type}格式报告...")

            if format_type == 'markdown':
                logger.info("📝 生成Markdown报告...")
                content = self.markdown_exporter.export(results)
                logger.info(f"✅ Markdown报告生成成功，长度: {len(content)} 字节")
                return content

            elif format_type == 'docx':
                logger.info("📄 生成Word文档...")
                if not self.pandoc_available:
                    logger.error("❌ pandoc不可用，无法生成Word文档")
                    st.error("❌ pandoc不可用，无法生成Word文档")
                    return None
                content = self.word_exporter.export(results)
                logger.info(f"✅ Word文档生成成功，大小: {len(content)} 字节")
                return content

            elif format_type == 'pdf':
                logger.info("📊 生成PDF文档...")
                if not self.pandoc_available:
                    logger.error("❌ pandoc不可用，无法生成PDF文档")
                    st.error("❌ pandoc不可用，无法生成PDF文档")
                    return None
                content = self.pdf_exporter.export(results)
                logger.info(f"✅ PDF文档生成成功，大小: {len(content)} 字节")
                return content

            else:
                logger.error(f"❌ 不支持的导出格式: {format_type}")
                st.error(f"❌ 不支持的导出格式: {format_type}")
                return None

        except Exception as e:
            logger.error(f"❌ 导出失败: {str(e)}", exc_info=True)
            st.error(f"❌ 导出失败: {str(e)}")
            return None


# 创建全局导出器实例
report_exporter = ReportExporter()

# 导出所有公共接口
__all__ = [
    "ReportExporter",
    "report_exporter",
    "MarkdownExporter",
    "WordExporter",
    "PDFExporter",
    # UI渲染
    "render_export_buttons",
    # 文件工具
    "save_modular_reports_to_results_dir",
    "save_report_to_results_dir",
    "save_analysis_report",
    "format_team_decision_content",
]

# 从子模块导入
from .ui_renderer import render_export_buttons
from .file_utils import (
    save_modular_reports_to_results_dir,
    save_report_to_results_dir,
    save_analysis_report,
    format_team_decision_content,
)
