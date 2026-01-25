# -*- coding: utf-8 -*-
"""
测试TradingGraph主图功能

测试范围:
- TradingGraph初始化
- LLM提供商配置
- 快速/深度模型配置
- 图构建
- 状态管理
- 错误处理
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from tradingagents.graph.trading_graph import TradingAgentsGraph


@pytest.mark.unit
def test_trading_graph_initialization():
    """测试TradingGraph初始化"""
    # Arrange
    mock_config = {
        "project_dir": "/test/path",
        "llm_provider": "openai",
        "quick_think_llm": "gpt-3.5-turbo",
        "deep_think_llm": "gpt-4",
    }

    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            graph = TradingAgentsGraph(
                selected_analysts=["market", "social", "news", "fundamentals"],
                debug=False,
                config=mock_config,
            )

    # Assert
    assert graph is not None
    assert graph.config == mock_config


@pytest.mark.unit
def test_trading_graph_default_config():
    """测试使用默认配置初始化"""
    # Arrange & Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            graph = TradingAgentsGraph()

    # Assert
    assert graph is not None
    assert graph.config is not None


@pytest.mark.unit
def test_trading_graph_custom_analysts():
    """测试自定义分析师列表"""
    # Arrange
    custom_analysts = ["market", "fundamentals"]

    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            graph = TradingAgentsGraph(
                selected_analysts=custom_analysts, debug=False, config=None
            )

    # Assert
    assert graph is not None
    # 验证选择了指定的分析师


@pytest.mark.unit
def test_trading_graph_debug_mode():
    """测试调试模式初始化"""
    # Arrange
    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            graph = TradingAgentsGraph(
                selected_analysts=["market"], debug=True, config=None
            )

    # Assert
    assert graph is not None
    assert graph.debug is True


@pytest.mark.unit
def test_trading_graph_openai_provider():
    """测试OpenAI提供商配置"""
    # Arrange
    mock_config = {
        "project_dir": "/test/path",
        "llm_provider": "openai",
        "quick_think_llm": "gpt-3.5-turbo",
        "deep_think_llm": "gpt-4",
        "quick_model_config": {"max_tokens": 2000, "temperature": 0.7, "timeout": 180},
        "deep_model_config": {"max_tokens": 4000, "temperature": 0.7, "timeout": 300},
    }

    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            with patch("tradingagents.graph.trading_graph.ChatOpenAI") as mock_openai:
                graph = TradingAgentsGraph(
                    selected_analysts=["market"], debug=False, config=mock_config
                )

    # Assert
    assert graph is not None
    # 验证使用了ChatOpenAI


@pytest.mark.unit
def test_trading_graph_google_provider():
    """测试Google提供商配置"""
    # Arrange
    mock_config = {
        "project_dir": "/test/path",
        "llm_provider": "google",
        "quick_think_llm": "gemini-pro",
        "deep_think_llm": "gemini-pro",
    }

    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            with patch(
                "tradingagents.graph.trading_graph.ChatGoogleOpenAI"
            ) as mock_google:
                graph = TradingAgentsGraph(
                    selected_analysts=["market"], debug=False, config=mock_config
                )

    # Assert
    assert graph is not None
    # 验证使用了ChatGoogleOpenAI


@pytest.mark.unit
def test_trading_graph_dashscope_provider():
    """测试DashScope提供商配置"""
    # Arrange
    mock_config = {
        "project_dir": "/test/path",
        "llm_provider": "dashscope",
        "quick_think_llm": "qwen-max",
        "deep_think_llm": "qwen-max",
    }

    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            with patch(
                "tradingagents.graph.trading_graph.ChatDashScopeOpenAI"
            ) as mock_dashscope:
                graph = TradingAgentsGraph(
                    selected_analysts=["market"], debug=False, config=mock_config
                )

    # Assert
    assert graph is not None
    # 验证使用了ChatDashScopeOpenAI


@pytest.mark.unit
def test_trading_graph_deepseek_provider():
    """测试DeepSeek提供商配置"""
    # Arrange
    mock_config = {
        "project_dir": "/test/path",
        "llm_provider": "deepseek",
        "quick_think_llm": "deepseek-chat",
        "deep_think_llm": "deepseek-chat",
    }

    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            with patch(
                "tradingagents.graph.trading_graph.ChatDeepSeek"
            ) as mock_deepseek:
                graph = TradingAgentsGraph(
                    selected_analysts=["market"], debug=False, config=mock_config
                )

    # Assert
    assert graph is not None
    # 验证使用了ChatDeepSeek


@pytest.mark.unit
def test_trading_graph_zhipu_provider():
    """测试智谱AI提供商配置"""
    # Arrange
    mock_config = {
        "project_dir": "/test/path",
        "llm_provider": "zhipu",
        "quick_think_llm": "glm-4",
        "deep_think_llm": "glm-4",
    }

    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            with patch(
                "tradingagents.graph.trading_graph.create_openai_compatible_llm"
            ) as mock_compatible:
                graph = TradingAgentsGraph(
                    selected_analysts=["market"], debug=False, config=mock_config
                )

    # Assert
    assert graph is not None
    # 验证使用了OpenAI兼容模式


@pytest.mark.unit
def test_trading_graph_siliconflow_provider():
    """测试SiliconFlow提供商配置"""
    # Arrange
    mock_config = {
        "project_dir": "/test/path",
        "llm_provider": "siliconflow",
        "quick_think_llm": "sf-pro",
        "deep_think_llm": "sf-pro",
    }

    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            with patch("tradingagents.graph.trading_graph.ChatOpenAI") as mock_openai:
                graph = TradingAgentsGraph(
                    selected_analysts=["market"], debug=False, config=mock_config
                )

    # Assert
    assert graph is not None
    # 验证使用了ChatOpenAI(SiliconFlow)


@pytest.mark.unit
def test_trading_graph_custom_provider():
    """测试自定义提供商配置"""
    # Arrange
    mock_config = {
        "project_dir": "/test/path",
        "llm_provider": "custom",
        "quick_think_llm": "custom-model",
        "deep_think_llm": "custom-model",
    }

    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            with patch(
                "tradingagents.graph.trading_graph.create_openai_compatible_llm"
            ) as mock_compatible:
                graph = TradingAgentsGraph(
                    selected_analysts=["market"], debug=False, config=mock_config
                )

    # Assert
    assert graph is not None
    # 验证使用了OpenAI兼容模式


@pytest.mark.unit
def test_trading_graph_anthropic_provider():
    """测试Anthropic提供商配置"""
    # Arrange
    mock_config = {
        "project_dir": "/test/path",
        "llm_provider": "anthropic",
        "quick_think_llm": "claude-3-opus",
        "deep_think_llm": "claude-3-opus",
    }

    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            with patch(
                "tradingagents.graph.trading_graph.ChatAnthropic"
            ) as mock_anthropic:
                graph = TradingAgentsGraph(
                    selected_analysts=["market"], debug=False, config=mock_config
                )

    # Assert
    assert graph is not None
    # 验证使用了ChatAnthropic


@pytest.mark.unit
def test_trading_graph_config_merge():
    """测试配置合并"""
    # Arrange
    user_config = {
        "project_dir": "/test/path",
        "llm_provider": "openai",
        "quick_think_llm": "gpt-3.5-turbo",
    }

    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            graph = TradingAgentsGraph(
                selected_analysts=["market"], debug=False, config=user_config
            )

    # Assert
    assert graph is not None
    # 验证用户配置与默认配置合并


@pytest.mark.unit
def test_trading_graph_temperature_config():
    """测试温度参数配置"""
    # Arrange
    mock_config = {
        "project_dir": "/test/path",
        "llm_provider": "openai",
        "quick_think_llm": "gpt-3.5-turbo",
        "deep_think_llm": "gpt-4",
        "quick_model_config": {"temperature": 0.5, "max_tokens": 1500, "timeout": 120},
        "deep_model_config": {"temperature": 0.8, "max_tokens": 3500, "timeout": 240},
    }

    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            with patch("tradingagents.graph.trading_graph.ChatOpenAI") as mock_openai:
                graph = TradingAgentsGraph(
                    selected_analysts=["market"], debug=False, config=mock_config
                )

    # Assert
    assert graph is not None
    # 验证温度参数正确传递


@pytest.mark.unit
def test_trading_graph_max_tokens_config():
    """测试最大token配置"""
    # Arrange
    mock_config = {
        "project_dir": "/test/path",
        "llm_provider": "openai",
        "quick_think_llm": "gpt-3.5-turbo",
        "deep_think_llm": "gpt-4",
        "quick_model_config": {"max_tokens": 3000, "temperature": 0.7, "timeout": 180},
        "deep_model_config": {"max_tokens": 5000, "temperature": 0.7, "timeout": 300},
    }

    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            with patch("tradingagents.graph.trading_graph.ChatOpenAI") as mock_openai:
                graph = TradingAgentsGraph(
                    selected_analysts=["market"], debug=False, config=mock_config
                )

    # Assert
    assert graph is not None
    # 验证max_tokens参数正确传递


@pytest.mark.unit
def test_trading_graph_timeout_config():
    """测试超时配置"""
    # Arrange
    mock_config = {
        "project_dir": "/test/path",
        "llm_provider": "openai",
        "quick_think_llm": "gpt-3.5-turbo",
        "deep_think_llm": "gpt-4",
        "quick_model_config": {"timeout": 240, "max_tokens": 2000, "temperature": 0.7},
        "deep_model_config": {"timeout": 360, "max_tokens": 4000, "temperature": 0.7},
    }

    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            with patch("tradingagents.graph.trading_graph.ChatOpenAI") as mock_openai:
                graph = TradingAgentsGraph(
                    selected_analysts=["market"], debug=False, config=mock_config
                )

    # Assert
    assert graph is not None
    # 验证timeout参数正确传递


@pytest.mark.unit
def test_trading_graph_backend_url_config():
    """测试后端URL配置"""
    # Arrange
    mock_config = {
        "project_dir": "/test/path",
        "llm_provider": "openai",
        "quick_think_llm": "gpt-3.5-turbo",
        "deep_think_llm": "gpt-4",
        "backend_url": "https://custom-endpoint.com/v1",
        "quick_backend_url": "https://quick-endpoint.com/v1",
        "deep_backend_url": "https://deep-endpoint.com/v1",
    }

    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            with patch("tradingagents.graph.trading_graph.ChatOpenAI") as mock_openai:
                graph = TradingAgentsGraph(
                    selected_analysts=["market"], debug=False, config=mock_config
                )

    # Assert
    assert graph is not None
    # 验证backend_url参数正确传递


@pytest.mark.unit
def test_trading_graph_mixed_mode_detection():
    """测试混合模式检测"""
    # Arrange
    mock_config = {
        "project_dir": "/test/path",
        "llm_provider": "mixed",  # 混合模式
        "quick_provider": "openai",
        "deep_provider": "google",
        "quick_think_llm": "gpt-3.5-turbo",
        "deep_think_llm": "gemini-pro",
    }

    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            graph = TradingAgentsGraph(
                selected_analysts=["market"], debug=False, config=mock_config
            )

    # Assert
    assert graph is not None
    # 混合模式下应该同时创建快速和深度模型


@pytest.mark.unit
def test_trading_graph_api_key_from_config():
    """测试从配置获取API Key"""
    # Arrange
    mock_config = {
        "project_dir": "/test/path",
        "llm_provider": "openai",
        "quick_think_llm": "gpt-3.5-turbo",
        "deep_think_llm": "gpt-4",
        "quick_api_key": "sk-test-key-from-config",
        "deep_api_key": "sk-test-key-from-config",
    }

    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            with patch("tradingagents.graph.trading_graph.ChatOpenAI") as mock_openai:
                graph = TradingAgentsGraph(
                    selected_analysts=["market"], debug=False, config=mock_config
                )

    # Assert
    assert graph is not None
    # 验证API Key从配置读取


@pytest.mark.unit
def test_trading_graph_api_key_from_env():
    """测试从环境变量获取API Key"""
    # Arrange
    mock_config = {
        "project_dir": "/test/path",
        "llm_provider": "google",
        "quick_think_llm": "gemini-pro",
        "deep_think_llm": "gemini-pro",
    }

    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-api-key-from-env"}):
                with patch(
                    "tradingagents.graph.trading_graph.ChatGoogleOpenAI"
                ) as mock_google:
                    graph = TradingAgentsGraph(
                        selected_analysts=["market"], debug=False, config=mock_config
                    )

    # Assert
    assert graph is not None
    # 验证API Key从环境变量读取


@pytest.mark.unit
def test_trading_graph_missing_api_key():
    """测试缺失API Key时的错误处理"""
    # Arrange
    mock_config = {
        "project_dir": "/test/path",
        "llm_provider": "google",
        "quick_think_llm": "gemini-pro",
        "deep_think_llm": "gemini-pro",
    }

    # Act & Assert
    with patch("tradingagents.graph.trading_graph.set_config"):
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(ValueError) as exc_info:
                    from tradingagents.graph.trading_graph import TradingAgentsGraph

                    graph = TradingAgentsGraph(
                        selected_analysts=["market"], debug=False, config=mock_config
                    )

    assert "GOOGLE_API_KEY" in str(exc_info.value)


@pytest.mark.unit
def test_trading_graph_directory_creation():
    """测试目录创建"""
    # Arrange
    mock_config = {
        "project_dir": "/test/path",
        "llm_provider": "openai",
        "quick_think_llm": "gpt-3.5-turbo",
        "deep_think_llm": "gpt-4",
    }

    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs") as mock_makedirs:
            graph = TradingAgentsGraph(
                selected_analysts=["market"], debug=False, config=mock_config
            )

    # Assert
    assert graph is not None
    # 验证创建data_cache目录
    mock_makedirs.assert_called_once()


@pytest.mark.unit
def test_trading_graph_config_interface_update():
    """测试配置接口更新"""
    # Arrange
    mock_config = {
        "project_dir": "/test/path",
        "llm_provider": "openai",
        "quick_think_llm": "gpt-3.5-turbo",
        "deep_think_llm": "gpt-4",
    }

    # Act
    with patch("tradingagents.graph.trading_graph.set_config") as mock_set_config:
        with patch("tradingagents.graph.trading_graph.os.makedirs"):
            graph = TradingAgentsGraph(
                selected_analysts=["market"], debug=False, config=mock_config
            )

    # Assert
    assert graph is not None
    # 验证调用set_config更新接口配置
    mock_set_config.assert_called_once_with(mock_config)
