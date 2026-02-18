#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF报告导出器
负责生成PDF格式的分析报告
"""

import os
import tempfile
import logging
from typing import Dict, Any
from tradingagents.utils.logging_manager import get_logger
from .base_exporter import BaseExporter

logger = get_logger('web.pdf_exporter')


class PDFExporter(BaseExporter):
    """PDF报告导出器"""

    def generate_report(self, results: Dict[str, Any]) -> bytes:
        """生成PDF格式的报告"""

        logger.info("📊 开始生成PDF文档...")

        if not self.pandoc_available:
            logger.error("❌ Pandoc不可用")
            raise Exception("Pandoc不可用，无法生成PDF文档。请安装pandoc或使用Markdown格式导出。")

        # 首先生成markdown内容
        logger.info("📝 生成Markdown内容...")
        from .markdown_exporter import MarkdownExporter
        md_exporter = MarkdownExporter()
        md_content = md_exporter.generate_report(results)
        logger.info(f"✅ Markdown内容生成完成，长度: {len(md_content)} 字符")

        # 简化的PDF引擎列表，优先使用最可能成功的
        pdf_engines = [
            ('wkhtmltopdf', 'HTML转PDF引擎，推荐安装'),
            ('weasyprint', '现代HTML转PDF引擎'),
            (None, '使用pandoc默认引擎')  # 不指定引擎，让pandoc自己选择
        ]

        last_error = None

        for engine_info in pdf_engines:
            engine, description = engine_info
            try:
                # 创建临时文件用于PDF输出
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                    output_file = tmp_file.name

                # 使用禁用YAML解析的参数（与Word导出一致）
                import pypandoc
                extra_args = ['--from=markdown-yaml_metadata_block']

                # 如果指定了引擎，添加引擎参数
                if engine:
                    extra_args.append(f'--pdf-engine={engine}')
                    logger.info(f"🔧 使用PDF引擎: {engine}")
                else:
                    logger.info(f"🔧 使用默认PDF引擎")

                logger.info(f"🔧 PDF参数: {extra_args}")

                # 清理内容避免YAML解析问题（与Word导出一致）
                cleaned_content = self._clean_markdown_for_pandoc(md_content)

                # 使用pypandoc将markdown转换为PDF - 禁用YAML解析
                pypandoc.convert_text(
                    cleaned_content,
                    'pdf',
                    format='markdown',  # 基础markdown格式
                    outputfile=output_file,
                    extra_args=extra_args
                )

                # 检查文件是否生成且有内容
                if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                    # 读取生成的PDF文件
                    with open(output_file, 'rb') as f:
                        pdf_content = f.read()

                    # 清理临时文件
                    os.unlink(output_file)

                    logger.info(f"✅ PDF生成成功，使用引擎: {engine or '默认'}")
                    return pdf_content
                else:
                    raise Exception("PDF文件生成失败或为空")

            except Exception as e:
                last_error = str(e)
                logger.error(f"PDF引擎 {engine or '默认'} 失败: {e}")

                # 清理可能存在的临时文件
                try:
                    if 'output_file' in locals() and os.path.exists(output_file):
                        os.unlink(output_file)
                except:
                    pass

                continue

        # 如果所有引擎都失败，提供详细的错误信息和解决方案
        error_msg = f"""PDF生成失败，最后错误: {last_error}

可能的解决方案:
1. 安装wkhtmltopdf (推荐):
   Windows: choco install wkhtmltopdf
   macOS: brew install wkhtmltopdf
   Linux: sudo apt-get install wkhtmltopdf

2. 安装LaTeX:
   Windows: choco install miktex
   macOS: brew install mactex
   Linux: sudo apt-get install texlive-full

3. 使用Markdown或Word格式导出作为替代方案
"""
        raise Exception(error_msg)

    def export(self, results: Dict[str, Any]) -> bytes:
        """导出为PDF格式"""
        return self.generate_report(results)
