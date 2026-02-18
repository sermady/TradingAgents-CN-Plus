# -*- coding: utf-8 -*-
"""
LLM响应缓存模块

⚠️ 已废弃: 此模块已合并到 llm_cache_enhanced.py
请使用: from tradingagents.cache.llm_cache_enhanced import get_llm_cache, LLMCache

为保持向后兼容，此模块现在重新导出增强版的功能。
"""

# 重新导出增强版的所有功能
from tradingagents.cache.llm_cache_enhanced import (
    get_llm_cache,
)

# 保留便捷函数以保持向后兼容
from typing import Optional


def cache_llm_response(
    prompt: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    ttl: Optional[int] = None,
) -> Optional[str]:
    """
    缓存LLM响应(便捷函数) [已废弃，请直接使用缓存实例]
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
    保存LLM响应到缓存(便捷函数) [已废弃，请直接使用缓存实例]
    """
    cache = get_llm_cache()
    cache.set(prompt, response, model, temperature, max_tokens, ttl)
