# -*- coding: utf-8 -*-
"""
缓存服务工具函数
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _run_async(coro):
    """在同步上下文中运行异步协程"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 如果事件循环已经在运行，使用 run_coroutine_threadsafe
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # 没有事件循环，创建一个新的
        return asyncio.run(coro)


# 全局缓存服务实例
_cache_service: Optional["UnifiedCacheService"] = None


def get_cache_service() -> "UnifiedCacheService":
    """获取全局缓存服务实例"""
    global _cache_service
    if _cache_service is None:
        from .core import UnifiedCacheService
        _cache_service = UnifiedCacheService()
    return _cache_service
