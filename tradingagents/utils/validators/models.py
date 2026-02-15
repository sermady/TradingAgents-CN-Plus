# -*- coding: utf-8 -*-
"""
股票数据验证模块 - 数据模型

包含StockDataPreparationResult数据类。
"""

from typing import Dict


class StockDataPreparationResult:
    """股票数据预获取结果类"""

    def __init__(self, is_valid: bool, stock_code: str, market_type: str = "",
                 stock_name: str = "", error_message: str = "", suggestion: str = "",
                 has_historical_data: bool = False, has_basic_info: bool = False,
                 data_period_days: int = 0, cache_status: str = ""):
        """
        初始化股票数据准备结果

        Args:
            is_valid: 是否通过验证
            stock_code: 股票代码
            market_type: 市场类型
            stock_name: 股票名称
            error_message: 错误消息
            suggestion: 建议
            has_historical_data: 是否有历史数据
            has_basic_info: 是否有基本信息
            data_period_days: 数据周期天数
            cache_status: 缓存状态
        """
        self.is_valid = is_valid
        self.stock_code = stock_code
        self.market_type = market_type
        self.stock_name = stock_name
        self.error_message = error_message
        self.suggestion = suggestion
        self.has_historical_data = has_historical_data
        self.has_basic_info = has_basic_info
        self.data_period_days = data_period_days
        self.cache_status = cache_status

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'is_valid': self.is_valid,
            'stock_code': self.stock_code,
            'market_type': self.market_type,
            'stock_name': self.stock_name,
            'error_message': self.error_message,
            'suggestion': self.suggestion,
            'has_historical_data': self.has_historical_data,
            'has_basic_info': self.has_basic_info,
            'data_period_days': self.data_period_days,
            'cache_status': self.cache_status
        }


# 保持向后兼容的别名
StockValidationResult = StockDataPreparationResult


# 导出
__all__ = [
    "StockDataPreparationResult",
    "StockValidationResult",  # 向后兼容别名
]
