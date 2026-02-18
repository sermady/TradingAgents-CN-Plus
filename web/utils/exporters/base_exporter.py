#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告导出器基类
包含所有导出器共享的基础方法和清理函数
"""

import logging
from typing import Dict, Any
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('web.base_exporter')


class BaseExporter:
    """报告导出器基类"""

    def __init__(self):
        """初始化基础导出器"""
        self.export_available = self._check_dependencies()
        self.pandoc_available = self._check_pandoc()

    def _check_dependencies(self) -> bool:
        """检查导出依赖是否可用"""
        try:
            import markdown
            return True
        except ImportError:
            logger.info("导出功能依赖包缺失: pip install pypandoc markdown")
            return False

    def _check_pandoc(self) -> bool:
        """检查pandoc是否可用"""
        if not self.export_available:
            return False

        try:
            import pypandoc
            pypandoc.get_pandoc_version()
            return True
        except (ImportError, OSError):
            # 尝试自动下载pandoc
            try:
                import pypandoc
                pypandoc.download_pandoc()
                logger.info("✅ pandoc下载成功！")
                return True
            except Exception as e:
                logger.error(f"❌ pandoc下载失败: {e}")
                return False

    def _clean_text_for_markdown(self, text: str) -> str:
        """清理文本中可能导致YAML解析问题的字符"""
        if not text:
            return "N/A"

        # 转换为字符串并清理特殊字符
        text = str(text)

        # 移除可能导致YAML解析问题的字符
        text = text.replace('&', '&amp;')  # HTML转义
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#39;')

        # 移除可能的YAML特殊字符
        text = text.replace('---', '—')  # 替换三个连字符
        text = text.replace('...', '…')  # 替换三个点

        return text

    def _clean_markdown_for_pandoc(self, content: str) -> str:
        """清理Markdown内容避免pandoc YAML解析问题"""
        if not content:
            return ""

        # 确保内容不以可能被误认为YAML的字符开头
        content = content.strip()

        # 如果第一行看起来像YAML分隔符，添加空行
        lines = content.split('\n')
        if lines and (lines[0].startswith('---') or lines[0].startswith('...')):
            content = '\n' + content

        # 替换可能导致YAML解析问题的字符序列，但保护表格分隔符
        # 先保护表格分隔符
        content = content.replace('|------|------|', '|TABLESEP|TABLESEP|')
        content = content.replace('|------|', '|TABLESEP|')

        # 然后替换其他的三连字符
        content = content.replace('---', '—')  # 替换三个连字符
        content = content.replace('...', '…')  # 替换三个点

        # 恢复表格分隔符
        content = content.replace('|TABLESEP|TABLESEP|', '|------|------|')
        content = content.replace('|TABLESEP|', '|------|')

        # 清理特殊引号
        content = content.replace('"', '"')  # 左双引号
        content = content.replace('"', '"')  # 右双引号
        content = content.replace(''', "'")  # 左单引号
        content = content.replace(''', "'")  # 右单引号

        # 确保内容以标准Markdown标题开始
        if not content.startswith('#'):
            content = '# 分析报告\n\n' + content

        return content

    def _add_team_decision_reports(self, md_content: str, state: Dict[str, Any]) -> str:
        """添加团队决策报告部分，与CLI端保持一致"""

        # II. 研究团队决策报告
        if 'investment_debate_state' in state and state['investment_debate_state']:
            md_content += "\n---\n\n## 🔬 研究团队决策\n\n"
            md_content += "*多头/空头研究员辩论分析，研究经理综合决策*\n\n"

            debate_state = state['investment_debate_state']

            # 多头研究员分析
            if debate_state.get('bull_history'):
                md_content += "### 📈 多头研究员分析\n\n"
                md_content += f"{self._clean_text_for_markdown(debate_state['bull_history'])}\n\n"

            # 空头研究员分析
            if debate_state.get('bear_history'):
                md_content += "### 📉 空头研究员分析\n\n"
                md_content += f"{self._clean_text_for_markdown(debate_state['bear_history'])}\n\n"

            # 研究经理决策
            if debate_state.get('judge_decision'):
                md_content += "### 🎯 研究经理综合决策\n\n"
                md_content += f"{self._clean_text_for_markdown(debate_state['judge_decision'])}\n\n"

        # III. 交易团队计划
        if 'trader_investment_plan' in state and state['trader_investment_plan']:
            md_content += "\n---\n\n## 💼 交易团队计划\n\n"
            md_content += "*专业交易员制定的具体交易执行计划*\n\n"
            md_content += f"{self._clean_text_for_markdown(state['trader_investment_plan'])}\n\n"

        # IV. 风险管理团队决策
        if 'risk_debate_state' in state and state['risk_debate_state']:
            md_content += "\n---\n\n## ⚖️ 风险管理团队决策\n\n"
            md_content += "*激进/保守/中性分析师风险评估，投资组合经理最终决策*\n\n"

            risk_state = state['risk_debate_state']

            # 激进分析师
            if risk_state.get('risky_history'):
                md_content += "### 🚀 激进分析师评估\n\n"
                md_content += f"{self._clean_text_for_markdown(risk_state['risky_history'])}\n\n"

            # 保守分析师
            if risk_state.get('safe_history'):
                md_content += "### 🛡️ 保守分析师评估\n\n"
                md_content += f"{self._clean_text_for_markdown(risk_state['safe_history'])}\n\n"

            # 中性分析师
            if risk_state.get('neutral_history'):
                md_content += "### ⚖️ 中性分析师评估\n\n"
                md_content += f"{self._clean_text_for_markdown(risk_state['neutral_history'])}\n\n"

            # 投资组合经理决策
            if risk_state.get('judge_decision'):
                md_content += "### 🎯 投资组合经理最终决策\n\n"
                md_content += f"{self._clean_text_for_markdown(risk_state['judge_decision'])}\n\n"

        # V. 最终交易决策
        if 'final_trade_decision' in state and state['final_trade_decision']:
            md_content += "\n---\n\n## 🎯 最终交易决策\n\n"
            md_content += "*综合所有团队分析后的最终投资决策*\n\n"
            md_content += f"{self._clean_text_for_markdown(state['final_trade_decision'])}\n\n"

        return md_content

    def _format_team_decision_content(self, content: Dict[str, Any], module_key: str) -> str:
        """格式化团队决策内容"""
        formatted_content = ""

        if module_key == 'investment_debate_state':
            # 研究团队决策格式化
            if content.get('bull_history'):
                formatted_content += "## 📈 多头研究员分析\n\n"
                formatted_content += f"{content['bull_history']}\n\n"

            if content.get('bear_history'):
                formatted_content += "## 📉 空头研究员分析\n\n"
                formatted_content += f"{content['bear_history']}\n\n"

            if content.get('judge_decision'):
                formatted_content += "## 🎯 研究经理综合决策\n\n"
                formatted_content += f"{content['judge_decision']}\n\n"

        elif module_key == 'risk_debate_state':
            # 风险管理团队决策格式化
            if content.get('risky_history'):
                formatted_content += "## 🚀 激进分析师评估\n\n"
                formatted_content += f"{content['risky_history']}\n\n"

            if content.get('safe_history'):
                formatted_content += "## 🛡️ 保守分析师评估\n\n"
                formatted_content += f"{content['safe_history']}\n\n"

            if content.get('neutral_history'):
                formatted_content += "## ⚖️ 中性分析师评估\n\n"
                formatted_content += f"{content['neutral_history']}\n\n"

            if content.get('judge_decision'):
                formatted_content += "## 🎯 投资组合经理最终决策\n\n"
                formatted_content += f"{content['judge_decision']}\n\n"

        return formatted_content
