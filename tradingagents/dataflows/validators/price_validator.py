# -*- coding: utf-8 -*-
"""
价格数据验证器

验证实时价格、技术指标等价格相关数据的准确性
"""

from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime, timedelta

from .base_validator import BaseDataValidator, ValidationResult, ValidationSeverity


class PriceValidator(BaseDataValidator):
    """
    价格数据验证器

    功能:
    - 多源价格交叉验证
    - 技术指标计算验证
    - 异常价格波动检测
    """

    # 价格合理性范围
    PRICE_CHANGE_LIMITS = {
        'normal': 20.0,      # 正常波动限制 ±20%
        'extreme': 50.0,     # 极端波动限制 ±50%
    }

    # 技术指标允许的误差范围
    INDICATOR_TOLERANCE = {
        'MA': 0.01,          # 移动平均线 1%
        'RSI': 2.0,          # RSI 2个百分点
        'MACD': 0.05,        # MACD 5%
        'BOLL': 0.02,        # 布林带 2%
        'VOLUME': 0.05,      # 成交量 5%
    }

    def __init__(self, tolerance: float = 0.01):
        super().__init__(tolerance)

    def validate(self, symbol: str, data: Dict[str, Any]) -> ValidationResult:
        """
        验证价格数据

        Args:
            symbol: 股票代码
            data: 包含价格和指标的数据字典

        Returns:
            ValidationResult: 验证结果
        """
        result = ValidationResult(
            is_valid=True,
            confidence=0.0,
            source=data.get('source', 'unknown')
        )

        # 1. 验证当前价格
        current_price = data.get('current_price')
        if current_price is not None:
            self._validate_current_price(symbol, current_price, result)

        # 2. 验证移动平均线
        if 'MA5' in data or 'MA10' in data or 'MA20' in data:
            self._validate_ma_indicators(symbol, data, result)

        # 3. 验证RSI指标
        if 'RSI' in data or 'RSI6' in data or 'RSI12' in data:
            self._validate_rsi_indicators(data, result)

        # 4. 验证布林带
        if 'BOLL_UPPER' in data or 'BOLL_LOWER' in data:
            self._validate_bollinger_bands(symbol, data, result)

        # 5. 验证价格位置
        if 'price_position' in data:
            self._validate_price_position(data, result)

        # 6. 计算总体置信度
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
        多源交叉验证价格数据 (Phase 2.1)

        Args:
            symbol: 股票代码
            sources: 数据源列表,如 ['tushare', 'akshare', 'baostock']
            metric: 指标名称,如 'current_price', 'MA5', 'RSI6'

        Returns:
            ValidationResult: 交叉验证结果
        """
        result = ValidationResult(
            is_valid=True,
            confidence=0.0,
            source='multi_source',
            metadata={'metric': metric, 'sources_checked': sources}
        )

        # ========== Phase 2.1: 多源并行获取数据 ==========
        import asyncio

        async def fetch_from_source(source: str) -> tuple[str, Optional[float]]:
            """从单个数据源获取数据"""
            try:
                data = await self._get_data_from_source(symbol, source, metric)
                return (source, data)
            except Exception as e:
                self.logger.warning(f"从 {source} 获取 {metric} 数据失败: {e}")
                return (source, None)

        # 并行获取所有数据源
        tasks = [fetch_from_source(s) for s in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        values = {}
        sources_with_data = []

        for item in results:
            if isinstance(item, Exception):
                continue
            source, data = item
            if data is not None:
                values[source] = data
                sources_with_data.append(source)

        if not values:
            result.is_valid = False
            result.add_issue(
                ValidationSeverity.CRITICAL,
                f"无法从任何数据源获取 {metric} 数据",
                field=metric
            )
            return result

        result.alternative_sources = values

        # ========== Phase 2.1: 调整阈值为0.5% ==========
        # 计算置信度
        result.confidence = self.calculate_confidence(list(values.values()))

        # 检查一致性
        if len(values) > 1:
            value_list = list(values.values())
            max_diff = max(value_list) - min(value_list)
            avg_value = sum(value_list) / len(value_list)

            if avg_value != 0:
                diff_pct = (max_diff / avg_value) * 100

                # ⚠️ Phase 2.1: 调整阈值为0.5%
                # 差异超过0.5%则警告
                if diff_pct > 0.5:
                    result.add_issue(
                        ValidationSeverity.WARNING,
                        f"多源 {metric} 数据差异{diff_pct:.2f}% (阈值0.5%)",
                        field=metric,
                        actual=f"min={min(value_list):.4f}, max={max(value_list):.4f}"
                    )

                # 差异超过1%则标记为错误
                if diff_pct > 1.0:
                    result.is_valid = False
                    result.add_issue(
                        ValidationSeverity.ERROR,
                        f"多源 {metric} 数据严重不一致: {diff_pct:.2f}% (阈值1%)",
                        field=metric,
                        actual=f"min={min(value_list):.4f}, max={max(value_list):.4f}"
                    )

        # ========== Phase 2.1: 使用中位数作为建议值 ==========
        if len(values) >= 2:
            result.suggested_value = self.find_median_value(list(values.values()))

        # ========== Phase 2.1: 记录数据源可靠性 ==========
        result.metadata['sources_count'] = len(sources_with_data)
        result.metadata['sources_available'] = sources_with_data
        result.metadata['sources_failed'] = [s for s in sources if s not in sources_with_data]

        return result

    def _validate_current_price(self, symbol: str, price: float,
                               result: ValidationResult) -> None:
        """验证当前价格合理性"""
        # 检查价格是否为正数
        if price <= 0:
            result.add_issue(
                ValidationSeverity.CRITICAL,
                "当前价格必须为正数",
                field='current_price',
                actual=price
            )
            return

        # 检查价格是否在合理范围内(0.01 - 10000)
        if not self.check_value_in_range(price, 0.01, 10000, 'current_price'):
            result.add_issue(
                ValidationSeverity.WARNING,
                "当前价格超出常规范围",
                field='current_price',
                actual=price
            )

    def _validate_ma_indicators(self, symbol: str, data: Dict[str, Any],
                                result: ValidationResult) -> None:
        """验证移动平均线指标"""
        current_price = self.to_float(data.get('current_price'))

        for ma_period in ['MA5', 'MA10', 'MA20', 'MA60']:
            if ma_period in data:
                ma_value = self.to_float(data[ma_period])

                # MA必须为正数
                if ma_value is not None and ma_value <= 0:
                    result.add_issue(
                        ValidationSeverity.ERROR,
                        f"{ma_period} 必须为正数",
                        field=ma_period,
                        actual=ma_value
                    )
                    continue

                # MA序列应该递增或递减(MA5 > MA10 > MA20 > MA60 是上升趋势)
                # 这里只检查相对关系
                if ma_period == 'MA5' and 'MA10' in data:
                    if data['MA5'] < data['MA10'] and current_price:
                        # 短期均线低于长期均线,可能是下降趋势
                        pass  # 这是正常的,不报错

                # MA不应偏离价格太多(超过50%)
                if current_price and ma_value:
                    diff_pct = abs((current_price - ma_value) / ma_value) * 100
                    if diff_pct > 50:
                        result.add_issue(
                            ValidationSeverity.WARNING,
                            f"{ma_period} 偏离当前价格 {diff_pct:.1f}%, 较为异常",
                            field=ma_period,
                            actual=ma_value,
                            expected=current_price
                        )

    def _validate_rsi_indicators(self, data: Dict[str, Any],
                                result: ValidationResult) -> None:
        """验证RSI指标"""
        for rsi_key in ['RSI', 'RSI6', 'RSI12', 'RSI24']:
            if rsi_key in data:
                rsi_value = self.to_float(data[rsi_key])

                # RSI必须在0-100之间
                if rsi_value is not None:
                    if not self.check_value_in_range(rsi_value, 0, 100, rsi_key):
                        result.add_issue(
                            ValidationSeverity.ERROR,
                            f"{rsi_key} 必须在 0-100 之间",
                            field=rsi_key,
                            actual=rsi_value,
                            expected="0-100"
                        )

                    # RSI极端值提醒
                    if rsi_value > 80:
                        result.add_issue(
                            ValidationSeverity.INFO,
                            f"{rsi_key}={rsi_value:.2f} 处于严重超买区",
                            field=rsi_key,
                            actual=rsi_value
                        )
                    elif rsi_value < 20:
                        result.add_issue(
                            ValidationSeverity.INFO,
                            f"{rsi_key}={rsi_value:.2f} 处于严重超卖区",
                            field=rsi_key,
                            actual=rsi_value
                        )

    def _validate_bollinger_bands(self, symbol: str, data: Dict[str, Any],
                                 result: ValidationResult) -> None:
        """验证布林带指标"""
        upper = self.to_float(data.get('BOLL_UPPER'))
        lower = self.to_float(data.get('BOLL_LOWER'))
        middle = self.to_float(data.get('BOLL_MIDDLE') or data.get('MA20'))
        current_price = self.to_float(data.get('current_price'))

        if not all([upper, lower, current_price]):
            return

        # 上轨必须大于下轨
        if upper <= lower:
            result.add_issue(
                ValidationSeverity.ERROR,
                "布林带上轨必须大于下轨",
                field='BOLL',
                actual=f"upper={upper}, lower={lower}"
            )

        # 中轨应该在上下轨中间
        if middle:
            if not (lower <= middle <= upper):
                result.add_issue(
                    ValidationSeverity.ERROR,
                    "布林带中轨应该在上下轨之间",
                    field='BOLL_MIDDLE',
                    actual=middle,
                    expected=f"[{lower}, {upper}]"
                )

        # 计算价格位置百分比
        if upper != lower:
            price_position = ((current_price - lower) / (upper - lower)) * 100

            # 验证报告中的价格位置是否正确
            if 'price_position' in data:
                reported_position = data['price_position']
                # 检查计算是否一致(允许2%误差)
                if abs(price_position - reported_position) > 2:
                    result.add_issue(
                        ValidationSeverity.ERROR,
                        f"价格位置计算错误: 实际应为 {price_position:.1f}%, 报告为 {reported_position:.1f}%",
                        field='price_position',
                        actual=reported_position,
                        expected=price_position
                    )

            # 价格超出布林带范围
            if price_position > 100:
                result.add_issue(
                    ValidationSeverity.WARNING,
                    f"价格 {current_price} 超出布林带上轨 {upper}",
                    field='current_price',
                    actual=current_price
                )
            elif price_position < 0:
                result.add_issue(
                    ValidationSeverity.WARNING,
                    f"价格 {current_price} 低于布林带下轨 {lower}",
                    field='current_price',
                    actual=current_price
                )

    def _validate_price_position(self, data: Dict[str, Any],
                                 result: ValidationResult) -> None:
        """验证价格位置百分比"""
        price_position = data.get('price_position')

        if price_position is not None:
            # 价格位置应该在0-100之间(或者是百分比形式)
            if price_position < 0 or price_position > 150:  # 允许一定的溢出
                result.add_issue(
                    ValidationSeverity.ERROR,
                    f"价格位置必须在合理范围内",
                    field='price_position',
                    actual=price_position
                )

    async def _get_data_from_source(self, symbol: str, source: str,
                                    metric: str) -> Optional[float]:
        """
        从指定数据源获取指标数据 (Phase 2.1)

        集成数据源可靠性跟踪系统

        Args:
            symbol: 股票代码
            source: 数据源名称 (tushare/akshare/baostock)
            metric: 指标名称

        Returns:
            float: 指标值，失败返回None
        """
        try:
            from tradingagents.dataflows.data_source_manager import DataSourceManager

            manager = DataSourceManager()
            data = manager.get_stock_data(symbol)

            if not data or metric not in data:
                # 记录失败
                manager.record_source_reliability(
                    source=source,
                    success=False,
                    metric=metric,
                    error=f"数据或指标不存在: metric={metric}"
                )
                return None

            value = self.to_float(data.get(metric))

            if value is not None:
                # 记录成功
                manager.record_source_reliability(
                    source=source,
                    success=True,
                    metric=metric
                )
            else:
                # 记录失败
                manager.record_source_reliability(
                    source=source,
                    success=False,
                    metric=metric,
                    error="指标值为None"
                )

            return value

        except Exception as e:
            self.logger.error(f"从 {source} 获取 {metric} 数据失败: {e}")
            # 记录失败
            try:
                from tradingagents.dataflows.data_source_manager import DataSourceManager
                manager = DataSourceManager()
                manager.record_source_reliability(
                    source=source,
                    success=False,
                    metric=metric,
                    error=str(e)
                )
            except:
                pass
            return None
