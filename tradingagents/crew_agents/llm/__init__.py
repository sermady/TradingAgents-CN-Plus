# -*- coding: utf-8 -*-
"""
LLM模块
提供AI模型配置和管理功能
"""

from .config_manager import (
    LLMConfigManager,
    ModelProvider,
    ModelConfig,
    llm_config_manager,
    get_current_llm,
    get_available_models,
    switch_model,
    get_model_info
)

__all__ = [
    'LLMConfigManager',
    'ModelProvider', 
    'ModelConfig',
    'llm_config_manager',
    'get_current_llm',
    'get_available_models',
    'switch_model',
    'get_model_info'
]