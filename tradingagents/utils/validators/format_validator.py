# -*- coding: utf-8 -*-
"""
股票代码格式验证器

负责验证股票代码的基本格式
"""
import re
import logging
from typing import Optional

from tradingagents.utils.logging_manager import get_logger

logger = get_logger('format_validator')


class FormatValidationError(Exception):
    """格式验证错误"""

    def __init__(self, message: str, stock_code: str = None, suggestion: str = None):
        self.message = message
        self.stock_code = stock_code
        self.suggestion = suggestion
        super().__init__(self.message)


class FormatValidator:
    """股票代码格式验证器"""

    @staticmethod
    def validate_stock_format(
        stock_code: str,
        market_type: str = "auto"
    ) -> tuple[bool, Optional[str], Optional[str]]:
        """验证股票代码格式

        Args:
            stock_code: 股票代码
            market_type: 市场类型（A股/港股/美股/auto）

        Returns:
            (是否有效, 错误消息, 建议)

        Raises:
            FormatValidationError: 格式错误时
        """
        stock_code = stock_code.strip()

        # 基本检查
        if not stock_code:
            raise FormatValidationError(
                message="股票代码不能为空",
                stock_code=stock_code,
                suggestion="请输入有效的股票代码"
            )

        if len(stock_code) > 10:
            raise FormatValidationError(
                message=f"股票代码长度不能超过10个字符: {stock_code}",
                stock_code=stock_code,
                suggestion="请检查股票代码格式"
            )

        # 根据市场类型验证
        if market_type == "A股":
            return FormatValidator._validate_china_format(stock_code)
        elif market_type == "港股":
            return FormatValidator._validate_hk_format(stock_code)
        elif market_type == "美股":
            return FormatValidator._validate_us_format(stock_code)
        else:
            # 自动检测
            return FormatValidator._auto_detect_format(stock_code)

    @staticmethod
    def _validate_china_format(stock_code: str) -> tuple[bool, Optional[str], Optional[str]]:
        """验证A股代码格式"""
        if not re.match(r'^\d{6}$', stock_code):
            return False, "A股代码格式错误，应为6位数字", "请输入6位数字的A股代码，如：000001、600519"
        return True, None, None

    @staticmethod
    def _validate_hk_format(stock_code: str) -> tuple[bool, Optional[str], Optional[str]]:
        """验证港股代码格式"""
        stock_code_upper = stock_code.upper()
        hk_format = re.match(r'^\d{4,5}\.HK$', stock_code_upper)
        digit_format = re.match(r'^\d{4,5}$', stock_code)

        if not (hk_format or digit_format):
            return False, "港股代码格式错误", "请输入4-5位数字.HK格式（如：0700.HK）或4-5位数字（如：0700）"
        return True, None, None

    @staticmethod
    def _validate_us_format(stock_code: str) -> tuple[bool, Optional[str], Optional[str]]:
        """验证美股代码格式"""
        if not re.match(r'^[A-Z]{1,5}$', stock_code.upper()):
            return False, "美股代码格式错误，应为1-5位字母", "请输入1-5位字母的美股代码，如：AAPL、TSLA"
        return True, None, None

    @staticmethod
    def _auto_detect_format(stock_code: str) -> tuple[bool, Optional[str], Optional[str]]:
        """自动检测股票代码格式和市场类型"""

        # A股：6位数字
        if re.match(r'^\d{6}$', stock_code):
            return True, None, None

        # 港股：4-5位数字.HK 或 纯4-5位数字
        if re.match(r'^\d{4,5}\.HK$', stock_code.upper()) or re.match(r'^\d{4,5}$', stock_code):
            return True, None, None

        # 美股：1-5位字母
        if re.match(r'^[A-Z]{1,5}$', stock_code.upper()):
            return True, None, None

        return False, "无法识别股票代码格式", "请确认股票代码格式是否正确"

    @staticmethod
    def detect_market_type(stock_code: str) -> str:
        """自动检测市场类型"""
        stock_code = stock_code.strip().upper()

        # A股：6位数字
        if re.match(r'^\d{6}$', stock_code):
            return "A股"

        # 港股：4-5位数字.HK 或 纯4-5位数字
        if re.match(r'^\d{4,5}\.HK$', stock_code) or re.match(r'^\d{4,5}$', stock_code):
            return "港股"

        # 美股：1-5位字母
        if re.match(r'^[A-Z]{1,5}$', stock_code):
            return "美股"

        return "未知"
