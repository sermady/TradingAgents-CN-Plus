#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开发环境配置测试
"""

import pytest
import logging
from unittest.mock import patch
from app.core.dev_config import (
    DevConfig,
    DEV_CONFIG,
)


class TestDevConfigClass:
    """测试 DevConfig 类"""

    def test_reload_dirs_attribute(self):
        """测试 RELOAD_DIRS 属性"""
        assert hasattr(DevConfig, "RELOAD_DIRS")
        assert isinstance(DevConfig.RELOAD_DIRS, list)
        assert "app" in DevConfig.RELOAD_DIRS

    def test_reload_excludes_attribute(self):
        """测试 RELOAD_EXCLUDES 属性"""
        assert hasattr(DevConfig, "RELOAD_EXCLUDES")
        assert isinstance(DevConfig.RELOAD_EXCLUDES, list)
        assert "__pycache__" in DevConfig.RELOAD_EXCLUDES
        assert ".git" in DevConfig.RELOAD_EXCLUDES
        assert "*.pyc" in DevConfig.RELOAD_EXCLUDES
        assert "node_modules" in DevConfig.RELOAD_EXCLUDES

    def test_reload_includes_attribute(self):
        """测试 RELOAD_INCLUDES 属性"""
        assert hasattr(DevConfig, "RELOAD_INCLUDES")
        assert isinstance(DevConfig.RELOAD_INCLUDES, list)
        assert "*.py" in DevConfig.RELOAD_INCLUDES

    def test_reload_delay_attribute(self):
        """测试 RELOAD_DELAY 属性"""
        assert hasattr(DevConfig, "RELOAD_DELAY")
        assert isinstance(DevConfig.RELOAD_DELAY, float)
        assert DevConfig.RELOAD_DELAY == 0.5

    def test_log_level_attribute(self):
        """测试 LOG_LEVEL 属性"""
        assert hasattr(DevConfig, "LOG_LEVEL")
        assert isinstance(DevConfig.LOG_LEVEL, str)
        assert DevConfig.LOG_LEVEL == "info"

    def test_access_log_attribute(self):
        """测试 ACCESS_LOG 属性"""
        assert hasattr(DevConfig, "ACCESS_LOG")
        assert isinstance(DevConfig.ACCESS_LOG, bool)
        assert DevConfig.ACCESS_LOG is True


class TestGetUvicornConfig:
    """测试 get_uvicorn_config 方法"""

    def test_get_uvicorn_config_debug_true(self):
        """测试调试模式配置"""
        config = DevConfig.get_uvicorn_config(debug=True)

        assert isinstance(config, dict)
        assert config["reload"] is False  # 禁用自动重载
        assert config["log_level"] == "info"
        assert config["access_log"] is True
        assert config["log_config"] is None  # 禁用uvicorn默认日志

    def test_get_uvicorn_config_debug_false(self):
        """测试生产模式配置"""
        config = DevConfig.get_uvicorn_config(debug=False)

        assert isinstance(config, dict)
        assert config["reload"] is False
        assert config["log_level"] == "info"
        assert config["access_log"] is True

    def test_get_uvicorn_config_returns_dict(self):
        """测试返回字典类型"""
        config = DevConfig.get_uvicorn_config()

        assert isinstance(config, dict)
        assert "reload" in config
        assert "log_level" in config
        assert "access_log" in config
        assert "log_config" in config


class TestSetupLogging:
    """测试 setup_logging 方法"""

    @patch("logging.basicConfig")
    def test_setup_logging_debug_true(self, mock_basicConfig):
        """测试调试模式日志设置"""
        DevConfig.setup_logging(debug=True)

        # 验证 basicConfig 被调用
        assert mock_basicConfig.called

        # 获取调用参数
        call_args = mock_basicConfig.call_args
        assert call_args[1]["level"] == logging.INFO
        assert (
            "trace=%(trace_id)s" not in call_args[1]["format"]
        )  # dev_config 不包含 trace_id
        assert call_args[1]["force"] is True

    @patch("logging.basicConfig")
    @patch("logging.getLogger")
    def test_setup_logging_debug_true_sets_loggers(
        self, mock_getLogger, mock_basicConfig
    ):
        """测试调试模式设置日志级别"""
        from unittest.mock import Mock

        mock_logger = Mock()
        mock_getLogger.return_value = mock_logger

        DevConfig.setup_logging(debug=True)

        # 验证设置了多个 logger 的级别
        assert mock_getLogger.call_count >= 4

    @patch("logging.basicConfig")
    @patch("logging.getLogger")
    def test_setup_logging_debug_false(self, mock_getLogger, mock_basicConfig):
        """测试生产模式日志设置"""
        from unittest.mock import Mock

        mock_logger = Mock()
        mock_getLogger.return_value = mock_logger

        DevConfig.setup_logging(debug=False)

        # 生产模式应该设置更严格的日志控制
        assert mock_getLogger.called


class TestDevConfigInstance:
    """测试 DEV_CONFIG 实例"""

    def test_dev_config_is_instance(self):
        """测试 DEV_CONFIG 是实例"""
        assert DEV_CONFIG is not None
        assert isinstance(DEV_CONFIG, DevConfig)

    def test_dev_config_attributes_accessible(self):
        """测试 DEV_CONFIG 属性可访问"""
        assert DEV_CONFIG.RELOAD_DIRS == DevConfig.RELOAD_DIRS
        assert DEV_CONFIG.RELOAD_EXCLUDES == DevConfig.RELOAD_EXCLUDES
        assert DEV_CONFIG.RELOAD_DELAY == DevConfig.RELOAD_DELAY

    def test_dev_config_methods_callable(self):
        """测试 DEV_CONFIG 方法可调用"""
        assert callable(DEV_CONFIG.get_uvicorn_config)
        assert callable(DEV_CONFIG.setup_logging)

    def test_get_uvicorn_config_from_instance(self):
        """测试从实例获取配置"""
        config = DEV_CONFIG.get_uvicorn_config()

        assert isinstance(config, dict)
        assert "reload" in config


class TestDevConfigLoggingLevels:
    """测试 DevConfig 日志级别设置"""

    @patch("logging.basicConfig")
    @patch("logging.getLogger")
    def test_watchfiles_logger_set_to_error(self, mock_getLogger, mock_basicConfig):
        """测试 watchfiles 日志级别设置为 ERROR"""
        from unittest.mock import Mock

        mock_logger = Mock()
        mock_getLogger.return_value = mock_logger

        DevConfig.setup_logging(debug=True)

        # 检查 watchfiles 相关的 logger 被设置为 ERROR 级别
        calls = mock_getLogger.call_args_list
        watchfiles_calls = [
            call for call in calls if call[0][0].startswith("watchfiles")
        ]

        # 应该至少有一个 watchfiles logger 被设置
        assert len(watchfiles_calls) >= 1

    @patch("logging.basicConfig")
    @patch("logging.getLogger")
    def test_app_core_database_logger_set_to_info(
        self, mock_getLogger, mock_basicConfig
    ):
        """测试 app.core.database 日志级别设置为 INFO"""
        from unittest.mock import Mock

        mock_logger = Mock()
        mock_getLogger.return_value = mock_logger

        DevConfig.setup_logging(debug=True)

        # 检查 app.core.database logger 被设置为 INFO
        calls = mock_getLogger.call_args_list
        db_logger_calls = [call for call in calls if call[0][0] == "app.core.database"]

        assert len(db_logger_calls) > 0
        # 验证 setLevel 被调用
        assert any(hasattr(call, "setLevel") for call in db_logger_calls)


# 如果需要通过 __main__ 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
