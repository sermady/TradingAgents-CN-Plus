# -*- coding: utf-8 -*-
"""股票代码工具模块

提供股票代码相关的通用工具函数
"""

import logging

logger = logging.getLogger(__name__)


class SymbolGenerator:
    """股票代码生成器

    提供股票代码标准化和完整代码生成功能
    """

    @staticmethod
    def generate_full_symbol(code: str) -> str:
        """根据股票代码生成完整标准化代码

        Args:
            code: 6位股票代码，如 "000001"

        Returns:
            str: 完整的代码，如 "000001.SZ"，如果无法识别则返回原始代码
        """
        # 确保 code 不为空
        if not code:
            return ""

        # 标准化为字符串并去除空格
        code = str(code).strip()

        # 如果长度不是 6，返回原始代码
        if len(code) != 6:
            return code

        # 根据代码前缀判断交易所
        if code.startswith(("60", "68", "90")):  # 上海证券交易所
            return f"{code}.SS"
        elif code.startswith(("00", "30", "20")):  # 深圳证券交易所
            return f"{code}.SZ"
        elif code.startswith(("8", "4")):  # 北京证券交易所
            return f"{code}.BJ"
        else:
            # 无法识别的代码，返回原始代码
            return code if code else ""

    @staticmethod
    def get_exchange_suffix(code: str) -> str:
        """根据股票代码获取交易所后缀

        Args:
            code: 6位股票代码

        Returns:
            str: 交易所后缀，如 "SZ", "SS", "BJ"，或空字符串
        """
        if not code:
            return ""

        code = str(code).strip()

        if len(code) != 6:
            return ""

        if code.startswith(("60", "68", "90")):
            return "SS"
        elif code.startswith(("00", "30", "20")):
            return "SZ"
        elif code.startswith(("8", "4")):
            return "BJ"
        else:
            return ""

    @staticmethod
    def get_exchange_name(code: str) -> str:
        """根据股票代码获取交易所名称

        Args:
            code: 6位股票代码

        Returns:
            str: 交易所名称，如 "上海证券交易所"
        """
        if not code:
            return "未知"

        code = str(code).strip()

        if len(code) != 6:
            return "未知"

        if code.startswith(("60", "68", "90")):
            return "上海证券交易所"
        elif code.startswith(("00", "30", "20")):
            return "深圳证券交易所"
        elif code.startswith(("8", "4")):
            return "北京证券交易所"
        else:
            return "未知"

    @staticmethod
    def extract_code_from_ts_code(ts_code: str) -> str:
        """从带后缀的代码中提取6位股票代码

        Args:
            ts_code: 带后缀的代码，如 "000001.SZ"

        Returns:
            str: 6位股票代码，如 "000001"
        """
        if not ts_code:
            return ""

        ts_code = str(ts_code).strip()

        if "." in ts_code:
            return ts_code.split(".")[0]
        else:
            return ts_code.zfill(6) if ts_code.isdigit() else ts_code
