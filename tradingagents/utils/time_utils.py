# -*- coding: utf-8 -*-
"""
时间工具模块 - 提供统一的当前时间获取和格式化功能
用于在分析提示词中明确提供当前日期，避免LLM依赖过时的训练数据时间认知

P0 改进: 统一项目中所有时间处理，替代直接使用 datetime.now()
"""

import os
from datetime import datetime, date, timedelta
from typing import Optional


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


def get_chinese_weekday() -> str:
    """获取中文星期几（如：周二）"""
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return weekdays[date.today().weekday()]


def get_iso_date() -> str:
    """获取ISO格式的当前日期（如：2026-01-25）"""
    return get_current_date_str("%Y-%m-%d")


def get_chinese_datetime() -> str:
    """获取中文格式的当前日期时间（如：2026年01月25日 14:30:00）"""
    return get_current_datetime_str("%Y年%m月%d日 %H:%M:%S")


# ==================== P0 改进: 统一 Worker 目录时间处理 ====================

def get_now() -> datetime:
    """
    获取当前日期时间（替代 datetime.now()）

    Returns:
        datetime: 当前日期时间对象
    """
    return datetime.now()


def get_today_str() -> str:
    """
    获取今天的日期字符串（ISO格式: YYYY-MM-DD）
    替代: datetime.now().strftime('%Y-%m-%d')

    Returns:
        str: 当前日期字符串
    """
    return datetime.now().strftime('%Y-%m-%d')


def get_days_ago_str(days: int, format_str: str = '%Y-%m-%d') -> str:
    """
    获取 N 天前的日期字符串
    替代: (datetime.now() - timedelta(days=N)).strftime('%Y-%m-%d')

    Args:
        days: 天数
        format_str: 日期格式字符串

    Returns:
        str: N天前的日期字符串
    """
    return (datetime.now() - timedelta(days=days)).strftime(format_str)


def get_days_later_str(days: int, format_str: str = '%Y-%m-%d') -> str:
    """
    获取 N 天后的日期字符串

    Args:
        days: 天数
        format_str: 日期格式字符串

    Returns:
        str: N天后的日期字符串
    """
    return (datetime.now() + timedelta(days=days)).strftime(format_str)


def get_timestamp() -> datetime:
    """
    获取当前时间戳（用于记录 updated_at, created_at 等）
    替代: datetime.now()

    Returns:
        datetime: 当前日期时间对象
    """
    return datetime.now()


def get_iso_timestamp() -> str:
    """
    获取 ISO 格式时间戳字符串
    替代: datetime.now().isoformat()

    Returns:
        str: ISO格式时间戳
    """
    return datetime.now().isoformat()


class Timer:
    """
    计时器上下文管理器
    用于统计代码执行时间

    示例:
        with Timer() as timer:
            # 执行一些操作
            pass
        print(f"耗时: {timer.duration:.2f}秒")
    """

    def __init__(self):
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.duration: float = 0.0

    def __enter__(self):
        self.start_time = datetime.now()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
        return False


class CacheTime:
    """
    缓存时间管理工具
    用于判断缓存是否过期

    示例:
        cache_time = CacheTime()

        # 设置缓存时间
        cache_time.update()

        # 检查缓存是否过期（默认3600秒）
        if cache_time.is_expired(ttl=3600):
            # 刷新缓存
            pass
    """

    def __init__(self):
        self._cache_time: Optional[datetime] = None

    def update(self):
        """更新缓存时间为当前时间"""
        self._cache_time = datetime.now()

    def is_expired(self, ttl_seconds: int) -> bool:
        """
        检查缓存是否过期

        Args:
            ttl_seconds: 缓存有效期（秒）

        Returns:
            bool: 是否已过期
        """
        if self._cache_time is None:
            return True
        return (datetime.now() - self._cache_time).total_seconds() > ttl_seconds

    def get_age_seconds(self) -> float:
        """
        获取缓存已存在的时间（秒）

        Returns:
            float: 缓存年龄（秒）
        """
        if self._cache_time is None:
            return float('inf')
        return (datetime.now() - self._cache_time).total_seconds()


def format_datetime(dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    格式化日期时间为字符串

    Args:
        dt: 日期时间对象
        format_str: 格式字符串

    Returns:
        str: 格式化后的字符串
    """
    return dt.strftime(format_str)


def parse_datetime(date_str: str, format_str: str = '%Y-%m-%d') -> datetime:
    """
    解析日期字符串为日期时间对象

    Args:
        date_str: 日期字符串
        format_str: 格式字符串

    Returns:
        datetime: 日期时间对象
    """
    return datetime.strptime(date_str, format_str)


if __name__ == "__main__":
    # 测试输出
    print(f"当前日期（中文）: {get_chinese_date()}")
    print(f"当前星期: {get_chinese_weekday()}")
    print(f"当前日期（ISO）: {get_iso_date()}")
    print(f"当前日期时间（中文）: {get_chinese_datetime()}")