# -*- coding: utf-8 -*-
"""
LLM适配器统一工厂
提供统一的LLM创建接口,减少LLM配置代码重复
"""

from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


class BaseLLMProvider(ABC):
    """LLM Provider基类"""

    @abstractmethod
    def create_llm(
        self,
        model: str,
        api_key: str,
        temperature: float,
        max_tokens: int,
        timeout: int,
        base_url: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        创建LLM实例

        Args:
            model: 模型名称
            api_key: API Key
            temperature: 温度参数
            max_tokens: 最大token数
            timeout: 超时时间
            base_url: 自定义端点
            **kwargs: 其他参数

        Returns:
            LLM实例
        """
        pass

    @abstractmethod
    def validate_config(
        self, model: str, api_key: str, base_url: Optional[str]
    ) -> Dict[str, Any]:
        """
        验证配置

        Args:
            model: 模型名称
            api_key: API Key
            base_url: 自定义端点

        Returns:
            验证结果 {"valid": bool, "errors": list}
        """
        pass

    @abstractmethod
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """
        获取可用模型列表

        Returns:
            模型字典
        """
        pass


class GoogleProvider(BaseLLMProvider):
    """Google AI Provider"""

    def create_llm(
        self,
        model: str,
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: int = 180,
        base_url: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """创建Google AI LLM实例"""
        from tradingagents.llm_adapters.google_openai_adapter import ChatGoogleOpenAI

        # 验证配置
        validation = self.validate_config(model, api_key, base_url)
        if not validation["valid"]:
            raise ValueError(f"Google配置无效: {validation['errors']}")

        return ChatGoogleOpenAI(
            model=model,
            google_api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    def validate_config(
        self, model: str, api_key: str, base_url: Optional[str]
    ) -> Dict[str, Any]:
        """验证Google配置"""
        errors = []

        if not api_key or len(api_key) < 10:
            errors.append("API Key无效或过短")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """获取Google可用模型"""
        from tradingagents.llm_adapters.google_openai_adapter import (
            GOOGLE_OPENAI_MODELS,
        )

        return GOOGLE_OPENAI_MODELS


class DashScopeProvider(BaseLLMProvider):
    """DashScope (阿里百炼) Provider"""

    def create_llm(
        self,
        model: str,
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: int = 180,
        base_url: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """创建DashScope LLM实例"""
        from tradingagents.llm_adapters.dashscope_openai_adapter import (
            ChatDashScopeOpenAI,
        )

        # 验证配置
        validation = self.validate_config(model, api_key, base_url)
        if not validation["valid"]:
            raise ValueError(f"DashScope配置无效: {validation['errors']}")

        return ChatDashScopeOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            request_timeout=timeout,
        )

    def validate_config(
        self, model: str, api_key: str, base_url: Optional[str]
    ) -> Dict[str, Any]:
        """验证DashScope配置"""
        errors = []

        if not api_key or len(api_key) < 10:
            errors.append("API Key无效或过短")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """获取DashScope可用模型"""
        # DashScope模型列表(从文档获取)
        return {
            "qwen-turbo": {
                "description": "Qwen Turbo - 快速模型",
                "context_length": 8192,
                "recommended_for": ["快速响应", "日常对话", "简单分析"],
            },
            "qwen-plus": {
                "description": "Qwen Plus - 增强模型",
                "context_length": 32768,
                "recommended_for": ["复杂分析", "专业任务", "深度思考"],
            },
            "qwen-max": {
                "description": "Qwen Max - 旗舰模型",
                "context_length": 32768,
                "recommended_for": ["复杂推理", "专业分析", "高质量输出"],
            },
        }


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek Provider"""

    def create_llm(
        self,
        model: str,
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: int = 180,
        base_url: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """创建DeepSeek LLM实例"""
        from tradingagents.llm_adapters.deepseek_adapter import ChatDeepSeek

        # 验证配置
        validation = self.validate_config(model, api_key, base_url)
        if not validation["valid"]:
            raise ValueError(f"DeepSeek配置无效: {validation['errors']}")

        return ChatDeepSeek(
            model=model,
            api_key=api_key,
            base_url=base_url or "https://api.deepseek.com",
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    def validate_config(
        self, model: str, api_key: str, base_url: Optional[str]
    ) -> Dict[str, Any]:
        """验证DeepSeek配置"""
        errors = []

        if not api_key or len(api_key) < 10:
            errors.append("API Key无效或过短")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """获取DeepSeek可用模型"""
        return {
            "deepseek-chat": {
                "description": "DeepSeek Chat - 通用对话模型",
                "context_length": 128000,
                "recommended_for": ["通用对话", "代码理解", "简单分析"],
            },
            "deepseek-coder": {
                "description": "DeepSeek Coder - 代码生成模型",
                "context_length": 128000,
                "recommended_for": ["代码生成", "代码审查", "技术文档"],
            },
        }


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (包括兼容端点)"""

    def create_llm(
        self,
        model: str,
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: int = 180,
        base_url: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """创建OpenAI LLM实例"""
        from langchain_openai import ChatOpenAI

        # 验证配置
        validation = self.validate_config(model, api_key, base_url)
        if not validation["valid"]:
            raise ValueError(f"OpenAI配置无效: {validation['errors']}")

        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=tokenperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    def validate_config(
        self, model: str, api_key: str, base_url: Optional[str]
    ) -> Dict[str, Any]:
        """验证OpenAI配置"""
        errors = []

        if not api_key or len(api_key) < 10:
            errors.append("API Key无效或过短")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """获取OpenAI可用模型"""
        return {
            "gpt-4o-mini": {
                "description": "GPT-4o Mini - 快速模型",
                "context_length": 128000,
                "recommended_for": ["快速响应", "日常对话", "简单分析"],
            },
            "gpt-4o": {
                "description": "GPT-4o - 旗舰模型",
                "context_length": 128000,
                "recommended_for": ["复杂分析", "专业任务", "深度推理"],
            },
        }


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Provider"""

    def create_llm(
        self,
        model: str,
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: int = 180,
        base_url: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """创建Anthropic LLM实例"""
        from langchain_anthropic import ChatAnthropic

        # 验证配置
        validation = self.validate_config(model, api_key, base_url)
        if not validation["valid"]:
            raise ValueError(f"Anthropic配置无效: {validation['errors']}")

        return ChatAnthropic(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    def validate_config(
        self, model: str, api_key: str, base_url: Optional[str]
    ) -> Dict[str, Any]:
        """验证Anthropic配置"""
        errors = []

        if not api_key or len(api_key) < 10:
            errors.append("API Key无效或过短")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """获取Anthropic可用模型"""
        return {
            "claude-3-sonnet": {
                "description": "Claude 3 Sonnet - 平衡模型",
                "context_length": 200000,
                "recommended_for": ["复杂分析", "专业任务", "高质量输出"],
            },
            "claude-3-opus": {
                "description": "Claude 3 Opus - 强大模型",
                "context_length": 200000,
                "recommended_for": ["复杂推理", "专业分析", "高级创意"],
            },
        }


class CustomProvider(BaseLLMProvider):
    """自定义Provider(OpenAI兼容端点)"""

    def create_llm(
        self,
        model: str,
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: int = 180,
        base_url: Optional[str] = None,
        provider_name: str = "custom",
        **kwargs,
    ) -> Any:
        """创建自定义LLM实例"""
        from langchain_openai import ChatOpenAI

        # 验证配置
        validation = self.validate_config(model, api_key, base_url)
        if not validation["valid"]:
            raise ValueError(f"自定义Provider配置无效: {validation['errors']}")

        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    def validate_config(
        self, model: str, api_key: str, base_url: Optional[str]
    ) -> Dict[str, Any]:
        """验证自定义Provider配置"""
        errors = []

        if not base_url:
            errors.append("必须提供base_url")

        if not api_key or len(api_key) < 10:
            errors.append("API Key无效或过短")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """获取自定义Provider可用模型"""
        # 返回空字典,需要用户配置
        return {}


class LLMFactory:
    """LLM工厂"""

    def __init__(self):
        """初始化LLM工厂"""
        self._providers: Dict[str, BaseLLMProvider] = {
            "google": GoogleProvider(),
            "dashscope": DashScopeProvider(),
            "alibaba": DashScopeProvider(),  # 阿里百炼
            "deepseek": DeepSeekProvider(),
            "openai": OpenAIProvider(),
            "siliconflow": OpenAIProvider(),
            "openrouter": OpenAIProvider(),
            "ollama": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "zhipu": CustomProvider(),
            "qianfan": CustomProvider(),
            "custom": CustomProvider(),
        }

        logger.info(f"🏭️ [LLM工厂] 已注册的Provider: {list(self._providers.keys())}")

    def register_provider(
        self,
        name: str,
        provider: BaseLLMProvider,
    ):
        """
        注册新的LLM Provider

        Args:
            name: Provider名称
            provider: Provider实例
        """
        self._providers[name] = provider
        logger.info(f"📝 [LLM工厂] 注册Provider: {name}")

    def create_llm(
        self,
        provider_name: str,
        model: str,
        api_key: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: int = 180,
        base_url: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        创建LLM实例

        Args:
            provider_name: Provider名称
            model: 模型名称
            api_key: API Key
            temperature: 温度参数
            max_tokens: 最大token数
            timeout: 超时时间
            base_url: 自定义端点
            **kwargs: 其他参数

        Returns:
            LLM实例

        Raises:
            ValueError: 不支持的Provider或配置无效
        """
        # 标准化provider名称
        provider_name = provider_name.lower()

        # 查找provider
        if provider_name not in self._providers:
            available = ", ".join(self._providers.keys())
            raise ValueError(
                f"不支持的Provider: {provider_name}. 可用Provider: {available}"
            )

        # 获取provider
        provider = self._providers[provider_name]

        logger.info(f"🏭️ [LLM工厂] 创建LLM: Provider={provider_name}, Model={model}")

        # 创建LLM
        llm = provider.create_llm(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            base_url=base_url,
            **kwargs,
        )

        logger.info(f"✅ [LLM工厂] LLM创建成功")

        return llm

    def validate_config(
        self,
        provider_name: str,
        model: str,
        api_key: str,
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        验证配置

        Args:
            provider_name: Provider名称
            model: 模型名称
            api_key: API Key
            base_url: 自定义端点

        Returns:
            验证结果 {"valid": bool, "errors": list, "provider": BaseLLMProvider}
        """
        provider_name = provider_name.lower()

        if provider_name not in self._providers:
            raise ValueError(f"不支持的Provider: {provider_name}")

        provider = self._providers[provider_name]
        validation = provider.validate_config(model, api_key, base_url)

        return {
            "valid": validation["valid"],
            "errors": validation["errors"],
            "provider": provider,
        }

    def get_available_models(self, provider_name: str) -> Dict[str, Dict[str, Any]]:
        """
        获取Provider的可用模型

        Args:
            provider_name: Provider名称

        Returns:
            模型字典
        """
        provider_name = provider_name.lower()

        if provider_name not in self._providers:
            raise ValueError(f"不支持的Provider: {provider_name}")

        return self._providers[provider_name].get_available_models()

    def list_providers(self) -> list[str]:
        """
        列出所有Provider

        Returns:
            Provider名称列表
        """
        return list(self._providers.keys())

    def get_provider_info(self, provider_name: str) -> Dict[str, Any]:
        """
        获取Provider信息

        Args:
            provider_name: Provider名称

        Returns:
            Provider信息字典
        """
        provider_name = provider_name.lower()

        if provider_name not in self._providers:
            raise ValueError(f"不支持的Provider: {provider_name}")

        provider = self._providers[provider_name]

        return {
            "name": provider_name,
            "provider_class": provider.__class__.__name__,
            "available_models": provider.get_available_models(),
        }


# 全局LLM工厂实例
_llm_factory: Optional[LLMFactory] = None


def get_llm_factory() -> LLMFactory:
    """
    获取LLM工厂实例(单例模式)

    Returns:
        LLM工厂实例
    """
    global _llm_factory

    if _llm_factory is None:
        _llm_factory = LLMFactory()

    return _llm_factory


def create_llm_by_factory(
    provider: str,
    model: str,
    api_key: str,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    timeout: int = 180,
    base_url: Optional[str] = None,
    **kwargs,
) -> Any:
    """
    通过工厂创建LLM实例(替代trading_graph.py中的create_llm_by_provider)

    Args:
        provider: Provider名称
        model: 模型名称
        api_key: API Key
        temperature: 温度参数
        max_tokens: 最大token数
        timeout: 超时时间
        base_url: 自定义端点
        **kwargs: 其他参数

    Returns:
        LLM实例
    """
    factory = get_llm_factory()
    return factory.create_llm(
        provider_name=provider,
        model=model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        base_url=base_url,
        **kwargs,
    )


def validate_llm_config(
    provider: str,
    model: str,
    api_key: str,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    验证LLM配置

    Args:
        provider: Provider名称
        model: 模型名称
        api_key: API Key
        base_url: 自定义端点

    Returns:
        验证结果
    """
    factory = get_llm_factory()
    return factory.validate_config(provider, model, api_key, base_url)
