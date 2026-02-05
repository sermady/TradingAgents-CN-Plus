#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动配置验证器测试
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from app.core.startup_validator import (
    ConfigLevel,
    ConfigItem,
    ValidationResult,
    StartupValidator,
)


class TestConfigLevel:
    """测试配置级别枚举"""

    def test_config_level_values(self):
        """测试配置级别值"""
        assert ConfigLevel.REQUIRED.value == "required"
        assert ConfigLevel.RECOMMENDED.value == "recommended"
        assert ConfigLevel.OPTIONAL.value == "optional"


class TestConfigItem:
    """测试配置项数据类"""

    def test_config_item_creation(self):
        """测试创建配置项"""
        item = ConfigItem(
            key="TEST_KEY",
            level=ConfigLevel.REQUIRED,
            description="Test description",
            example="example_value",
        )

        assert item.key == "TEST_KEY"
        assert item.level == ConfigLevel.REQUIRED
        assert item.description == "Test description"
        assert item.example == "example_value"

    def test_config_item_optional_fields(self):
        """测试配置项可选字段"""
        item = ConfigItem(
            key="TEST_KEY",
            level=ConfigLevel.OPTIONAL,
            description="Test description",
        )

        assert item.example is None
        assert item.help_url is None
        assert item.validator is None


class TestValidationResult:
    """测试验证结果数据类"""

    def test_validation_result_creation(self):
        """测试创建验证结果"""
        result = ValidationResult(
            success=True,
            missing_required=[],
            missing_recommended=[],
            invalid_configs=[],
            warnings=[],
        )

        assert result.success is True
        assert result.missing_required == []
        assert result.missing_recommended == []


class TestStartupValidator:
    """测试启动配置验证器"""

    def test_validator_creation(self):
        """测试创建验证器实例"""
        validator1 = StartupValidator()
        validator2 = StartupValidator()

        # 应该能创建多个实例（不一定是单例）
        assert validator1 is not None
        assert validator2 is not None

    def test_required_configs_defined(self):
        """测试必需配置项已定义"""
        validator = StartupValidator()

        # 验证必需配置项列表不为空
        assert len(validator.REQUIRED_CONFIGS) > 0

        # 验证包含预期的配置项
        required_keys = [item.key for item in validator.REQUIRED_CONFIGS]
        assert "MONGODB_HOST" in required_keys
        assert "MONGODB_PORT" in required_keys
        assert "REDIS_HOST" in required_keys

    def test_recommended_configs_defined(self):
        """测试推荐配置项已定义"""
        validator = StartupValidator()

        # 验证推荐配置项列表不为空
        assert len(validator.RECOMMENDED_CONFIGS) > 0

    def test_validate_all_configs_present(self):
        """测试验证所有配置都存在"""
        # 设置所有必需的环境变量
        env_vars = {
            "MONGODB_HOST": "localhost",
            "MONGODB_PORT": "27017",
            "MONGODB_DATABASE": "tradingagents",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
        }

        with patch.dict(os.environ, env_vars):
            validator = StartupValidator()
            result = validator.validate()

            assert isinstance(result, ValidationResult)

    def test_validate_missing_required(self):
        """测试验证缺少必需配置"""
        # 清空必需的环境变量
        required_keys = [
            "MONGODB_HOST",
            "MONGODB_PORT",
            "MONGODB_DATABASE",
            "REDIS_HOST",
            "REDIS_PORT",
        ]

        env_vars = {key: "" for key in required_keys}

        with patch.dict(os.environ, env_vars, clear=True):
            validator = StartupValidator()
            result = validator.validate()

            # 应该有缺少的必需配置
            assert len(result.missing_required) > 0 or not result.success

    def test_validate_function(self):
        """测试全局验证函数"""
        from app.core.startup_validator import validate_startup_config

        # 设置所有必需的环境变量
        env_vars = {
            "MONGODB_HOST": "localhost",
            "MONGODB_PORT": "27017",
            "MONGODB_DATABASE": "tradingagents",
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
        }

        with patch.dict(os.environ, env_vars):
            result = validate_startup_config()
            assert isinstance(result, ValidationResult)


# 如果需要通过 __main__ 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
