# -*- coding: utf-8 -*-
"""
测试LLM工厂功能

测试范围:
- LLM工厂创建
- Provider注册
- LLM实例创建
- 配置验证
- 模型列表获取
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

os.environ["USE_MONGODB_STORAGE"] = "false"
os.environ["TRADINGAGENTS_SKIP_DB_INIT"] = "true"


@pytest.mark.unit
def test_llm_factory_creation():
    """测试LLM工厂创建"""
    from tradingagents.llm_adapters.llm_factory import LLMFactory, get_llm_factory

    # Act
    factory = LLMFactory()

    # Assert
    assert factory is not None
    assert isinstance(factory, LLMFactory)

    # Test singleton
    factory2 = get_llm_factory()
    assert factory2 is not None


@pytest.mark.unit
def test_llm_factory_list_providers():
    """测试列出所有Provider"""
    from tradingagents.llm_adapters.llm_factory import LLMFactory

    # Arrange
    factory = LLMFactory()

    # Act
    providers = factory.list_providers()

    # Assert
    assert isinstance(providers, list)
    assert len(providers) > 0
    assert "openai" in providers
    assert "google" in providers
    assert "deepseek" in providers
    assert "dashscope" in providers
    assert "anthropic" in providers


@pytest.mark.unit
def test_llm_factory_register_provider():
    """测试注册新Provider"""
    from tradingagents.llm_adapters.llm_factory import (
        LLMFactory,
        BaseLLMProvider,
    )

    # Arrange
    factory = LLMFactory()

    class MockProvider(BaseLLMProvider):
        def create_llm(
            self,
            model,
            api_key,
            temperature=0.7,
            max_tokens=2000,
            timeout=180,
            base_url=None,
            **kwargs,
        ):
            return Mock()

        def validate_config(self, model, api_key, base_url):
            return {"valid": True, "errors": []}

        def get_available_models(self):
            return {"mock-model": {"description": "Mock Model"}}

    mock_provider = MockProvider()

    # Act
    factory.register_provider("mock", mock_provider)
    providers = factory.list_providers()

    # Assert
    assert "mock" in providers


@pytest.mark.unit
def test_llm_factory_create_openai_llm():
    """测试创建OpenAI LLM"""
    from tradingagents.llm_adapters.llm_factory import LLMFactory

    # Arrange
    factory = LLMFactory()

    with patch("langchain_openai.ChatOpenAI") as mock_chat_openai:
        mock_instance = Mock()
        mock_chat_openai.return_value = mock_instance

        # Act
        llm = factory.create_llm(
            provider_name="openai",
            model="gpt-4o-mini",
            api_key="test-api-key-12345",
            temperature=0.7,
            max_tokens=2000,
        )

        # Assert
        assert llm is not None
        mock_chat_openai.assert_called_once()


@pytest.mark.unit
def test_llm_factory_create_deepseek_llm():
    """测试创建DeepSeek LLM"""
    from tradingagents.llm_adapters.llm_factory import LLMFactory

    # Arrange
    factory = LLMFactory()

    with patch("tradingagents.llm_adapters.deepseek_adapter.ChatDeepSeek") as mock_chat:
        mock_instance = Mock()
        mock_chat.return_value = mock_instance

        # Act
        llm = factory.create_llm(
            provider_name="deepseek",
            model="deepseek-chat",
            api_key="test-api-key-12345",
            temperature=0.7,
            max_tokens=2000,
        )

        # Assert
        assert llm is not None
        mock_chat.assert_called_once()


@pytest.mark.unit
def test_llm_factory_create_google_llm():
    """测试创建Google LLM"""
    from tradingagents.llm_adapters.llm_factory import LLMFactory

    # Arrange
    factory = LLMFactory()

    with patch(
        "tradingagents.llm_adapters.google_openai_adapter.ChatGoogleOpenAI"
    ) as mock_chat:
        mock_instance = Mock()
        mock_chat.return_value = mock_instance

        # Act
        llm = factory.create_llm(
            provider_name="google",
            model="gemini-pro",
            api_key="test-api-key-12345",
            temperature=0.7,
            max_tokens=2000,
        )

        # Assert
        assert llm is not None
        mock_chat.assert_called_once()


@pytest.mark.unit
def test_llm_factory_create_dashscope_llm():
    """测试创建DashScope LLM"""
    from tradingagents.llm_adapters.llm_factory import LLMFactory

    # Arrange
    factory = LLMFactory()

    with patch(
        "tradingagents.llm_adapters.dashscope_openai_adapter.ChatDashScopeOpenAI"
    ) as mock_chat:
        mock_instance = Mock()
        mock_chat.return_value = mock_instance

        # Act
        llm = factory.create_llm(
            provider_name="dashscope",
            model="qwen-plus",
            api_key="test-api-key-12345",
            temperature=0.7,
            max_tokens=2000,
        )

        # Assert
        assert llm is not None
        mock_chat.assert_called_once()


@pytest.mark.unit
def test_llm_factory_create_anthropic_llm():
    """测试创建Anthropic LLM"""
    from tradingagents.llm_adapters.llm_factory import LLMFactory

    # Arrange
    factory = LLMFactory()

    with patch("langchain_anthropic.ChatAnthropic") as mock_chat:
        mock_instance = Mock()
        mock_chat.return_value = mock_instance

        # Act
        llm = factory.create_llm(
            provider_name="anthropic",
            model="claude-3-sonnet",
            api_key="test-api-key-12345",
            temperature=0.7,
            max_tokens=2000,
        )

        # Assert
        assert llm is not None
        mock_chat.assert_called_once()


@pytest.mark.unit
def test_llm_factory_invalid_provider():
    """测试无效Provider"""
    from tradingagents.llm_adapters.llm_factory import LLMFactory

    # Arrange
    factory = LLMFactory()

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        factory.create_llm(
            provider_name="invalid_provider",
            model="model",
            api_key="test-api-key",
        )

    assert "不支持的Provider" in str(exc_info.value)


@pytest.mark.unit
def test_llm_factory_validate_config_valid():
    """测试有效配置验证"""
    from tradingagents.llm_adapters.llm_factory import LLMFactory

    # Arrange
    factory = LLMFactory()

    # Act
    result = factory.validate_config(
        provider_name="openai",
        model="gpt-4o-mini",
        api_key="test-api-key-12345",
        base_url=None,
    )

    # Assert
    assert result["valid"] is True
    assert len(result["errors"]) == 0


@pytest.mark.unit
def test_llm_factory_validate_config_invalid_api_key():
    """测试无效API Key"""
    from tradingagents.llm_adapters.llm_factory import LLMFactory

    # Arrange
    factory = LLMFactory()

    # Act
    result = factory.validate_config(
        provider_name="openai",
        model="gpt-4o-mini",
        api_key="short",  # Too short
        base_url=None,
    )

    # Assert
    assert result["valid"] is False
    assert len(result["errors"]) > 0


@pytest.mark.unit
def test_llm_factory_get_available_models():
    """测试获取可用模型列表"""
    from tradingagents.llm_adapters.llm_factory import LLMFactory

    # Arrange
    factory = LLMFactory()

    # Act
    models = factory.get_available_models("openai")

    # Assert
    assert isinstance(models, dict)
    assert len(models) > 0
    # 检查模型信息结构
    for model_name, model_info in models.items():
        assert "description" in model_info
        assert "context_length" in model_info or "recommended_for" in model_info


@pytest.mark.unit
def test_llm_factory_get_provider_info():
    """测试获取Provider信息"""
    from tradingagents.llm_adapters.llm_factory import LLMFactory

    # Arrange
    factory = LLMFactory()

    # Act
    info = factory.get_provider_info("openai")

    # Assert
    assert info["name"] == "openai"
    assert "provider_class" in info
    assert "available_models" in info


@pytest.mark.unit
def test_llm_factory_custom_provider():
    """测试自定义Provider"""
    from tradingagents.llm_adapters.llm_factory import LLMFactory

    # Arrange
    factory = LLMFactory()

    with patch("langchain_openai.ChatOpenAI") as mock_chat:
        mock_instance = Mock()
        mock_chat.return_value = mock_instance

        # Act
        llm = factory.create_llm(
            provider_name="custom",
            model="custom-model",
            api_key="test-api-key-12345",
            base_url="https://custom-endpoint.com/v1",
            temperature=0.7,
            max_tokens=2000,
        )

        # Assert
        assert llm is not None


@pytest.mark.unit
def test_create_llm_by_factory_function():
    """测试工厂函数"""
    from tradingagents.llm_adapters.llm_factory import create_llm_by_factory

    with patch("langchain_openai.ChatOpenAI") as mock_chat:
        mock_instance = Mock()
        mock_chat.return_value = mock_instance

        # Act
        llm = create_llm_by_factory(
            provider="openai",
            model="gpt-4o-mini",
            api_key="test-api-key-12345",
        )

        # Assert
        assert llm is not None


@pytest.mark.unit
def test_validate_llm_config_function():
    """测试配置验证函数"""
    from tradingagents.llm_adapters.llm_factory import validate_llm_config

    # Act
    result = validate_llm_config(
        provider="openai",
        model="gpt-4o-mini",
        api_key="test-api-key-12345",
    )

    # Assert
    assert "valid" in result
    assert "errors" in result


@pytest.mark.unit
def test_provider_name_case_insensitive():
    """测试Provider名称大小写不敏感"""
    from tradingagents.llm_adapters.llm_factory import LLMFactory

    # Arrange
    factory = LLMFactory()

    with patch("langchain_openai.ChatOpenAI") as mock_chat:
        mock_instance = Mock()
        mock_chat.return_value = mock_instance

        # Act - 使用大写
        llm = factory.create_llm(
            provider_name="OPENAI",
            model="gpt-4o-mini",
            api_key="test-api-key-12345",
        )

        # Assert
        assert llm is not None


@pytest.mark.unit
def test_llm_factory_provider_aliases():
    """测试Provider别名"""
    from tradingagents.llm_adapters.llm_factory import LLMFactory

    # Arrange
    factory = LLMFactory()
    providers = factory.list_providers()

    # Assert - 阿里百炼别名
    assert "alibaba" in providers
    assert "dashscope" in providers

    # OpenRouter别名
    assert "openrouter" in providers
    assert "siliconflow" in providers


@pytest.mark.unit
def test_custom_provider_requires_base_url():
    """测试自定义Provider需要base_url"""
    from tradingagents.llm_adapters.llm_factory import LLMFactory

    # Arrange
    factory = LLMFactory()

    # Act - 不提供base_url
    result = factory.validate_config(
        provider_name="custom",
        model="custom-model",
        api_key="test-api-key-12345",
        base_url=None,
    )

    # Assert
    assert result["valid"] is False
    assert any("base_url" in error for error in result["errors"])


@pytest.mark.unit
def test_get_llm_factory_singleton():
    """测试单例模式"""
    from tradingagents.llm_adapters.llm_factory import get_llm_factory

    # Act
    factory1 = get_llm_factory()
    factory2 = get_llm_factory()

    # Assert
    assert factory1 is factory2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
