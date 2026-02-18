# -*- coding: utf-8 -*-
"""
数据源配置服务工具函数

提供数据源测试相关的通用工具函数
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def truncate_api_key(api_key: str, visible_chars: int = 8) -> str:
    """
    截断 API Key，只显示前几位和后几位，中间用省略号代替

    Args:
        api_key: 原始 API Key
        visible_chars: 前后显示的字符数

    Returns:
        截断后的 API Key
    """
    if not api_key:
        return ""

    if len(api_key) <= visible_chars * 2 + 3:
        return api_key

    return f"{api_key[:visible_chars]}...{api_key[-visible_chars:]}"
