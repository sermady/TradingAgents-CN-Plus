# -*- coding: utf-8 -*-
"""
配置管理模块

注意：旧版配置管理已弃用，请使用新的统一配置管理：
- app.core.unified_config_service.UnifiedConfigManager

此模块保留用于向后兼容。
"""

# 向后兼容：导入旧版配置管理器
try:
    from .config_manager import (
        config_manager,
        token_tracker,
        ModelConfig,
        PricingConfig,
        UsageRecord,
    )
except ImportError:
    config_manager = None
    token_tracker = None
    ModelConfig = None
    PricingConfig = None
    UsageRecord = None

__all__ = [
    "config_manager",
    "token_tracker",
    "ModelConfig",
    "PricingConfig",
    "UsageRecord",
]
