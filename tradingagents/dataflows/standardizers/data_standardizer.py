# -*- coding: utf-8 -*-
"""
数据标准化器

统一处理不同数据源的数据格式和单位问题
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class DataStandardizer:
    """
    数据标准化器

    功能:
    - 统一数据格式
    - 标准化单位（手/股, 万元/亿元）
    - 修复常见数据错误
    """

    # 成交量单位转换
    SHARES_PER_LOT = 100  # 1手 = 100股

    # 金额单位转换
    WAN_TO_YI = 10000  # 1万元 = 10000万元 = 1亿元
    YI_TO_WAN = 10000

    @staticmethod
    def standardize_volume(volume: Any, unit: Optional[str] = None) -> Dict[str, Any]:
        """
        标准化成交量到"股"

        Args:
            volume: 成交量数值
            unit: 原始单位 ('lots', 'shares', None表示自动推断)

        Returns:
            Dict: {
                'value': 标准化后的值,
                'original_unit': 原始单位,
                'standard_unit': 'shares',
                'conversion_ratio': 转换倍数
            }
        """
        if volume is None:
            return {'value': None, 'original_unit': None, 'standard_unit': 'shares'}

        try:
            volume = float(volume)
        except (ValueError, TypeError):
            return {'value': None, 'original_unit': None, 'standard_unit': 'shares'}

        # 如果没有指定单位，默认为"股"
        # 🔧 修复：移除不可靠的启发式推断，避免二次转换错误
        # 问题：954,158股会被误判为"手"（<100万且能被100整除），导致二次转换
        if unit is None:
            unit = 'shares'  # 默认为股
            logger.warning(
                f"⚠️ 成交量单位未明确标注，默认为'股'。"
                f"数据源应明确标注volume_unit字段以避免转换错误。"
                f"当前值: {volume:,.0f}"
            )

        # 转换
        if unit == 'lots':
            return {
                'value': volume * DataStandardizer.SHARES_PER_LOT,
                'original_unit': 'lots',
                'standard_unit': 'shares',
                'conversion_ratio': DataStandardizer.SHARES_PER_LOT,
                'description': f'{volume}手 = {volume * 100}股'
            }
        else:  # shares
            return {
                'value': volume,
                'original_unit': 'shares',
                'standard_unit': 'shares',
                'conversion_ratio': 1,
                'description': f'{volume}股'
            }

    @staticmethod
    def standardize_market_cap(market_cap: Any, unit: Optional[str] = None) -> Dict[str, Any]:
        """
        标准化市值到"亿元"

        Args:
            market_cap: 市值数值
            unit: 原始单位 ('yuan', 'wan', 'yi')

        Returns:
            Dict: 标准化后的市值信息
        """
        if market_cap is None:
            return {'value': None, 'unit': None}

        try:
            market_cap = float(market_cap)
        except (ValueError, TypeError):
            return {'value': None, 'unit': None}

        # 自动推断单位
        if unit is None:
            if market_cap > 1000000:  # 超过100万，可能是元
                unit = 'yuan'
            elif market_cap < 1000:  # 小于1000，可能是亿元
                unit = 'yi'
            else:  # 中间值，可能是万元
                unit = 'wan'

        # 转换到亿元
        if unit == 'yuan':
            value_yi = market_cap / 100000000
        elif unit == 'wan':
            value_yi = market_cap / 10000
        else:  # yi
            value_yi = market_cap

        return {
            'value': value_yi,
            'unit': 'yi',
            'original_value': market_cap,
            'original_unit': unit,
            'description': f'{market_cap}{unit} = {value_yi:.2f}亿元'
        }

    @staticmethod
    def calculate_and_validate_ps_ratio(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算并验证PS比率

        PS = 市值 / 营业收入

        这是修复605589报告PS错误的关键方法

        Args:
            data: 包含market_cap和revenue的数据字典

        Returns:
            Dict: {
                'ps_ratio': 计算出的PS值,
                'is_valid': 是否与报告值一致,
                'reported_ps': 报告中的PS值,
                'calculation_details': 计算详情
            }
        """
        result = {
            'ps_ratio': None,
            'is_valid': True,
            'reported_ps': data.get('PS') or data.get('ps_ratio'),
            'calculation_details': {}
        }

        # 获取市值和营收
        market_cap = data.get('market_cap') or data.get('total_market_cap')
        revenue = data.get('revenue') or data.get('total_revenue') or data.get('operating_revenue')

        if not all([market_cap, revenue]):
            result['calculation_details']['error'] = '缺少市值或营收数据'
            result['is_valid'] = False
            return result

        try:
            market_cap = float(market_cap)
            revenue = float(revenue)
        except (ValueError, TypeError):
            result['calculation_details']['error'] = '市值或营收数据类型错误'
            result['is_valid'] = False
            return result

        if revenue == 0:
            result['calculation_details']['error'] = '营收为0，无法计算PS'
            result['is_valid'] = False
            return result

        # 计算PS
        calculated_ps = market_cap / revenue

        result['ps_ratio'] = round(calculated_ps, 2)
        result['calculation_details'] = {
            'market_cap': market_cap,
            'revenue': revenue,
            'formula': 'PS = 市值 / 营收',
            'calculation': f'PS = {market_cap} / {revenue} = {calculated_ps:.2f}'
        }

        # 如果有报告值，验证是否一致
        reported_ps = result.get('reported_ps')
        if reported_ps is not None:
            try:
                reported_ps = float(reported_ps)
                # 允许10%的误差
                if reported_ps > 0:
                    diff_pct = abs((calculated_ps - reported_ps) / reported_ps) * 100

                    result['calculation_details']['reported_ps'] = reported_ps
                    result['calculation_details']['diff_pct'] = diff_pct

                    if diff_pct > 10:
                        result['is_valid'] = False
                        result['calculation_details']['warning'] = (
                            f'⚠️ PS比率严重错误！报告值={reported_ps:.2f}, '
                            f'正确值应为≈{calculated_ps:.2f} (差异{diff_pct:.1f}%)'
                        )

                        # 记录错误
                        logger.error(
                            f"PS比率计算错误: 报告={reported_ps:.2f}, "
                            f"根据市值({market_cap:.2f}亿)和营收({revenue:.2f}亿)计算应为≈{calculated_ps:.2f}"
                        )
                    else:
                        result['calculation_details']['info'] = f'✅ PS比率一致 (差异{diff_pct:.1f}%)'

            except (ValueError, TypeError):
                pass

        return result

    @staticmethod
    def standardize_bollinger_bands(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化布林带数据，计算价格位置

        这是修复605589报告布林带矛盾的关键方法

        Args:
            data: 包含布林带数据的价格信息

        Returns:
            Dict: 标准化后的布林带数据
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }

        # 获取布林带数据
        upper = data.get('BOLL_UPPER') or data.get('boll_upper') or data.get('upper_band')
        lower = data.get('BOLL_LOWER') or data.get('boll_lower') or data.get('lower_band')
        middle = data.get('BOLL_MIDDLE') or data.get('boll_middle') or data.get('middle_band') or data.get('MA20')
        current_price = data.get('current_price') or data.get('close') or data.get('price')

        if not all([upper, lower, current_price]):
            result['is_valid'] = False
            result['errors'].append('缺少布林带或价格数据')
            return result

        try:
            upper = float(upper)
            lower = float(lower)
            current_price = float(current_price)
            if middle:
                middle = float(middle)
        except (ValueError, TypeError) as e:
            result['is_valid'] = False
            result['errors'].append(f'布林带数据类型错误: {e}')
            return result

        # 验证上轨 > 下轨
        if upper <= lower:
            result['is_valid'] = False
            result['errors'].append(f'布林带上轨({upper})必须大于下轨({lower})')

        # 验证中轨在上下轨之间
        if middle and not (lower <= middle <= upper):
            result['is_valid'] = False
            result['errors'].append(f'布林带中轨({middle})应在上下轨之间({lower}, {upper})')

        # 计算价格位置百分比
        if upper != lower:
            price_position = ((current_price - lower) / (upper - lower)) * 100
            result['price_position'] = round(price_position, 1)

            # 检查报告中是否有价格位置数据
            reported_position = data.get('price_position')
            if reported_position is not None:
                try:
                    reported_position = float(reported_position)
                    # 允许2%的误差
                    if abs(price_position - reported_position) > 2:
                        result['is_valid'] = False
                        result['errors'].append(
                            f'价格位置计算错误: 报告={reported_position:.1f}%, '
                            f'实际应为≈{price_position:.1f}%'
                        )
                        logger.error(
                            f"布林带价格位置错误: 报告={reported_position:.1f}%, "
                            f"根据价格({current_price})、上轨({upper})、下轨({lower})计算应为{price_position:.1f}%"
                        )
                except (ValueError, TypeError):
                    pass

        result['bollinger_bands'] = {
            'upper': upper,
            'lower': lower,
            'middle': middle,
            'current_price': current_price,
            'price_position': result.get('price_position'),
            'band_width': upper - lower
        }

        # 价格超出范围警告
        if result['price_position']:
            if result['price_position'] > 100:
                result['warnings'].append(f'价格({current_price})超出布林带上轨({upper})')
            elif result['price_position'] < 0:
                result['warnings'].append(f'价格({current_price})低于布林带下轨({lower})')

        return result

    @staticmethod
    def standardize_data(data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """
        综合标准化数据

        Args:
            data: 原始数据字典
            symbol: 股票代码

        Returns:
            Dict: 标准化后的数据和验证结果
        """
        result = {
            'data': data.copy(),
            'validations': {},
            'standardizations': {}
        }

        # 1. 标准化成交量
        if 'volume' in data:
            vol_std = DataStandardizer.standardize_volume(data['volume'])
            result['standardizations']['volume'] = vol_std
            result['data']['volume_standardized'] = vol_std['value']

        # 2. 标准化市值
        if 'market_cap' in data:
            cap_std = DataStandardizer.standardize_market_cap(data['market_cap'])
            result['standardizations']['market_cap'] = cap_std
            result['data']['market_cap_yi'] = cap_std['value']

        # 3. 计算并验证PS比率
        ps_validation = DataStandardizer.calculate_and_validate_ps_ratio(data)
        result['validations']['ps_ratio'] = ps_validation

        # 如果PS有错误，添加建议值
        if not ps_validation['is_valid'] and ps_validation['ps_ratio']:
            result['data']['PS_suggested'] = ps_validation['ps_ratio']
            logger.warning(
                f"[{symbol}] PS比率错误已检测到，建议值: {ps_validation['ps_ratio']}"
            )

        # 4. 标准化布林带
        if any(k in data for k in ['BOLL_UPPER', 'BOLL_LOWER', 'boll_upper', 'boll_lower']):
            boll_std = DataStandardizer.standardize_bollinger_bands(data)
            result['validations']['bollinger_bands'] = boll_std

            # 如果价格位置有错误，添加正确值
            if not boll_std['is_valid'] and 'price_position' in boll_std:
                result['data']['price_position_suggested'] = boll_std['price_position']
                logger.warning(
                    f"[{symbol}] 布林带价格位置错误已检测到，建议值: {boll_std['price_position']}%"
                )

        return result
