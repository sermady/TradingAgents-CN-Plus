# -*- coding: utf-8 -*-
"""
报告交叉引用生成器

在最终报告摘要中生成各分析师报告的交叉引用
"""

from typing import Dict, List
from tradingagents.utils.recommendation_standardizer import RecommendationStandardizer


class CrossReferenceGenerator:
    """交叉引用生成器"""

    @staticmethod
    def generate_perspective_summary(reports: Dict[str, str]) -> str:
        """
        生成各分析师观点摘要

        Args:
            reports: 所有报告的字典

        Returns:
            str: 观点摘要
        """
        summary = "## 各分析师观点对比\n\n"

        # 提取各报告的核心观点
        perspectives = []

        if "market_report" in reports:
            rec = CrossReferenceGenerator._extract_key_points(
                reports["market_report"], "技术分析"
            )
            perspectives.append(("技术分析师", rec))

        if "fundamentals_report" in reports:
            rec = CrossReferenceGenerator._extract_key_points(
                reports["fundamentals_report"], "基本面分析"
            )
            perspectives.append(("基本面分析师", rec))

        if "news_report" in reports:
            rec = CrossReferenceGenerator._extract_key_points(
                reports["news_report"], "消息面分析"
            )
            perspectives.append(("新闻分析师", rec))

        # 生成表格
        summary += "| 分析师 | 核心观点 | 建议 |\n"
        summary += "|--------|----------|------|\n"

        for name, points in perspectives:
            summary += f"| {name} | {points['view']} | {points['recommendation']} |\n"

        # 添加共识与分歧说明
        summary += "\n### 共识与分歧\n\n"
        recommendations = [points["recommendation"] for name, points in perspectives]
        summary += CrossReferenceGenerator._analyze_agreement(recommendations)

        return summary

    @staticmethod
    def _extract_key_points(report: str, analyst_type: str) -> Dict[str, str]:
        """
        提取报告关键点

        Args:
            report: 报告内容
            analyst_type: 分析师类型

        Returns:
            Dict: 包含 view 和 recommendation
        """
        # 默认值
        view = analyst_type
        recommendation = "中性观望"

        # 提取建议关键词
        rec = RecommendationStandardizer.normalize(report)
        if rec:
            recommendation = rec.value

        # 尝试提取更具体的观点
        lines = report.split('\n')
        for i, line in enumerate(lines):
            # 查找趋势判断
            if "趋势" in line and ("上涨" in line or "下跌" in line or "震荡" in line):
                # 简化提取
                if "上涨" in line:
                    view = f"趋势{analyst_type}偏多"
                elif "下跌" in line:
                    view = f"趋势{analyst_type}偏空"
                break

        return {"view": view, "recommendation": recommendation}

    @staticmethod
    def _analyze_agreement(recommendations: List[str]) -> str:
        """
        分析建议的一致性

        Args:
            recommendations: 建议列表

        Returns:
            str: 分析结果
        """
        # 统计各类建议数量
        buy_keywords = ["买入", "强烈买入", "谨慎买入", "看多"]
        sell_keywords = ["卖出", "强烈卖出", "谨慎卖出", "看空", "回避"]
        hold_keywords = ["持有", "观望", "中性"]

        buy_count = sum(1 for r in recommendations if any(k in r for k in buy_keywords))
        sell_count = sum(1 for r in recommendations if any(k in r for k in sell_keywords))
        hold_count = sum(1 for r in recommendations if any(k in r for k in hold_keywords))

        total = len(recommendations)

        if buy_count == total:
            return "- ✅ **共识**: 所有分析师均持看多观点\n"
        elif sell_count == total:
            return "- ✅ **共识**: 所有分析师均持看空观点\n"
        elif buy_count > 0 and sell_count > 0:
            return "- ⚠️ **分歧**: 分析师观点存在分歧，请仔细阅读各报告详情\n"
            f"  - 看多: {buy_count}位，看空: {sell_count}位"
        elif hold_count == total:
            return "- ➖ **中性**: 分析师普遍持观望态度\n"
        else:
            return "- ℹ️ **混合**: 分析师观点不一，建议综合参考\n"

    @staticmethod
    def generate_consistency_report(consistency_issues: List) -> str:
        """
        生成一致性报告

        Args:
            consistency_issues: 一致性问题列表

        Returns:
            str: 报告内容
        """
        if not consistency_issues:
            return ""

        report = "## 📋 报告一致性检查\n\n"

        for issue in consistency_issues:
            if issue.get("severity") == "critical":
                report += f"🔴 **严重问题**: {issue.get('description')}\n"
            elif issue.get("severity") == "warning":
                report += f"🟡 **警告**: {issue.get('description')}\n"
            else:
                report += f"ℹ️ **提示**: {issue.get('description')}\n"

        report += "\n"
        return report
