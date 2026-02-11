# -*- coding: utf-8 -*-
"""
增强功能配置集成模块

将所有新创建的优化模块集成到现有系统中。
通过环境变量控制是否启用增强功能。

作者: Claude
创建日期: 2026-02-12
"""

import os
from typing import Optional, Dict, Any
from functools import lru_cache

# 导入统一日志系统
try:
    from tradingagents.utils.logging_init import get_logger

    logger = get_logger("enhancements_integration")
except:
    import logging

    logger = logging.getLogger("enhancements_integration")


class EnhancementsConfig:
    """增强功能配置"""

    # 功能开关
    ENABLE_ENHANCED_PARALLEL_EXECUTION = (
        os.getenv("ENABLE_ENHANCED_PARALLEL_EXECUTION", "false").lower() == "true"
    )

    ENABLE_ENHANCED_LLM_CACHE = (
        os.getenv("ENABLE_ENHANCED_LLM_CACHE", "false").lower() == "true"
    )

    ENABLE_ENHANCED_REDIS_CLIENT = (
        os.getenv("ENABLE_ENHANCED_REDIS_CLIENT", "false").lower() == "true"
    )

    ENABLE_ENHANCED_PROGRESS_TRACKER = (
        os.getenv("ENABLE_ENHANCED_PROGRESS_TRACKER", "false").lower() == "true"
    )

    # 超时配置
    ANALYST_TIMEOUT_SECONDS = int(os.getenv("ANALYST_TIMEOUT_SECONDS", "180"))
    ANALYST_ALLOW_PARTIAL_FAILURE = (
        os.getenv("ANALYST_ALLOW_PARTIAL_FAILURE", "true").lower() == "true"
    )

    # 缓存配置
    LLM_CACHE_BACKEND = os.getenv("LLM_CACHE_BACKEND", "memory")  # memory, redis, file
    LLM_CACHE_MAX_SIZE = int(os.getenv("LLM_CACHE_MAX_SIZE", "10000"))
    LLM_CACHE_DEFAULT_TTL = int(os.getenv("LLM_CACHE_DEFAULT_TTL", "3600"))

    # Redis配置
    REDIS_MAX_RETRIES = int(os.getenv("REDIS_MAX_RETRIES", "3"))
    REDIS_RETRY_DELAY = float(os.getenv("REDIS_RETRY_DELAY", "1.0"))

    @classmethod
    def is_any_enabled(cls) -> bool:
        """检查是否有任何增强功能启用"""
        return any(
            [
                cls.ENABLE_ENHANCED_PARALLEL_EXECUTION,
                cls.ENABLE_ENHANCED_LLM_CACHE,
                cls.ENABLE_ENHANCED_REDIS_CLIENT,
                cls.ENABLE_ENHANCED_PROGRESS_TRACKER,
            ]
        )

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """获取所有增强功能状态"""
        return {
            "enhanced_parallel_execution": {
                "enabled": cls.ENABLE_ENHANCED_PARALLEL_EXECUTION,
                "timeout": cls.ANALYST_TIMEOUT_SECONDS,
                "allow_partial_failure": cls.ANALYST_ALLOW_PARTIAL_FAILURE,
            },
            "enhanced_llm_cache": {
                "enabled": cls.ENABLE_ENHANCED_LLM_CACHE,
                "backend": cls.LLM_CACHE_BACKEND,
                "max_size": cls.LLM_CACHE_MAX_SIZE,
                "default_ttl": cls.LLM_CACHE_DEFAULT_TTL,
            },
            "enhanced_redis_client": {
                "enabled": cls.ENABLE_ENHANCED_REDIS_CLIENT,
                "max_retries": cls.REDIS_MAX_RETRIES,
                "retry_delay": cls.REDIS_RETRY_DELAY,
            },
            "enhanced_progress_tracker": {
                "enabled": cls.ENABLE_ENHANCED_PROGRESS_TRACKER,
            },
        }


# 全局配置实例
_config = None


def get_config() -> EnhancementsConfig:
    """获取配置实例"""
    global _config
    if _config is None:
        _config = EnhancementsConfig()
    return _config


def init_enhanced_redis():
    """初始化增强型Redis客户端"""
    if not EnhancementsConfig.ENABLE_ENHANCED_REDIS_CLIENT:
        logger.info("🔧 [增强功能] 增强型Redis客户端已禁用，使用标准版本")
        return None

    try:
        from app.core.redis_client_enhanced import init_redis, get_connection_stats

        import asyncio

        loop = asyncio.get_event_loop()
        success = loop.run_until_complete(
            init_redis(
                max_retries=EnhancementsConfig.REDIS_MAX_RETRIES,
                retry_delay=EnhancementsConfig.REDIS_RETRY_DELAY,
            )
        )

        if success:
            stats = get_connection_stats()
            logger.info(f"✅ [增强功能] 增强型Redis客户端初始化成功: {stats}")
            return True
        else:
            logger.warning("⚠️ [增强功能] 增强型Redis客户端初始化失败")
            return False

    except Exception as e:
        logger.error(f"❌ [增强功能] 初始化增强型Redis客户端失败: {e}")
        return False


def init_enhanced_llm_cache():
    """初始化增强型LLM缓存"""
    if not EnhancementsConfig.ENABLE_ENHANCED_LLM_CACHE:
        logger.info("🔧 [增强功能] 增强型LLM缓存已禁用，使用标准版本")
        return None

    try:
        from tradingagents.cache.llm_cache_enhanced import get_enhanced_llm_cache

        cache = get_enhanced_llm_cache(
            cache_backend=EnhancementsConfig.LLM_CACHE_BACKEND,
            max_size=EnhancementsConfig.LLM_CACHE_MAX_SIZE,
            default_ttl=EnhancementsConfig.LLM_CACHE_DEFAULT_TTL,
        )

        logger.info(
            f"✅ [增强功能] 增强型LLM缓存初始化成功: "
            f"backend={EnhancementsConfig.LLM_CACHE_BACKEND}, "
            f"max_size={EnhancementsConfig.LLM_CACHE_MAX_SIZE}"
        )
        return cache

    except Exception as e:
        logger.error(f"❌ [增强功能] 初始化增强型LLM缓存失败: {e}")
        return None


def get_enhanced_parallel_executor(base_setup, progress_callback=None):
    """获取增强型并行执行器"""
    if not EnhancementsConfig.ENABLE_ENHANCED_PARALLEL_EXECUTION:
        logger.info("🔧 [增强功能] 增强型并行执行器已禁用，使用标准版本")
        from tradingagents.graph.parallel_analysts import create_parallel_executor

        return create_parallel_executor(base_setup)

    try:
        from tradingagents.graph.parallel_analysts_v2 import (
            create_enhanced_parallel_executor,
        )

        executor = create_enhanced_parallel_executor(
            base_setup=base_setup,
            analyst_timeout=EnhancementsConfig.ANALYST_TIMEOUT_SECONDS,
            progress_callback=progress_callback,
            use_cache=EnhancementsConfig.ENABLE_ENHANCED_LLM_CACHE,
            allow_partial_failure=EnhancementsConfig.ANALYST_ALLOW_PARTIAL_FAILURE,
        )

        logger.info(
            f"✅ [增强功能] 使用增强型并行执行器: "
            f"timeout={EnhancementsConfig.ANALYST_TIMEOUT_SECONDS}s, "
            f"allow_partial_failure={EnhancementsConfig.ANALYST_ALLOW_PARTIAL_FAILURE}"
        )
        return executor

    except Exception as e:
        logger.error(f"❌ [增强功能] 创建增强型并行执行器失败: {e}，回退到标准版本")
        from tradingagents.graph.parallel_analysts import create_parallel_executor

        return create_parallel_executor(base_setup)


def create_enhanced_progress_tracker(
    task_id: str, analysts: list, research_depth: str, llm_provider: str
):
    """创建增强型进度跟踪器"""
    if not EnhancementsConfig.ENABLE_ENHANCED_PROGRESS_TRACKER:
        logger.info("🔧 [增强功能] 增强型进度跟踪器已禁用，使用标准版本")
        from app.services.redis_progress_tracker import RedisProgressTracker

        return RedisProgressTracker(
            task_id=task_id,
            analysts=analysts,
            research_depth=research_depth,
            llm_provider=llm_provider,
        )

    try:
        from app.services.progress.tracker_enhanced import EnhancedProgressTracker

        tracker = EnhancedProgressTracker(
            task_id=task_id,
            analysts=analysts,
            research_depth=research_depth,
            llm_provider=llm_provider,
            use_redis=True,
        )

        logger.info(f"✅ [增强功能] 使用增强型进度跟踪器: {task_id}")
        return tracker

    except Exception as e:
        logger.error(f"❌ [增强功能] 创建增强型进度跟踪器失败: {e}，回退到标准版本")
        from app.services.redis_progress_tracker import RedisProgressTracker

        return RedisProgressTracker(
            task_id=task_id,
            analysts=analysts,
            research_depth=research_depth,
            llm_provider=llm_provider,
        )


def init_all_enhancements():
    """初始化所有增强功能"""
    logger.info("🔧 [增强功能] 开始初始化所有增强功能...")

    if not EnhancementsConfig.is_any_enabled():
        logger.info("🔧 [增强功能] 所有增强功能均已禁用")
        return

    results = {
        "redis": init_enhanced_redis(),
        "llm_cache": init_enhanced_llm_cache() is not None,
        "config": EnhancementsConfig.get_status(),
    }

    enabled_count = sum(
        [
            EnhancementsConfig.ENABLE_ENHANCED_PARALLEL_EXECUTION,
            EnhancementsConfig.ENABLE_ENHANCED_LLM_CACHE,
            EnhancementsConfig.ENABLE_ENHANCED_REDIS_CLIENT,
            EnhancementsConfig.ENABLE_ENHANCED_PROGRESS_TRACKER,
        ]
    )

    logger.info(f"✅ [增强功能] 初始化完成: {enabled_count} 个功能已启用")
    logger.info(f"📊 [增强功能] 状态: {results}")

    return results


# 向后兼容的便捷函数
def is_enhancements_enabled() -> bool:
    """检查是否有增强功能启用"""
    return EnhancementsConfig.is_any_enabled()


def get_enhancements_status() -> Dict[str, Any]:
    """获取增强功能状态"""
    return EnhancementsConfig.get_status()
