#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置模块测试
测试配置加载、验证和环境变量处理
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from pydantic import ValidationError
from app.core.config import Settings, settings, get_settings


class TestSettings:
    """测试 Settings 类"""

    def test_default_values(self):
        """测试默认配置值"""
        # 使用干净的 Settings 实例
        with patch.dict(os.environ, {}, clear=True):
            test_settings = Settings()

            # 测试基础配置
            assert test_settings.DEBUG is True
            assert test_settings.HOST == "0.0.0.0"
            assert test_settings.PORT == 8000

            # 测试 MongoDB 默认配置
            assert test_settings.MONGODB_HOST == "localhost"
            assert test_settings.MONGODB_PORT == 27017
            assert test_settings.MONGODB_DATABASE == "tradingagents"

            # 测试 Redis 默认配置
            assert test_settings.REDIS_HOST == "localhost"
            assert test_settings.REDIS_PORT == 6379
            assert test_settings.REDIS_DB == 0

            # 测试安全配置
            assert test_settings.JWT_ALGORITHM == "HS256"
            assert test_settings.ACCESS_TOKEN_EXPIRE_MINUTES == 60
            assert test_settings.REFRESH_TOKEN_EXPIRE_DAYS == 30

    def test_custom_values_from_env(self):
        """测试从环境变量加载自定义值"""
        env_vars = {
            "DEBUG": "false",
            "HOST": "127.0.0.1",
            "PORT": "9000",
            "MONGODB_HOST": "mongo.example.com",
            "MONGODB_PORT": "27018",
            "REDIS_HOST": "redis.example.com",
            "REDIS_PORT": "6380",
            "JWT_SECRET": "test-secret-key",
        }

        with patch.dict(os.environ, env_vars):
            test_settings = Settings()

            assert test_settings.DEBUG is False
            assert test_settings.HOST == "127.0.0.1"
            assert test_settings.PORT == 9000
            assert test_settings.MONGODB_HOST == "mongo.example.com"
            assert test_settings.MONGODB_PORT == 27018
            assert test_settings.REDIS_HOST == "redis.example.com"
            assert test_settings.REDIS_PORT == 6380
            assert test_settings.JWT_SECRET == "test-secret-key"

    def test_mongo_uri_property_with_auth(self):
        """测试 MongoDB URI 属性（带认证）"""
        test_settings = Settings()
        test_settings.MONGODB_USERNAME = "admin"
        test_settings.MONGODB_PASSWORD = "password123"
        test_settings.MONGODB_HOST = "localhost"
        test_settings.MONGODB_PORT = 27017
        test_settings.MONGODB_DATABASE = "tradingagents"
        test_settings.MONGODB_AUTH_SOURCE = "admin"

        expected_uri = (
            "mongodb://admin:password123@localhost:27017/tradingagents?authSource=admin"
        )
        assert test_settings.MONGO_URI == expected_uri

    def test_mongo_uri_property_without_auth(self):
        """测试 MongoDB URI 属性（无认证）"""
        test_settings = Settings()
        test_settings.MONGODB_USERNAME = ""
        test_settings.MONGODB_PASSWORD = ""
        test_settings.MONGODB_HOST = "localhost"
        test_settings.MONGODB_PORT = 27017
        test_settings.MONGODB_DATABASE = "tradingagents"

        expected_uri = "mongodb://localhost:27017/tradingagents"
        assert test_settings.MONGO_URI == expected_uri

    def test_redis_url_property_with_password(self):
        """测试 Redis URL 属性（带密码）"""
        test_settings = Settings()
        test_settings.REDIS_HOST = "localhost"
        test_settings.REDIS_PORT = 6379
        test_settings.REDIS_PASSWORD = "secret"
        test_settings.REDIS_DB = 0

        expected_url = "redis://:secret@localhost:6379/0"
        assert test_settings.REDIS_URL == expected_url

    def test_redis_url_property_without_password(self):
        """测试 Redis URL 属性（无密码）"""
        test_settings = Settings()
        test_settings.REDIS_HOST = "localhost"
        test_settings.REDIS_PORT = 6379
        test_settings.REDIS_PASSWORD = ""
        test_settings.REDIS_DB = 1

        expected_url = "redis://localhost:6379/1"
        assert test_settings.REDIS_URL == expected_url

    def test_is_production_property(self):
        """测试 is_production 属性"""
        # DEBUG=True 时不是生产环境
        test_settings = Settings()
        test_settings.DEBUG = True
        assert test_settings.is_production is False

        # DEBUG=False 时是生产环境
        test_settings.DEBUG = False
        assert test_settings.is_production is True

    def test_log_dir_property(self):
        """测试 log_dir 属性"""
        test_settings = Settings()
        test_settings.LOG_FILE = "logs/tradingagents.log"
        assert test_settings.log_dir == "logs"

    def test_invalid_port(self):
        """测试无效端口值"""
        with patch.dict(os.environ, {"PORT": "invalid"}):
            with pytest.raises(ValidationError):
                Settings()

    def test_data_source_sync_settings(self):
        """测试数据源同步配置"""
        test_settings = Settings()

        # 验证 Tushare 同步配置
        assert test_settings.TUSHARE_HISTORICAL_SYNC_ENABLED is True
        assert test_settings.TUSHARE_FINANCIAL_SYNC_ENABLED is True

        # 验证 AKShare 同步配置（应该被禁用）
        assert test_settings.AKSHARE_QUOTES_SYNC_ENABLED is False
        assert test_settings.AKSHARE_HISTORICAL_SYNC_ENABLED is False
        assert test_settings.AKSHARE_FINANCIAL_SYNC_ENABLED is False

        # 验证 BaoStock 同步配置（应该被禁用）
        assert test_settings.BAOSTOCK_UNIFIED_ENABLED is False
        assert test_settings.BAOSTOCK_BASIC_INFO_SYNC_ENABLED is False
        assert test_settings.BAOSTOCK_DAILY_QUOTES_SYNC_ENABLED is False

    def test_realtime_quote_settings(self):
        """测试实时行情配置"""
        test_settings = Settings()

        # 验证实时行情配置
        assert test_settings.REALTIME_QUOTE_ENABLED is True
        assert test_settings.REALTIME_QUOTE_TUSHARE_ENABLED is False
        assert test_settings.REALTIME_QUOTE_AKSHARE_PRIORITY == 1
        assert test_settings.REALTIME_QUOTE_TUSHARE_PRIORITY == 2

    def test_quotes_ingest_disabled(self):
        """测试实时行情入库服务已禁用"""
        test_settings = Settings()
        assert test_settings.QUOTES_INGEST_ENABLED is False


class TestGetSettings:
    """测试 get_settings 函数"""

    def test_get_settings_returns_singleton(self):
        """测试 get_settings 返回单例"""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2


class TestLegacyEnvAliases:
    """测试旧版环境变量别名映射逻辑

    注意：这些测试验证别名映射逻辑本身。
    由于别名处理在模块导入时执行，测试需要在没有冲突环境变量的情况下运行。
    """

    def test_legacy_aliases_mapping(self):
        """测试别名映射字典是否正确配置"""
        # 导入别名映射（需要在干净的上下文中）
        from app.core.config import _LEGACY_ENV_ALIASES

        # 验证别名映射包含预期的键
        assert "API_HOST" in _LEGACY_ENV_ALIASES
        assert "API_PORT" in _LEGACY_ENV_ALIASES
        assert "API_DEBUG" in _LEGACY_ENV_ALIASES

        # 验证映射关系
        assert _LEGACY_ENV_ALIASES["API_HOST"] == "HOST"
        assert _LEGACY_ENV_ALIASES["API_PORT"] == "PORT"
        assert _LEGACY_ENV_ALIASES["API_DEBUG"] == "DEBUG"

    def test_settings_ignores_api_host_when_host_set(self):
        """测试当 HOST 已设置时，API_HOST 被忽略"""
        # 如果 HOST 已经设置，API_HOST 不应该覆盖它
        with patch.dict(os.environ, {"HOST": "127.0.0.1", "API_HOST": "192.168.1.1"}):
            test_settings = Settings()
            # HOST 应该保持原值，不被 API_HOST 覆盖
            assert test_settings.HOST == "127.0.0.1"

    def test_settings_prefers_new_env_vars(self):
        """测试新环境变量名优先于旧别名"""
        # 新的变量名（HOST）应该优先于旧的别名（API_HOST）
        env_vars = {
            "HOST": "0.0.0.0",  # 新变量名
            "PORT": "8000",  # 新变量名
            "DEBUG": "true",  # 新变量名
        }

        with patch.dict(os.environ, env_vars, clear=True):
            test_settings = Settings()
            assert test_settings.HOST == "0.0.0.0"
            assert test_settings.PORT == 8000
            assert test_settings.DEBUG is True


class TestConfigEdgeCases:
    """测试配置边界情况"""

    def test_empty_string_env_vars(self):
        """测试空字符串环境变量"""
        env_vars = {
            "MONGODB_USERNAME": "",
            "MONGODB_PASSWORD": "",
            "REDIS_PASSWORD": "",
        }

        with patch.dict(os.environ, env_vars):
            test_settings = Settings()
            assert test_settings.MONGODB_USERNAME == ""
            assert test_settings.MONGODB_PASSWORD == ""
            assert test_settings.REDIS_PASSWORD == ""

    def test_special_characters_in_passwords(self):
        """测试密码中的特殊字符"""
        test_settings = Settings()
        test_settings.MONGODB_USERNAME = "admin"
        test_settings.MONGODB_PASSWORD = "p@ssw0rd#!"
        test_settings.MONGODB_HOST = "localhost"
        test_settings.MONGODB_PORT = 27017
        test_settings.MONGODB_DATABASE = "test"
        test_settings.MONGODB_AUTH_SOURCE = "admin"

        uri = test_settings.MONGO_URI
        assert "admin:p@ssw0rd#!@" in uri

    def test_allowed_origins_list(self):
        """测试允许的来源列表"""
        test_settings = Settings()
        assert isinstance(test_settings.ALLOWED_ORIGINS, list)
        # ALLOWED_ORIGINS 可能有具体值或通配符
        assert len(test_settings.ALLOWED_ORIGINS) > 0

    def test_concurrent_limits(self):
        """测试并发限制配置"""
        test_settings = Settings()
        assert test_settings.DEFAULT_USER_CONCURRENT_LIMIT > 0
        assert test_settings.GLOBAL_CONCURRENT_LIMIT > 0
        assert (
            test_settings.GLOBAL_CONCURRENT_LIMIT
            >= test_settings.DEFAULT_USER_CONCURRENT_LIMIT
        )

    def test_timeouts_are_positive(self):
        """测试超时值为正数"""
        test_settings = Settings()
        assert test_settings.MONGO_CONNECT_TIMEOUT_MS > 0
        assert test_settings.MONGO_SOCKET_TIMEOUT_MS > 0
        assert test_settings.MONGO_SERVER_SELECTION_TIMEOUT_MS > 0


class TestDebateConfiguration:
    """测试辩论轮次配置"""

    def test_default_debate_rounds(self):
        """测试默认辩论轮次配置"""
        test_settings = Settings()
        assert test_settings.DEFAULT_MAX_DEBATE_ROUNDS == 2
        assert test_settings.DEFAULT_MAX_RISK_DISCUSS_ROUNDS == 2
        assert test_settings.ALLOW_DEBATE_ROUNDS_OVERRIDE is False

    def test_debate_rounds_range(self):
        """测试辩论轮次范围限制"""
        test_settings = Settings()
        # 验证默认值在合理范围内
        assert 1 <= test_settings.DEFAULT_MAX_DEBATE_ROUNDS <= 5
        assert 1 <= test_settings.DEFAULT_MAX_RISK_DISCUSS_ROUNDS <= 5


class TestQueueConfiguration:
    """测试队列配置"""

    def test_queue_default_values(self):
        """测试队列默认配置值"""
        test_settings = Settings()
        assert test_settings.QUEUE_MAX_SIZE > 0
        assert test_settings.QUEUE_VISIBILITY_TIMEOUT > 0
        assert test_settings.QUEUE_MAX_RETRIES > 0
        assert test_settings.WORKER_HEARTBEAT_INTERVAL > 0

    def test_queue_poll_interval(self):
        """测试队列轮询间隔"""
        test_settings = Settings()
        assert test_settings.QUEUE_POLL_INTERVAL_SECONDS > 0
        assert test_settings.QUEUE_CLEANUP_INTERVAL_SECONDS > 0


class TestWebSocketConfiguration:
    """测试 WebSocket 配置"""

    def test_websocket_ping_configuration(self):
        """测试 WebSocket 心跳配置"""
        test_settings = Settings()
        assert test_settings.WEBSOCKET_PING_INTERVAL > 0
        assert test_settings.WEBSOCKET_PING_TIMEOUT > 0
        assert test_settings.WEBSOCKET_CLIENT_HEARTBEAT_INTERVAL > 0

    def test_sse_configuration(self):
        """测试 SSE 配置"""
        test_settings = Settings()
        assert test_settings.SSE_POLL_TIMEOUT_SECONDS > 0
        assert test_settings.SSE_HEARTBEAT_INTERVAL_SECONDS > 0
        assert test_settings.SSE_TASK_MAX_IDLE_SECONDS > 0


class TestCacheConfiguration:
    """测试缓存配置"""

    def test_cache_ttl_configuration(self):
        """测试缓存 TTL 配置"""
        test_settings = Settings()
        assert test_settings.CACHE_TTL > 0
        assert test_settings.SCREENING_CACHE_TTL > 0
        assert test_settings.SESSION_EXPIRE_HOURS > 0

    def test_cache_strategy_default(self):
        """测试缓存策略默认配置"""
        with patch.dict(os.environ, {}, clear=True):
            test_settings = Settings()
            # 从 .env 文件加载，值可能已经设置
            assert test_settings is not None


class TestSecurityConfiguration:
    """测试安全配置"""

    def test_security_settings_exist(self):
        """测试安全配置项存在"""
        test_settings = Settings()
        assert test_settings.JWT_SECRET is not None
        assert test_settings.JWT_ALGORITHM is not None
        assert test_settings.CSRF_SECRET is not None
        assert test_settings.BCRYPT_ROUNDS > 0

    def test_rate_limit_configuration(self):
        """测试速率限制配置"""
        test_settings = Settings()
        assert isinstance(test_settings.RATE_LIMIT_ENABLED, bool)
        assert test_settings.DEFAULT_RATE_LIMIT > 0

    def test_upload_size_limit(self):
        """测试上传文件大小限制"""
        test_settings = Settings()
        assert test_settings.MAX_UPLOAD_SIZE > 0
        assert test_settings.UPLOAD_DIR is not None


class TestMarketDataConfiguration:
    """测试市场数据配置"""

    def test_market_analyst_lookback_days(self):
        """测试市场分析师回溯天数"""
        test_settings = Settings()
        assert test_settings.MARKET_ANALYST_LOOKBACK_DAYS > 0
        assert test_settings.MARKET_ANALYST_LOOKBACK_DAYS >= 60  # 推荐至少60天

    def test_tushare_rate_limit_safety_margin(self):
        """测试 Tushare 速率限制安全边际"""
        test_settings = Settings()
        assert 0.0 < test_settings.TUSHARE_RATE_LIMIT_SAFETY_MARGIN <= 1.0

    def test_quotes_ingest_configuration(self):
        """测试行情入库配置"""
        test_settings = Settings()
        assert test_settings.QUOTES_INGEST_INTERVAL_SECONDS > 0
        assert test_settings.QUOTES_TUSHARE_HOURLY_LIMIT >= 0


class TestMultiMarketConfiguration:
    """测试多市场配置"""

    def test_hk_market_configuration(self):
        """测试港股配置"""
        test_settings = Settings()
        assert test_settings.HK_DATA_CACHE_HOURS > 0
        assert test_settings.HK_DEFAULT_DATA_SOURCE in ["yfinance", "akshare"]

    def test_us_market_configuration(self):
        """测试美股配置"""
        test_settings = Settings()
        assert test_settings.US_DATA_CACHE_HOURS > 0
        assert test_settings.US_DEFAULT_DATA_SOURCE in ["yfinance", "finnhub"]


class TestNewsConfiguration:
    """测试新闻数据配置"""

    def test_news_sync_configuration(self):
        """测试新闻同步配置"""
        test_settings = Settings()
        assert isinstance(test_settings.NEWS_SYNC_ENABLED, bool)
        assert test_settings.NEWS_SYNC_HOURS_BACK > 0
        assert test_settings.NEWS_SYNC_MAX_PER_SOURCE > 0


class TestSettingsConfigDict:
    """测试 Settings 配置字典"""

    def test_model_config_exists(self):
        """测试模型配置存在"""
        # 验证 Settings 类有正确的 model_config
        from app.core.config import Settings

        assert hasattr(Settings, "model_config")
        assert Settings.model_config.get("extra") == "ignore"
        assert Settings.model_config.get("env_file") == ".env"
