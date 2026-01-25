# -*- coding: utf-8 -*-
"""
LLM Adapter 单元测试
测试所有 LLM 提供商的适配器
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from tests.conftest import pytest


# 测试标记
pytestmark = pytest.mark.unit


class TestBaseLLMAdapter:
    """基础 LLM 适配器测试"""

    @pytest.mark.asyncio
    async def test_base_adapter_initialization(self):
        """测试基础适配器初始化"""
        from tradingagents.llm_adapters.base import BaseLLMAdapter

        adapter = BaseLLMAdapter(
            api_key="test_key", model="test-model", temperature=0.7
        )

        assert adapter.api_key == "test_key"
        assert adapter.model == "test-model"
        assert adapter.temperature == 0.7

    @pytest.mark.asyncio
    async def test_generate_completion_base(self):
        """测试基础生成补全方法"""
        from tradingagents.llm_adapters.base import BaseLLMAdapter
        from abc import ABC

        # BaseLLMAdapter 是抽象类，不能直接实例化
        # 只能测试其存在性和方法签名
        assert hasattr(BaseLLMAdapter, "generate_completion")
        assert hasattr(BaseLLMAdapter, "generate_chat_completion")

    @pytest.mark.asyncio
    async def test_stream_completion_not_implemented(self):
        """测试流式补全未实现"""
        from tradingagents.llm_adapters.base import BaseLLMAdapter
        import asyncio

        # 测试抽象方法需要抛出 NotImplementedError
        # 这里我们只验证接口存在
        assert hasattr(BaseLLMAdapter, "stream_completion")


class TestOpenAIAdapter:
    """OpenAI 适配器测试"""

    @pytest.mark.asyncio
    async def test_openai_adapter_initialization(self):
        """测试 OpenAI 适配器初始化"""
        from tradingagents.llm_adapters.openai_adapter import OpenAIAdapter

        adapter = OpenAIAdapter(
            api_key="sk-test-key", model="gpt-4", temperature=0.7, max_tokens=1000
        )

        assert adapter.api_key == "sk-test-key"
        assert adapter.model == "gpt-4"
        assert adapter.temperature == 0.7
        assert adapter.max_tokens == 1000

    @pytest.mark.asyncio
    @patch("openai.AsyncOpenAI")
    async def test_generate_chat_completion_success(self, mock_openai):
        """测试生成聊天补全 - 成功场景"""
        from tradingagents.llm_adapters.openai_adapter import OpenAIAdapter

        # Mock OpenAI 客户端
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "测试响应"
        mock_response.usage.total_tokens = 100
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        adapter = OpenAIAdapter(api_key="test-key", model="gpt-4")
        result = await adapter.generate_chat_completion(
            messages=[{"role": "user", "content": "测试"}]
        )

        assert result["content"] == "测试响应"
        assert result["total_tokens"] == 100

    @pytest.mark.asyncio
    @patch("openai.AsyncOpenAI")
    async def test_generate_chat_completion_with_functions(self, mock_openai):
        """测试生成聊天补全 - 带函数调用"""
        from tradingagents.llm_adapters.openai_adapter import OpenAIAdapter

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = None
        mock_response.choices[0].message.tool_calls = [
            Mock(function=Mock(arguments='{"param": "value"}', name="test_function"))
        ]
        mock_response.usage.total_tokens = 150
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        adapter = OpenAIAdapter(api_key="test-key", model="gpt-4")
        result = await adapter.generate_chat_completion(
            messages=[{"role": "user", "content": "测试"}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "test_function",
                        "description": "测试函数",
                        "parameters": {"type": "object"},
                    },
                }
            ],
        )

        assert "tool_calls" in result
        assert result["total_tokens"] == 150

    @pytest.mark.asyncio
    @patch("openai.AsyncOpenAI")
    async def test_generate_chat_completion_error(self, mock_openai):
        """测试生成聊天补全 - 错误场景"""
        from tradingagents.llm_adapters.openai_adapter import OpenAIAdapter
        from openai import APIError

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=APIError("API Error")
        )
        mock_openai.return_value = mock_client

        adapter = OpenAIAdapter(api_key="test-key", model="gpt-4")

        with pytest.raises(APIError):
            await adapter.generate_chat_completion(
                messages=[{"role": "user", "content": "测试"}]
            )

    @pytest.mark.asyncio
    @patch("openai.AsyncOpenAI")
    async def test_stream_completion(self, mock_openai):
        """测试流式补全"""
        from tradingagents.llm_adapters.openai_adapter import OpenAIAdapter
        import asyncio

        mock_client = AsyncMock()

        # Mock 流式响应
        async def mock_stream():
            chunks = ["测试", "流式", "响应"]
            for chunk in chunks:
                yield Mock(choices=[Mock(delta=Mock(content=chunk))])

        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream())
        mock_openai.return_value = mock_client

        adapter = OpenAIAdapter(api_key="test-key", model="gpt-4")

        # 收集流式输出
        full_content = ""
        async for chunk in adapter.stream_completion(
            messages=[{"role": "user", "content": "测试"}]
        ):
            full_content += chunk

        assert len(full_content) > 0


class TestGoogleAIAdapter:
    """Google AI (Gemini) 适配器测试"""

    @pytest.mark.asyncio
    async def test_google_adapter_initialization(self):
        """测试 Google AI 适配器初始化"""
        from tradingagents.llm_adapters.google_ai_adapter import GoogleAIAdapter

        adapter = GoogleAIAdapter(
            api_key="test-key", model="gemini-pro", temperature=0.7
        )

        assert adapter.api_key == "test-key"
        assert adapter.model == "gemini-pro"

    @pytest.mark.asyncio
    @patch("google.generativeai.GenerativeModel")
    async def test_generate_completion_success(self, mock_model):
        """测试生成补全 - 成功场景"""
        from tradingagents.llm_adapters.google_ai_adapter import GoogleAIAdapter

        mock_response = Mock()
        mock_response.text = "测试响应"
        mock_response.usage_metadata.total_token_count = 100

        mock_instance = AsyncMock()
        mock_instance.generate_content_async = AsyncMock(return_value=mock_response)
        mock_model.return_value = mock_instance

        adapter = GoogleAIAdapter(api_key="test-key", model="gemini-pro")
        result = await adapter.generate_completion(prompt="测试提示")

        assert result["content"] == "测试响应"
        assert result["total_tokens"] == 100

    @pytest.mark.asyncio
    @patch("google.generativeai.GenerativeModel")
    async def test_generate_chat_completion(self, mock_model):
        """测试生成聊天补全"""
        from tradingagents.llm_adapters.google_ai_adapter import GoogleAIAdapter

        mock_response = Mock()
        mock_response.text = "聊天响应"
        mock_response.usage_metadata.total_token_count = 150

        mock_instance = AsyncMock()
        mock_instance.generate_content_async = AsyncMock(return_value=mock_response)
        mock_model.return_value = mock_instance

        adapter = GoogleAIAdapter(api_key="test-key", model="gemini-pro")
        result = await adapter.generate_chat_completion(
            messages=[{"role": "user", "content": "测试"}]
        )

        assert result["content"] == "聊天响应"


class TestDashScopeAdapter:
    """DashScope (阿里云) 适配器测试"""

    @pytest.mark.asyncio
    async def test_dashscope_adapter_initialization(self):
        """测试 DashScope 适配器初始化"""
        from tradingagents.llm_adapters.dashscope_adapter import DashScopeAdapter

        adapter = DashScopeAdapter(
            api_key="sk-test-key", model="qwen-turbo", temperature=0.7
        )

        assert adapter.api_key == "sk-test-key"
        assert adapter.model == "qwen-turbo"

    @pytest.mark.asyncio
    @patch("dashscope.Generation.call")
    async def test_generate_completion_success(self, mock_call):
        """测试生成补全 - 成功场景"""
        from tradingagents.llm_adapters.dashscope_adapter import DashScopeAdapter

        mock_response = {"output": {"text": "测试响应"}, "usage": {"total_tokens": 100}}
        mock_call.return_value = mock_response

        adapter = DashScopeAdapter(api_key="test-key", model="qwen-turbo")
        result = await adapter.generate_completion(prompt="测试提示")

        assert result["content"] == "测试响应"
        assert result["total_tokens"] == 100


class TestDeepSeekAdapter:
    """DeepSeek 适配器测试"""

    @pytest.mark.asyncio
    async def test_deepseek_adapter_initialization(self):
        """测试 DeepSeek 适配器初始化"""
        from tradingagents.llm_adapters.deepseek_adapter import DeepSeekAdapter

        adapter = DeepSeekAdapter(
            api_key="sk-test-key", model="deepseek-chat", temperature=0.7
        )

        assert adapter.api_key == "sk-test-key"
        assert adapter.model == "deepseek-chat"

    @pytest.mark.asyncio
    @patch("openai.AsyncOpenAI")
    async def test_generate_completion_success(self, mock_openai):
        """测试生成补全 - 成功场景（使用 OpenAI 兼容 API）"""
        from tradingagents.llm_adapters.deepseek_adapter import DeepSeekAdapter

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "DeepSeek 响应"
        mock_response.usage.total_tokens = 100
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai.return_value = mock_client

        adapter = DeepSeekAdapter(
            api_key="test-key",
            model="deepseek-chat",
            base_url="https://api.deepseek.com/v1",
        )
        result = await adapter.generate_chat_completion(
            messages=[{"role": "user", "content": "测试"}]
        )

        assert result["content"] == "DeepSeek 响应"
        assert result["total_tokens"] == 100


class TestLLMAdapterFactory:
    """LLM 适配器工厂测试"""

    @pytest.mark.asyncio
    async def test_create_openai_adapter(self):
        """测试创建 OpenAI 适配器"""
        from tradingagents.llm_adapters.factory import LLMAdapterFactory

        config = {"provider": "openai", "api_key": "test-key", "model": "gpt-4"}

        adapter = LLMAdapterFactory.create_adapter(config)
        assert adapter.__class__.__name__ == "OpenAIAdapter"

    @pytest.mark.asyncio
    async def test_create_google_adapter(self):
        """测试创建 Google AI 适配器"""
        from tradingagents.llm_adapters.factory import LLMAdapterFactory

        config = {"provider": "google", "api_key": "test-key", "model": "gemini-pro"}

        adapter = LLMAdapterFactory.create_adapter(config)
        assert adapter.__class__.__name__ == "GoogleAIAdapter"

    @pytest.mark.asyncio
    async def test_create_dashscope_adapter(self):
        """测试创建 DashScope 适配器"""
        from tradingagents.llm_adapters.factory import LLMAdapterFactory

        config = {"provider": "dashscope", "api_key": "test-key", "model": "qwen-turbo"}

        adapter = LLMAdapterFactory.create_adapter(config)
        assert adapter.__class__.__name__ == "DashScopeAdapter"

    @pytest.mark.asyncio
    async def test_create_deepseek_adapter(self):
        """测试创建 DeepSeek 适配器"""
        from tradingagents.llm_adapters.factory import LLMAdapterFactory

        config = {
            "provider": "deepseek",
            "api_key": "test-key",
            "model": "deepseek-chat",
        }

        adapter = LLMAdapterFactory.create_adapter(config)
        assert adapter.__class__.__name__ == "DeepSeekAdapter"

    @pytest.mark.asyncio
    async def test_create_invalid_adapter(self):
        """测试创建无效适配器"""
        from tradingagents.llm_adapters.factory import LLMAdapterFactory

        config = {
            "provider": "invalid_provider",
            "api_key": "test-key",
            "model": "test-model",
        }

        with pytest.raises(ValueError):
            LLMAdapterFactory.create_adapter(config)
