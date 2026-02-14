# -*- coding: utf-8 -*-
"""
数据源适配器常量定义
"""

# 网络错误关键词（用于判断是否可重试）
NETWORK_ERROR_KEYWORDS = [
    "connection",
    "remote",
    "timeout",
    "aborted",
    "reset",
    "closed",
]

# 默认重试配置
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_DELAY = 1.0  # 秒
DEFAULT_MAX_DELAY = 30.0  # 秒
DEFAULT_BACKOFF = 2.0
