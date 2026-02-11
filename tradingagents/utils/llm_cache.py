# -*- coding: utf-8 -*-
"""
LLM 调用缓存模块
缓存 LLM 调用结果以提高性能，避免重复调用

作者: Claude
创建日期: 2026-02-12
"""

import hashlib
import json
import time
from typing import Optional, Any, Dict
from functools import wraps
from datetime import datetime, timedelta

from tradingagents.utils.logging_init import get_logger

logger = get_logger("llm_cache")


class LLMCache:
    """LLM 调用缓存管理器"""

    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000):
        """
        初始化缓存

        Args:
            ttl_seconds: 缓存过期时间（秒），默认1小时
            max_size: 最大缓存条目数
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl_seconds = ttl_seconds
        self._max_size = max_size
        self._hit_count = 0
        self._miss_count = 0

    def _generate_key(self, messages: list, model: str, **kwargs) -> str:
        """生成缓存键"""
        # 提取消息内容
        message_contents = []
        for msg in messages:
            if hasattr(msg, "content"):
                content = msg.content
            elif isinstance(msg, dict):
                content = msg.get("content", "")
            else:
                content = str(msg)
            message_contents.append(content)

        # 创建缓存键
        cache_data = {
            "messages": message_contents,
            "model": model,
            "kwargs": {
                k: v
                for k, v in kwargs.items()
                if k not in ["session_id", "analysis_type"]
            },
        }
        cache_str = json.dumps(cache_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(cache_str.encode()).hexdigest()

    def get(self, messages: list, model: str, **kwargs) -> Optional[Any]:
        """获取缓存结果"""
        key = self._generate_key(messages, model, **kwargs)

        if key in self._cache:
            entry = self._cache[key]
            # 检查是否过期
            if time.time() - entry["timestamp"] < self._ttl_seconds:
                self._hit_count += 1
                logger.debug(
                    f"🎯 LLM缓存命中 | Key: {key[:8]}... | 总命中: {self._hit_count}"
                )
                return entry["result"]
            else:
                # 过期，删除
                del self._cache[key]

        self._miss_count += 1
        return None

    def set(self, messages: list, model: str, result: Any, **kwargs):
        """设置缓存结果"""
        # 清理过期条目
        self._cleanup_expired()

        # 如果缓存已满，清理最旧的条目
        if len(self._cache) >= self._max_size:
            self._cleanup_oldest(100)  # 清理100个最旧的

        key = self._generate_key(messages, model, **kwargs)
        self._cache[key] = {"result": result, "timestamp": time.time(), "model": model}
        logger.debug(
            f"💾 LLM缓存已保存 | Key: {key[:8]}... | 缓存大小: {len(self._cache)}"
        )

    def _cleanup_expired(self):
        """清理过期条目"""
        current_time = time.time()
        expired_keys = [
            key
            for key, entry in self._cache.items()
            if current_time - entry["timestamp"] > self._ttl_seconds
        ]
        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"🧹 清理 {len(expired_keys)} 个过期缓存条目")

    def _cleanup_oldest(self, count: int):
        """清理最旧的条目"""
        sorted_items = sorted(self._cache.items(), key=lambda x: x[1]["timestamp"])
        for key, _ in sorted_items[:count]:
            del self._cache[key]
        logger.debug(f"🧹 清理 {count} 个最旧缓存条目")

    def get_stats(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        return {
            "hits": self._hit_count,
            "misses": self._miss_count,
            "size": len(self._cache),
            "hit_rate": self._hit_count / (self._hit_count + self._miss_count)
            if (self._hit_count + self._miss_count) > 0
            else 0,
        }

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._hit_count = 0
        self._miss_count = 0
        logger.info("🗑️ LLM缓存已清空")


# 全局缓存实例
_llm_cache = LLMCache(ttl_seconds=3600, max_size=1000)


def get_llm_cache() -> LLMCache:
    """获取全局LLM缓存实例"""
    return _llm_cache


def cached_llm_invoke(func):
    """
    LLM调用缓存装饰器

    使用示例:
        @cached_llm_invoke
        def invoke(self, messages, **kwargs):
            # 原始的invoke实现
            pass
    """

    @wraps(func)
    def wrapper(self, messages, **kwargs):
        cache = get_llm_cache()
        model = getattr(self, "model", "unknown")

        # 尝试从缓存获取
        cached_result = cache.get(messages, model, **kwargs)
        if cached_result is not None:
            return cached_result

        # 调用原始函数
        result = func(self, messages, **kwargs)

        # 缓存结果
        cache.set(messages, model, result, **kwargs)

        return result

    return wrapper


def clear_llm_cache():
    """清空LLM缓存"""
    get_llm_cache().clear()


def get_llm_cache_stats() -> Dict[str, int]:
    """获取LLM缓存统计"""
    return get_llm_cache().get_stats()
