#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置系统兼容层测试
"""

import pytest
import os
import warnings
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from app.core.config_compat import ConfigManagerCompat


class TestConfigManagerCompatInitialization:
    """测试 ConfigManagerCompat 初始化"""

    def test_init_emits_deprecation_warning(self):
        """测试初始化时发出废弃警告"""
        with pytest.warns(DeprecationWarning):
            manager = ConfigManagerCompat()
            assert manager._warned is True

    def test_init_emits_warning_for_each_instance(self):
        """测试每个实例都会发出废弃警告（当前实现）"""
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always", DeprecationWarning)
            manager1 = ConfigManagerCompat()
            manager2 = ConfigManagerCompat()  # 第二次初始化

            # 过滤出 DeprecationWarning
            deprecation_warnings = [
                w for w in warning_list if issubclass(w.category, DeprecationWarning)
            ]

            # 当前实现中每个实例都会发出警告
            assert len(deprecation_warnings) == 2
            assert manager1._warned is True
            assert manager2._warned is True


class TestGetDataDir:
    """测试获取数据目录"""

    def test_get_data_dir_from_env(self):
        """测试从环境变量获取数据目录"""
        with patch.dict(os.environ, {"DATA_DIR": "/custom/data/dir"}):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                manager = ConfigManagerCompat()
                result = manager.get_data_dir()
                assert result == "/custom/data/dir"

    def test_get_data_dir_default(self):
        """测试获取默认数据目录"""
        with patch.dict(os.environ, {}, clear=True):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                manager = ConfigManagerCompat()
                result = manager.get_data_dir()
                assert result == "./data"


class TestLoadSettings:
    """测试加载系统设置"""

    @patch("app.core.config_compat.asyncio.get_event_loop")
    @patch("app.services.config_service.config_service.get_system_config")
    def test_load_settings_from_service(self, mock_get_config, mock_get_loop):
        """测试从配置服务加载设置"""
        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        mock_loop.run_until_complete.return_value = Mock(
            system_settings={"key": "value"}
        )
        mock_get_loop.return_value = mock_loop

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            manager = ConfigManagerCompat()
            result = manager.load_settings()

            assert result == {"key": "value"}

    @patch("app.core.config_compat.asyncio.get_event_loop")
    def test_load_settings_fallback_to_default(self, mock_get_loop):
        """测试加载设置失败时回退到默认值"""
        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        mock_loop.run_until_complete.side_effect = Exception("DB error")
        mock_get_loop.return_value = mock_loop

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            manager = ConfigManagerCompat()
            result = manager.load_settings()

            # 应该返回默认设置
            assert "max_debate_rounds" in result
            assert "online_tools" in result

    @patch("app.core.config_compat.asyncio.get_event_loop")
    def test_load_settings_when_loop_running(self, mock_get_loop):
        """测试事件循环正在运行时加载设置"""
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        mock_get_loop.return_value = mock_loop

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            manager = ConfigManagerCompat()
            result = manager.load_settings()

            # 应该返回默认设置
            assert isinstance(result, dict)


class TestSaveSettings:
    """测试保存系统设置"""

    @patch("app.core.config_compat.asyncio.get_event_loop")
    @patch("app.services.config_service.config_service.update_system_settings")
    def test_save_settings_success(self, mock_update, mock_get_loop):
        """测试保存设置成功"""
        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        mock_loop.run_until_complete = Mock()
        mock_get_loop.return_value = mock_loop

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            manager = ConfigManagerCompat()
            result = manager.save_settings({"key": "value"})

            assert result is True

    @patch("app.core.config_compat.asyncio.get_event_loop")
    def test_save_settings_when_loop_running(self, mock_get_loop):
        """测试事件循环正在运行时保存设置"""
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        mock_get_loop.return_value = mock_loop

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            manager = ConfigManagerCompat()

            with pytest.warns(RuntimeWarning):
                result = manager.save_settings({"key": "value"})

            assert result is False

    @patch("app.core.config_compat.asyncio.get_event_loop")
    def test_save_settings_failure(self, mock_get_loop):
        """测试保存设置失败"""
        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        mock_loop.run_until_complete.side_effect = Exception("DB error")
        mock_get_loop.return_value = mock_loop

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            manager = ConfigManagerCompat()

            with pytest.warns(RuntimeWarning):
                result = manager.save_settings({"key": "value"})

            assert result is False


class TestGetModels:
    """测试获取模型配置"""

    @patch("app.core.config_compat.asyncio.get_event_loop")
    @patch("app.services.config_service.config_service.get_system_config")
    def test_get_models_success(self, mock_get_config, mock_get_loop):
        """测试获取模型配置成功"""
        mock_llm = Mock(
            provider="openai",
            model_name="gpt-4",
            api_key="test-key",
            base_url="https://api.openai.com",
            max_tokens=4096,
            temperature=0.7,
            enabled=True,
        )

        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        mock_loop.run_until_complete.return_value = Mock(llm_configs=[mock_llm])
        mock_get_loop.return_value = mock_loop

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            manager = ConfigManagerCompat()
            result = manager.get_models()

            assert len(result) == 1
            assert result[0]["provider"] == "openai"
            assert result[0]["model_name"] == "gpt-4"

    @patch("app.core.config_compat.asyncio.get_event_loop")
    def test_get_models_returns_empty_on_error(self, mock_get_loop):
        """测试获取模型配置失败时返回空列表"""
        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        mock_loop.run_until_complete.side_effect = Exception("DB error")
        mock_get_loop.return_value = mock_loop

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            manager = ConfigManagerCompat()
            result = manager.get_models()

            assert result == []

    @patch("app.core.config_compat.asyncio.get_event_loop")
    def test_get_models_when_loop_running(self, mock_get_loop):
        """测试事件循环正在运行时获取模型"""
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        mock_get_loop.return_value = mock_loop

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            manager = ConfigManagerCompat()
            result = manager.get_models()

            assert result == []


class TestGetModelConfig:
    """测试获取指定模型配置"""

    @patch("app.core.config_compat.asyncio.get_event_loop")
    @patch("app.services.config_service.config_service.get_system_config")
    def test_get_model_config_success(self, mock_get_config, mock_get_loop):
        """测试获取指定模型配置成功"""
        mock_llm = Mock(
            provider="openai",
            model_name="gpt-4",
            api_key="test-key",
            base_url="https://api.openai.com",
            max_tokens=4096,
            temperature=0.7,
            enabled=True,
        )

        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        mock_loop.run_until_complete.return_value = Mock(llm_configs=[mock_llm])
        mock_get_loop.return_value = mock_loop

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            manager = ConfigManagerCompat()
            result = manager.get_model_config("openai", "gpt-4")

            assert result is not None
            assert result["provider"] == "openai"
            assert result["model_name"] == "gpt-4"

    @patch("app.core.config_compat.asyncio.get_event_loop")
    def test_get_model_config_not_found(self, mock_get_loop):
        """测试获取不存在的模型配置"""
        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        mock_loop.run_until_complete.return_value = Mock(llm_configs=[])
        mock_get_loop.return_value = mock_loop

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            manager = ConfigManagerCompat()
            result = manager.get_model_config("unknown", "model")

            assert result is None


class TestDefaultSettings:
    """测试默认设置"""

    def test_default_settings_structure(self):
        """测试默认设置结构"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            manager = ConfigManagerCompat()
            defaults = manager._get_default_settings()

            assert isinstance(defaults, dict)
            # 验证包含预期的键
            assert "max_debate_rounds" in defaults
            assert "max_risk_discuss_rounds" in defaults
            assert "online_tools" in defaults
            assert "online_news" in defaults
            assert "memory_enabled" in defaults

    def test_default_settings_values(self):
        """测试默认设置值"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            manager = ConfigManagerCompat()
            defaults = manager._get_default_settings()

            assert defaults["max_debate_rounds"] == 1
            assert defaults["max_risk_discuss_rounds"] == 1
            assert defaults["online_tools"] is True
            assert defaults["memory_enabled"] is True


# 如果需要通过 __main__ 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
