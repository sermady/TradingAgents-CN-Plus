# -*- coding: utf-8 -*-
"""
LLM响应缓存实现
提供基于内容的智能缓存,减少LLM调用和Token消耗
"""

import time
import hashlib
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


class LLMCache:
    """LLM响应缓存"""

    def __init__(
        self,
        cache_backend: str = "memory",  # memory, redis, mongodb, file
        max_size: int = 10000,
        default_ttl: int = 3600,  # 1小时
    ):
        """
        初始化LLM缓存

        Args:
            cache_backend: 缓存后端 (memory/redis/mongodb/file)
            max_size: 最大缓存数量
            default_ttl: 默认TTL(秒)
        """
        self.cache_backend = cache_backend
        self.max_size = max_size
        self.default_ttl = default_ttl

        # 内存缓存
        self._memory_cache: Dict[str, Tuple[str, float, int]] = {}

        logger.info(
            f"🗄️ [LLM缓存] 初始化缓存: backend={cache_backend}, max_size={max_size}, default_ttl={default_ttl}s"
        )

    def _get_cache_key(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """
        生成缓存键

        Args:
            prompt: 提示词
            model: 模型名称
            temperature: 温度
            max_tokens: 最大token数

        Returns:
            缓存键
        """
        key_string = f"{model}:{temperature}:{max_tokens}:{prompt}"
        return hashlib.sha256(key_string.encode("utf-8")).hexdigest()

    def get(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        ttl: Optional[int] = None,
    ) -> Optional[str]:
        """
        从缓存获取响应

        Args:
            prompt: 提示词
            model: 模型名称
            temperature: 温度
            max_tokens: 最大token数
            ttl: TTL(秒),None则使用默认TTL

        Returns:
            缓存的响应,如果不存在或过期则返回None
        """
        cache_key = self._get_cache_key(prompt, model, temperature, max_tokens)

        if self.cache_backend == "memory":
            return self._get_from_memory(cache_key, ttl)

        logger.debug(f"🔍 [LLM缓存] 缓存未命中: key={cache_key[:16]}...")
        return None

    def set(
        self,
        prompt: str,
        response: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        ttl: Optional[int] = None,
    ):
        """
        保存响应到缓存

        Args:
            prompt: 提示词
            response: LLM响应
            model: 模型名称
            temperature: 温度
            max_tokens: 最大token数
            ttl: TTL(秒),None则使用默认TTL
        """
        if ttl is None:
            ttl = self.default_ttl

        cache_key = self._get_cache_key(prompt, model, temperature, max_tokens)

        if self.cache_backend == "memory":
            self._save_to_memory(cache_key, response, ttl)

        logger.debug(f"💾 [LLM缓存] 缓存命中: key={cache_key[:16]}...")

    def _get_from_memory(
        self,
        cache_key: str,
        ttl: int,
    ) -> Optional[str]:
        """从内存缓存获取"""
        if cache_key not in self._memory_cache:
            return None

        response, timestamp, hit_count = self._memory_cache[cache_key]
        age = time.time() - timestamp

        # 检查是否过期
        if age > ttl:
            del self._memory_cache[cache_key]
            logger.debug(f"⏰️ [LLM缓存] 缓存过期: age={age:.1f}s > {ttl}s")
            return None

        # 更新命中次数
        self._memory_cache[cache_key] = (response, timestamp, hit_count + 1)

        logger.info(
            f"✅ [LLM缓存] 缓存命中: key={cache_key[:16]}..., age={age:.1f}s, 命中次数={hit_count}"
        )
        return response

    def _save_to_memory(
        self,
        cache_key: str,
        response: str,
        ttl: int,
    ):
        """保存到内存缓存"""
        # 检查缓存大小,必要时清理
        if len(self._memory_cache) >= self.max_size:
            self._evict_oldest()

        self._memory_cache[cache_key] = (response, time.time(), 1)

    def _evict_oldest(self):
        """淘汰最旧的缓存"""
        if not self._memory_cache:
            return

        # 找到最旧的缓存
        oldest_key = min(
            self._memory_cache.items(),
            key=lambda x: x[1][1],
        )

        del self.memory_cache[oldest_key]
        logger.info(f"🗑️ [LLM缓存] 淘汰旧缓存: key={oldest_key[:16]}...")

    def clear(self):
        """清除所有缓存"""
        cache_size = len(self._memory_cache)
        self._memory_cache.clear()
        logger.info(f"🗑️ [LLM缓存] 已清除缓存: 共{cache_size}条")

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "backend": self.cache_backend,
            "size": len(self.memory_cache),
            "max_size": self.max_size,
            "hit_rate": self._calculate_hit_rate(),
        }

    def _calculate_hit_rate(self) -> float:
        """计算缓存命中率"""
        total_hits = sum(hit_count for _, _, hit_count in self._memory_cache.values())
        total_access = len(self.memory_cache)
        return (total_hits / total_access * 100) if total_access > 0 else 0


# 全局缓存实例
_llm_cache: Optional[LLMCache] = None


def get_llm_cache(
    cache_backend: str = "memory",
    max_size: int = 10000,
    default_ttl: int = 3600,
) -> LLMCache:
    """
    获取LLM缓存实例(单例模式)

    Args:
        cache_backend: 缓存后端
        max_size: 最大缓存数量
        default_ttl: 默认TTL

    Returns:
        LLM缓存实例
    """
    global _llm_cache

    if _llm_cache is None:
        _llm_cache = LLMCache(
            cache_backend=cache_backend,
            max_size=max_size,
            default_ttl=default_ttl,
        )

    return _llm_cache


def cache_llm_response(
    prompt: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    ttl: Optional[int] = None,
) -> Optional[str]:
    """
    缓存LLM响应(便捷函数)

    Args:
        prompt: 提示词
        model: 模型名称
        temperature: 温度
        max_tokens: 最大token数
        ttl: TTL(秒),None则使用默认TTL

    Returns:
        缓存的响应,如果不存在或过期则返回None
    """
    cache = get_llm_cache()
    return cache.get(prompt, model, temperature, max_tokens, ttl)


def save_llm_response(
    prompt: str,
    response: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    ttl: Optional[int] = None,
):
    """
    保存LLM响应到缓存(便捷函数)

    Args:
        prompt: 提示词
        response: LLM响应
        model: 模型名称
        temperature: 温度
        max_tokens: 最大token数
        ttl: TTL(秒),None则使用默认TTL
    """
    cache = get_llm_cache()
    cache.set(prompt, response, model, temperature, max_tokens, ttl)


def clear_llm_cache():
    """清除LLM缓存"""
    cache = get_llm_cache()
    cache.clear()
