# -*- coding: utf-8 -*-
"""
LLM相关Fixtures
"""

import pytest
from typing import Dict, Any, Callable
from unittest.mock import AsyncMock, patch


@pytest.fixture
def mock_openai_response():
    """
    Mock OpenAI API响应
    """

    def _create_response(content: str, tokens: int = 100, model: str = "gpt-4"):
        async def _acreate(*args, **kwargs):
            mock_response = AsyncMock()
            mock_response.choices = [
                AsyncMock(message=AsyncMock(content=content, role="assistant"))
            ]
            mock_response.usage = AsyncMock(
                prompt_tokens=50, completion_tokens=tokens, total_tokens=50 + tokens
            )
            mock_response.model = model
            return mock_response

        with patch("openai.ChatCompletion.acreate", side_effect=_acreate):
            yield {"content": content, "model": model, "tokens": 50 + tokens}

    return _create_response


@pytest.fixture
def mock_gemini_response():
    """
    Mock Google Gemini API响应
    """

    def _create_response(content: str, tokens: int = 100, model: str = "gemini-pro"):
        async def _generate_content(*args, **kwargs):
            mock_response = AsyncMock()
            mock_response.text = content
            mock_response.usage_metadata = AsyncMock(
                prompt_token_count=50,
                candidates_token_count=tokens,
                total_token_count=50 + tokens,
            )
            mock_response.model = model
            return mock_response

        with patch(
            "google.generativeai.GenerativeModel.generate_content",
            side_effect=_generate_content,
        ):
            yield {"content": content, "model": model, "tokens": 50 + tokens}

    return _create_response


@pytest.fixture
def mock_dashscope_response():
    """
    Mock DashScope API响应
    """

    def _create_response(content: str, tokens: int = 100, model: str = "qwen-turbo"):
        async def _call(*args, **kwargs):
            mock_response = AsyncMock()
            mock_response.output = {"text": content}
            mock_response.usage = {
                "input_tokens": 50,
                "output_tokens": tokens,
                "total_tokens": 50 + tokens,
            }
            return mock_response

        with patch("dashscope.Generation.call", side_effect=_call):
            yield {"content": content, "model": model, "tokens": 50 + tokens}

    return _create_response


@pytest.fixture
def mock_deepseek_response():
    """
    Mock DeepSeek API响应
    """

    def _create_response(content: str, tokens: int = 100, model: str = "deepseek-chat"):
        async def _acreate(*args, **kwargs):
            mock_response = AsyncMock()
            mock_response.choices = [AsyncMock(message=AsyncMock(content=content))]
            mock_response.usage = AsyncMock(
                prompt_tokens=50, completion_tokens=tokens, total_tokens=50 + tokens
            )
            return mock_response

        with patch("openai.ChatCompletion.acreate", side_effect=_acreate):
            yield {"content": content, "model": model, "tokens": 50 + tokens}

    return _create_response


@pytest.fixture
def mock_llm_factory():
    """
    Mock LLM工厂
    返回一个可以生成各种LLM响应的工厂
    """

    class MockLLMFactory:
        def __init__(self):
            self.responses = {}

        def set_response(self, provider: str, content: str):
            """设置特定provider的响应"""
            self.responses[provider] = content

        def get_response(self, provider: str, default: str = "Mock response"):
            """获取特定provider的响应"""
            return self.responses.get(provider, default)

    return MockLLMFactory()


@pytest.fixture
def mock_tool_call():
    """
    Mock LLM工具调用
    """

    def _create_tool_call(tool_name: str, tool_args: Dict[str, Any]):
        async def _call(*args, **kwargs):
            mock_response = AsyncMock()
            mock_response.choices = [
                AsyncMock(
                    message=AsyncMock(
                        content="",
                        tool_calls=[
                            {
                                "id": "call_123",
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "arguments": str(tool_args),
                                },
                            }
                        ],
                    )
                )
            ]
            return mock_response

        return _call

    return _create_tool_call


@pytest.fixture
def sample_llm_messages():
    """
    样本LLM消息
    """
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Analyze this stock."},
    ]


@pytest.fixture
def sample_tool_schemas():
    """
    样本工具schema
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "get_stock_price",
                "description": "Get stock price",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Stock code"}
                    },
                    "required": ["code"],
                },
            },
        }
    ]
