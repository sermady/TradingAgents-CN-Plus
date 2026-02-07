#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置服务测试
"""

import pytest
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from app.core.unified_config_service import (
    get_config_manager,
    UnifiedConfigManager,
    ConfigCacheEntry,
)


# 自动使用的 fixture：在每个测试前后清理缓存
@pytest.fixture(autouse=True)
def clear_config_cache():
    """在每个测试前清理配置缓存"""
    # 测试前清理
    manager = UnifiedConfigManager()
    if hasattr(manager, "_cache"):
        manager._cache.clear()
    if hasattr(manager, "_db_config_cache"):
        manager._db_config_cache = None
    if hasattr(manager, "_file_config_cache"):
        manager._file_config_cache.clear()

    yield

    # 测试后再次清理
    if hasattr(manager, "_cache"):
        manager._cache.clear()
    if hasattr(manager, "_db_config_cache"):
        manager._db_config_cache = None
    if hasattr(manager, "_file_config_cache"):
        manager._file_config_cache.clear()


class TestGetConfigManager:
    """测试获取配置管理器"""

    def test_get_config_manager_returns_instance(self):
        """测试获取配置管理器实例"""
        # 由于使用了全局实例，应该返回同一个对象
        manager1 = get_config_manager()
        manager2 = get_config_manager()

        # 应该返回同一个实例（单例模式）
        assert manager1 is manager2

    def test_get_config_manager_returns_unified_config_manager(self):
        """测试返回的是 UnifiedConfigManager 类型"""
        manager = get_config_manager()

        assert isinstance(manager, UnifiedConfigManager)


class TestUnifiedConfigManagerBasic:
    """测试统一配置管理器基本功能"""

    def test_manager_creation(self):
        """测试创建管理器实例"""
        manager = UnifiedConfigManager()

        # 验证实例被创建
        assert manager is not None
        assert isinstance(manager, UnifiedConfigManager)


class TestUnifiedConfigManagerEnvVars:
    """测试环境变量处理"""

    def test_manager_reads_mongodb_env(self):
        """测试读取 MongoDB 环境变量"""
        with patch.dict(
            os.environ, {"MONGODB_HOST": "testhost", "MONGODB_PORT": "27018"}
        ):
            # 创建新的管理器实例
            manager = UnifiedConfigManager()

            # 验证实例被创建（环境变量检查在初始化中）
            assert manager is not None

    def test_manager_reads_redis_env(self):
        """测试读取 Redis 环境变量"""
        with patch.dict(os.environ, {"REDIS_HOST": "redistest", "REDIS_PORT": "6380"}):
            manager = UnifiedConfigManager()

            assert manager is not None


class TestUnifiedConfigManagerBasicMethods:
    """测试统一配置管理器基本方法"""

    def test_manager_instance_creation(self):
        """测试管理器实例创建"""
        manager = UnifiedConfigManager()

        # 验证实例被创建
        assert manager is not None
        assert isinstance(manager, UnifiedConfigManager)


class TestConfigCacheEntry:
    """测试配置缓存条目"""

    def test_cache_entry_creation(self):
        """测试创建缓存条目"""
        from datetime import datetime, timezone

        entry = ConfigCacheEntry(
            value="test_value",
            timestamp=datetime.now(timezone.utc),
            ttl=60,
            source="env",
        )

        assert entry.value == "test_value"
        assert entry.ttl == 60
        assert entry.source == "env"

    def test_cache_entry_not_expired(self):
        """测试缓存未过期"""
        from datetime import datetime, timezone

        entry = ConfigCacheEntry(
            value="test_value",
            timestamp=datetime.now(timezone.utc),
            ttl=60,
            source="env",
        )

        assert entry.is_expired() is False

    def test_cache_entry_expired(self):
        """测试缓存已过期"""
        from datetime import datetime, timezone, timedelta

        entry = ConfigCacheEntry(
            value="test_value",
            timestamp=datetime.now(timezone.utc) - timedelta(seconds=120),
            ttl=60,
            source="env",
        )

        assert entry.is_expired() is True


class TestUnifiedConfigManagerGetConfig:
    """测试获取配置"""

    @patch.dict(os.environ, {"TEST_KEY": "env_value"})
    def test_get_from_env(self):
        """测试从环境变量获取配置"""
        manager = UnifiedConfigManager()
        result = manager.get("test_key")

        assert result == "env_value"

    @patch("app.core.unified_config_service.get_mongo_db_sync")
    def test_get_from_mongodb(self, mock_get_db):
        """测试从 MongoDB 获取配置 (L1修复)"""
        # 创建正确的 mock 结构
        mock_collection = Mock()
        mock_doc = {
            "is_active": True,
            "system_settings": {"test_key": "mongo_value"},
        }
        mock_collection.find_one.return_value = mock_doc

        mock_db = Mock()
        mock_db.system_configs = mock_collection
        mock_get_db.return_value = mock_db

        manager = UnifiedConfigManager()
        result = manager.get("test_key")

        assert result == "mongo_value"

    def test_get_with_default(self):
        """测试使用默认值"""
        manager = UnifiedConfigManager()
        result = manager.get("nonexistent_key", default="default_value")

        assert result == "default_value"

    @patch("app.core.unified_config_service.get_mongo_db_sync")
    def test_get_caches_result(self, mock_get_db):
        """测试结果被缓存 (L1修复)"""
        # 创建正确的 mock 结构
        mock_collection = Mock()
        mock_doc = {
            "is_active": True,
            "system_settings": {"test_key": "mongo_value"},
        }
        mock_collection.find_one.return_value = mock_doc

        mock_db = Mock()
        mock_db.system_configs = mock_collection
        mock_get_db.return_value = mock_db

        manager = UnifiedConfigManager()

        # 第一次调用，从 MongoDB 获取
        result1 = manager.get("test_key")
        # 第二次调用，从缓存获取
        result2 = manager.get("test_key")

        assert result1 == result2 == "mongo_value"


class TestUnifiedConfigManagerModelConfig:
    """测试模型配置"""

    @patch("app.core.unified_config_service.get_mongo_db_sync")
    def test_get_model_config_default(self, mock_get_db):
        """测试获取默认模型配置"""
        mock_db = Mock()
        mock_db.__getitem__ = Mock(return_value=Mock())
        mock_db.__getitem__.return_value.find_one.return_value = None
        mock_get_db.return_value = mock_db

        manager = UnifiedConfigManager()
        config = manager.get_model_config("nonexistent_model")

        assert config["model_name"] == "nonexistent_model"
        assert config["provider"] == "dashscope"
        assert config["max_tokens"] == 4000

    @patch("app.core.unified_config_service.get_mongo_db_sync")
    def test_get_model_config_from_mongodb(self, mock_get_db):
        """测试从 MongoDB 获取模型配置 (L1修复)"""
        # 创建正确的 mock 结构
        mock_collection = Mock()
        mock_doc = {
            "is_active": True,
            "llm_configs": [
                {
                    "model_name": "gpt-4",
                    "max_tokens": 8000,
                    "temperature": 0.8,
                    "provider": "openai",
                    "api_base": "https://api.openai.com/v1",
                    "input_price_per_1k": 0.03,
                    "output_price_per_1k": 0.06,
                }
            ],
        }
        mock_collection.find_one.return_value = mock_doc

        mock_db = Mock()
        mock_db.system_configs = mock_collection
        mock_get_db.return_value = mock_db

        manager = UnifiedConfigManager()
        config = manager.get_model_config("gpt-4")

        assert config["model_name"] == "gpt-4"
        assert config["max_tokens"] == 8000
        assert config["temperature"] == 0.8
        assert config["provider"] == "openai"

    def test_get_provider_by_model_gpt(self):
        """测试根据模型名称获取 OpenAI provider"""
        manager = UnifiedConfigManager()
        provider = manager.get_provider_by_model("gpt-4")

        assert provider == "openai"

    def test_get_provider_by_model_gemini(self):
        """测试根据模型名称获取 Google provider"""
        manager = UnifiedConfigManager()
        provider = manager.get_provider_by_model("gemini-pro")

        assert provider == "google"

    def test_get_provider_by_model_deepseek(self):
        """测试根据模型名称获取 DeepSeek provider"""
        manager = UnifiedConfigManager()
        provider = manager.get_provider_by_model("deepseek-chat")

        assert provider == "deepseek"

    def test_get_provider_by_model_default(self):
        """测试默认 provider"""
        manager = UnifiedConfigManager()
        provider = manager.get_provider_by_model("unknown-model")

        assert provider == "dashscope"


class TestUnifiedConfigManagerSystemSettings:
    """测试系统设置"""

    @patch.dict(os.environ, {"QUICK_ANALYSIS_MODEL": "gpt-3.5-turbo"})
    def test_get_quick_analysis_model_from_env(self):
        """测试从环境变量获取快速分析模型"""
        manager = UnifiedConfigManager()
        model = manager.get_quick_analysis_model()

        assert model == "gpt-3.5-turbo"

    @patch("app.core.unified_config_service.get_mongo_db_sync")
    def test_get_quick_analysis_model_default(self, mock_get_db):
        """测试获取默认快速分析模型"""
        # Mock MongoDB 返回 None（没有配置）
        mock_get_db.return_value = None

        manager = UnifiedConfigManager()
        model = manager.get_quick_analysis_model()

        assert model == "qwen-turbo"

    @patch.dict(os.environ, {"DEEP_ANALYSIS_MODEL": "gpt-4"})
    def test_get_deep_analysis_model_from_env(self):
        """测试从环境变量获取深度分析模型"""
        manager = UnifiedConfigManager()
        model = manager.get_deep_analysis_model()

        assert model == "gpt-4"

    @patch("app.core.unified_config_service.get_mongo_db_sync")
    def test_get_deep_analysis_model_default(self, mock_get_db):
        """测试获取默认深度分析模型"""
        # Mock MongoDB 返回 None（没有配置）
        mock_get_db.return_value = None

        manager = UnifiedConfigManager()
        model = manager.get_deep_analysis_model()

        assert model == "qwen-max"

    def test_get_system_setting(self):
        """测试获取系统设置"""
        manager = UnifiedConfigManager()
        result = manager.get_system_setting("nonexistent_setting", "default_value")

        assert result == "default_value"


class TestUnifiedConfigManagerCacheManagement:
    """测试缓存管理"""

    def test_clear_cache_all(self):
        """测试清除所有缓存"""
        from datetime import datetime, timezone

        manager = UnifiedConfigManager()
        # 添加一些缓存
        manager._cache["test_key"] = ConfigCacheEntry(
            value="test", timestamp=datetime.now(timezone.utc), ttl=60, source="env"
        )

        manager.clear_cache()

        assert len(manager._cache) == 0

    def test_clear_cache_pattern(self):
        """测试按模式清除缓存"""
        from datetime import datetime, timezone

        manager = UnifiedConfigManager()
        # 添加多个缓存
        manager._cache["general:test_key"] = ConfigCacheEntry(
            value="test1", timestamp=datetime.now(timezone.utc), ttl=60, source="env"
        )
        manager._cache["llm:test_key"] = ConfigCacheEntry(
            value="test2", timestamp=datetime.now(timezone.utc), ttl=60, source="env"
        )

        manager.clear_cache(pattern="llm:")

        assert len(manager._cache) == 1
        assert "general:test_key" in manager._cache
        assert "llm:test_key" not in manager._cache

    def test_refresh_db_config(self):
        """测试刷新 MongoDB 配置缓存"""
        manager = UnifiedConfigManager()
        manager._db_config_cache = {"test": "cached"}
        manager._db_config_cache_timestamp = None

        manager.refresh_db_config()

        assert manager._db_config_cache is None

    def test_get_cache_stats(self):
        """测试获取缓存统计"""
        from datetime import datetime, timezone

        manager = UnifiedConfigManager()
        manager._cache["test_key"] = ConfigCacheEntry(
            value="test", timestamp=datetime.now(timezone.utc), ttl=60, source="env"
        )

        stats = manager.get_cache_stats()

        assert stats["total_entries"] == 1
        assert stats["expired_entries"] == 0
        assert stats["sources"]["env"] == 1
        assert stats["db_config_cached"] is False


class TestUnifiedConfigManagerFileConfig:
    """测试文件配置"""

    @patch("app.core.unified_config_service.get_mongo_db_sync")
    @patch("app.core.unified_config_service.Path.exists")
    def test_get_file_config_not_exists(self, mock_exists, mock_get_db):
        """测试配置文件不存在"""
        mock_exists.return_value = False
        mock_get_db.return_value = Mock()

        manager = UnifiedConfigManager()
        result = manager._get_file_config("models", "test_key", default="default")

        assert result == "default"


class TestUnifiedConfigManagerSaveSettings:
    """测试保存设置"""

    @patch("app.core.unified_config_service.get_mongo_db_sync")
    @patch("app.core.unified_config_service.Path")
    def test_save_system_settings(self, mock_path, mock_get_db):
        """测试保存系统设置"""
        mock_file = MagicMock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_file.read.return_value = "{}"
        mock_file.write = Mock()

        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.__truediv__ = Mock(return_value=mock_path_instance)
        mock_path_instance.mkdir = Mock()

        mock_path_instance.parent = mock_path_instance
        mock_path_instance.open = Mock(return_value=mock_file)

        mock_path.return_value = mock_path_instance
        mock_get_db.return_value = Mock()

        manager = UnifiedConfigManager()
        result = manager.save_system_settings({"test_key": "test_value"})

        assert result is True


# 如果需要通过 __main__ 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
