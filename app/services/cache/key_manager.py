# -*- coding: utf-8 -*-
"""
缓存键管理模块

提供缓存键的规范化、生成和解析功能
"""

import hashlib
from typing import Any


class KeyManager:
    """缓存键管理器"""

    @staticmethod
    def normalize_key(key: str, category: str = "general") -> str:
        """
        规范化缓存键

        Args:
            key: 原始键
            category: 缓存类别

        Returns:
            规范化的缓存键
        """
        # 转换为小写
        key = key.lower()
        # 替换特殊字符
        key = key.replace(" ", "_").replace(":", "_").replace("-", "_")
        # 添加类别前缀
        return f"{category}:{key}"

    @staticmethod
    def generate_cache_key(category: str, *args, **kwargs) -> str:
        """
        生成缓存键

        Args:
            category: 缓存类别
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            缓存键字符串
        """
        # 序列化参数
        key_parts = [str(arg) for arg in args]
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))

        # 生成哈希
        key_str = ":".join(key_parts)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()[:16]

        return f"{category}:{key_hash}"
