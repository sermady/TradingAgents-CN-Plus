# -*- coding: utf-8 -*-
# TradingAgents/graph/base.py
"""
核心类和 LLM 初始化逻辑
"""

import os
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from tradingagents.llm_adapters import ChatDashScopeOpenAI, ChatGoogleOpenAI

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("agents")


def create_llm_by_provider(
    provider: str,
    model: str,
    backend_url: str,
    temperature: float,
    max_tokens: int,
    timeout: int,
    api_key: str = None,
):
    """
    根据 provider 创建对应的 LLM 实例

    Args:
        provider: 供应商名称 (google, dashscope, deepseek, openai, etc.)
        model: 模型名称
        backend_url: API 地址
        temperature: 温度参数
        max_tokens: 最大 token 数
        timeout: 超时时间
        api_key: API Key（可选，如果未提供则从环境变量读取）

    Returns:
        LLM 实例
    """
    from tradingagents.llm_adapters.deepseek_adapter import ChatDeepSeek
    from tradingagents.llm_adapters.openai_compatible_base import (
        create_openai_compatible_llm,
    )

    logger.info(f"🔧 [创建LLM] provider={provider}, model={model}, url={backend_url}")
    logger.info(f"🔑 [API Key] 来源: {'数据库配置' if api_key else '环境变量'}")

    if provider.lower() == "google":
        # 优先使用传入的 API Key，否则从环境变量读取
        google_api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError(
                "使用Google需要设置GOOGLE_API_KEY环境变量或在数据库中配置API Key"
            )

        # 传递 base_url 参数，使厂家配置的 default_base_url 生效
        return ChatGoogleOpenAI(
            model=model,
            google_api_key=google_api_key,
            base_url=backend_url if backend_url else None,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    elif provider.lower() == "dashscope":
        # 优先使用传入的 API Key，否则从环境变量读取
        dashscope_api_key = api_key or os.getenv("DASHSCOPE_API_KEY")

        # 传递 base_url 参数，使厂家配置的 default_base_url 生效
        return ChatDashScopeOpenAI(
            model=model,
            api_key=dashscope_api_key,  # 🔥 传递 API Key
            base_url=backend_url if backend_url else None,  # 如果有自定义 URL 则使用
            temperature=temperature,
            max_tokens=max_tokens,
            request_timeout=timeout,
        )

    elif provider.lower() == "deepseek":
        # 优先使用传入的 API Key，否则从环境变量读取
        deepseek_api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not deepseek_api_key:
            raise ValueError(
                "使用DeepSeek需要设置DEEPSEEK_API_KEY环境变量或在数据库中配置API Key"
            )

        return ChatDeepSeek(
            model=model,
            api_key=deepseek_api_key,
            base_url=backend_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    elif provider.lower() == "zhipu":
        # 智谱AI处理
        zhipu_api_key = api_key or os.getenv("ZHIPU_API_KEY")
        if not zhipu_api_key:
            raise ValueError(
                "使用智谱AI需要设置ZHIPU_API_KEY环境变量或在数据库中配置API Key"
            )

        return create_openai_compatible_llm(
            provider="zhipu",
            model=model,
            api_key=zhipu_api_key,
            base_url=backend_url,  # 使用用户提供的backend_url
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    elif provider.lower() in ["openai", "siliconflow", "openrouter", "ollama"]:
        # 优先使用传入的 API Key，否则从环境变量读取
        if not api_key:
            if provider.lower() == "siliconflow":
                api_key = os.getenv("SILICONFLOW_API_KEY")
            elif provider.lower() == "openrouter":
                api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
            elif provider.lower() == "openai":
                api_key = os.getenv("OPENAI_API_KEY")

        return ChatOpenAI(
            model=model,
            base_url=backend_url,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    elif provider.lower() == "anthropic":
        return ChatAnthropic(
            model=model,
            base_url=backend_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    elif provider.lower() in ["qianfan", "custom_openai"]:
        return create_openai_compatible_llm(
            provider=provider,
            model=model,
            base_url=backend_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    else:
        # 🔧 自定义厂家：使用 OpenAI 兼容模式
        logger.info(f"🔧 使用 OpenAI 兼容模式处理自定义厂家: {provider}")

        # 尝试从环境变量获取 API Key（支持多种命名格式）
        api_key_candidates = [
            f"{provider.upper()}_API_KEY",  # 例如: KYX_API_KEY
            f"{provider}_API_KEY",  # 例如: kyx_API_KEY
            "CUSTOM_OPENAI_API_KEY",  # 通用环境变量
        ]

        custom_api_key = None
        for env_var in api_key_candidates:
            custom_api_key = os.getenv(env_var)
            if custom_api_key:
                logger.info(f"✅ 从环境变量 {env_var} 获取到 API Key")
                break

        if not custom_api_key:
            logger.warning(
                f"⚠️ 未找到自定义厂家 {provider} 的 API Key，尝试使用默认配置"
            )

        return ChatOpenAI(
            model=model,
            base_url=backend_url,
            api_key=custom_api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
