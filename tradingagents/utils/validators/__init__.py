# -*- coding: utf-8 -*-
"""
股票数据验证器 - 统一导出

提供格式验证和市场特定的数据验证功能
"""

# 主验证器和结果类
from tradingagents.utils.validators.stock_validator import (
    StockDataPreparer,
    StockDataPreparationResult,
    StockValidationResult,  # 向后兼容
    get_stock_preparer,
    prepare_stock_data,
    is_stock_data_ready,
)

# 格式验证器
from tradingagents.utils.validators.format_validator import (
    FormatValidator,
    FormatValidationError,
)

# 市场特定验证器
from tradingagents.utils.validators.market_validators.china_validator import ChinaStockValidator
from tradingagents.utils.validators.market_validators.hk_validator import HKStockValidator
from tradingagents.utils.validators.market_validators.us_validator import USStockValidator

__all__ = [
    # 主验证器
    'StockDataPreparer',
    'StockDataPreparationResult',
    'StockValidationResult',
    'get_stock_preparer',
    'prepare_stock_data',
    'is_stock_data_ready',
    # 格式验证
    'FormatValidator',
    'FormatValidationError',
    # 市场验证器
    'ChinaStockValidator',
    'HKStockValidator',
    'USStockValidator',
]
