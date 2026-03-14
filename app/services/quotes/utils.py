# -*- coding: utf-8 -*-
"""行情采集服务工具函数

提供股票代码标准化等通用工具。
"""

from typing import Optional


def normalize_stock_code(code: str) -> str:
    """
    标准化股票代码为6位数字

    处理以下情况：
    - sz000001 -> 000001
    - sh600036 -> 600036
    - 000001 -> 000001
    - 1 -> 000001

    Args:
        code: 原始股票代码

    Returns:
        str: 标准化后的6位股票代码
    """
    if not code:
        return ""

    code_str = str(code).strip()

    # 如果代码长度超过6位，去掉前面的交易所前缀（如 sz, sh）
    if len(code_str) > 6:
        # 提取所有数字字符
        code_str = ''.join(filter(str.isdigit, code_str))

    # 如果是纯数字，补齐到6位
    if code_str.isdigit():
        code_clean = code_str.lstrip('0') or '0'  # 移除前导0，如果全是0则保留一个0
        return code_clean.zfill(6)  # 补齐到6位

    # 如果不是纯数字，尝试提取数字部分
    code_digits = ''.join(filter(str.isdigit, code_str))
    if code_digits:
        return code_digits.zfill(6)

    # 无法提取有效代码，返回空字符串
    return ""
