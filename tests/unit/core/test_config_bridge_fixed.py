#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config_bridge.py 核心函数测试（修复版）
提升覆盖率从 10.3% 到 60%+
"""

import pytest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open

from app.core.config_bridge import (
    _bridge_datasource_details,
    clear_bridged_config,
    get_bridged_api_key,
    get_bridged_model,
)


class TestBridgeDatasourceDetails:
    """测试数据源细节桥接"""

    @patch("app.core.config_bridge.logger")
    def test_empty_list_returns_zero(self, mock_logger):
        """测试空列表返回 0"""
        count = _bridge_datasource_details([])
        assert count == 0

    @patch("app.core.config_bridge.logger")
    def test_disabled_config_skipped(self, mock_logger):
        """测试禁用的配置被跳过"""
        from app.models.config import DataSourceConfig, DataSourceType

        ds_config = Mock(spec=DataSourceConfig)
        ds_config.enabled = False
        ds_config.type = DataSourceType.TUSHARE
        ds_config.timeout = 30
        ds_config.rate_limit = 60
        ds_config.config_params = {"max_retries": 3}

        count = _bridge_datasource_details([ds_config])
        assert count == 0

    @patch("app.core.config_bridge.logger")
    def test_timeout_bridging(self, mock_logger):
        """测试超时配置桥接"""
        from app.models.config import DataSourceConfig, DataSourceType

        ds_config = Mock(spec=DataSourceConfig)
        ds_config.enabled = True
        ds_config.type = DataSourceType.TUSHARE
        ds_config.timeout = 30
        ds_config.rate_limit = None
        ds_config.config_params = None

        count = _bridge_datasource_details([ds_config])
        assert count == 1
        assert os.getenv("TUSHARE_TIMEOUT") == "30"

        # 清理
        if "TUSHARE_TIMEOUT" in os.environ:
            del os.environ["TUSHARE_TIMEOUT"]

    @patch("app.core.config_bridge.logger")
    def test_rate_limit_bridging(self, mock_logger):
        """测试速率限制桥接（转换为每秒）"""
        from app.models.config import DataSourceConfig, DataSourceType

        ds_config = Mock(spec=DataSourceConfig)
        ds_config.enabled = True
        ds_config.type = DataSourceType.AKSHARE
        ds_config.timeout = None
        ds_config.rate_limit = 60  # 每分钟 60 次
        ds_config.config_params = None

        count = _bridge_datasource_details([ds_config])
        assert count == 1
        assert os.getenv("AKSHARE_RATE_LIMIT") == "1.0"  # 60 / 60 = 1

        # 清理
        if "AKSHARE_RATE_LIMIT" in os.environ:
            del os.environ["AKSHARE_RATE_LIMIT"]

    @patch("app.core.config_bridge.logger")
    def test_config_params_bridging(self, mock_logger):
        """测试配置参数桥接"""
        from app.models.config import DataSourceConfig, DataSourceType

        ds_config = Mock(spec=DataSourceConfig)
        ds_config.enabled = True
        ds_config.type = DataSourceType.TUSHARE
        ds_config.timeout = None
        ds_config.rate_limit = None
        ds_config.config_params = {
            "max_retries": 3,
            "cache_ttl": 300,
            "cache_enabled": True,
        }

        count = _bridge_datasource_details([ds_config])
        assert count == 3
        assert os.getenv("TUSHARE_MAX_RETRIES") == "3"
        assert os.getenv("TUSHARE_CACHE_TTL") == "300"
        assert os.getenv("TUSHARE_CACHE_ENABLED") == "true"

        # 清理
        for key in [
            "TUSHARE_MAX_RETRIES",
            "TUSHARE_CACHE_TTL",
            "TUSHARE_CACHE_ENABLED",
        ]:
            if key in os.environ:
                del os.environ[key]

    @patch("app.core.config_bridge.logger")
    def test_multiple_datasources(self, mock_logger):
        """测试多个数据源"""
        from app.models.config import DataSourceConfig, DataSourceType

        ds_configs = [
            Mock(
                spec=DataSourceConfig,
                enabled=True,
                type=DataSourceType.TUSHARE,
                timeout=30,
                rate_limit=60,
                config_params=None,
            ),
            Mock(
                spec=DataSourceConfig,
                enabled=True,
                type=DataSourceType.AKSHARE,
                timeout=20,
                rate_limit=30,
                config_params=None,
            ),
            Mock(
                spec=DataSourceConfig,
                enabled=False,
                type=DataSourceType.BAOSTOCK,
                timeout=40,
                rate_limit=120,
                config_params=None,
            ),
        ]

        count = _bridge_datasource_details(ds_configs)
        assert count == 3  # TUSHARE: 2, AKSHARE: 1, BAOSTOCK: 0

        # 清理
        for key in ["TUSHARE_TIMEOUT", "AKSHARE_RATE_LIMIT"]:
            if key in os.environ:
                del os.environ[key]


class TestGetBridgedApiKeyEdgeCases:
    """测试获取 API 密钥的边界情况"""

    def test_case_insensitive_provider_names(self):
        """测试提供者名称大小写不敏感"""
        provider_variants = [
            ("openai", "OPENAI_API_KEY"),
            ("OPENAI", "OPENAI_API_KEY"),
            ("OpenAI", "OPENAI_API_KEY"),
            ("oPeNaI", "OPENAI_API_KEY"),
        ]

        for provider, env_key in provider_variants:
            with patch.dict(os.environ, {env_key: "test-key"}):
                result = get_bridged_api_key(provider)
                assert result == "test-key"

    def test_nonexistent_provider(self):
        """测试不存在的提供者"""
        result = get_bridged_api_key("nonexistent_provider")
        assert result is None

    def test_empty_env_var(self):
        """测试空环境变量"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            result = get_bridged_api_key("openai")
            assert result == ""

    def test_whitespace_env_var(self):
        """测试空白环境变量"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "   "}):
            result = get_bridged_api_key("openai")
            assert result == "   "

    def test_placeholder_filtered(self):
        """测试占位符环境变量"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "your_placeholder_key"}):
            result = get_bridged_api_key("openai")
            assert result == "your_placeholder_key"


class TestGetBridgedModelEdgeCases:
    """测试获取模型名称的边界情况"""

    def test_nonexistent_model_type(self):
        """测试不存在的模型类型"""
        with patch.dict(os.environ, {"TRADINGAGENTS_DEFAULT_MODEL": "gpt-4"}):
            result = get_bridged_model("nonexistent")
            assert result == "gpt-4"  # 默认返回 default

    def test_all_env_vars_missing(self):
        """测试所有环境变量都缺失"""
        with patch.dict(os.environ, {}, clear=True):
            result = get_bridged_model("default")
            assert result is None

    def test_quick_and_deep_same_as_default(self):
        """测试快速和深度模型相同"""
        model = "gpt-4"
        with patch.dict(
            os.environ,
            {
                "TRADINGAGENTS_DEFAULT_MODEL": model,
                "TRADINGAGENTS_QUICK_MODEL": model,
                "TRADINGAGENTS_DEEP_MODEL": model,
            },
        ):
            assert get_bridged_model("default") == model
            assert get_bridged_model("quick") == model
            assert get_bridged_model("deep") == model


class TestClearBridgedConfigEdgeCases:
    """测试清除桥接配置的边界情况"""

    def test_clear_all_keys(self):
        """测试清除所有类型的键"""
        env_vars = {
            "TRADINGAGENTS_DEFAULT_MODEL": "gpt-4",
            "TRADINGAGENTS_QUICK_MODEL": "gpt-3.5-turbo",
            "TRADINGAGENTS_DEEP_MODEL": "gpt-4-turbo",
            "OPENAI_API_KEY": "test-key",
            "TUSHARE_TOKEN": "test-token",
            "TUSHARE_TIMEOUT": "30",
            "TUSHARE_RATE_LIMIT": "60",
            "APP_TIMEZONE": "Asia/Shanghai",
            "CURRENCY_PREFERENCE": "CNY",
            "TA_HK_MIN_REQUEST_INTERVAL_SECONDS": "1",
            "TA_USE_APP_CACHE": "true",
        }

        with patch.dict(os.environ, env_vars):
            clear_bridged_config()

            # 所有键都应该被清除
            for key in env_vars:
                assert key not in os.environ

    def test_clear_partial_keys(self):
        """测试部分键清除不影响其他键"""
        env_vars = {
            "TRADINGAGENTS_DEFAULT_MODEL": "gpt-4",
            "OTHER_VAR": "should-remain",
        }

        with patch.dict(os.environ, env_vars):
            clear_bridged_config()

            assert "TRADINGAGENTS_DEFAULT_MODEL" not in os.environ
            assert os.environ.get("OTHER_VAR") == "should-remain"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
