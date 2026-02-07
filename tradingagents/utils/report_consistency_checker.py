# -*- coding: utf-8 -*-
"""
报告一致性检查器

检测 AI 生成的各分析师报告之间的矛盾和不一致
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re


class RecommendationLevel(Enum):
    """投资建议等级"""

    STRONG_BUY = 1
    BUY = 2
    HOLD = 3
    SELL = 4
    STRONG_SELL = 5


@dataclass
class ConsistencyIssue:
    """一致性问题"""

    severity: str  # critical, warning, info
    source_reports: List[str]  # 涉及的报告
    description: str  # 问题描述
    suggestion: str  # 修复建议


class ReportConsistencyChecker:
    """报告一致性检查器"""

    # 建议等级映射
    RECOMMENDATION_MAP = {
        "强烈买入": RecommendationLevel.STRONG_BUY,
        "买入": RecommendationLevel.BUY,
        "持有": RecommendationLevel.HOLD,
        "卖出": RecommendationLevel.SELL,
        "强烈卖出": RecommendationLevel.STRONG_SELL,
        "谨慎看多": RecommendationLevel.BUY,
        "谨慎看空": RecommendationLevel.SELL,
        "逢低买入": RecommendationLevel.BUY,
        "立即止盈": RecommendationLevel.SELL,
        "坚决回避": RecommendationLevel.STRONG_SELL,
    }

    def __init__(self):
        self.issues: List[ConsistencyIssue] = []

    def check_all_reports(self, reports: Dict[str, str]) -> List[ConsistencyIssue]:
        """
        检查所有报告的一致性

        Args:
            reports: 包含所有报告的字典，键为报告类型，值为报告内容

        Returns:
            List[ConsistencyIssue]: 发现的问题列表
        """
        self.issues = []

        # 检查1: 投资建议一致性
        self._check_recommendation_consistency(reports)

        # 检查2: 价格数据一致性
        self._check_price_consistency(reports)

        # 检查3: 成交量数据完整性
        self._check_volume_consistency(reports)

        # 检查4: 财务数据计算逻辑一致性（检查AI是否用错公式）
        self._check_financial_calculation_logic(reports)

        return self.issues

    def _check_recommendation_consistency(self, reports: Dict[str, str]):
        """检查各报告的投资建议是否一致"""
        recommendations = {}

        for report_type, content in reports.items():
            if (
                "investment_plan" in report_type
                or "trader" in report_type
                or "decision" in report_type
            ):
                rec = self._extract_recommendation(content)
                if rec:
                    # 提取关键词用于映射
                    rec_keyword = self._extract_recommendation_keyword(rec)
                    if rec_keyword:
                        recommendations[report_type] = rec_keyword

        if len(recommendations) < 2:
            return  # 需要至少2个报告才能比较

        # 检查是否存在严重矛盾
        rec_levels = [
            self.RECOMMENDATION_MAP.get(r, RecommendationLevel.HOLD).value
            for r in recommendations.values()
        ]

        # 阈值设为 2：买入(2) vs 卖出(4) 差异为2，已构成矛盾
        if max(rec_levels) - min(rec_levels) >= 2:
            self.issues.append(
                ConsistencyIssue(
                    severity="critical",
                    source_reports=list(recommendations.keys()),
                    description=f"投资建议严重不一致: {recommendations}",
                    suggestion="建议在最终决策中明确说明各报告的观点差异，并给出综合判断依据",
                )
            )

    def _check_price_consistency(self, reports: Dict[str, str]):
        """检查各报告中的价格数据是否一致"""
        prices = {}

        for report_type, content in reports.items():
            # 提取当前价格 - 支持多种格式
            patterns = [
                r"当前价[^\d]*(¥?\d+\.?\d*)",
                r"最新收盘价[^\d]*(¥?\d+\.?\d*)",
                r"收盘价[^\d]*(¥?\d+\.?\d*)",
                r"当前价格[^\d]*(¥?\d+\.?\d*)",
            ]
            for pattern in patterns:
                price_match = re.search(pattern, content)
                if price_match:
                    prices[report_type] = float(price_match.group(1).replace("¥", ""))
                    break

        if len(prices) < 2:
            return

        price_values = list(prices.values())
        if (
            max(price_values) - min(price_values) > min(price_values) * 0.05
        ):  # 5%差异阈值
            self.issues.append(
                ConsistencyIssue(
                    severity="warning",
                    source_reports=list(prices.keys()),
                    description=f"价格数据不一致: {prices}",
                    suggestion="统一使用数据源管理器提供的实时价格",
                )
            )

    def _check_volume_consistency(self, reports: Dict[str, str]):
        """检查成交量数据完整性"""
        for report_type, content in reports.items():
            if "market_report" in report_type:
                # 检查是否报告缺少单日成交量数据
                if (
                    "未提供" in content or "缺少" in content
                ) and "单日成交量" in content:
                    self.issues.append(
                        ConsistencyIssue(
                            severity="info",
                            source_reports=[report_type],
                            description="技术报告缺少单日成交量数据",
                            suggestion="确认数据源管理器已更新成交量增强功能",
                        )
                    )

    def _check_financial_calculation_logic(self, reports: Dict[str, str]):
        """
        检查财务数据计算逻辑的一致性

        注意：PE_TTM 高值本身不是异常（军工股常见），但需要检查 AI 是否
        用静态利润去错误地"验算"PE_TTM
        """
        for report_type, content in reports.items():
            if "fundamentals_report" in report_type:
                # 检查 AI 是否用错误口径"验算"估值指标
                # 正确做法：
                # - PE_TTM 应该用 TTM 利润计算（过去12个月滚动）
                # - PE静态应该用年报/最新期归母净利润计算
                # - PB应该用净资产计算
                # - PS应该用营收计算

                # 检查1: PE_TTM 验算错误
                if "PE_TTM" in content and "验算" in content:
                    # 查找类似 "市值 ÷ 归母净利润 = XX倍" 的验算
                    if re.search(r"验算.*归母净利润|归母净利润.*验算", content):
                        self.issues.append(
                            ConsistencyIssue(
                                severity="warning",
                                source_reports=[report_type],
                                description="用错误口径验算PE_TTM（使用了归母净利润而非TTM净利润）",
                                suggestion="PE_TTM应该用过去12个月滚动利润计算，不能用单期归母净利润验算",
                            )
                        )

                # 检查2: 提取错误的验算公式（查找PE相关验算中使用的利润字段）
                pe_calc_matches = re.findall(
                    r"PE[_\(]?TTM[\)\)]?\s*[=：]\s*[\d.]+\s*[÷/]\s*[\d.]+", content
                )
                for match in pe_calc_matches:
                    # 检查验算公式附近是否有"归母净利润"字样
                    match_start = content.find(match)
                    context = content[
                        max(0, match_start - 50) : match_start + len(match) + 50
                    ]
                    if "归母净利润" in context and "TTM" not in context.upper():
                        self.issues.append(
                            ConsistencyIssue(
                                severity="warning",
                                source_reports=[report_type],
                                description="PE_TTM验算使用了错误的利润口径（使用了归母净利润而非TTM净利润）",
                                suggestion="PE_TTM=市值/TTM净利润，PE静态=市值/归母净利润，两者不能混用",
                            )
                        )

                # 检查3: AI声称PE_TTM数据错误
                if re.search(r"PE_TTM.*错误|错误.*PE_TTM|严重高估|严重低估", content):
                    # 查找是否使用了错误的验算方法
                    if re.search(r"验算.*归母净利润|归母净利润.*验算", content):
                        self.issues.append(
                            ConsistencyIssue(
                                severity="critical",
                                source_reports=[report_type],
                                description="基于错误验算声称PE_TTM错误（使用归母净利润验算TTM指标）",
                                suggestion="PE_TTM应该用TTM净利润验算。如果验算结果不一致，请检查是否使用了正确的利润口径",
                            )
                        )

    def _extract_recommendation_keyword(self, text: str) -> Optional[str]:
        """
        从建议文本中提取关键词用于映射

        Args:
            text: 建议文本

        Returns:
            Optional[str]: 提取的关键词
        """
        # 定义关键词模式，按优先级排序
        patterns = [
            r"(强烈买入|强力买入|重仓买入)",
            r"(强烈卖出|坚决回避|清仓)",
            r"(谨慎买入|谨慎看多|逢低买入)",
            r"(谨慎卖出|谨慎看空|逢高卖出)",
            r"(立即止盈|建议减仓)",
            r"(买入|看多)",
            r"(卖出|看空)",
            r"(持有|观望|中性)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return None

    def _extract_recommendation(self, content: str) -> Optional[str]:
        """从报告内容中提取投资建议"""
        # 查找包含建议的段落
        patterns = [
            r"(评级|建议|操作策略)[：:]\s*([^\n]+)",
            r"(买入|卖出|持有|回避|止盈)",
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(0)

        return None

    def generate_consistency_summary(self) -> str:
        """生成一致性检查摘要"""
        if not self.issues:
            return "✅ 所有报告检查通过，未发现一致性问题。"

        summary = f"⚠️ 发现 {len(self.issues)} 个一致性问题:\n\n"

        for i, issue in enumerate(self.issues, 1):
            icon = (
                "🔴"
                if issue.severity == "critical"
                else "🟡"
                if issue.severity == "warning"
                else "ℹ️"
            )
            summary += f"{icon} **问题{i}** ({issue.severity}): {issue.description}\n"
            summary += f"   涉及报告: {', '.join(issue.source_reports)}\n"
            summary += f"   建议: {issue.suggestion}\n\n"

        return summary
