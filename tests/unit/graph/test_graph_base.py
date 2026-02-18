# -*- coding: utf-8 -*-
"""
测试 tradingagents.graph.base 模块

测试范围:
- create_llm_by_provider 函数
- 各种 LLM 提供商的创建逻辑
- API Key 优先级处理
- 错误处理
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock


@pytest.mark.unit
class TestCreateLLMByProvider:
    """测试 create_llm_by_provider 函数"""

    def test_create_llm_google_with_api_key(self):
        """测试使用传入的 API Key 创建 Google LLM"""
        from tradingagents.graph.base import create_llm_by_provider

        with patch("tradingagents.graph.base.ChatGoogleOpenAI") as mock_chat_google:
            mock_instance = Mock()
            mock_chat_google.return_value = mock_instance

            result = create_llm_by_provider(
                provider="google",
                model="gemini-pro",
                backend_url="https://generativelanguage.googleapis.com",
                temperature=0.7,
                max_tokens=1000,
                timeout=30,
                api_key="test-google-api-key",
            )

            mock_chat_google.assert_called_once()
            call_kwargs = mock_chat_google.call_args[1]
            assert call_kwargs["model"] == "gemini-pro"
            assert call_kwargs["google_api_key"] == "test-google-api-key"
            assert result == mock_instance

    def test_create_llm_google_without_api_key_uses_env(self):
        """测试 Google LLM 从环境变量获取 API Key"""
        from tradingagents.graph.base import create_llm_by_provider

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "env-google-key"}):
            with patch("tradingagents.graph.base.ChatGoogleOpenAI") as mock_chat_google:
                mock_instance = Mock()
                mock_chat_google.return_value = mock_instance

                result = create_llm_by_provider(
                    provider="google",
                    model="gemini-pro",
                    backend_url=None,
                    temperature=0.5,
                    max_tokens=500,
                    timeout=60,
                    api_key=None,
                )

                call_kwargs = mock_chat_google.call_args[1]
                assert call_kwargs["google_api_key"] == "env-google-key"

    def test_create_llm_google_no_api_key_raises(self):
        """测试 Google LLM 没有 API Key 时抛出异常"""
        from tradingagents.graph.base import create_llm_by_provider

        # 清除环境变量
        env_copy = os.environ.copy()
        if "GOOGLE_API_KEY" in os.environ:
            del os.environ["GOOGLE_API_KEY"]

        try:
            with pytest.raises(ValueError) as exc_info:
                create_llm_by_provider(
                    provider="google",
                    model="gemini-pro",
                    backend_url=None,
                    temperature=0.7,
                    max_tokens=1000,
                    timeout=30,
                    api_key=None,
                )

            assert "GOOGLE_API_KEY" in str(exc_info.value)
        finally:
            # 恢复环境变量
            for key, value in env_copy.items():
                os.environ[key] = value

    def test_create_llm_dashscope_with_api_key(self):
        """测试创建 DashScope (阿里云) LLM"""
        from tradingagents.graph.base import create_llm_by_provider

        with patch(
            "tradingagents.graph.base.ChatDashScopeOpenAI"
        ) as mock_chat_dashscope:
            mock_instance = Mock()
            mock_chat_dashscope.return_value = mock_instance

            result = create_llm_by_provider(
                provider="dashscope",
                model="qwen-turbo",
                backend_url="https://dashscope.aliyuncs.com",
                temperature=0.8,
                max_tokens=2000,
                timeout=45,
                api_key="test-dashscope-key",
            )

            mock_chat_dashscope.assert_called_once()
            call_kwargs = mock_chat_dashscope.call_args[1]
            assert call_kwargs["model"] == "qwen-turbo"
            assert call_kwargs["api_key"] == "test-dashscope-key"

    def test_create_llm_deepseek_with_api_key(self):
        """测试创建 DeepSeek LLM"""
        from tradingagents.graph.base import create_llm_by_provider

        # ChatDeepSeek 在函数内部导入，需要 patch 源模块
        with patch(
            "tradingagents.llm_adapters.deepseek_adapter.ChatDeepSeek"
        ) as mock_chat_deepseek:
            mock_instance = Mock()
            mock_chat_deepseek.return_value = mock_instance

            result = create_llm_by_provider(
                provider="deepseek",
                model="deepseek-chat",
                backend_url="https://api.deepseek.com",
                temperature=0.6,
                max_tokens=1500,
                timeout=60,
                api_key="test-deepseek-key",
            )

            mock_chat_deepseek.assert_called_once()
            call_kwargs = mock_chat_deepseek.call_args[1]
            assert call_kwargs["model"] == "deepseek-chat"
            assert call_kwargs["api_key"] == "test-deepseek-key"

    def test_create_llm_deepseek_no_api_key_raises(self):
        """测试 DeepSeek 没有 API Key 时抛出异常"""
        from tradingagents.graph.base import create_llm_by_provider

        # 清除环境变量
        env_copy = os.environ.copy()
        if "DEEPSEEK_API_KEY" in os.environ:
            del os.environ["DEEPSEEK_API_KEY"]

        try:
            with pytest.raises(ValueError) as exc_info:
                create_llm_by_provider(
                    provider="deepseek",
                    model="deepseek-chat",
                    backend_url=None,
                    temperature=0.7,
                    max_tokens=1000,
                    timeout=30,
                    api_key=None,
                )

            assert "DEEPSEEK_API_KEY" in str(exc_info.value)
        finally:
            for key, value in env_copy.items():
                os.environ[key] = value

    def test_create_llm_zhipu_with_api_key(self):
        """测试创建智谱AI LLM"""
        from tradingagents.graph.base import create_llm_by_provider

        # create_openai_compatible_llm 在函数内部导入
        with patch(
            "tradingagents.llm_adapters.openai_compatible_base.create_openai_compatible_llm"
        ) as mock_create:
            mock_instance = Mock()
            mock_create.return_value = mock_instance

            result = create_llm_by_provider(
                provider="zhipu",
                model="glm-4",
                backend_url="https://open.bigmodel.cn",
                temperature=0.7,
                max_tokens=1000,
                timeout=30,
                api_key="test-zhipu-key",
            )

            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["provider"] == "zhipu"
            assert call_kwargs["model"] == "glm-4"
            assert call_kwargs["api_key"] == "test-zhipu-key"

    def test_create_llm_openai_with_api_key(self):
        """测试创建 OpenAI LLM"""
        from tradingagents.graph.base import create_llm_by_provider

        with patch("tradingagents.graph.base.ChatOpenAI") as mock_chat_openai:
            mock_instance = Mock()
            mock_chat_openai.return_value = mock_instance

            result = create_llm_by_provider(
                provider="openai",
                model="gpt-4",
                backend_url="https://api.openai.com",
                temperature=0.7,
                max_tokens=1000,
                timeout=30,
                api_key="test-openai-key",
            )

            mock_chat_openai.assert_called_once()
            call_kwargs = mock_chat_openai.call_args[1]
            assert call_kwargs["model"] == "gpt-4"
            assert call_kwargs["api_key"] == "test-openai-key"

    def test_create_llm_openai_from_env(self):
        """测试 OpenAI LLM 从环境变量获取 API Key"""
        from tradingagents.graph.base import create_llm_by_provider

        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-openai-key"}):
            with patch("tradingagents.graph.base.ChatOpenAI") as mock_chat_openai:
                mock_instance = Mock()
                mock_chat_openai.return_value = mock_instance

                result = create_llm_by_provider(
                    provider="openai",
                    model="gpt-3.5-turbo",
                    backend_url=None,
                    temperature=0.5,
                    max_tokens=500,
                    timeout=60,
                    api_key=None,
                )

                call_kwargs = mock_chat_openai.call_args[1]
                assert call_kwargs["api_key"] == "env-openai-key"

    def test_create_llm_siliconflow(self):
        """测试创建 SiliconFlow LLM"""
        from tradingagents.graph.base import create_llm_by_provider

        with patch.dict(os.environ, {"SILICONFLOW_API_KEY": "siliconflow-key"}):
            with patch("tradingagents.graph.base.ChatOpenAI") as mock_chat_openai:
                mock_instance = Mock()
                mock_chat_openai.return_value = mock_instance

                result = create_llm_by_provider(
                    provider="siliconflow",
                    model="Qwen/Qwen2.5-7B-Instruct",
                    backend_url="https://api.siliconflow.cn",
                    temperature=0.7,
                    max_tokens=1000,
                    timeout=30,
                    api_key=None,
                )

                call_kwargs = mock_chat_openai.call_args[1]
                assert call_kwargs["api_key"] == "siliconflow-key"

    def test_create_llm_openrouter(self):
        """测试创建 OpenRouter LLM"""
        from tradingagents.graph.base import create_llm_by_provider

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "openrouter-key"}):
            with patch("tradingagents.graph.base.ChatOpenAI") as mock_chat_openai:
                mock_instance = Mock()
                mock_chat_openai.return_value = mock_instance

                result = create_llm_by_provider(
                    provider="openrouter",
                    model="anthropic/claude-3-opus",
                    backend_url="https://openrouter.ai/api",
                    temperature=0.7,
                    max_tokens=1000,
                    timeout=30,
                    api_key=None,
                )

                call_kwargs = mock_chat_openai.call_args[1]
                assert call_kwargs["api_key"] == "openrouter-key"

    def test_create_llm_anthropic(self):
        """测试创建 Anthropic LLM"""
        from tradingagents.graph.base import create_llm_by_provider

        with patch("tradingagents.graph.base.ChatAnthropic") as mock_chat_anthropic:
            mock_instance = Mock()
            mock_chat_anthropic.return_value = mock_instance

            result = create_llm_by_provider(
                provider="anthropic",
                model="claude-3-opus-20240229",
                backend_url=None,
                temperature=0.7,
                max_tokens=1000,
                timeout=30,
                api_key="test-anthropic-key",
            )

            mock_chat_anthropic.assert_called_once()
            call_kwargs = mock_chat_anthropic.call_args[1]
            assert call_kwargs["model"] == "claude-3-opus-20240229"

    def test_create_llm_qianfan(self):
        """测试创建千帆 LLM"""
        from tradingagents.graph.base import create_llm_by_provider

        # create_openai_compatible_llm 在函数内部导入
        with patch(
            "tradingagents.llm_adapters.openai_compatible_base.create_openai_compatible_llm"
        ) as mock_create:
            mock_instance = Mock()
            mock_create.return_value = mock_instance

            result = create_llm_by_provider(
                provider="qianfan",
                model="ernie-bot-4",
                backend_url="https://aip.baidubce.com",
                temperature=0.7,
                max_tokens=1000,
                timeout=30,
                api_key="test-qianfan-key",
            )

            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["provider"] == "qianfan"

    def test_create_llm_custom_provider(self):
        """测试创建自定义提供商 LLM (OpenAI 兼容模式)

        注意：自定义提供商代码路径只从环境变量获取 API Key，
        不会使用传入的 api_key 参数。
        """
        from tradingagents.graph.base import create_llm_by_provider

        with patch.dict(
            os.environ, {"CUSTOM_PROVIDER_API_KEY": "env-custom-key"}, clear=False
        ):
            with patch("tradingagents.graph.base.ChatOpenAI") as mock_chat_openai:
                mock_instance = Mock()
                mock_chat_openai.return_value = mock_instance

                result = create_llm_by_provider(
                    provider="custom_provider",
                    model="custom-model",
                    backend_url="https://custom.api.com",
                    temperature=0.7,
                    max_tokens=1000,
                    timeout=30,
                    api_key=None,  # 自定义提供商忽略此参数
                )

                mock_chat_openai.assert_called_once()
                call_kwargs = mock_chat_openai.call_args[1]
                # 自定义提供商从环境变量获取 API Key
                assert call_kwargs["api_key"] == "env-custom-key"

    def test_create_llm_custom_provider_from_env(self):
        """测试自定义提供商从环境变量获取 API Key"""
        from tradingagents.graph.base import create_llm_by_provider

        with patch.dict(os.environ, {"CUSTOMPROVIDER_API_KEY": "env-custom-key"}):
            with patch("tradingagents.graph.base.ChatOpenAI") as mock_chat_openai:
                mock_instance = Mock()
                mock_chat_openai.return_value = mock_instance

                result = create_llm_by_provider(
                    provider="customprovider",
                    model="model-name",
                    backend_url="https://api.customprovider.com",
                    temperature=0.7,
                    max_tokens=1000,
                    timeout=30,
                    api_key=None,
                )

                call_kwargs = mock_chat_openai.call_args[1]
                assert call_kwargs["api_key"] == "env-custom-key"

    def test_create_llm_ollama(self):
        """测试创建 Ollama LLM (本地部署)"""
        from tradingagents.graph.base import create_llm_by_provider

        with patch("tradingagents.graph.base.ChatOpenAI") as mock_chat_openai:
            mock_instance = Mock()
            mock_chat_openai.return_value = mock_instance

            result = create_llm_by_provider(
                provider="ollama",
                model="llama2",
                backend_url="http://localhost:11434",
                temperature=0.7,
                max_tokens=1000,
                timeout=60,
                api_key=None,  # Ollama 不需要 API Key
            )

            mock_chat_openai.assert_called_once()
            call_kwargs = mock_chat_openai.call_args[1]
            assert call_kwargs["model"] == "llama2"
            assert call_kwargs["base_url"] == "http://localhost:11434"

    def test_create_llm_provider_case_insensitive(self):
        """测试提供商名称大小写不敏感"""
        from tradingagents.graph.base import create_llm_by_provider

        with patch("tradingagents.graph.base.ChatOpenAI") as mock_chat_openai:
            mock_instance = Mock()
            mock_chat_openai.return_value = mock_instance

            # 测试大写
            result = create_llm_by_provider(
                provider="OPENAI",
                model="gpt-4",
                backend_url=None,
                temperature=0.7,
                max_tokens=1000,
                timeout=30,
                api_key="test-key",
            )

            mock_chat_openai.assert_called_once()


@pytest.mark.unit
class TestLLMProviderParameters:
    """测试 LLM 提供商参数传递"""

    def test_temperature_parameter(self):
        """测试 temperature 参数正确传递"""
        from tradingagents.graph.base import create_llm_by_provider

        with patch("tradingagents.graph.base.ChatOpenAI") as mock_chat_openai:
            mock_instance = Mock()
            mock_chat_openai.return_value = mock_instance

            create_llm_by_provider(
                provider="openai",
                model="gpt-4",
                backend_url=None,
                temperature=0.3,  # 低温度
                max_tokens=1000,
                timeout=30,
                api_key="test-key",
            )

            call_kwargs = mock_chat_openai.call_args[1]
            assert call_kwargs["temperature"] == 0.3

    def test_max_tokens_parameter(self):
        """测试 max_tokens 参数正确传递"""
        from tradingagents.graph.base import create_llm_by_provider

        with patch("tradingagents.graph.base.ChatOpenAI") as mock_chat_openai:
            mock_instance = Mock()
            mock_chat_openai.return_value = mock_instance

            create_llm_by_provider(
                provider="openai",
                model="gpt-4",
                backend_url=None,
                temperature=0.7,
                max_tokens=2048,
                timeout=30,
                api_key="test-key",
            )

            call_kwargs = mock_chat_openai.call_args[1]
            assert call_kwargs["max_tokens"] == 2048

    def test_timeout_parameter(self):
        """测试 timeout 参数正确传递"""
        from tradingagents.graph.base import create_llm_by_provider

        with patch("tradingagents.graph.base.ChatOpenAI") as mock_chat_openai:
            mock_instance = Mock()
            mock_chat_openai.return_value = mock_instance

            create_llm_by_provider(
                provider="openai",
                model="gpt-4",
                backend_url=None,
                temperature=0.7,
                max_tokens=1000,
                timeout=120,
                api_key="test-key",
            )

            call_kwargs = mock_chat_openai.call_args[1]
            assert call_kwargs["timeout"] == 120

    def test_backend_url_parameter(self):
        """测试 backend_url 参数正确传递"""
        from tradingagents.graph.base import create_llm_by_provider

        with patch("tradingagents.graph.base.ChatOpenAI") as mock_chat_openai:
            mock_instance = Mock()
            mock_chat_openai.return_value = mock_instance

            custom_url = "https://custom.openai.proxy.com"
            create_llm_by_provider(
                provider="openai",
                model="gpt-4",
                backend_url=custom_url,
                temperature=0.7,
                max_tokens=1000,
                timeout=30,
                api_key="test-key",
            )

            call_kwargs = mock_chat_openai.call_args[1]
            assert call_kwargs["base_url"] == custom_url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
