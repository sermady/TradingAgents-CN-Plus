# -*- coding: utf-8 -*-
"""
报告一致性校验器

在生成最终报告前，校验各子报告的数据一致性：
1. 检测投资建议矛盾，并在最终报告中明确说明调和逻辑
2. 校验必填字段（目标价、止损位、置信度等）
3. 检查数据来源一致性
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# 导入日志
try:
    from tradingagents.utils.logging_init import get_logger
    logger = get_logger("report_validator")
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """验证结果数据类"""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations_conflict: bool = False
    conflict_resolution: str = ""
    missing_fields: List[str] = field(default_factory=list)
    data_inconsistencies: List[Dict[str, Any]] = field(default_factory=list)


class ReportValidator:
    """报告一致性校验器"""

    # 必填字段定义
    REQUIRED_FIELDS = {
        "final_trade_decision": ["recommendation", "target_price", "confidence"],
        "fundamentals_report": ["pe_ratio", "current_price"],
        "technical_report": ["current_price", "volume"],
        "sentiment_report": ["sentiment_score"],
    }

    # 投资建议映射
    RECOMMENDATION_MAPPING = {
        "买入": 1,
        "持有": 0,
        "卖出": -1,
        "强烈买入": 2,
        "强烈卖出": -2,
    }

    def __init__(self):
        self.validation_result = ValidationResult()

    def validate_all_reports(
        self,
        reports: Dict[str, str],
        stock_code: str,
        company_name: str
    ) -> ValidationResult:
        """
        验证所有报告的一致性

        Args:
            reports: 报告字典，key为报告类型，value为报告内容
            stock_code: 股票代码
            company_name: 公司名称

        Returns:
            ValidationResult: 验证结果
        """
        self.validation_result = ValidationResult()

        # 1. 检查必填字段
        self._check_required_fields(reports)

        # 2. 检测投资建议矛盾
        self._check_recommendation_conflicts(reports)

        # 3. 检查价格数据一致性
        self._check_price_consistency(reports)

        # 4. 检查成交量数据一致性
        self._check_volume_consistency(reports)

        # 5. 检查公司名称一致性
        self._check_company_name_consistency(reports, stock_code, company_name)

        # 设置最终验证状态
        if self.validation_result.errors:
            self.validation_result.is_valid = False

        return self.validation_result

    def _check_required_fields(self, reports: Dict[str, str]) -> None:
        """检查必填字段"""
        for report_type, content in reports.items():
            if report_type in self.REQUIRED_FIELDS:
                required = self.REQUIRED_FIELDS[report_type]
                for field_name in required:
                    if not self._field_exists_in_report(content, field_name):
                        self.validation_result.missing_fields.append(
                            f"{report_type}: {field_name}"
                        )
                        self.validation_result.warnings.append(
                            f"报告 {report_type} 缺少必填字段: {field_name}"
                        )

    def _field_exists_in_report(self, content: str, field_name: str) -> bool:
        """检查字段是否存在于报告中"""
        if not content:
            return False

        # 字段名称映射到可能的中文表述
        field_patterns = {
            "recommendation": [r"投资建议", r"交易建议", r"建议", r"买入|持有|卖出"],
            "target_price": [r"目标价", r"目标价位", r"价格目标"],
            "confidence": [r"置信度", r"信心程度", r"确定性"],
            "pe_ratio": [r"市盈率", r"P/E", r"PE"],
            "current_price": [r"当前价", r"现价", r"股价"],
            "volume": [r"成交量", r"交易量"],
            "sentiment_score": [r"情绪评分", r"情绪指数", r"情绪"],
        }

        patterns = field_patterns.get(field_name, [field_name])
        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        return False

    def _check_recommendation_conflicts(self, reports: Dict[str, str]) -> None:
        """检测投资建议矛盾"""
        recommendations = {}

        # 从各报告提取投资建议
        for report_type, content in reports.items():
            if content:
                rec = self._extract_recommendation(content)
                if rec:
                    recommendations[report_type] = rec

        if len(recommendations) < 2:
            return

        # 检查是否存在矛盾
        rec_values = list(recommendations.values())
        rec_scores = [self.RECOMMENDATION_MAPPING.get(r, 0) for r in rec_values]

        # 如果存在买入和卖出的矛盾
        has_buy = any(s > 0 for s in rec_scores)
        has_sell = any(s < 0 for s in rec_scores)

        if has_buy and has_sell:
            self.validation_result.recommendations_conflict = True

            # 生成调和逻辑说明
            conflict_details = []
            for report_type, rec in recommendations.items():
                conflict_details.append(f"{report_type}: {rec}")

            self.validation_result.conflict_resolution = self._generate_conflict_resolution(
                recommendations
            )

            self.validation_result.warnings.append(
                f"检测到投资建议矛盾: {', '.join(conflict_details)}"
            )

    def _extract_recommendation(self, content: str) -> Optional[str]:
        """从报告内容中提取投资建议"""
        patterns = [
            r"最终交易建议[：:\s]*\*{0,2}(买入|持有|卖出|强烈买入|强烈卖出)\*{0,2}",
            r"投资建议[：:\s]*\*{0,2}(买入|持有|卖出|强烈买入|强烈卖出)\*{0,2}",
            r"建议[：:\s]*\*{0,2}(买入|持有|卖出)\*{0,2}",
            r"\*{2}(买入|持有|卖出)\*{2}",
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)

        return None

    def _generate_conflict_resolution(self, recommendations: Dict[str, str]) -> str:
        """生成投资建议矛盾的调和逻辑说明"""
        resolution = "## 投资建议调和说明\n\n"
        resolution += "各分析维度存在不同观点，综合考虑如下：\n\n"

        # 按建议类型分组
        buy_reports = []
        hold_reports = []
        sell_reports = []

        for report_type, rec in recommendations.items():
            if "买入" in rec:
                buy_reports.append(report_type)
            elif "卖出" in rec:
                sell_reports.append(report_type)
            else:
                hold_reports.append(report_type)

        if buy_reports:
            resolution += f"**看多观点** ({', '.join(buy_reports)}): "
            resolution += "基于技术面/基本面积极信号\n\n"

        if sell_reports:
            resolution += f"**看空观点** ({', '.join(sell_reports)}): "
            resolution += "基于风险因素/估值压力\n\n"

        if hold_reports:
            resolution += f"**中性观点** ({', '.join(hold_reports)}): "
            resolution += "建议观望等待更明确信号\n\n"

        # 最终调和结论
        resolution += "**调和结论**: "
        if len(buy_reports) > len(sell_reports):
            resolution += "多数分析维度看多，但需关注空头观点提示的风险因素，建议谨慎买入或分批建仓。\n"
        elif len(sell_reports) > len(buy_reports):
            resolution += "多数分析维度看空，建议减仓或观望，关注多头观点中的潜在机会。\n"
        else:
            resolution += "多空观点势均力敌，建议维持现有仓位观望，等待更明确的市场信号。\n"

        return resolution

    def _check_price_consistency(self, reports: Dict[str, str]) -> None:
        """检查价格数据一致性"""
        prices = {}

        for report_type, content in reports.items():
            if content:
                price = self._extract_price(content)
                if price:
                    prices[report_type] = price

        if len(prices) < 2:
            return

        # 检查价格差异
        price_values = list(prices.values())
        max_price = max(price_values)
        min_price = min(price_values)

        if min_price > 0:
            price_diff_pct = (max_price - min_price) / min_price * 100

            if price_diff_pct > 5:  # 差异超过5%
                self.validation_result.data_inconsistencies.append({
                    "type": "price",
                    "description": f"价格数据差异 {price_diff_pct:.2f}%",
                    "details": prices
                })
                self.validation_result.warnings.append(
                    f"价格数据不一致，差异达 {price_diff_pct:.2f}%: {prices}"
                )

    def _extract_price(self, content: str) -> Optional[float]:
        """从报告内容中提取当前价格"""
        patterns = [
            r"当前价[格位]?[：:\s]*[¥￥$]?\s*(\d+\.?\d*)",
            r"现价[：:\s]*[¥￥$]?\s*(\d+\.?\d*)",
            r"股价[：:\s]*[¥￥$]?\s*(\d+\.?\d*)",
            r"收盘价[：:\s]*[¥￥$]?\s*(\d+\.?\d*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue

        return None

    def _check_volume_consistency(self, reports: Dict[str, str]) -> None:
        """检查成交量数据一致性"""
        volumes = {}

        for report_type, content in reports.items():
            if content:
                volume = self._extract_volume(content)
                if volume:
                    volumes[report_type] = volume

        if len(volumes) < 2:
            return

        # 检查成交量差异
        volume_values = list(volumes.values())
        max_volume = max(volume_values)
        min_volume = min(volume_values)

        if min_volume > 0:
            volume_diff_ratio = max_volume / min_volume

            if volume_diff_ratio > 2:  # 差异超过2倍
                self.validation_result.data_inconsistencies.append({
                    "type": "volume",
                    "description": f"成交量数据差异 {volume_diff_ratio:.2f} 倍",
                    "details": volumes
                })
                self.validation_result.warnings.append(
                    f"成交量数据不一致，差异达 {volume_diff_ratio:.2f} 倍: {volumes}"
                )

    def _extract_volume(self, content: str) -> Optional[float]:
        """从报告内容中提取成交量"""
        patterns = [
            r"成交量[：:\s]*([0-9,]+\.?\d*)\s*股",
            r"成交量[：:\s]*([0-9,]+\.?\d*)\s*万股",
            r"交易量[：:\s]*([0-9,]+\.?\d*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    value_str = match.group(1).replace(",", "")
                    value = float(value_str)
                    # 如果是万股，转换为股
                    if "万股" in pattern:
                        value *= 10000
                    return value
                except ValueError:
                    continue

        return None

    def _check_company_name_consistency(
        self,
        reports: Dict[str, str],
        stock_code: str,
        company_name: str
    ) -> None:
        """检查公司名称一致性"""
        for report_type, content in reports.items():
            if content:
                # 检查是否包含正确的股票代码
                if stock_code not in content:
                    self.validation_result.warnings.append(
                        f"报告 {report_type} 可能未提及股票代码 {stock_code}"
                    )

    def generate_validation_report(self) -> str:
        """生成验证报告"""
        report = "# 报告一致性验证结果\n\n"

        # 验证状态
        status = "✅ 通过" if self.validation_result.is_valid else "❌ 未通过"
        report += f"**验证状态**: {status}\n\n"

        # 错误信息
        if self.validation_result.errors:
            report += "## 错误\n\n"
            for error in self.validation_result.errors:
                report += f"- ❌ {error}\n"
            report += "\n"

        # 警告信息
        if self.validation_result.warnings:
            report += "## 警告\n\n"
            for warning in self.validation_result.warnings:
                report += f"- ⚠️ {warning}\n"
            report += "\n"

        # 缺失字段
        if self.validation_result.missing_fields:
            report += "## 缺失字段\n\n"
            for field in self.validation_result.missing_fields:
                report += f"- {field}\n"
            report += "\n"

        # 数据不一致
        if self.validation_result.data_inconsistencies:
            report += "## 数据不一致\n\n"
            for inconsistency in self.validation_result.data_inconsistencies:
                report += f"### {inconsistency['type']}\n"
                report += f"{inconsistency['description']}\n\n"
            report += "\n"

        # 投资建议矛盾调和
        if self.validation_result.recommendations_conflict:
            report += self.validation_result.conflict_resolution
            report += "\n"

        report += f"\n---\n*验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"

        return report


def validate_reports(
    reports: Dict[str, str],
    stock_code: str,
    company_name: str
) -> Tuple[ValidationResult, str]:
    """
    验证报告一致性的便捷函数

    Args:
        reports: 报告字典
        stock_code: 股票代码
        company_name: 公司名称

    Returns:
        Tuple[ValidationResult, str]: (验证结果, 验证报告文本)
    """
    validator = ReportValidator()
    result = validator.validate_all_reports(reports, stock_code, company_name)
    report = validator.generate_validation_report()
    return result, report
