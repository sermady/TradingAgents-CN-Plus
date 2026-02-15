# -*- coding: utf-8 -*-
"""
管理器模块
包含缓存管理、降级策略、配置管理等

注意：为避免循环导入，这些类需要直接从子模块导入
"""

# 延迟导入，避免循环导入问题
# 使用方式：
#   from tradingagents.dataflows.managers.cache_manager import CacheManager
#   from tradingagents.dataflows.managers.fallback_manager import FallbackManager
#   from tradingagents.dataflows.managers.config_manager import ConfigManager

__all__ = ["CacheManager", "FallbackManager", "ConfigManager"]
