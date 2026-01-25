# -*- coding: utf-8 -*-
"""
基本面数据验证器

验证PE、PB、PS、市值、财务数据等基本面指标的准确性
"""

from typing import Dict, Any, List, Optional
import asyncio

from .base_validator import BaseDataValidator, ValidationResult, ValidationSeverity


class FundamentalsValidator(BaseDataValidator):
    """
    基本面数据验证器

    功能:
    - PE/PB/PS等估值指标交叉验证
    - 市值计算验证
    - 财务数据一致性检查
    - PS比率自动计算和验证
    """

    # 基本面指标合理性范围
    VALID_RANGES = {
        'PE': (-500, 500),          # 市盈率 (允许负值)
        'PB': (0, 100),             # 市净率
        'PS': (0, 100),             # 市销率
        'ROE': (-100, 100),         # 净资产收益率 (%)
        'ROA': (-100, 100),         # 总资产收益率 (%)
        'margin': (0, 100),         # 利润率 (%)
        'debt_ratio': (0, 200),     # 资产负债率 (%)
    }

    def __init__(self, tolerance: float = 0.05):
        super().__init__(tolerance)

    def validate(self, symbol: str, data: Dict[str, Any]) -> ValidationResult:
        """
        验证基本面数据

        Args:
            symbol: 股票代码
            data: 包含基本面指标的数据字典

        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult(
            is_valid=True,
            confidence=0.0,
            source=data.get('source', 'unknown')
        )

        # 1. 验证PE(市盈率)
        if 'PE' in data or 'pe_ratio' in data:
            self._validate_pe_ratio(data, result)

        # 2. 验证PB(市净率)
        if 'PB' in data or 'pb_ratio' in data:
            self._validate_pb_ratio(data, result)

        # 3. 验证PS(市销率) - 重点验证!
        if 'PS' in data or 'ps_ratio' in data:
            self._validate_ps_ratio(data, result)
        elif all(k in data for k in ['market_cap', 'revenue'] or k in data for k in ['total市值', '总营收']):
            # 如果有市值和营收,自动计算PS并验证
            self._calculate_and_validate_ps(data, result)

        # 4. 验证市值
        if 'market_cap' in data or 'total市值' in data:
            self._validate_market_cap(data, result)

        # 5. 验证ROE/ROA
        if 'ROE' in data or 'ROA' in data:
            self._validate_roe_roa(data, result)

        # 6. 验证利润率
        if any(k in data for k in ['gross_margin', 'net_margin', '毛利率', '净利率']):
            self._validate_margins(data, result)

        # 7. 验证资产负债率
        if 'debt_ratio' in data or '资产负债率' in data:
            self._validate_debt_ratio(data, result)

        # 8. 验证市值和股价的一致性
        has_english_keys = all(k in data for k in ['market_cap', 'share_count', 'current_price'])
        has_chinese_keys = all(k in data for k in ['total市值', '总股本', '当前价'])
        if has_english_keys or has_chinese_keys:
            self._validate_market_cap_consistency(data, result)

        # 9. 计算总体置信度
        if result.discrepancies:
            warning_count = len(result.get_issues_by_severity(ValidationSeverity.WARNING))
            error_count = len(result.get_issues_by_severity(ValidationSeverity.ERROR))
            result.confidence = max(0.0, 1.0 - (warning_count * 0.1) - (error_count * 0.3))
        else:
            result.confidence = 1.0

        return result

    async def cross_validate(self, symbol: str, sources: List[str],
                            metric: str) -> ValidationResult:
        """
        多源交叉验证基本面指标

        Args:
            symbol: 股票代码
            sources: 数据源列表
            metric: 指标名称

        Returns:
            ValidationResult: 交叉验证结果
        """
        result = ValidationResult(
            is_valid=True,
            confidence=0.0,
            source='multi_source',
            metadata={'metric': metric, 'sources_checked': sources}
        )

        # 这里实现多源获取和比较逻辑
        # 类似PriceValidator的实现
        # 暂时返回基本结果

        return result

    def _validate_pe_ratio(self, data: Dict[str, Any],
                          result: ValidationResult) -> None:
        """验证市盈率"""
        pe = data.get('PE') or data.get('pe_ratio')

        if pe is not None:
            min_pe, max_pe = self.VALID_RANGES['PE']

            if not self.check_value_in_range(pe, min_pe, max_pe, 'PE'):
                result.add_issue(
                    ValidationSeverity.ERROR,
                    f"PE={pe} 超出合理范围 [{min_pe}, {max_pe}]",
                    field='PE',
                    actual=pe
                )

            # 负PE说明亏损,提醒但不标记为错误
            if pe < 0:
                result.add_issue(
                    ValidationSeverity.INFO,
                    f"PE={pe} 为负值,公司可能处于亏损状态",
                    field='PE',
                    actual=pe
                )

    def _validate_pb_ratio(self, data: Dict[str, Any],
                          result: ValidationResult) -> None:
        """验证市净率"""
        pb = data.get('PB') or data.get('pb_ratio')

        if pb is not None:
            min_pb, max_pb = self.VALID_RANGES['PB']

            if not self.check_value_in_range(pb, min_pb, max_pb, 'PB'):
                result.add_issue(
                    ValidationSeverity.WARNING,
                    f"PB={pb} 超出常规范围 [{min_pb}, {max_pb}]",
                    field='PB',
                    actual=pb
                )

            # PB < 1 可能表示被低估
            if pb < 1:
                result.add_issue(
                    ValidationSeverity.INFO,
                    f"PB={pb} 小于1,股价可能低于净资产",
                    field='PB',
                    actual=pb
                )

    def _validate_ps_ratio(self, data: Dict[str, Any],
                          result: ValidationResult) -> None:
        """
        验证市销率(PS Ratio)

        PS = 市值 / 营收

        这是修复605589问题的关键方法!
        """
        ps = data.get('PS') or data.get('ps_ratio')

        if ps is None:
            return

        min_ps, max_ps = self.VALID_RANGES['PS']

        # 检查PS是否在合理范围内
        if not self.check_value_in_range(ps, min_ps, max_ps, 'PS'):
            result.add_issue(
                ValidationSeverity.ERROR,
                f"PS={ps} 超出合理范围 [{min_ps}, {max_ps}]",
                field='PS',
                actual=ps
            )

        # PS极低值警告(可能是计算错误)
        if ps < 0.5:
            result.add_issue(
                ValidationSeverity.WARNING,
                f"PS={ps} 过低,可能存在计算错误",
                field='PS',
                actual=ps
            )
            # 尝试重新计算
            if 'market_cap' in data and ('revenue' in data or 'total_revenue' in data):
                calculated_ps = self._calculate_ps_from_components(data)
                if calculated_ps and abs(calculated_ps - ps) / ps > 0.5:
                    result.add_issue(
                        ValidationSeverity.ERROR,
                        f"PS计算错误! 报告值={ps}, 正确值应为≈{calculated_ps:.2f}",
                        field='PS',
                        actual=ps,
                        expected=calculated_ps
                    )
                    result.suggested_value = calculated_ps

    def _calculate_and_validate_ps(self, data: Dict[str, Any],
                                   result: ValidationResult) -> None:
        """
        从市值和营收自动计算PS并验证

        这是修复PS比率错误的核心方法
        """
        market_cap = data.get('market_cap') or data.get('total市值')
        revenue = data.get('revenue') or data.get('total_revenue') or data.get('总营收')

        if not all([market_cap, revenue]):
            return

        # 确保数值类型
        try:
            market_cap = float(market_cap)
            revenue = float(revenue)
        except (ValueError, TypeError):
            result.add_issue(
                ValidationSeverity.ERROR,
                "市值或营收数据类型错误",
                field='PS'
            )
            return

        # 计算PS
        if revenue > 0:
            calculated_ps = market_cap / revenue

            # 检查数据中是否已有PS值
            existing_ps = data.get('PS') or data.get('ps_ratio')

            if existing_ps:
                # 验证现有PS是否正确
                diff_pct = abs((calculated_ps - existing_ps) / existing_ps) * 100

                if diff_pct > 10:  # 差异超过10%
                    result.add_issue(
                        ValidationSeverity.ERROR,
                        f"PS比率严重错误! 报告值={existing_ps:.2f}, "
                        f"根据市值({market_cap:.2f}亿)和营收({revenue:.2f}亿)计算应为≈{calculated_ps:.2f}",
                        field='PS',
                        actual=existing_ps,
                        expected=calculated_ps
                    )
                    result.suggested_value = calculated_ps
            else:
                # 数据中没有PS,添加建议值
                result.metadata['calculated_ps'] = calculated_ps
                result.add_issue(
                    ValidationSeverity.INFO,
                    f"已自动计算PS比率={calculated_ps:.2f}",
                    field='PS'
                )
        else:
            result.add_issue(
                ValidationSeverity.WARNING,
                "营收为0或负值,无法计算PS比率",
                field='PS'
            )

    def _calculate_ps_from_components(self, data: Dict[str, Any]) -> Optional[float]:
        """
        从市值和营收计算PS

        Returns:
            Optional[float]: 计算出的PS值
        """
        market_cap = data.get('market_cap') or data.get('total市值')
        revenue = data.get('revenue') or data.get('total_revenue') or data.get('总营收')

        if not all([market_cap, revenue]) or revenue == 0:
            return None

        try:
            return float(market_cap) / float(revenue)
        except (ValueError, TypeError, ZeroDivisionError):
            return None

    def _validate_market_cap(self, data: Dict[str, Any],
                            result: ValidationResult) -> None:
        """验证市值"""
        market_cap = data.get('market_cap') or data.get('total市值')

        if market_cap is not None:
            # 市值必须在合理范围内(1亿 - 10万亿)
            if not self.check_value_in_range(market_cap, 1, 100000, 'market_cap'):
                result.add_issue(
                    ValidationSeverity.WARNING,
                    f"市值={market_cap}亿 超出常规范围",
                    field='market_cap',
                    actual=market_cap
                )

    def _validate_roe_roa(self, data: Dict[str, Any],
                         result: ValidationResult) -> None:
        """验证ROE和ROA"""
        roe = data.get('ROE') or data.get('roe')
        roa = data.get('ROA') or data.get('roa')

        # ROE验证
        if roe is not None:
            min_roe, max_roe = self.VALID_RANGES['ROE']
            if not self.check_value_in_range(roe, min_roe, max_roe, 'ROE'):
                result.add_issue(
                    ValidationSeverity.ERROR,
                    f"ROE={roe}% 超出合理范围",
                    field='ROE',
                    actual=roe
                )

            # ROE异常高值警告
            if roe > 50:
                result.add_issue(
                    ValidationSeverity.WARNING,
                    f"ROE={roe}% 异常高,需要核查",
                    field='ROE',
                    actual=roe
                )

        # ROA验证
        if roa is not None:
            min_roa, max_roa = self.VALID_RANGES['ROA']
            if not self.check_value_in_range(roa, min_roa, max_roa, 'ROA'):
                result.add_issue(
                    ValidationSeverity.ERROR,
                    f"ROA={roa}% 超出合理范围",
                    field='ROA',
                    actual=roa
                )

        # ROE应该大于ROA(正常情况)
        if roe and roa and roe < roa:
            result.add_issue(
                ValidationSeverity.WARNING,
                f"ROE({roe}%) 小于 ROA({roa}%), 数据可能有误",
                field='ROE/ROA'
            )

    def _validate_margins(self, data: Dict[str, Any],
                         result: ValidationResult) -> None:
        """验证利润率指标"""
        gross_margin = data.get('gross_margin') or data.get('毛利率')
        net_margin = data.get('net_margin') or data.get('净利率')

        # 毛利率验证
        if gross_margin is not None:
            min_margin, max_margin = self.VALID_RANGES['margin']
            if not self.check_value_in_range(gross_margin, min_margin, max_margin, 'gross_margin'):
                result.add_issue(
                    ValidationSeverity.ERROR,
                    f"毛利率={gross_margin}% 超出合理范围",
                    field='gross_margin',
                    actual=gross_margin
                )

        # 净利率验证
        if net_margin is not None:
            min_margin, max_margin = self.VALID_RANGES['margin']
            if not self.check_value_in_range(net_margin, -100, 100, 'net_margin'):
                result.add_issue(
                    ValidationSeverity.ERROR,
                    f"净利率={net_margin}% 超出合理范围",
                    field='net_margin',
                    actual=net_margin
                )

        # 毛利率应该大于净利率
        if gross_margin and net_margin and gross_margin < net_margin:
            result.add_issue(
                ValidationSeverity.ERROR,
                f"毛利率({gross_margin}%) 小于净利率({net_margin}%), 逻辑错误",
                field='margins'
            )

    def _validate_debt_ratio(self, data: Dict[str, Any],
                            result: ValidationResult) -> None:
        """验证资产负债率"""
        debt_ratio = data.get('debt_ratio') or data.get('资产负债率')

        if debt_ratio is not None:
            min_ratio, max_ratio = self.VALID_RANGES['debt_ratio']

            if not self.check_value_in_range(debt_ratio, min_ratio, max_ratio, 'debt_ratio'):
                result.add_issue(
                    ValidationSeverity.ERROR,
                    f"资产负债率={debt_ratio}% 超出合理范围",
                    field='debt_ratio',
                    actual=debt_ratio
                )

            # 高负债率警告
            if debt_ratio > 80:
                result.add_issue(
                    ValidationSeverity.WARNING,
                    f"资产负债率={debt_ratio}% 较高,财务风险较大",
                    field='debt_ratio',
                    actual=debt_ratio
                )

    def _validate_market_cap_consistency(self, data: Dict[str, Any],
                                        result: ValidationResult) -> None:
        """
        验证市值计算的一致性

        市值 = 股价 × 总股本
        """
        market_cap = data.get('market_cap') or data.get('total市值')
        share_count = data.get('share_count') or data.get('总股本')
        price = data.get('current_price') or data.get('当前价')

        if all([market_cap, share_count, price]):
            try:
                # 计算预期市值 (注意单位!)
                # 假设: market_cap单位是亿元, share_count单位是万股, price单位是元
                # 市值(亿) = (股本(万) × 股价) / 10000

                calculated_market_cap = (share_count * price) / 10000

                # 比较,允许10%误差
                if market_cap > 0:
                    diff_pct = abs((calculated_market_cap - market_cap) / market_cap) * 100

                    if diff_pct > 10:
                        result.add_issue(
                            ValidationSeverity.WARNING,
                            f"市值计算不一致: 报告={market_cap:.2f}亿, "
                            f"根据股本({share_count}万股)和股价({price}元)计算={calculated_market_cap:.2f}亿",
                            field='market_cap',
                            actual=market_cap,
                            expected=calculated_market_cap
                        )

            except (ValueError, TypeError, ZeroDivisionError) as e:
                result.add_issue(
                    ValidationSeverity.WARNING,
                    f"市值一致性检查失败: {e}",
                    field='market_cap'
                )
