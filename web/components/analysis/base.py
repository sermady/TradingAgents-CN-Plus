# -*- coding: utf-8 -*-
"""
分析结果组件 - 基础函数和常量
"""

from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def safe_timestamp_to_datetime(timestamp_value):
    """安全地将时间戳转换为datetime对象"""
    if isinstance(timestamp_value, datetime):
        # 如果已经是datetime对象（来自MongoDB）
        return timestamp_value
    elif isinstance(timestamp_value, (int, float)):
        # 如果是时间戳数字（来自文件系统）
        try:
            return datetime.fromtimestamp(timestamp_value)
        except (ValueError, OSError):
            # 时间戳无效，使用当前时间
            return datetime.now()
    else:
        # 其他情况，使用当前时间
        return datetime.now()


def get_analysis_results_dir():
    """获取分析结果目录"""
    results_dir = Path(__file__).parent.parent.parent / "data" / "analysis_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


def get_favorites_file():
    """获取收藏文件路径"""
    return get_analysis_results_dir() / "favorites.json"


def get_tags_file():
    """获取标签文件路径"""
    return get_analysis_results_dir() / "tags.json"
