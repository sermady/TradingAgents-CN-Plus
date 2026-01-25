# -*- coding: utf-8 -*-
"""
测试成交量单位推断的边界情况
暴露954,158被误判为"手"的问题
"""

import pytest
from tradingagents.dataflows.standardizers.data_standardizer import DataStandardizer
from tradingagents.dataflows.validators.volume_validator import VolumeValidator


class TestVolumeUnitInferenceBug:
    """
    测试启发式单位推断的bug

    问题场景：
    1. 某些数据流可能绕过Provider层，直接传入原始数据
    2. 原始数据可能是"股"但没有标注单位
    3. 启发式推断将<100万的值误判为"手"
    4. 导致二次转换，数值错误
    """

    def test_critical_bug_954158_shares_without_label(self):
        """
        ✅ 修复后：954,158股（未标注单位）默认为"股"

        场景：某处代码直接传入了954,158股，但没有标注volume_unit字段
        修复后行为：默认为"股"，不再进行启发式推断
        结果：954,158股 → 保持954,158股（正确！）
        """
        # 模拟：某处代码直接传入了954,158股，但没有标注单位
        volume_in_shares = 954158  # 这已经是股了！
        volume_unit = None  # 但没有标注单位

        # DataStandardizer会默认为"股"
        result = DataStandardizer.standardize_volume(volume_in_shares, unit=volume_unit)

        # ✅ 修复：应该默认为"股"
        # 预期：保持954,158股
        # 实际：954,158股（正确）
        print(f"\n输入: {volume_in_shares} (无单位标注)")
        print(f"推断单位: {result.get('original_unit')}")
        print(f"输出值: {result['value']}")
        print(f"描述: {result.get('description')}")

        # 这个断言现在应该通过
        assert result['value'] == 954158, (
            f"期望954,158股，实际得到{result['value']}股"
        )
        assert result['original_unit'] == 'shares'

    def test_validator_bug_954158_shares_without_label(self):
        """
        ✅ 修复后：VolumeValidator默认推断为"股"
        """
        validator = VolumeValidator()
        data = {
            'volume': 954158,  # 这已经是股了
            # 没有 volume_unit 字段
        }

        inferred_unit = validator._infer_volume_unit(954158, data)

        print(f"\nVolumeValidator推断: {inferred_unit}")

        # ✅ 修复：应该默认推断为"股"
        assert inferred_unit == 'shares', (
            f"期望推断为'shares'，实际推断为'{inferred_unit}'"
        )

    def test_boundary_exactly_1million(self):
        """
        边界测试：刚好1,000,000
        """
        # 1,000,000股（无标注）
        result = DataStandardizer.standardize_volume(1000000, unit=None)

        print(f"\n1,000,000推断结果: {result['original_unit']}, 值={result['value']}")

        # 应该被推断为"股"（因为>=100万）
        assert result['value'] == 1000000

    def test_boundary_999999(self):
        """
        边界测试：999,999（刚好在100万之下）
        """
        result = DataStandardizer.standardize_volume(999999, unit=None)

        print(f"\n999,999推断结果: {result['original_unit']}, 值={result['value']}")

        # 🔴 问题：999,999 < 100万，但不是手（不能被100整除）
        # 会被默认推断为"股"，这是正确的
        # 但如果是999,900（能被100整除），会被误判为"手"
        assert result['value'] == 999999

    def test_boundary_999900_can_be_divided_by_100(self):
        """
        边界测试：999,900（能被100整除，<100万）
        🔴 高风险：会被误判为"手"
        """
        result = DataStandardizer.standardize_volume(999900, unit=None)

        print(f"\n999,900推断结果: {result['original_unit']}, 值={result['value']}")

        # 🔴 bug：999900能被100整除且<100万，会被推断为"手"
        # 如果原始数据就是999,900股，会被错误转换为99,990,000股
        assert result['value'] == 999900, (
            f"BUG暴露：999,900股被误判为'手'！"
            f"期望999,900股，实际得到{result['value']}股"
        )

    def test_large_shares_correctly_inferred(self):
        """
        正常情况：大数值应该被正确推断为"股"
        """
        # 5,000,000股（无标注）
        result = DataStandardizer.standardize_volume(5000000, unit=None)

        print(f"\n5,000,000推断结果: {result['original_unit']}, 值={result['value']}")

        # >100万，应该被正确推断为"股"
        assert result['value'] == 5000000
        assert result['original_unit'] == 'shares'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
