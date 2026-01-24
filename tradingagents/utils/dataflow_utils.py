# -*- coding: utf-8 -*-
"""
数据流通用工具函数

从 tradingagents/dataflows/utils.py 迁移而来
"""

import os
import json
import pandas as pd
from datetime import date, timedelta, datetime
from typing import Annotated

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("agents")


SavePathType = Annotated[str, "File path to save data. If None, data is not saved."]


def save_output(data: pd.DataFrame, tag: str, save_path: SavePathType = None) -> None:
    """
    保存 DataFrame 到 CSV 文件

    Args:
        data: 要保存的 DataFrame
        tag: 标签（用于日志）
        save_path: 保存路径，如果为 None 则不保存
    """
    if save_path:
        data.to_csv(save_path)
        logger.info(f"{tag} saved to {save_path}")


def get_current_date():
    """
    获取当前日期（YYYY-MM-DD 格式）

    Returns:
        str: 当前日期字符串
    """
    return date.today().strftime("%Y-%m-%d")


def decorate_all_methods(decorator):
    """
    类装饰器：为类的所有方法应用指定的装饰器

    Args:
        decorator: 要应用的装饰器函数

    Returns:
        function: 类装饰器函数

    Example:
        >>> @decorate_all_methods(my_decorator)
        >>> class MyClass:
        >>>     def method1(self):
        >>>         pass
    """

    def class_decorator(cls):
        for attr_name, attr_value in cls.__dict__.items():
            if callable(attr_value):
                setattr(cls, attr_name, decorator(attr_value))
        return cls

    return class_decorator


def get_next_weekday(date_input):
    """
    获取下一个工作日（跳过周末）

    Args:
        date_input: 日期对象或日期字符串（YYYY-MM-DD）

    Returns:
        datetime: 下一个工作日的日期对象

    Example:
        >>> get_next_weekday("2025-10-04")  # 周六
        datetime(2025, 10, 6)  # 返回周一
    """
    if not isinstance(date_input, datetime):
        date_input = datetime.strptime(date_input, "%Y-%m-%d")

    if date_input.weekday() >= 5:  # 周六(5)或周日(6)
        days_to_add = 7 - date_input.weekday()
        next_weekday = date_input + timedelta(days=days_to_add)
        return next_weekday
    else:
        return date_input


def get_trading_date_range(target_date=None, lookback_days=10):
    """
    获取用于查询交易数据的日期范围

    策略：获取最近N天的数据，以确保能获取到最后一个交易日的数据
    自动调整周末日期到最近的交易日，处理周末、节假日和数据延迟的情况

    Args:
        target_date: 目标日期（datetime对象或字符串YYYY-MM-DD），默认为今天
        lookback_days: 向前查找的天数，默认10天（可以覆盖周末+小长假）

    Returns:
        tuple: (start_date, end_date) 两个字符串，格式YYYY-MM-DD

    Example:
        >>> get_trading_date_range("2025-10-13", 10)
        ("2025-10-03", "2025-10-13")

        >>> get_trading_date_range("2025-10-12", 10)  # 周日
        ("2025-10-02", "2025-10-10")  # 自动调整到周五
    """
    from datetime import datetime, timedelta

    # 处理输入日期
    if target_date is None:
        target_date = datetime.now()
    elif isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d")

    # 如果是未来日期，使用今天
    today = datetime.now()
    if target_date.date() > today.date():
        target_date = today

    # 🔧 调整：如果 target_date 是周末（周六/周日），调整为前一个工作日（周五）
    if target_date.weekday() >= 5:  # 5=周六, 6=周日
        days_to_subtract = target_date.weekday() - 4  # 周六减1天=周五，周日减2天=周五
        target_date = target_date - timedelta(days=days_to_subtract)
        logger.info(
            f"📅 [交易日调整] target_date={target_date.strftime('%Y-%m-%d')} (原始是周末，已调整为最近交易日)"
        )

    # 计算开始日期（向前推N天）
    start_date = target_date - timedelta(days=lookback_days)

    # 返回日期范围
    return start_date.strftime("%Y-%m-%d"), target_date.strftime("%Y-%m-%d")
