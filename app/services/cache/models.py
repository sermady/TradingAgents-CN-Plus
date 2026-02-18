# -*- coding: utf-8 -*-
"""
缓存数据模型
"""

from datetime import datetime, timezone
from typing import Any


class CacheEntry:
    """缓存条目"""

    def __init__(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,  # 默认1小时
        source: str = "memory",
    ):
        self.key = key
        self.value = value
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.ttl = ttl
        self.source = source
        self.hit_count = 0

    def is_expired(self) -> bool:
        """检查是否过期"""
        age = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return age > self.ttl
