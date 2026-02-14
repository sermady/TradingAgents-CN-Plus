# -*- coding: utf-8 -*-
"""
数据验证模块 [已废弃]

⚠️ 建议使用: tradingagents.dataflows.validators

此模块已废弃，请使用以下替代:
- BaseDataValidator: 基础验证器类
- ValidationResult: 验证结果
- PriceValidator: 价格验证
- VolumeValidator: 成交量验证
- FundamentalsValidator: 基本面验证

示例:
    from tradingagents.dataflows.validators import PriceValidator, VolumeValidator
"""

# 为保持向后兼容，保留原有导入
from .data_validator import DataValidator, get_data_validator, validate_market_data

__all__ = ["DataValidator", "get_data_validator", "validate_market_data"]

# 建议使用新的验证器
__deprecated__ = True
