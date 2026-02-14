# -*- coding: utf-8 -*-
# TradingAgents/graph/llm_init.py
"""
LLM 初始化逻辑
"""

import os
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from tradingagents.llm_adapters import ChatDashScopeOpenAI, ChatGoogleOpenAI

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("agents")


class LLMInitializer:
    """LLM 初始化器"""

    @staticmethod
    def initialize_llms(config: Dict[str, Any]):
        """
        初始化快速和深度思考 LLM

        Args:
            config: 配置字典

        Returns:
            (quick_thinking_llm, deep_thinking_llm)
        """
        from .base import create_llm_by_provider

        # 🔧 从配置中读取模型参数（优先使用用户配置，否则使用默认值）
        quick_config = config.get("quick_model_config", {})
        deep_config = config.get("deep_model_config", {})

        # 读取快速模型参数
        quick_max_tokens = quick_config.get("max_tokens", 4000)
        quick_temperature = quick_config.get("temperature", 0.7)
        quick_timeout = quick_config.get("timeout", 180)

        # 读取深度模型参数
        deep_max_tokens = deep_config.get("max_tokens", 4000)
        deep_temperature = deep_config.get("temperature", 0.7)
        deep_timeout = deep_config.get("timeout", 180)

        # 🔧 检查是否为混合模式（快速模型和深度模型来自不同厂家）
        quick_provider = config.get("quick_provider")
        deep_provider = config.get("deep_provider")
        quick_backend_url = config.get("quick_backend_url")
        deep_backend_url = config.get("deep_backend_url")

        if quick_provider and deep_provider and quick_provider != deep_provider:
            # 混合模式：快速模型和深度模型来自不同厂家
            logger.info(f"🔀 [混合模式] 检测到不同厂家的模型组合")
            logger.info(f"   快速模型: {config['quick_think_llm']} ({quick_provider})")
            logger.info(f"   深度模型: {config['deep_think_llm']} ({deep_provider})")

            # 使用统一的函数创建 LLM 实例
            quick_thinking_llm = create_llm_by_provider(
                provider=quick_provider,
                model=config["quick_think_llm"],
                backend_url=quick_backend_url or config.get("backend_url", ""),
                temperature=quick_temperature,
                max_tokens=quick_max_tokens,
                timeout=quick_timeout,
                api_key=config.get("quick_api_key"),  # 🔥 传递 API Key
            )

            deep_thinking_llm = create_llm_by_provider(
                provider=deep_provider,
                model=config["deep_think_llm"],
                backend_url=deep_backend_url or config.get("backend_url", ""),
                temperature=deep_temperature,
                max_tokens=deep_max_tokens,
                timeout=deep_timeout,
                api_key=config.get("deep_api_key"),  # 🔥 传递 API Key
            )

            logger.info(f"✅ [混合模式] LLM 实例创建成功")
            return quick_thinking_llm, deep_thinking_llm

        # 单一厂家模式
        provider = config["llm_provider"]

        if provider.lower() == "openai":
            logger.info(
                f"🔧 [OpenAI-快速模型] max_tokens={quick_max_tokens}, temperature={quick_temperature}, timeout={quick_timeout}s"
            )
            logger.info(
                f"🔧 [OpenAI-深度模型] max_tokens={deep_max_tokens}, temperature={deep_temperature}, timeout={deep_timeout}s"
            )

            deep_thinking_llm = ChatOpenAI(
                model=config["deep_think_llm"],
                base_url=config["backend_url"],
                temperature=deep_temperature,
                max_tokens=deep_max_tokens,
                timeout=deep_timeout,
            )
            quick_thinking_llm = ChatOpenAI(
                model=config["quick_think_llm"],
                base_url=config["backend_url"],
                temperature=quick_temperature,
                max_tokens=quick_max_tokens,
                timeout=quick_timeout,
            )

        elif provider == "siliconflow":
            # SiliconFlow支持：使用OpenAI兼容API
            siliconflow_api_key = os.getenv("SILICONFLOW_API_KEY")
            if not siliconflow_api_key:
                raise ValueError("使用SiliconFlow需要设置SILICONFLOW_API_KEY环境变量")

            logger.info(f"🌐 [SiliconFlow] 使用API密钥: {siliconflow_api_key[:20]}...")
            logger.info(
                f"🔧 [SiliconFlow-快速模型] max_tokens={quick_max_tokens}, temperature={quick_temperature}, timeout={quick_timeout}s"
            )
            logger.info(
                f"🔧 [SiliconFlow-深度模型] max_tokens={deep_max_tokens}, temperature={deep_temperature}, timeout={deep_timeout}s"
            )

            deep_thinking_llm = ChatOpenAI(
                model=config["deep_think_llm"],
                base_url=config["backend_url"],
                api_key=siliconflow_api_key,
                temperature=deep_temperature,
                max_tokens=deep_max_tokens,
                timeout=deep_timeout,
            )
            quick_thinking_llm = ChatOpenAI(
                model=config["quick_think_llm"],
                base_url=config["backend_url"],
                api_key=siliconflow_api_key,
                temperature=quick_temperature,
                max_tokens=quick_max_tokens,
                timeout=quick_timeout,
            )

        elif provider == "openrouter":
            # OpenRouter支持：优先使用OPENROUTER_API_KEY，否则使用OPENAI_API_KEY
            openrouter_api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv(
                "OPENAI_API_KEY"
            )
            if not openrouter_api_key:
                raise ValueError(
                    "使用OpenRouter需要设置OPENROUTER_API_KEY或OPENAI_API_KEY环境变量"
                )

            logger.info(f"🌐 [OpenRouter] 使用API密钥: {openrouter_api_key[:20]}...")
            logger.info(
                f"🔧 [OpenRouter-快速模型] max_tokens={quick_max_tokens}, temperature={quick_temperature}, timeout={quick_timeout}s"
            )
            logger.info(
                f"🔧 [OpenRouter-深度模型] max_tokens={deep_max_tokens}, temperature={deep_temperature}, timeout={deep_timeout}s"
            )

            deep_thinking_llm = ChatOpenAI(
                model=config["deep_think_llm"],
                base_url=config["backend_url"],
                api_key=openrouter_api_key,
                temperature=deep_temperature,
                max_tokens=deep_max_tokens,
                timeout=deep_timeout,
            )
            quick_thinking_llm = ChatOpenAI(
                model=config["quick_think_llm"],
                base_url=config["backend_url"],
                api_key=openrouter_api_key,
                temperature=quick_temperature,
                max_tokens=quick_max_tokens,
                timeout=quick_timeout,
            )

        elif provider == "ollama":
            logger.info(
                f"🔧 [Ollama-快速模型] max_tokens={quick_max_tokens}, temperature={quick_temperature}, timeout={quick_timeout}s"
            )
            logger.info(
                f"🔧 [Ollama-深度模型] max_tokens={deep_max_tokens}, temperature={deep_temperature}, timeout={deep_timeout}s"
            )

            deep_thinking_llm = ChatOpenAI(
                model=config["deep_think_llm"],
                base_url=config["backend_url"],
                temperature=deep_temperature,
                max_tokens=deep_max_tokens,
                timeout=deep_timeout,
            )
            quick_thinking_llm = ChatOpenAI(
                model=config["quick_think_llm"],
                base_url=config["backend_url"],
                temperature=quick_temperature,
                max_tokens=quick_max_tokens,
                timeout=quick_timeout,
            )

        elif provider.lower() == "anthropic":
            logger.info(
                f"🔧 [Anthropic-快速模型] max_tokens={quick_max_tokens}, temperature={quick_temperature}, timeout={quick_timeout}s"
            )
            logger.info(
                f"🔧 [Anthropic-深度模型] max_tokens={deep_max_tokens}, temperature={deep_temperature}, timeout={deep_timeout}s"
            )

            deep_thinking_llm = ChatAnthropic(
                model=config["deep_think_llm"],
                base_url=config["backend_url"],
                temperature=deep_temperature,
                max_tokens=deep_max_tokens,
                timeout=deep_timeout,
            )
            quick_thinking_llm = ChatAnthropic(
                model=config["quick_think_llm"],
                base_url=config["backend_url"],
                temperature=quick_temperature,
                max_tokens=quick_max_tokens,
                timeout=deep_timeout,
            )

        elif provider.lower() == "google":
            # 使用 Google OpenAI 兼容适配器，解决工具调用格式不匹配问题
            logger.info(f"🔧 使用Google AI OpenAI 兼容适配器 (解决工具调用问题)")

            # 🔥 优先使用数据库配置的 API Key，否则从环境变量读取
            google_api_key = (
                config.get("quick_api_key")
                or config.get("deep_api_key")
                or os.getenv("GOOGLE_API_KEY")
            )
            if not google_api_key:
                raise ValueError(
                    "使用Google AI需要在数据库中配置API Key或设置GOOGLE_API_KEY环境变量"
                )

            logger.info(
                f"🔑 [Google AI] API Key 来源: {'数据库配置' if config.get('quick_api_key') or config.get('deep_api_key') else '环境变量'}"
            )

            logger.info(
                f"🔧 [Google-快速模型] max_tokens={quick_max_tokens}, temperature={quick_temperature}, timeout={quick_timeout}s"
            )
            logger.info(
                f"🔧 [Google-深度模型] max_tokens={deep_max_tokens}, temperature={deep_temperature}, timeout={deep_timeout}s"
            )

            # 获取 backend_url（如果配置中有的话）
            backend_url = config.get("backend_url")
            if backend_url:
                logger.info(f"🔧 [Google AI] 使用配置的 backend_url: {backend_url}")
            else:
                logger.info(f"🔧 [Google AI] 未配置 backend_url，使用默认端点")

            deep_thinking_llm = ChatGoogleOpenAI(
                model=config["deep_think_llm"],
                google_api_key=google_api_key,
                base_url=backend_url if backend_url else None,
                temperature=deep_temperature,
                max_tokens=deep_max_tokens,
                timeout=deep_timeout,
            )
            quick_thinking_llm = ChatGoogleOpenAI(
                model=config["quick_think_llm"],
                google_api_key=google_api_key,
                base_url=backend_url if backend_url else None,
                temperature=quick_temperature,
                max_tokens=quick_max_tokens,
                timeout=deep_timeout,
                transport="rest",
            )

            logger.info(
                f"✅ [Google AI] 已启用优化的工具调用和内容格式处理并应用用户配置的模型参数"
            )

        elif (
            provider.lower() == "dashscope"
            or provider.lower() == "alibaba"
            or "dashscope" in provider.lower()
            or "阿里百炼" in provider
        ):
            # 使用 OpenAI 兼容适配器，支持原生 Function Calling
            logger.info(f"🔧 使用阿里百炼 OpenAI 兼容适配器 (支持原生工具调用)")

            # 🔥 优先使用数据库配置的 API Key，否则从环境变量读取
            dashscope_api_key = (
                config.get("quick_api_key")
                or config.get("deep_api_key")
                or os.getenv("DASHSCOPE_API_KEY")
            )
            logger.info(
                f"🔑 [阿里百炼] API Key 来源: {'数据库配置' if config.get('quick_api_key') or config.get('deep_api_key') else '环境变量'}"
            )

            logger.info(
                f"🔧 [阿里百炼-快速模型] max_tokens={quick_max_tokens}, temperature={quick_temperature}, timeout={quick_timeout}s"
            )
            logger.info(
                f"🔧 [阿里百炼-深度模型] max_tokens={deep_max_tokens}, temperature={deep_temperature}, timeout={deep_timeout}s"
            )

            # 获取 backend_url（如果配置中有的话）
            backend_url = config.get("backend_url")
            if backend_url:
                logger.info(f"🔧 [阿里百炼] 使用自定义 API 地址: {backend_url}")

            # 🔥 详细日志：打印所有 LLM 初始化参数
            logger.info("=" * 80)
            logger.info("🤖 [LLM初始化] 阿里百炼深度模型参数:")
            logger.info(f"   model: {config['deep_think_llm']}")
            logger.info(
                f"   api_key: {'有值' if dashscope_api_key else '空'} (长度: {len(dashscope_api_key) if dashscope_api_key else 0})"
            )
            logger.info(f"   base_url: {backend_url if backend_url else '默认'}")
            logger.info(f"   temperature: {deep_temperature}")
            logger.info(f"   max_tokens: {deep_max_tokens}")
            logger.info(f"   request_timeout: {deep_timeout}")
            logger.info("=" * 80)

            deep_thinking_llm = ChatDashScopeOpenAI(
                model=config["deep_think_llm"],
                api_key=dashscope_api_key,  # 🔥 传递 API Key
                base_url=backend_url if backend_url else None,  # 传递 base_url
                temperature=deep_temperature,
                max_tokens=deep_max_tokens,
                request_timeout=deep_timeout,
            )

            logger.info("=" * 80)
            logger.info("🤖 [LLM初始化] 阿里百炼快速模型参数:")
            logger.info(f"   model: {config['quick_think_llm']}")
            logger.info(
                f"   api_key: {'有值' if dashscope_api_key else '空'} (长度: {len(dashscope_api_key) if dashscope_api_key else 0})"
            )
            logger.info(f"   base_url: {backend_url if backend_url else '默认'}")
            logger.info(f"   temperature: {quick_temperature}")
            logger.info(f"   max_tokens: {quick_max_tokens}")
            logger.info(f"   request_timeout: {quick_timeout}")
            logger.info("=" * 80)

            quick_thinking_llm = ChatDashScopeOpenAI(
                model=config["quick_think_llm"],
                api_key=dashscope_api_key,  # 🔥 传递 API Key
                base_url=backend_url if backend_url else None,  # 传递 base_url
                temperature=quick_temperature,
                max_tokens=quick_max_tokens,
                request_timeout=quick_timeout,
            )
            logger.info(f"✅ [阿里百炼] 已应用用户配置的模型参数")

        elif (
            provider.lower() == "deepseek"
            or "deepseek" in provider.lower()
        ):
            # DeepSeek V3配置 - 使用支持token统计的适配器
            from tradingagents.llm_adapters.deepseek_adapter import ChatDeepSeek

            deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
            if not deepseek_api_key:
                raise ValueError("使用DeepSeek需要设置DEEPSEEK_API_KEY环境变量")

            deepseek_base_url = os.getenv(
                "DEEPSEEK_BASE_URL", "https://api.deepseek.com"
            )

            logger.info(
                f"🔧 [DeepSeek-快速模型] max_tokens={quick_max_tokens}, temperature={quick_temperature}, timeout={quick_timeout}s"
            )
            logger.info(
                f"🔧 [DeepSeek-深度模型] max_tokens={deep_max_tokens}, temperature={deep_temperature}, timeout={deep_timeout}s"
            )

            # 使用支持token统计的DeepSeek适配器
            deep_thinking_llm = ChatDeepSeek(
                model=config["deep_think_llm"],
                api_key=deepseek_api_key,
                base_url=deepseek_base_url,
                temperature=deep_temperature,
                max_tokens=deep_max_tokens,
                timeout=deep_timeout,
            )
            quick_thinking_llm = ChatDeepSeek(
                model=config["quick_think_llm"],
                api_key=deepseek_api_key,
                base_url=deepseek_base_url,
                temperature=quick_temperature,
                max_tokens=quick_max_tokens,
                timeout=quick_timeout,
            )

            logger.info(f"✅ [DeepSeek] 已启用token统计功能并应用用户配置的模型参数")

        elif provider.lower() == "custom_openai":
            # 自定义OpenAI端点配置
            from tradingagents.llm_adapters.openai_compatible_base import (
                create_openai_compatible_llm,
            )

            custom_api_key = os.getenv("CUSTOM_OPENAI_API_KEY")
            if not custom_api_key:
                raise ValueError(
                    "使用自定义OpenAI端点需要设置CUSTOM_OPENAI_API_KEY环境变量"
                )

            custom_base_url = config.get(
                "custom_openai_base_url", "https://api.openai.com/v1"
            )

            logger.info(f"🔧 [自定义OpenAI] 使用端点: {custom_base_url}")
            logger.info(
                f"🔧 [自定义OpenAI-快速模型] max_tokens={quick_max_tokens}, temperature={quick_temperature}, timeout={quick_timeout}s"
            )
            logger.info(
                f"🔧 [自定义OpenAI-深度模型] max_tokens={deep_max_tokens}, temperature={deep_temperature}, timeout={deep_timeout}s"
            )

            # 使用OpenAI兼容适配器创建LLM实例
            deep_thinking_llm = create_openai_compatible_llm(
                provider="custom_openai",
                model=config["deep_think_llm"],
                base_url=custom_base_url,
                temperature=deep_temperature,
                max_tokens=deep_max_tokens,
                timeout=deep_timeout,
            )
            quick_thinking_llm = create_openai_compatible_llm(
                provider="custom_openai",
                model=config["quick_think_llm"],
                base_url=custom_base_url,
                temperature=quick_temperature,
                max_tokens=quick_max_tokens,
                timeout=deep_timeout,
            )

            logger.info(f"✅ [自定义OpenAI] 已配置自定义端点并应用用户配置的模型参数")

        elif provider.lower() == "qianfan":
            # 百度千帆（文心一言）配置 - 统一由适配器内部读取与校验 QIANFAN_API_KEY
            from tradingagents.llm_adapters.openai_compatible_base import (
                create_openai_compatible_llm,
            )

            logger.info(
                f"🔧 [千帆-快速模型] max_tokens={quick_max_tokens}, temperature={quick_temperature}, timeout={quick_timeout}s"
            )
            logger.info(
                f"🔧 [千帆-深度模型] max_tokens={deep_max_tokens}, temperature={deep_temperature}, timeout={deep_timeout}s"
            )

            # 使用OpenAI兼容适配器创建LLM实例（基类会使用千帆默认base_url并负责密钥校验）
            deep_thinking_llm = create_openai_compatible_llm(
                provider="qianfan",
                model=config["deep_think_llm"],
                temperature=deep_temperature,
                max_tokens=deep_max_tokens,
                timeout=deep_timeout,
            )
            quick_thinking_llm = create_openai_compatible_llm(
                provider="qianfan",
                model=config["quick_think_llm"],
                temperature=quick_temperature,
                max_tokens=quick_max_tokens,
                timeout=deep_timeout,
            )
            logger.info("✅ [千帆] 文心一言适配器已配置成功并应用用户配置的模型参数")

        elif provider.lower() == "zhipu":
            # 智谱AI GLM配置 - 使用专门的ChatZhipuOpenAI适配器
            from tradingagents.llm_adapters.openai_compatible_base import (
                ChatZhipuOpenAI,
            )

            # 🔥 优先使用数据库配置的 API Key，否则从环境变量读取
            zhipu_api_key = (
                config.get("quick_api_key")
                or config.get("deep_api_key")
                or os.getenv("ZHIPU_API_KEY")
            )
            logger.info(
                f"🔑 [智谱AI] API Key 来源: {'数据库配置' if config.get('quick_api_key') or config.get('deep_api_key') else '环境变量'}"
            )

            if not zhipu_api_key:
                raise ValueError(
                    "使用智谱AI需要在数据库中配置API Key或设置ZHIPU_API_KEY环境变量"
                )

            logger.info(
                f"🔧 [智谱AI-快速模型] max_tokens={quick_max_tokens}, temperature={quick_temperature}, timeout={quick_timeout}s"
            )
            logger.info(
                f"🔧 [智谱AI-深度模型] max_tokens={deep_max_tokens}, temperature={deep_temperature}, timeout={deep_timeout}s"
            )

            # 获取 backend_url（如果配置中有的话）
            backend_url = config.get("backend_url")
            if backend_url:
                logger.info(f"🔧 [智谱AI] 使用配置的 backend_url: {backend_url}")
            else:
                logger.info(f"🔧 [智谱AI] 未配置 backend_url，使用默认端点")

            # 使用专门的ChatZhipuOpenAI适配器创建LLM实例
            deep_thinking_llm = ChatZhipuOpenAI(
                model=config["deep_think_llm"],
                api_key=zhipu_api_key,
                base_url=backend_url,  # 使用用户配置的backend_url
                temperature=deep_temperature,
                max_tokens=deep_max_tokens,
                timeout=deep_timeout,
            )
            quick_thinking_llm = ChatZhipuOpenAI(
                model=config["quick_think_llm"],
                api_key=zhipu_api_key,
                base_url=backend_url,  # 使用用户配置的backend_url
                temperature=quick_temperature,
                max_tokens=quick_max_tokens,
                timeout=deep_timeout,
            )

            logger.info("✅ [智谱AI] 已使用专用适配器配置成功并应用用户配置的模型参数")

        else:
            # 🔧 通用的 OpenAI 兼容厂家支持（用于自定义厂家）
            logger.info(
                f"🔧 使用通用 OpenAI 兼容适配器处理自定义厂家: {provider}"
            )
            from tradingagents.llm_adapters.openai_compatible_base import (
                create_openai_compatible_llm,
            )

            # 获取厂家配置中的 API Key 和 base_url
            provider_name = provider

            # 尝试从环境变量获取 API Key（支持多种命名格式）
            api_key_candidates = [
                f"{provider_name.upper()}_API_KEY",  # 例如: KYX_API_KEY
                f"{provider_name}_API_KEY",  # 例如: kyx_API_KEY
                "CUSTOM_OPENAI_API_KEY",  # 通用环境变量
            ]

            custom_api_key = None
            for env_var in api_key_candidates:
                custom_api_key = os.getenv(env_var)
                if custom_api_key:
                    logger.info(f"✅ 从环境变量 {env_var} 获取到 API Key")
                    break

            if not custom_api_key:
                raise ValueError(
                    f"使用自定义厂家 {provider_name} 需要设置以下环境变量之一:\n"
                    f"  - {provider_name.upper()}_API_KEY\n"
                    f"  - CUSTOM_OPENAI_API_KEY"
                )

            # 获取 backend_url（从配置中获取）
            backend_url = config.get("backend_url")
            if not backend_url:
                raise ValueError(
                    f"使用自定义厂家 {provider_name} 需要在数据库配置中设置 default_base_url"
                )

            logger.info(f"🔧 [自定义厂家 {provider_name}] 使用端点: {backend_url}")

            logger.info(
                f"🔧 [{provider_name}-快速模型] max_tokens={quick_max_tokens}, temperature={quick_temperature}, timeout={quick_timeout}s"
            )
            logger.info(
                f"🔧 [{provider_name}-深度模型] max_tokens={deep_max_tokens}, temperature={deep_temperature}, timeout={deep_timeout}s"
            )

            # 使用 custom_openai 适配器创建 LLM 实例
            deep_thinking_llm = create_openai_compatible_llm(
                provider="custom_openai",
                model=config["deep_think_llm"],
                api_key=custom_api_key,
                base_url=backend_url,
                temperature=deep_temperature,
                max_tokens=deep_max_tokens,
                timeout=deep_timeout,
            )
            quick_thinking_llm = create_openai_compatible_llm(
                provider="custom_openai",
                model=config["quick_think_llm"],
                api_key=custom_api_key,
                base_url=backend_url,
                temperature=quick_temperature,
                max_tokens=quick_max_tokens,
                timeout=deep_timeout,
            )

            logger.info(
                f"✅ [自定义厂家 {provider_name}] 已配置自定义端点并应用用户配置的模型参数"
            )

        return quick_thinking_llm, deep_thinking_llm
