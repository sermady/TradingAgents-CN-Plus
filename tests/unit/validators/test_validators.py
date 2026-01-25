# -*- coding: utf-8 -*-
"""
验证器单元测试

测试数据验证器的核心功能
"""

import pytest
from tradingagents.dataflows.validators.price_validator import PriceValidator
from tradingagents.dataflows.validators.fundamentals_validator import FundamentalsValidator
from tradingagents.dataflows.validators.volume_validator import VolumeValidator
from tradingagents.dataflows.validators.base_validator import ValidationSeverity


class TestPriceValidator:
    """价格数据验证器测试"""

    def test_validate_current_price(self):
        """测试当前价格验证"""
        validator = PriceValidator()

        # 正常价格
        data = {'current_price': 31.18, 'source': 'test'}
        result = validator.validate('600765', data)
        assert result.is_valid == True
        assert result.confidence > 0.8

        # 异常价格（负数）
        data_invalid = {'current_price': -10.0, 'source': 'test'}
        result_invalid = validator.validate('600765', data_invalid)
        assert result_invalid.is_valid == False

        # 异常价格（超出范围）
        data_out_of_range = {'current_price': 100000.0, 'source': 'test'}
        result_out = validator.validate('600765', data_out_of_range)
        assert result_out.is_valid == True  # 仍然有效，但有警告
        assert len(result_out.get_issues_by_severity(ValidationSeverity.WARNING)) > 0

    def test_validate_ma_indicators(self):
        """测试移动平均线验证"""
        validator = PriceValidator()

        # 正常MA数据
        data = {
            'current_price': 31.18,
            'MA5': 30.42,
            'MA10': 29.98,
            'MA20': 29.54,
            'MA60': 27.88,
            'source': 'test'
        }
        result = validator.validate('600765', data)
        assert result.is_valid == True

        # MA为负数
        data_invalid = {
            'current_price': 31.18,
            'MA5': -10.0,
            'source': 'test'
        }
        result_invalid = validator.validate('600765', data_invalid)
        assert result_invalid.is_valid == False

    def test_validate_rsi_indicators(self):
        """测试RSI指标验证"""
        validator = PriceValidator()

        # 正常RSI
        data = {'RSI6': 82.37, 'source': 'test'}
        result = validator.validate('600765', data)
        assert result.is_valid == True
        # RSI超买应该有INFO级别提示
        info_issues = result.get_issues_by_severity(ValidationSeverity.INFO)
        assert len(info_issues) > 0

        # RSI超出范围
        data_invalid = {'RSI': 150.0, 'source': 'test'}
        result_invalid = validator.validate('600765', data_invalid)
        assert result_invalid.is_valid == False

    def test_validate_bollinger_bands(self):
        """测试布林带验证"""
        validator = PriceValidator()

        # 正常布林带（价格位置略有差异，但在容忍范围内）
        # 报告值106.8%，计算值108.06%，差异1.26% < 2%阈值
        data = {
            'current_price': 31.18,
            'BOLL_UPPER': 30.98,
            'BOLL_LOWER': 28.50,
            'BOLL_MIDDLE': 29.74,
            'price_position': 106.8,
            'source': 'test'
        }
        result = validator.validate('600765', data)
        # 差异小于2%，不应该报ERROR
        assert result.is_valid == True

        # 严重错误的价格位置（差异超过2%）
        data_wrong = {
            'current_price': 31.18,
            'BOLL_UPPER': 30.98,
            'BOLL_LOWER': 28.50,
            'price_position': 50.0,  # 完全错误的值
            'source': 'test'
        }
        result_wrong = validator.validate('600765', data_wrong)
        # 应该检测到ERROR
        error_issues = result_wrong.get_issues_by_severity(ValidationSeverity.ERROR)
        assert len(error_issues) > 0

        # 上轨小于下轨（错误）
        data_invalid = {
            'current_price': 31.18,
            'BOLL_UPPER': 28.0,
            'BOLL_LOWER': 30.0,
            'source': 'test'
        }
        result_invalid = validator.validate('600765', data_invalid)
        assert result_invalid.is_valid == False


class TestFundamentalsValidator:
    """基本面数据验证器测试"""

    def test_validate_pe_ratio(self):
        """测试市盈率验证"""
        validator = FundamentalsValidator()

        # 正常PE
        data = {'PE': 25.7, 'source': 'test'}
        result = validator.validate('600765', data)
        assert result.is_valid == True

        # PE超出范围
        data_invalid = {'PE': 1000.0, 'source': 'test'}
        result_invalid = validator.validate('600765', data_invalid)
        assert result_invalid.is_valid == False

        # 负PE（亏损公司）
        data_negative = {'PE': -15.5, 'source': 'test'}
        result_negative = validator.validate('600765', data_negative)
        assert result_negative.is_valid == True
        # 应该有INFO级别提示
        assert len(result_negative.get_issues_by_severity(ValidationSeverity.INFO)) > 0

    def test_validate_ps_ratio(self):
        """测试PS比率验证 - 修复605589问题的关键测试"""
        validator = FundamentalsValidator()

        # 正确的PS数据
        data_correct = {
            'market_cap': 263.9,
            'revenue': 92.0,
            'PS': 2.87,
            'source': 'test'
        }
        result_correct = validator.validate('605589', data_correct)
        assert result_correct.is_valid == True
        assert result_correct.confidence > 0.8

        # 错误的PS数据（605589报告中的错误）
        data_wrong = {
            'market_cap': 263.9,
            'revenue': 92.0,
            'PS': 0.10,  # 错误值
            'source': 'test'
        }
        result_wrong = validator.validate('605589', data_wrong)
        # 应该检测到PS错误
        assert result_wrong.is_valid == False
        error_issues = result_wrong.get_issues_by_severity(ValidationSeverity.ERROR)
        assert len(error_issues) > 0
        # 应该有建议值
        assert result_wrong.suggested_value is not None
        assert abs(result_wrong.suggested_value - 2.87) < 0.1

    def test_calculate_ps_from_components(self):
        """测试PS比率计算"""
        validator = FundamentalsValidator()

        # 测试计算
        data = {
            'market_cap': 263.9,
            'revenue': 92.0
        }
        ps = validator._calculate_ps_from_components(data)
        assert ps is not None
        assert abs(ps - 2.87) < 0.1

    def test_validate_market_cap_consistency(self):
        """测试市值计算一致性"""
        validator = FundamentalsValidator()

        # 一致的数据
        data_consistent = {
            'market_cap': 263.9,
            'share_count': 84600,  # 万股
            'current_price': 31.18
        }
        # 263.9亿 vs (84600 * 31.18) / 10000 = 263.8亿
        result = validator.validate('605589', data_consistent)
        # 误差应该很小
        assert result.is_valid == True

        # 不一致的数据
        data_inconsistent = {
            'market_cap': 100.0,
            'share_count': 84600,
            'current_price': 31.18
        }
        result_inconsistent = validator.validate('605589', data_inconsistent)
        # 应该有警告
        warning_issues = result_inconsistent.get_issues_by_severity(ValidationSeverity.WARNING)
        assert len(warning_issues) > 0


class TestVolumeValidator:
    """成交量数据验证器测试"""

    def test_validate_current_volume(self):
        """测试当前成交量验证"""
        validator = VolumeValidator()

        # 正常成交量
        data = {'volume': 1000000, 'source': 'test'}
        result = validator.validate('600765', data)
        assert result.is_valid == True

        # 负成交量
        data_invalid = {'volume': -1000, 'source': 'test'}
        result_invalid = validator.validate('600765', data_invalid)
        assert result_invalid.is_valid == False

    def test_standardize_volume(self):
        """测试成交量单位标准化"""
        validator = VolumeValidator()

        # 手转股
        volume_lots = 10000  # 10000手
        standardized, original_unit = validator.standardize_volume(volume_lots, 'lots')
        assert standardized == 10000 * 100  # 1000000股
        assert original_unit == 'lots'

        # 股无需转换
        volume_shares = 500000
        standardized2, original_unit2 = validator.standardize_volume(volume_shares, 'shares')
        assert standardized2 == 500000
        assert original_unit2 == 'shares'

    def test_infer_volume_unit(self):
        """测试成交量单位推断"""
        validator = VolumeValidator()

        # 大数值推断为股
        data_large = {'volume': 5000000, 'share_count': 1000000, 'turnover_rate': 50.0}
        unit = validator._infer_volume_unit(5000000, data_large)
        assert unit == 'shares'

    def test_compare_volumes(self):
        """测试成交量比较"""
        validator = VolumeValidator()

        # 相同单位
        is_consistent, diff_pct = validator.compare_volumes(1000000, 1005000, 'shares', 'shares')
        assert is_consistent == True  # 5%差异在容忍范围内

        # 不同单位
        is_consistent2, diff_pct2 = validator.compare_volumes(10000, 1000000, 'lots', 'shares')
        assert is_consistent2 == True  # 10000手 = 1000000股
        assert diff_pct2 == 0.0


class TestValidationResult:
    """ValidationResult数据类测试"""

    def test_add_issue(self):
        """测试添加问题"""
        from tradingagents.dataflows.validators.base_validator import ValidationResult

        result = ValidationResult(is_valid=True, confidence=0.9, source='test')

        # 添加WARNING问题
        result.add_issue(ValidationSeverity.WARNING, '测试警告', field='test_field')
        assert result.is_valid == True  # WARNING不影响有效性
        assert len(result.discrepancies) == 1

        # 添加ERROR问题
        result.add_issue(ValidationSeverity.ERROR, '测试错误', field='test_field2')
        assert result.is_valid == False  # ERROR会影响有效性

    def test_get_error_count(self):
        """测试错误计数"""
        from tradingagents.dataflows.validators.base_validator import ValidationResult

        result = ValidationResult(is_valid=True, confidence=0.9, source='test')

        result.add_issue(ValidationSeverity.INFO, '信息', field='test')
        result.add_issue(ValidationSeverity.WARNING, '警告', field='test')
        result.add_issue(ValidationSeverity.ERROR, '错误', field='test')

        counts = result.get_error_count()
        assert counts['info'] == 1
        assert counts['warning'] == 1
        assert counts['error'] == 1
        assert counts['critical'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
