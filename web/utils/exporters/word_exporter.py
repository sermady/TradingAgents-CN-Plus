#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Word报告导出器
负责生成Word文档格式的分析报告
"""

import os
import tempfile
import logging
from typing import Dict, Any
from tradingagents.utils.logging_manager import get_logger
from .base_exporter import BaseExporter

logger = get_logger('web.word_exporter')


class WordExporter(BaseExporter):
    """Word报告导出器"""

    def generate_report(self, results: Dict[str, Any]) -> bytes:
        """生成Word文档格式的报告"""

        logger.info("📄 开始生成Word文档...")

        if not self.pandoc_available:
            logger.error("❌ Pandoc不可用")
            raise Exception("Pandoc不可用，无法生成Word文档。请安装pandoc或使用Markdown格式导出。")

        # 首先生成markdown内容
        logger.info("📝 生成Markdown内容...")
        from .markdown_exporter import MarkdownExporter
        md_exporter = MarkdownExporter()
        md_content = md_exporter.generate_report(results)
        logger.info(f"✅ Markdown内容生成完成，长度: {len(md_content)} 字符")

        try:
            logger.info("📁 创建临时文件用于docx输出...")
            # 创建临时文件用于docx输出
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_file:
                output_file = tmp_file.name
            logger.info(f"📁 临时文件路径: {output_file}")

            # 使用强制禁用YAML的参数
            import pypandoc
            extra_args = ['--from=markdown-yaml_metadata_block']  # 禁用YAML解析
            logger.info(f"🔧 pypandoc参数: {extra_args} (禁用YAML解析)")

            logger.info("🔄 使用pypandoc将markdown转换为docx...")

            # 调试：保存实际的Markdown内容
            debug_file = '/app/debug_markdown.md'
            try:
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(md_content)
                logger.info(f"🔍 实际Markdown内容已保存到: {debug_file}")
                logger.info(f"📊 内容长度: {len(md_content)} 字符")

                # 显示前几行内容
                lines = md_content.split('\n')[:5]
                logger.info("🔍 前5行内容:")
                for i, line in enumerate(lines, 1):
                    logger.info(f"  {i}: {repr(line)}")
            except Exception as e:
                logger.error(f"保存调试文件失败: {e}")

            # 清理内容避免YAML解析问题
            cleaned_content = self._clean_markdown_for_pandoc(md_content)
            logger.info(f"🧹 内容清理完成，清理后长度: {len(cleaned_content)} 字符")

            # 使用测试成功的参数进行转换
            pypandoc.convert_text(
                cleaned_content,
                'docx',
                format='markdown',  # 基础markdown格式
                outputfile=output_file,
                extra_args=extra_args
            )
            logger.info("✅ pypandoc转换完成")

            logger.info("📖 读取生成的docx文件...")
            # 读取生成的docx文件
            with open(output_file, 'rb') as f:
                docx_content = f.read()
            logger.info(f"✅ 文件读取完成，大小: {len(docx_content)} 字节")

            logger.info("🗑️ 清理临时文件...")
            # 清理临时文件
            os.unlink(output_file)
            logger.info("✅ 临时文件清理完成")

            return docx_content
        except Exception as e:
            logger.error(f"❌ Word文档生成失败: {e}", exc_info=True)
            raise Exception(f"生成Word文档失败: {e}")

    def export(self, results: Dict[str, Any]) -> bytes:
        """导出为Word格式"""
        return self.generate_report(results)
