# -*- coding: utf-8 -*-
"""
日期解析工具模块
提供日期格式转换、交易日计算等功能
"""

from datetime import datetime, timedelta
from typing import Optional, List
from zoneinfo import ZoneInfo

from tradingagents.config.runtime_settings import get_timezone_name


def parse_date(date_str: str) -> Optional[datetime]:
    """
    解析日期字符串为datetime对象

    Args:
        date_str: 日期字符串，支持多种格式 (YYYY-MM-DD, YYYYMMDD, YYYY/MM/DD)

    Returns:
        datetime对象或None
    """
    if not date_str:
        return None

    formats = [
        "%Y-%m-%d",
        "%Y%m%d",
        "%Y/%m/%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y%m%d%H%M%S",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


def format_date(date: datetime, fmt: str = "%Y-%m-%d") -> str:
    """
    格式化日期为字符串

    Args:
        date: datetime对象
        fmt: 格式字符串

    Returns:
        格式化后的日期字符串
    """
    if not date:
        return ""
    return date.strftime(fmt)


def get_trading_days(start_date: str, end_date: str) -> List[str]:
    """
    获取指定日期范围内的交易日列表

    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)

    Returns:
        交易日列表
    """
    start = parse_date(start_date)
    end = parse_date(end_date)

    if not start or not end:
        return []

    trading_days = []
    current = start

    while current <= end:
        # 跳过周末 (5=周六, 6=周日)
        if current.weekday() < 5:
            trading_days.append(format_date(current))
        current += timedelta(days=1)

    return trading_days


def get_current_trading_date() -> str:
    """
    获取当前交易日日期

    Returns:
        当前日期 (YYYY-MM-DD)
    """
    tz = ZoneInfo(get_timezone_name())
    now = datetime.now(tz)

    # 如果是周末，返回下一个周一
    if now.weekday() == 5:  # 周六
        now = now + timedelta(days=2)
    elif now.weekday() == 6:  # 周日
        now = now + timedelta(days=1)

    return format_date(now)


def is_trading_time() -> bool:
    """
    检查当前是否为交易时间

    Returns:
        是否为交易时间
    """
    tz = ZoneInfo(get_timezone_name())
    now = datetime.now(tz)

    # 检查是否为工作日
    if now.weekday() >= 5:  # 周六或周日
        return False

    # A股交易时间: 9:30-11:30, 13:00-15:00
    time_str = now.strftime("%H:%M")
    morning_start, morning_end = "09:30", "11:30"
    afternoon_start, afternoon_end = "13:00", "15:00"

    return (
        morning_start <= time_str <= morning_end
        or afternoon_start <= time_str <= afternoon_end
    )


def get_date_range(days: int, end_date: Optional[str] = None) -> tuple:
    """
    获取日期范围

    Args:
        days: 天数
        end_date: 结束日期，默认为今天

    Returns:
        (开始日期, 结束日期) 元组
    """
    if end_date:
        end = parse_date(end_date)
    else:
        tz = ZoneInfo(get_timezone_name())
        end = datetime.now(tz)

    if not end:
        end = datetime.now()

    start = end - timedelta(days=days)
    return format_date(start), format_date(end)
