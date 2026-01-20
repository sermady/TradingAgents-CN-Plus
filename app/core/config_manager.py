# -*- coding: utf-8 -*-
"""
Centralized Configuration Manager
Unifies configuration from Environment Variables, Local Files, and MongoDB.
Acts as the single source of truth for the application.
"""

import os
import logging
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone

from app.core.config import settings as env_settings
from app.core.database import get_mongo_db_sync
from app.models.config import LLMConfig, SystemConfig

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Centralized Configuration Manager.
    Priorities: Environment Variables > MongoDB > Default/File Settings
    """
    
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self._db_config_cache: Optional[Dict[str, Any]] = None
        self._last_cache_update: datetime = datetime.min.replace(tzinfo=timezone.utc)
        self._cache_ttl_seconds = 60
        self._initialized = True

    def _get_db_config_sync(self) -> Dict[str, Any]:
        """
        Fetch system configuration from MongoDB synchronously.
        """
        try:
            # Check cache first
            now = datetime.now(timezone.utc)
            if self._db_config_cache and (now - self._last_cache_update).total_seconds() < self._cache_ttl_seconds:
                return self._db_config_cache

            db = get_mongo_db_sync()
            collection = db.system_configs
            # Fetch the latest active configuration
            doc = collection.find_one({"is_active": True}, sort=[("version", -1)])
            
            if doc:
                self._db_config_cache = doc
                self._last_cache_update = now
                return doc
            return {}
        except Exception as e:
            logger.warning(f"Failed to fetch config from MongoDB: {e}")
            return {}

    def get_system_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a system setting value with priority:
        1. Environment Variable (Upper case key)
        2. MongoDB System Settings
        3. env_settings (pydantic)
        4. Default value provided
        """
        # 1. Environment Variable
        env_key = key.upper()
        if env_key in os.environ:
            return os.environ[env_key]
        
        # 2. MongoDB
        db_config = self._get_db_config_sync()
        system_settings = db_config.get("system_settings", {})
        if key in system_settings:
            return system_settings[key]
        
        # 3. Pydantic Settings (if applicable)
        if hasattr(env_settings, env_key):
            return getattr(env_settings, env_key)
            
        return default

    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific LLM model.
        Returns a dictionary with keys: max_tokens, temperature, timeout, retry_times, api_base
        """
        db_config = self._get_db_config_sync()
        llm_configs = db_config.get("llm_configs", [])
        
        # Default config
        config = {
            "max_tokens": 4000,
            "temperature": 0.7,
            "timeout": 180,
            "retry_times": 3,
            "api_base": None
        }

        # Find in DB config
        for llm_cfg in llm_configs:
            # Handle both dict and object (if parsed)
            cfg_name = llm_cfg.get("model_name") if isinstance(llm_cfg, dict) else getattr(llm_cfg, "model_name", "")
            
            if cfg_name == model_name:
                if isinstance(llm_cfg, dict):
                    config.update({k: v for k, v in llm_cfg.items() if k in config and v is not None})
                else:
                    # Assuming Pydantic model
                    if hasattr(llm_cfg, "max_tokens") and llm_cfg.max_tokens: config["max_tokens"] = llm_cfg.max_tokens
                    if hasattr(llm_cfg, "temperature") and llm_cfg.temperature: config["temperature"] = llm_cfg.temperature
                    if hasattr(llm_cfg, "timeout") and llm_cfg.timeout: config["timeout"] = llm_cfg.timeout
                    if hasattr(llm_cfg, "retry_times") and llm_cfg.retry_times: config["retry_times"] = llm_cfg.retry_times
                    if hasattr(llm_cfg, "api_base") and llm_cfg.api_base: config["api_base"] = llm_cfg.api_base
                break
        
        return config

    def get_quick_analysis_model(self) -> str:
        """Get the model name configured for quick analysis."""
        return self.get_system_setting("quick_analysis_model", "qwen-turbo")

    def get_deep_analysis_model(self) -> str:
        """Get the model name configured for deep analysis."""
        return self.get_system_setting("deep_analysis_model", "qwen-max")

    def get_provider_by_model(self, model_name: str) -> str:
        """
        Identify the provider for a given model name.
        Defaults to 'dashscope' if not found.
        """
        db_config = self._get_db_config_sync()
        llm_configs = db_config.get("llm_configs", [])
        
        for llm_cfg in llm_configs:
            cfg_name = llm_cfg.get("model_name") if isinstance(llm_cfg, dict) else getattr(llm_cfg, "model_name", "")
            if cfg_name == model_name:
                return llm_cfg.get("provider", "dashscope") if isinstance(llm_cfg, dict) else getattr(llm_cfg, "provider", "dashscope")
        
        # Fallback heuristics
        if "gpt" in model_name: return "openai"
        if "gemini" in model_name: return "google"
        if "claude" in model_name: return "anthropic"
        if "deepseek" in model_name: return "deepseek"
        
        return "dashscope"

# Global instance
config_manager = ConfigManager()
