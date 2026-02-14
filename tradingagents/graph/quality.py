# -*- coding: utf-8 -*-
# TradingAgents/graph/quality.py
"""
报告质量检查相关逻辑
"""

from typing import Dict, Any

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("agents")


class QualityChecker:
    """质量检查器"""

    @staticmethod
    def run_quality_checks(final_state: dict):
        """
        运行报告质量检查并记录结果

        Args:
            final_state: 最终状态字典，包含所有生成的报告
        """
        try:
            # 收集所有报告
            reports = {}
            report_types = [
                "market_report",
                "fundamentals_report",
                "news_report",
                "sentiment_report",
                "china_market_report",
                "investment_plan",
                "trader_investment_plan",
                "final_trade_decision",
            ]

            for report_type in report_types:
                content = final_state.get(report_type, "")
                if content and isinstance(content, str):
                    reports[report_type] = content

            if not reports:
                logger.debug("[质量检查] 无报告内容可检查")
                return

            # 1. 报告一致性检查
            from tradingagents.utils.report_consistency_checker import (
                ReportConsistencyChecker,
            )

            checker = ReportConsistencyChecker()
            issues = checker.check_all_reports(reports)

            if issues:
                logger.warning(f"[质量检查] 发现 {len(issues)} 个一致性问题")
                for issue in issues:
                    logger.warning(
                        f"[质量检查] {issue.severity}: {issue.description} "
                        f"(涉及: {', '.join(issue.source_reports)})"
                    )
                # 将问题保存到状态中
                final_state["quality_issues"] = issues
                final_state["consistency_summary"] = (
                    checker.generate_consistency_summary()
                )

            # 2. 数据质量检查
            from tradingagents.utils.data_quality_filter import DataQualityFilter

            data_issues = []

            # 检查基本面报告的数据质量
            fundamentals_content = reports.get("fundamentals_report", "")
            if fundamentals_content:
                data_issues.extend(
                    DataQualityFilter.check_financial_data_quality(fundamentals_content)
                )

            if data_issues:
                logger.info(f"[质量检查] 发现 {len(data_issues)} 个数据质量问题")
                for issue in data_issues:
                    logger.info(
                        f"[质量检查] {issue['severity']}: {issue['description']}"
                    )
                if "quality_issues" not in final_state:
                    final_state["quality_issues"] = []
                final_state["quality_issues"].extend(data_issues)

            # 3. 生成交叉引用摘要
            from tradingagents.utils.cross_reference_generator import (
                CrossReferenceGenerator,
            )

            perspective_summary = CrossReferenceGenerator.generate_perspective_summary(
                reports
            )
            final_state["perspective_summary"] = perspective_summary

            # 记录检查结果
            total_issues = len(issues) + len(data_issues)
            logger.info(f"[质量检查] 检查完成: {total_issues} 个问题")

        except Exception as e:
            logger.error(f"[质量检查] 执行失败: {e}", exc_info=True)

    @staticmethod
    def apply_quality_results_to_decision(final_state: dict, decision: dict):
        """
        将质量检查结果应用到最终决策中

        Args:
            final_state: 包含质量检查结果的最终状态
            decision: 待更新的决策字典
        """
        # 获取质量检查结果
        quality_issues = final_state.get("quality_issues", [])
        data_issues = final_state.get("data_quality_issues", [])
        consistency_summary = final_state.get("consistency_summary", "")
        perspective_summary = final_state.get("perspective_summary", "")

        # 统计严重程度
        critical_count = sum(
            1 for i in quality_issues if getattr(i, "severity", None) == "critical"
        )
        warning_count = sum(
            1 for i in quality_issues if getattr(i, "severity", None) == "warning"
        )
        data_warning_count = sum(
            1 for i in data_issues if i.get("severity") == "warning"
        )

        # 添加质量检查结果到决策中
        decision["quality_issues"] = [
            {
                "severity": getattr(i, "severity", "info"),
                "description": getattr(i, "description", ""),
                "source": ", ".join(getattr(i, "source_reports", [])),
            }
            for i in quality_issues
        ]
        decision["data_quality_issues"] = data_issues
        decision["consistency_summary"] = consistency_summary
        decision["perspective_summary"] = perspective_summary

        # 根据严重程度调整置信度
        original_confidence = decision.get("confidence", 0.7)
        adjusted_confidence = original_confidence

        if critical_count > 0:
            # 严重问题：置信度减半
            adjusted_confidence = original_confidence * 0.5
            logger.warning(
                f"[质量检查] 存在{critical_count}个严重一致性问题，置信度从{original_confidence:.2f}降至{adjusted_confidence:.2f}"
            )
        elif warning_count >= 2:
            # 多个警告：置信度降低20%
            adjusted_confidence = original_confidence * 0.8
            logger.warning(
                f"[质量检查] 存在{warning_count}个警告，置信度从{original_confidence:.2f}降至{adjusted_confidence:.2f}"
            )
        elif data_warning_count > 0:
            # 数据质量问题：置信度降低10%
            adjusted_confidence = original_confidence * 0.9
            logger.warning(
                f"[质量检查] 存在{data_warning_count}个数据质量问题，置信度从{original_confidence:.2f}降至{adjusted_confidence:.2f}"
            )

        # 确保置信度不低于0.1
        decision["confidence"] = max(adjusted_confidence, 0.1)

        # 添加质量警告信息到决策理由中
        if critical_count > 0 or warning_count > 0 or data_warning_count > 0:
            original_reasoning = decision.get("reasoning", "")
            quality_warning = f"\n\n⚠️ 质量提醒: 检测到{critical_count}个严重问题、{warning_count}个警告、{data_warning_count}个数据质量问题。"
            decision["reasoning"] = original_reasoning + quality_warning
