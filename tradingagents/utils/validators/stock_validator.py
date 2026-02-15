# -*- coding: utf-8 -*-
"""
股票数据验证器（主入口）

整合所有市场特定的验证器，提供统一的验证接口
"""
import logging
from typing import Dict, Optional
from datetime import datetime

from tradingagents.utils.logging_manager import get_logger

# 导入市场特定验证器
from tradingagents.utils.validators.format_validator import FormatValidator, FormatValidationError
from tradingagents.utils.validators.market_validators.china_validator import ChinaStockValidator
from tradingagents.utils.validators.market_validators.hk_validator import HKStockValidator
from tradingagents.utils.validators.market_validators.us_validator import USStockValidator

logger = get_logger('stock_validator')


class StockDataPreparationResult:
    """股票数据准备结果类"""

    def __init__(
        self,
        is_valid: bool,
        stock_code: str,
        market_type: str = "",
        stock_name: str = "",
        error_message: str = "",
        suggestion: str = "",
        has_historical_data: bool = False,
        has_basic_info: bool = False,
        data_period_days: int = 0,
        cache_status: str = ""
    ):
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


# 保持向后兼容
StockValidationResult = StockDataPreparationResult


class StockDataPreparer:
    """股票数据准备和验证器（主类）"""

    def __init__(self, default_period_days: int = 30, db=None, cache=None):
        self.default_period_days = default_period_days
        self.timeout_seconds = 15  # 数据获取超时时间

        # 初始化市场特定验证器
        self.china_validator = ChinaStockValidator(db, cache)
        self.hk_validator = HKStockValidator(db, cache)
        self.us_validator = USStockValidator(db, cache)
        self.format_validator = FormatValidator()

    def prepare_stock_data(
        self,
        stock_code: str,
        market_type: str = "auto",
        period_days: int = None,
        analysis_date: str = None
    ) -> StockDataPreparationResult:
        """
        准备和验证股票数据

        Args:
            stock_code: 股票代码
            market_type: 市场类型 ("A股", "港股", "美股", "auto")
            period_days: 历史数据时长（天），默认使用类初始化时的值
            analysis_date: 分析日期，默认为今天

        Returns:
            StockDataPreparationResult: 数据准备结果
        """
        if period_days is None:
            period_days = self.default_period_days

        if analysis_date is None:
            analysis_date = datetime.now().strftime('%Y-%m-%d')

        logger.info(f"开始准备股票数据: {stock_code} (市场: {market_type}, 时长: {period_days}天)")

        # 1. 格式验证
        try:
            is_valid, error_msg, suggestion = self.format_validator.validate_stock_format(
                stock_code, market_type
            )
            if not is_valid:
                return StockDataPreparationResult(
                    is_valid=False,
                    stock_code=stock_code,
                    market_type=market_type,
                    error_message=error_msg,
                    suggestion=suggestion
                )
        except FormatValidationError as e:
            return StockDataPreparationResult(
                is_valid=False,
                stock_code=stock_code,
                market_type=market_type,
                error_message=e.message,
                suggestion=e.suggestion
            )

        # 2. 自动检测市场类型
        if market_type == "auto":
            market_type = self.format_validator.detect_market_type(stock_code)
            logger.debug(f"自动检测市场类型: {market_type}")

        # 3. 根据市场类型选择验证器
        if market_type == "A股":
            return self._prepare_with_validator(
                self.china_validator, stock_code, period_days, analysis_date
            )
        elif market_type == "港股":
            return self._prepare_with_validator(
                self.hk_validator, stock_code, period_days, analysis_date
            )
        elif market_type == "美股":
            return self._prepare_with_validator(
                self.us_validator, stock_code, period_days, analysis_date
            )
        else:
            return StockDataPreparationResult(
                is_valid=False,
                stock_code=stock_code,
                market_type=market_type,
                error_message="未知的市场类型",
                suggestion="请选择有效的市场类型：A股、港股、美股"
            )

    def _prepare_with_validator(
        self,
        validator,
        stock_code: str,
        period_days: int,
        analysis_date: str
    ) -> StockDataPreparationResult:
        """使用特定验证器准备数据"""
        result_dict = validator.validate(stock_code, period_days, analysis_date)

        # 转换为 StockDataPreparationResult
        return StockDataPreparationResult(
            is_valid=result_dict.get('is_valid', False),
            stock_code=result_dict.get('stock_code', stock_code),
            market_type=result_dict.get('market_type', ''),
            error_message=result_dict.get('error_message', ''),
            suggestion=result_dict.get('suggestion', ''),
            has_historical_data=result_dict.get('has_historical_data', False),
            has_basic_info=result_dict.get('has_basic_info', False),
        )


# 工厂函数
def get_stock_preparer(default_period_days: int = 30, db=None, cache=None) -> StockDataPreparer:
    """获取股票数据准备器实例"""
    return StockDataPreparer(default_period_days, db, cache)


# 便捷函数
def prepare_stock_data(
    stock_code: str,
    market_type: str = "auto",
    period_days: int = 30,
    analysis_date: str = None
) -> StockDataPreparationResult:
    """准备股票数据（便捷函数）"""
    preparer = get_stock_preparer(default_period_days=period_days)
    return preparer.prepare_stock_data(stock_code, market_type, period_days, analysis_date)


def is_stock_data_ready(
    stock_code: str,
    market_type: str = "auto",
    period_days: int = 30
) -> bool:
    """检查股票数据是否准备就绪"""
    result = prepare_stock_data(stock_code, market_type, period_days)
    return result.is_valid and result.has_historical_data
