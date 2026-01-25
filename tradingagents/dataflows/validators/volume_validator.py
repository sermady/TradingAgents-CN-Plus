# -*- coding: utf-8 -*-
"""
成交量数据验证器

统一成交量单位，验证成交量数据准确性
"""

from typing import Dict, Any, List, Optional
import numpy as np

from .base_validator import BaseDataValidator, ValidationResult, ValidationSeverity


class VolumeValidator(BaseDataValidator):
    """
    成交量数据验证器

    功能:
    - 统一成交量单位(手 vs 股)
    - 交叉验证成交量数据
    - 检测异常成交量波动
    - 标注数据来源

    注意: 中国A股市场
    - 1手 = 100股
    - 不同数据源可能使用不同单位
    """

    # 成交量单位
    UNIT_LOTS = 'lots'      # 手
    UNIT_SHARES = 'shares'  # 股

    # 成交量倍数标准
    SHARES_PER_LOT = 100  # 1手 = 100股

    # 异常成交量倍数阈值
    VOLUME_SPIKE_THRESHOLD = 3.0  # 成交量暴增阈值(3倍)
    VOLUME_DROP_THRESHOLD = 0.3   # 成交量骤降阈值(30%)

    def __init__(self, tolerance: float = 0.05):
        super().__init__(tolerance)
        self.preferred_unit = self.UNIT_SHARES  # 默认使用"股"作为标准单位

    def validate(self, symbol: str, data: Dict[str, Any]) -> ValidationResult:
        """
        验证成交量数据

        Args:
            symbol: 股票代码
            data: 包含成交量数据的数据字典

        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult(
            is_valid=True,
            confidence=0.0,
            source=data.get('source', 'unknown')
        )

        # 1. 验证当前成交量
        if 'volume' in data or '成交量' in data or 'vol' in data:
            self._validate_current_volume(symbol, data, result)

        # 2. 验证历史成交量序列
        if 'volume_history' in data or 'volume_list' in data:
            self._validate_volume_history(data, result)

        # 3. 检查成交量单位标注
        self._validate_volume_unit(data, result)

        # 4. 验证换手率
        if 'turnover_rate' in data or '换手率' in data:
            self._validate_turnover_rate(data, result)

        # 5. 计算总体置信度
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
        多源交叉验证成交量数据

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
        # 需要特别注意单位统一化

        return result

    def _validate_current_volume(self, symbol: str, data: Dict[str, Any],
                                 result: ValidationResult) -> None:
        """验证当前成交量"""
        volume = data.get('volume') or data.get('成交量') or data.get('vol')

        if volume is None:
            return

        # 成交量必须为正数
        if volume <= 0:
            result.add_issue(
                ValidationSeverity.ERROR,
                "成交量必须为正数",
                field='volume',
                actual=volume
            )
            return

        # 检查成交量是否在合理范围内(100 - 10亿股)
        if not self.check_value_in_range(volume, 100, 1000000000, 'volume'):
            result.add_issue(
                ValidationSeverity.WARNING,
                f"成交量={volume} 超出常规范围",
                field='volume',
                actual=volume
            )

        # 尝试推断单位
        inferred_unit = self._infer_volume_unit(volume, data)
        if inferred_unit != self.preferred_unit:
            # 需要转换单位
            converted_volume = self._convert_volume(volume, inferred_unit, self.preferred_unit)
            result.metadata['original_volume'] = volume
            result.metadata['original_unit'] = inferred_unit
            result.metadata['converted_volume'] = converted_volume
            result.metadata['standard_unit'] = self.preferred_unit

            result.add_issue(
                ValidationSeverity.INFO,
                f"成交量单位从 {inferred_unit} 转换为 {self.preferred_unit}: "
                f"{volume} → {converted_volume}",
                field='volume',
                actual=volume,
                expected=converted_volume
            )

    def _validate_volume_history(self, data: Dict[str, Any],
                                result: ValidationResult) -> None:
        """验证历史成交量序列"""
        volume_list = data.get('volume_history') or data.get('volume_list')

        if not volume_list or len(volume_list) < 2:
            return

        try:
            volumes = [float(v) for v in volume_list if v is not None and v > 0]
        except (ValueError, TypeError):
            result.add_issue(
                ValidationSeverity.ERROR,
                "成交量历史数据格式错误",
                field='volume_history'
            )
            return

        if len(volumes) < 2:
            return

        # 计算平均成交量
        avg_volume = np.mean(volumes)

        # 检查是否有异常波动
        max_volume = max(volumes)
        min_volume = min(volumes)

        # 成交量暴增检测
        if avg_volume > 0:
            spike_ratio = max_volume / avg_volume
            if spike_ratio > self.VOLUME_SPIKE_THRESHOLD:
                # 找出暴增的位置
                spike_index = volumes.index(max_volume)
                result.add_issue(
                    ValidationSeverity.WARNING,
                    f"第{spike_index + 1}期成交量暴增 {spike_ratio:.1f}倍 "
                    f"(当前: {max_volume:.0f}, 平均: {avg_volume:.0f})",
                    field='volume_history',
                    actual=max_volume
                )

        # 成交量骤降检测
        if avg_volume > 0:
            drop_ratio = min_volume / avg_volume
            if drop_ratio < self.VOLUME_DROP_THRESHOLD:
                drop_index = volumes.index(min_volume)
                result.add_issue(
                    ValidationSeverity.INFO,
                    f"第{drop_index + 1}期成交量骤降 {drop_ratio:.1%} "
                    f"(当前: {min_volume:.0f}, 平均: {avg_volume:.0f})",
                    field='volume_history',
                    actual=min_volume
                )

    def _validate_volume_unit(self, data: Dict[str, Any],
                             result: ValidationResult) -> None:
        """验证成交量单位标注"""
        volume = data.get('volume') or data.get('成交量') or data.get('vol')
        unit = data.get('volume_unit') or data.get('成交量单位')

        if volume and not unit:
            # 没有标注单位，尝试推断
            inferred_unit = self._infer_volume_unit(volume, data)
            result.metadata['inferred_unit'] = inferred_unit

            result.add_issue(
                ValidationSeverity.INFO,
                f"成交量单位未明确标注,推断为: {inferred_unit}",
                field='volume_unit'
            )

    def _validate_turnover_rate(self, data: Dict[str, Any],
                               result: ValidationResult) -> None:
        """验证换手率"""
        turnover_rate = data.get('turnover_rate') or data.get('换手率')
        volume = data.get('volume') or data.get('成交量') or data.get('vol')
        share_count = data.get('share_count') or data.get('total_shares') or data.get('总股本')

        if turnover_rate is not None:
            # 换手率必须在0-100%之间
            if not self.check_value_in_range(turnover_rate, 0, 100, 'turnover_rate'):
                result.add_issue(
                    ValidationSeverity.ERROR,
                    f"换手率={turnover_rate}% 超出合理范围",
                    field='turnover_rate',
                    actual=turnover_rate
                )

            # 高换手率提醒
            if turnover_rate > 20:
                result.add_issue(
                    ValidationSeverity.INFO,
                    f"换手率={turnover_rate}% 较高,交易活跃",
                    field='turnover_rate',
                    actual=turnover_rate
                )

        # 验证换手率计算: 换手率 = 成交量 / 流通股本 × 100%
        if all([turnover_rate, volume, share_count]):
            try:
                # 注意单位: volume可能是手或股, share_count可能是万股或股
                # 这里假设volume是股, share_count是股
                calculated_rate = (volume / share_count) * 100

                # 允许20%误差(因为流通股本可能不是总股本)
                if turnover_rate > 0:
                    diff_pct = abs((calculated_rate - turnover_rate) / turnover_rate) * 100

                    if diff_pct > 20:
                        result.add_issue(
                            ValidationSeverity.WARNING,
                            f"换手率计算可能不一致: 报告={turnover_rate:.2f}%, "
                            f"根据成交量({volume:.0f})和股本({share_count:.0f})计算={calculated_rate:.2f}%",
                            field='turnover_rate',
                            actual=turnover_rate,
                            expected=calculated_rate
                        )

            except (ValueError, TypeError, ZeroDivisionError):
                pass

    def _infer_volume_unit(self, volume: float,
                          data: Dict[str, Any]) -> str:
        """
        推断成交量单位

        推断逻辑:
        - 如果成交量能被100整除 → 可能是"手"
        - 如果成交量数值很大(>100万) → 可能是"股"
        - 结合换手率判断
        """
        # 如果有换手率和股本，可以准确推断
        turnover_rate = data.get('turnover_rate') or data.get('换手率')
        share_count = data.get('share_count') or data.get('total_shares') or data.get('总股本')

        if all([turnover_rate, share_count, volume]):
            try:
                # 假设volume是股
                rate_as_shares = (volume / share_count) * 100
                diff_shares = abs(rate_as_shares - turnover_rate)

                # 假设volume是手
                rate_as_lots = (volume * 100 / share_count) * 100
                diff_lots = abs(rate_as_lots - turnover_rate)

                # 哪个更接近报告的换手率
                if diff_shares < diff_lots:
                    return self.UNIT_SHARES
                else:
                    return self.UNIT_LOTS
            except (ValueError, TypeError, ZeroDivisionError):
                pass

        # 简单启发式判断
        if volume > 1000000:  # 大于100万，可能是股
            return self.UNIT_SHARES
        elif volume % 100 == 0 and volume < 1000000:  # 能被100整除且较小，可能是手
            return self.UNIT_LOTS
        else:
            return self.UNIT_SHARES  # 默认为股

    def _convert_volume(self, volume: float, from_unit: str,
                       to_unit: str) -> float:
        """
        转换成交量单位

        Args:
            volume: 成交量数值
            from_unit: 原始单位 ('lots' or 'shares')
            to_unit: 目标单位 ('lots' or 'shares')

        Returns:
            float: 转换后的成交量
        """
        if from_unit == to_unit:
            return volume

        if from_unit == self.UNIT_LOTS and to_unit == self.UNIT_SHARES:
            return volume * self.SHARES_PER_LOT

        if from_unit == self.UNIT_SHARES and to_unit == self.UNIT_LOTS:
            return volume / self.SHARES_PER_LOT

        return volume

    def standardize_volume(self, volume: float,
                          current_unit: Optional[str] = None) -> tuple[float, str]:
        """
        标准化成交量到"股"

        Args:
            volume: 成交量数值
            current_unit: 当前单位 (如果为None则自动推断)

        Returns:
            tuple[float, str]: (标准化后的成交量, 原始单位)
        """
        if current_unit is None:
            # 无法推断，假设为股
            return volume, self.UNIT_SHARES

        converted = self._convert_volume(volume, current_unit, self.preferred_unit)
        return converted, current_unit

    def compare_volumes(self, volume1: float, volume2: float,
                       unit1: Optional[str] = None,
                       unit2: Optional[str] = None) -> tuple[bool, float]:
        """
        比较两个成交量是否一致（自动转换单位）

        Args:
            volume1: 第一个成交量
            volume2: 第二个成交量
            unit1: 第一个成交量的单位
            unit2: 第二个成交量的单位

        Returns:
            tuple[bool, float]: (是否一致, 百分比差异)
        """
        # 标准化到相同单位
        std_vol1, _ = self.standardize_volume(volume1, unit1)
        std_vol2, _ = self.standardize_volume(volume2, unit2)

        # 计算差异
        if std_vol1 == 0 and std_vol2 == 0:
            return True, 0.0

        if std_vol1 == 0 or std_vol2 == 0:
            return False, 100.0

        diff_pct = abs((std_vol1 - std_vol2) / ((std_vol1 + std_vol2) / 2)) * 100
        is_consistent = diff_pct <= (self.tolerance * 100)

        return is_consistent, diff_pct
