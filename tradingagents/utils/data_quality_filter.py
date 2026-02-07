# -*- coding: utf-8 -*-
"""
数据质量过滤器

检测和标记财务数据中的质量问题
"""

from typing import Dict, List, Tuple
import re


class DataQualityFilter:
    """数据质量过滤器"""

    @classmethod
    def check_financial_data_quality(cls, report_text: str) -> List[Dict]:
        """
        检查财务报告中的数据质量问题

        Args:
            report_text: 基本面分析报告文本

        Returns:
            List[Dict]: 发现的问题列表
        """
        issues = []

        # 检查1: PE_TTM 计算逻辑错误
        issues.extend(cls._check_pe_ttm_calculation_logic(report_text))

        # 检查2: 数据缺失
        issues.extend(cls._check_missing_data(report_text))

        # 检查3: 估值计算不一致
        issues.extend(cls._check_valuation_inconsistency(report_text))

        return issues

    @classmethod
    def _check_pe_ttm_calculation_logic(cls, report_text: str) -> List[Dict]:
        """
        检查 PE_TTM 计算逻辑是否正确

        注意：PE_TTM 高值本身不是异常（军工股常见），但要检查
        AI 是否用静态利润去错误地"验算"PE_TTM

        PE_TTM = 市值 / TTM净利润（过去12个月滚动）
        PE静态 = 市值 / 年报归母净利润
        """
        issues = []

        # 检查1: PE_TTM 验算风险（任何验算都可能出错）
        if "PE_TTM" in report_text and "验算" in report_text:
            # 查找验算公式
            pe_calc_pattern = r"PE[_\(]?TTM[\)\)]?\s*[=：]\s*[\d.]+\s*[÷/]\s*[\d.]+"
            pe_matches = re.findall(pe_calc_pattern, report_text)
            for match in pe_matches:
                # 检查验算公式上下文（60个字符）
                match_start = report_text.find(match)
                context_start = max(0, match_start - 60)
                context_end = min(len(report_text), match_start + len(match) + 60)
                context = report_text[context_start:context_end]

                # 如果上下文中没有明确说明使用TTM净利润，则警告
                has_ttm_keyword = (
                    "TTM" in context.upper()
                    or "滚动" in context
                    or "过去12个月" in context
                )

                if not has_ttm_keyword:
                    issues.append(
                        {
                            "severity": "warning",
                            "category": "calculation_logic",
                            "description": "PE_TTM验算未明确使用TTM净利润",
                            "detail": "PE_TTM必须用TTM滚动利润计算（过去12个月），不能用单期归母净利润验算。正确公式：PE_TTM = 总市值 / TTM净利润",
                        }
                    )

        # 检查2: 提取错误的验算公式模式（查找PE相关验算中使用的利润字段）
        if "PE_TTM" in report_text and "验算" in report_text:
            # 查找类似 "市值 ÷ 归母净利润 = XX倍" 的验算
            if re.search(r"验算.*归母净利润|归母净利润.*验算", report_text):
                issues.append(
                    {
                        "severity": "warning",
                        "category": "calculation_logic",
                        "description": "PE_TTM验算使用了错误的利润口径",
                        "detail": "检测到在PE_TTM验算中使用了归母净利润。PE_TTM必须用TTM净利润计算，与PE静态（用归母净利润）是不同的指标",
                    }
                )

        # 检查3: AI基于错误验算声称PE_TTM数据错误
        if re.search(r"PE_TTM.*错误|错误.*PE_TTM|严重高估|严重低估", report_text):
            # 如果同时有验算，标记为严重问题
            if "验算" in report_text:
                issues.append(
                    {
                        "severity": "critical",
                        "category": "calculation_logic",
                        "description": "基于验算声称PE_TTM数据错误",
                        "detail": "报告声称PE_TTM错误并进行了验算。请确保：1）验算使用的是TTM净利润（过去12个月），2）如果验算结果与报告值一致，则说明数据本身没有问题。正确做法：先用TTM净利润验算，如果仍有差异再指出数据问题",
                    }
                )

        return issues

    @classmethod
    def _check_missing_data(cls, report_text: str) -> List[Dict]:
        """检查数据缺失"""
        issues = []

        # 检查是否标记了数据缺失
        missing_patterns = [
            (r"数据[未暂]提供", "数据未提供"),
            (r"N/A", "数据为N/A"),
            (r"无法[获取计算]", "无法获取/计算"),
        ]

        for pattern, desc in missing_patterns:
            if re.search(pattern, report_text):
                issues.append(
                    {
                        "severity": "info",
                        "category": "missing_data",
                        "description": desc,
                        "detail": "报告中存在数据缺失",
                    }
                )

        return issues

    @classmethod
    def _check_valuation_inconsistency(cls, report_text: str) -> List[Dict]:
        """检查估值指标计算不一致"""
        issues = []

        # 提取所有 PE 相关的数值
        pe_matches = re.findall(
            r"PE[（\(]?TTM[）\)]?\s*[：:]\s*(\d+\.?\d*)倍", report_text
        )
        pe_static_matches = re.findall(
            r"PE[（\(]?静态[）\)]?\s*[：:]\s*(\d+\.?\d*)倍", report_text
        )

        if pe_matches and pe_static_matches:
            try:
                pe_ttm = float(pe_matches[0])
                pe_static = float(pe_static_matches[0])

                # 如果 PE_TTM 和 PE_STATIC 差异过大（超过50%），可能是计算错误
                if pe_ttm > 0 and pe_static > 0:
                    ratio = (
                        pe_ttm / pe_static if pe_ttm > pe_static else pe_static / pe_ttm
                    )
                    if ratio > 1.5:  # 差异超过50%
                        issues.append(
                            {
                                "severity": "info",
                                "category": "valuation_inconsistency",
                                "description": f"PE_TTM({pe_ttm})与PE静态({pe_static})差异较大",
                                "detail": "可能存在计算口径不一致，请核实数据来源",
                            }
                        )
            except (ValueError, IndexError):
                pass

        return issues

    @classmethod
    def generate_quality_summary(cls, issues: List[Dict]) -> str:
        """
        生成数据质量摘要

        Args:
            issues: 问题列表

        Returns:
            str: 摘要内容
        """
        if not issues:
            return ""

        summary = "\n### ⚠️ 数据质量说明\n\n"

        # 按严重程度分组
        critical = [i for i in issues if i.get("severity") == "critical"]
        warning = [i for i in issues if i.get("severity") == "warning"]
        info = [i for i in issues if i.get("severity") == "info"]

        if critical:
            summary += "**严重问题**:\n"
            for issue in critical:
                summary += f"- {issue['description']}: {issue.get('detail', '')}\n"
            summary += "\n"

        if warning:
            summary += "**警告**:\n"
            for issue in warning:
                summary += f"- {issue['description']}: {issue.get('detail', '')}\n"
            summary += "\n"

        if info:
            summary += "**提示**:\n"
            for issue in info:
                summary += f"- {issue['description']}\n"

        return summary

    @classmethod
    def filter_and_mark_data(
        cls, financial_data: Dict, report_text: str
    ) -> Tuple[Dict, str]:
        """
        过滤并标记数据质量问题

        Args:
            financial_data: 原始财务数据
            report_text: 报告文本

        Returns:
            Tuple[Dict, str]: (过滤后的数据, 质量说明)
        """
        # 检查数据质量
        issues = cls.check_financial_data_quality(report_text)
        quality_summary = cls.generate_quality_summary(issues)

        # 对于数据质量问题，我们只标记不过滤
        # 因为 AI 需要基于原始数据进行分析
        return financial_data, quality_summary
