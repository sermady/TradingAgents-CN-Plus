# -*- coding: utf-8 -*-
"""
Billing Service Tests
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestBillingService:
    """BillingService 测试类"""

    def test_calculate_cost_basic(self):
        """测试基本成本计算"""
        with patch("app.services.billing_service.get_config_manager") as mock_config:
            mock_config_manager = Mock()
            mock_config_manager.get_model_config.return_value = {
                "input_price_per_1k": 0.001,
                "output_price_per_1k": 0.002,
                "currency": "CNY",
            }
            mock_config.return_value = mock_config_manager

            with patch("app.services.billing_service.UsageStatisticsService"):
                from app.services.billing_service import BillingService

                service = BillingService()

                cost, currency = service.calculate_cost(
                    provider="openai",
                    model_name="gpt-4",
                    input_tokens=1000,
                    output_tokens=2000,
                )

                # 1000 / 1000 * 0.001 = 0.001 (输入)
                # 2000 / 1000 * 0.002 = 0.004 (输出)
                # 总计: 0.005
                assert cost == 0.005
                assert currency == "CNY"

    def test_calculate_cost_zero_tokens(self):
        """测试零token成本计算"""
        with patch("app.services.billing_service.get_config_manager") as mock_config:
            mock_config_manager = Mock()
            mock_config_manager.get_model_config.return_value = {
                "input_price_per_1k": 0.001,
                "output_price_per_1k": 0.002,
                "currency": "CNY",
            }
            mock_config.return_value = mock_config_manager

            with patch("app.services.billing_service.UsageStatisticsService"):
                from app.services.billing_service import BillingService

                service = BillingService()

                cost, currency = service.calculate_cost(
                    provider="openai",
                    model_name="gpt-4",
                    input_tokens=0,
                    output_tokens=0,
                )

                assert cost == 0.0
                assert currency == "CNY"

    def test_calculate_cost_missing_model_config(self):
        """测试模型配置缺失时的成本计算"""
        with patch("app.services.billing_service.get_config_manager") as mock_config:
            mock_config_manager = Mock()
            mock_config_manager.get_model_config.return_value = None
            mock_config.return_value = mock_config_manager

            with patch("app.services.billing_service.UsageStatisticsService"):
                from app.services.billing_service import BillingService

                service = BillingService()

                cost, currency = service.calculate_cost(
                    provider="openai",
                    model_name="unknown-model",
                    input_tokens=1000,
                    output_tokens=1000,
                )

                # 使用默认价格 (0.0)
                assert cost == 0.0
                assert currency == "CNY"

    def test_calculate_cost_usd_currency(self):
        """测试USD货币的成本计算"""
        with patch("app.services.billing_service.get_config_manager") as mock_config:
            mock_config_manager = Mock()
            mock_config_manager.get_model_config.return_value = {
                "input_price_per_1k": 0.01,
                "output_price_per_1k": 0.03,
                "currency": "USD",
            }
            mock_config.return_value = mock_config_manager

            with patch("app.services.billing_service.UsageStatisticsService"):
                from app.services.billing_service import BillingService

                service = BillingService()

                cost, currency = service.calculate_cost(
                    provider="anthropic",
                    model_name="claude-3-5-sonnet",
                    input_tokens=5000,
                    output_tokens=10000,
                )

                # 5000 / 1000 * 0.01 = 0.05 (输入)
                # 10000 / 1000 * 0.03 = 0.3 (输出)
                # 总计: 0.35
                assert cost == 0.35
                assert currency == "USD"

    def test_get_model_price_info(self):
        """测试获取模型价格信息"""
        with patch("app.services.billing_service.get_config_manager") as mock_config:
            mock_config_manager = Mock()
            mock_config_manager.get_model_config.return_value = {
                "input_price_per_1k": 0.002,
                "output_price_per_1k": 0.006,
                "currency": "CNY",
                "provider": "deepseek",
            }
            mock_config.return_value = mock_config_manager

            with patch("app.services.billing_service.UsageStatisticsService"):
                from app.services.billing_service import BillingService

                service = BillingService()

                # 调用 get_model_pricing
                model_info = service.get_model_pricing("deepseek", "deepseek-chat")

                assert model_info is not None
                assert model_info.get("currency") == "CNY"


class TestBillingServiceEdgeCases:
    """BillingService 边界情况测试"""

    def test_calculate_cost_large_tokens(self):
        """测试大量token的成本计算"""
        with patch("app.services.billing_service.get_config_manager") as mock_config:
            mock_config_manager = Mock()
            mock_config_manager.get_model_config.return_value = {
                "input_price_per_1k": 0.001,
                "output_price_per_1k": 0.002,
                "currency": "CNY",
            }
            mock_config.return_value = mock_config_manager

            with patch("app.services.billing_service.UsageStatisticsService"):
                from app.services.billing_service import BillingService

                service = BillingService()

                # 百万级 token
                cost, currency = service.calculate_cost(
                    provider="openai",
                    model_name="gpt-4",
                    input_tokens=1000000,
                    output_tokens=1000000,
                )

                # 1000000 / 1000 * 0.001 = 1.0 (输入)
                # 1000000 / 1000 * 0.002 = 2.0 (输出)
                # 总计: 3.0
                assert cost == 3.0
                assert currency == "CNY"

    def test_calculate_cost_fractional_tokens(self):
        """测试小数token的处理"""
        with patch("app.services.billing_service.get_config_manager") as mock_config:
            mock_config_manager = Mock()
            mock_config_manager.get_model_config.return_value = {
                "input_price_per_1k": 0.001,
                "output_price_per_1k": 0.002,
                "currency": "CNY",
            }
            mock_config.return_value = mock_config_manager

            with patch("app.services.billing_service.UsageStatisticsService"):
                from app.services.billing_service import BillingService

                service = BillingService()

                cost, currency = service.calculate_cost(
                    provider="openai",
                    model_name="gpt-4",
                    input_tokens=1,
                    output_tokens=1,
                )

                # 极小 token 仍然正确计算
                assert cost > 0
                assert currency == "CNY"
