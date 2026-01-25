# -*- coding: utf-8 -*-
"""
时间工具模块 - 提供统一的当前时间获取和格式化功能
用于在分析提示词中明确提供当前日期，避免LLM依赖过时的训练数据时间认知
"""

import os
from datetime import datetime, date


def get_current_date() -> date:
    """
    获取当前日期

    Returns:
        date: 当前日期对象
    """
    return date.today()


def get_current_datetime() -> datetime:
    """
    获取当前日期时间

    Returns:
        datetime: 当前日期时间对象
    """
    return datetime.now()


def get_current_date_str(format_str: str = "%Y年%m月%d日") -> str:
    """
    获取当前日期的格式化字符串（默认中文格式）

    Args:
        format_str: 日期格式字符串，默认"%Y年%m月%d日"

    Returns:
        str: 格式化后的日期字符串
    """
    today = get_current_date()
    return today.strftime(format_str)


def get_current_datetime_str(format_str: str = "%Y年%m月%d日 %H:%M:%S") -> str:
    """
    获取当前日期时间的格式化字符串（默认中文格式）

    Args:
        format_str: 日期时间格式字符串，默认"%Y年%m月%d日 %H:%M:%S"

    Returns:
        str: 格式化后的日期时间字符串
    """
    now = get_current_datetime()
    return now.strftime(format_str)


# 预定义格式的快捷函数
def get_chinese_date() -> str:
    """获取中文格式的当前日期（如：2026年01月25日）"""
    return get_current_date_str("%Y年%m月%d日")


def get_iso_date() -> str:
    """获取ISO格式的当前日期（如：2026-01-25）"""
    return get_current_date_str("%Y-%m-%d")


def get_chinese_datetime() -> str:
    """获取中文格式的当前日期时间（如：2026年01月25日 14:30:00）"""
    return get_current_datetime_str("%Y年%m月%d日 %H:%M:%S")


if __name__ == "__main__":
    # 测试输出
    print(f"当前日期（中文）: {get_chinese_date()}")
    print(f"当前日期（ISO）: {get_iso_date()}")
    print(f"当前日期时间（中文）: {get_chinese_datetime()}")