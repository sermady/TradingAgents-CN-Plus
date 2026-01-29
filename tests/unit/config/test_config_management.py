# -*- coding: utf-8 -*-
"""
配置管理功能测试
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tradingagents.config.config_manager import (
    ConfigManager,
    ModelConfig,
    PricingConfig,
    TokenTracker,
)


class TestConfigManagerBasic:
    """测试配置管理器基本功能"""

    def test_config_manager_creation(self):
        """测试配置管理器创建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            assert config_manager is not None

    def test_models_not_empty(self):
        """测试模型配置不为空"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            models = config_manager.load_models()
            assert len(models) > 0, "应该有默认模型配置"


class TestModelConfig:
    """测试模型配置"""

    def test_add_and_remove_model(self):
        """测试添加和删除模型"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            initial_count = len(config_manager.load_models())

            new_model = ModelConfig(
                provider="test_provider",
                model_name="test_model",
                api_key="test_key_123",
                max_tokens=2000,
                temperature=0.5,
            )

            models = config_manager.load_models()
            models.append(new_model)
            config_manager.save_models(models)

            reloaded_models = config_manager.load_models()
            assert len(reloaded_models) == initial_count + 1

            test_model = next(
                (m for m in reloaded_models if m.provider == "test_provider"), None
            )
            assert test_model is not None
            assert test_model.api_key == "test_key_123"


class TestPricingConfig:
    """测试定价配置"""

    def test_pricing_not_empty(self):
        """测试定价配置不为空"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            pricing_configs = config_manager.load_pricing()
            assert len(pricing_configs) > 0, "应该有默认定价配置"

    def test_add_and_remove_pricing(self):
        """测试添加和删除定价"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)

            new_pricing = PricingConfig(
                provider="test_provider",
                model_name="test_model",
                input_price_per_1k=0.001,
                output_price_per_1k=0.002,
                currency="CNY",
            )

            pricing_configs = config_manager.load_pricing()
            initial_count = len(pricing_configs)
            pricing_configs.append(new_pricing)
            config_manager.save_pricing(pricing_configs)

            reloaded = config_manager.load_pricing()
            assert len(reloaded) == initial_count + 1

    def test_cost_calculation(self):
        """测试成本计算"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)

            cost = config_manager.calculate_cost("dashscope", "qwen-turbo", 1000, 500)
            assert cost >= 0, "成本应该大于等于0"

    def test_cost_formula(self):
        """测试成本计算公式"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)

            pricing_configs = config_manager.load_pricing()
            pricing = next(
                (
                    p
                    for p in pricing_configs
                    if p.provider == "dashscope" and p.model_name == "qwen-turbo"
                ),
                None,
            )

            if pricing:
                input_tokens = 1000
                output_tokens = 500
                expected_cost = (input_tokens / 1000) * pricing.input_price_per_1k + (
                    output_tokens / 1000
                ) * pricing.output_price_per_1k

                calculated_cost = config_manager.calculate_cost(
                    "dashscope", "qwen-turbo", input_tokens, output_tokens
                )
                assert abs(calculated_cost - expected_cost) < 0.000001


class TestSettingsConfig:
    """测试系统设置"""

    def test_settings_contains_default(self):
        """测试设置包含默认配置"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            settings = config_manager.load_settings()
            assert "default_provider" in settings

    def test_settings_save_and_load(self):
        """测试设置保存和加载"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)

            settings = config_manager.load_settings()
            settings["test_setting"] = "test_value"
            config_manager.save_settings(settings)

            reloaded_settings = config_manager.load_settings()
            assert reloaded_settings["test_setting"] == "test_value"


class TestTokenTracker:
    """测试Token跟踪器"""

    def test_token_tracker_creation(self):
        """测试TokenTracker创建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            token_tracker = TokenTracker(config_manager)
            assert token_tracker is not None

    def test_cost_estimation(self):
        """测试成本估算"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)
            token_tracker = TokenTracker(config_manager)

            estimated_cost = token_tracker.estimate_cost(
                provider="dashscope",
                model_name="qwen-turbo",
                estimated_input_tokens=1000,
                estimated_output_tokens=500,
            )
            assert estimated_cost >= 0, "估算成本应该大于等于0"


class TestPricingAccuracy:
    """测试定价准确性"""

    def test_different_providers_pricing(self):
        """测试不同供应商的定价"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_manager = ConfigManager(temp_dir)

            test_cases = [
                ("dashscope", "qwen-turbo", 1000, 500),
                ("dashscope", "qwen-plus", 2000, 1000),
            ]

            for provider, model, input_tokens, output_tokens in test_cases:
                cost = config_manager.calculate_cost(
                    provider, model, input_tokens, output_tokens
                )
                assert cost >= 0, f"{provider} {model} 成本应该大于等于0"

                pricing_configs = config_manager.load_pricing()
                pricing = next(
                    (
                        p
                        for p in pricing_configs
                        if p.provider == provider and p.model_name == model
                    ),
                    None,
                )

                if pricing:
                    expected_cost = (
                        input_tokens / 1000
                    ) * pricing.input_price_per_1k + (
                        output_tokens / 1000
                    ) * pricing.output_price_per_1k
                    assert abs(cost - expected_cost) < 0.000001
                else:
                    assert cost == 0.0
