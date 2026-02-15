# -*- coding: utf-8 -*-
"""模型和提供商查询服务

提取自 simple_analysis_service.py 中的模型查询相关逻辑：
- get_provider_by_model_name
- get_provider_by_model_name_sync
- get_provider_and_url_by_model_sync
- _get_env_api_key_for_provider
- _get_default_backend_url
- _get_default_provider_by_model
- create_analysis_config
"""

import logging
import os
from typing import Dict, Any, Optional

from pymongo import MongoClient

from app.core.config import settings
from app.services.config_service import ConfigService
from app.utils.error_handler import handle_errors, async_handle_errors
from tradingagents.default_config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)

# 配置服务实例
config_service = ConfigService()

# 研究深度配置常量
RESEARCH_DEPTH_CONFIG = {
    "快速": {
        "max_debate_rounds": 1,
        "max_risk_discuss_rounds": 1,
        "memory_enabled": False,
        "online_tools": True,
        "level": 1,
    },
    "基础": {
        "max_debate_rounds": 1,
        "max_risk_discuss_rounds": 1,
        "memory_enabled": True,
        "online_tools": True,
        "level": 2,
    },
    "标准": {
        "max_debate_rounds": 1,
        "max_risk_discuss_rounds": 2,
        "memory_enabled": True,
        "online_tools": True,
        "level": 3,
    },
    "深度": {
        "max_debate_rounds": 2,
        "max_risk_discuss_rounds": 2,
        "memory_enabled": True,
        "online_tools": True,
        "level": 4,
    },
    "全面": {
        "max_debate_rounds": 3,
        "max_risk_discuss_rounds": 3,
        "memory_enabled": True,
        "online_tools": True,
        "level": 5,
    },
}

# 研究深度到辩论轮数的映射
RESEARCH_DEPTH_TO_DEBATE_ROUNDS = {
    "快速": 1,
    "基础": 1,
    "标准": 1,
    "深度": 2,
    "全面": 3,
}


class ModelProviderService:
    """模型和提供商查询服务"""

    # 环境变量到API Key的映射
    ENV_KEY_MAP = {
        "google": "GOOGLE_API_KEY",
        "dashscope": "DASHSCOPE_API_KEY",
        "openai": "OPENAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "siliconflow": "SILICONFLOW_API_KEY",
        "qianfan": "QIANFAN_API_KEY",
        "302ai": "AI302_API_KEY",
    }

    # 默认后端URL映射
    DEFAULT_URLS = {
        "google": "https://generativelanguage.googleapis.com/v1beta",
        "dashscope": "https://dashscope.aliyuncs.com/api/v1",
        "openai": "https://api.openai.com/v1",
        "deepseek": "https://api.deepseek.com",
        "anthropic": "https://api.anthropic.com",
        "openrouter": "https://openrouter.ai/api/v1",
        "qianfan": "https://qianfan.baidubce.com/v2",
        "302ai": "https://api.302.ai/v1",
    }

    # 模型到提供商的默认映射
    MODEL_PROVIDER_MAP = {
        # 阿里百炼 (DashScope)
        "qwen-turbo": "dashscope",
        "qwen-plus": "dashscope",
        "qwen-max": "dashscope",
        "qwen-plus-latest": "dashscope",
        "qwen-max-longcontext": "dashscope",
        # OpenAI
        "gpt-3.5-turbo": "openai",
        "gpt-4": "openai",
        "gpt-4-turbo": "openai",
        "gpt-4o": "openai",
        "gpt-4o-mini": "openai",
        # Google
        "gemini-pro": "google",
        "gemini-2.0-flash": "google",
        "gemini-2.0-flash-thinking-exp": "google",
        # DeepSeek
        "deepseek-chat": "deepseek",
        "deepseek-coder": "deepseek",
        # 智谱AI
        "glm-4": "zhipu",
        "glm-3-turbo": "zhipu",
        "chatglm3-6b": "zhipu",
    }

    @classmethod
    def get_env_api_key(cls, provider: str) -> Optional[str]:
        """从环境变量获取指定供应商的 API Key"""
        env_key_name = cls.ENV_KEY_MAP.get(provider.lower())
        if env_key_name:
            api_key = os.getenv(env_key_name)
            if api_key and api_key.strip() and api_key != "your-api-key":
                return api_key
        return None

    @classmethod
    def get_default_backend_url(cls, provider: str) -> str:
        """根据供应商名称返回默认的 backend_url"""
        url = cls.DEFAULT_URLS.get(
            provider, "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        logger.info(f"🔧 [默认URL] {provider} -> {url}")
        return url

    @classmethod
    def get_default_provider(cls, model_name: str) -> str:
        """根据模型名称返回默认的供应商映射"""
        provider = cls.MODEL_PROVIDER_MAP.get(model_name, "dashscope")
        logger.info(f"🔧 使用默认映射: {model_name} -> {provider}")
        return provider

    @classmethod
    def _query_provider_from_db(cls, model_name: str) -> Optional[Dict[str, Any]]:
        """从数据库查询模型配置"""
        try:
            client = MongoClient(settings.MONGO_URI)
            db = client[settings.MONGO_DB]

            # 查询最新的活跃配置
            configs_collection = db.system_configs
            doc = configs_collection.find_one(
                {"is_active": True}, sort=[("version", -1)]
            )

            if doc and "llm_configs" in doc:
                llm_configs = doc["llm_configs"]

                for config_dict in llm_configs:
                    if config_dict.get("model_name") == model_name:
                        provider = config_dict.get("provider")
                        api_base = config_dict.get("api_base")
                        model_api_key = config_dict.get("api_key")

                        # 从 llm_providers 集合中查找厂家配置
                        providers_collection = db.llm_providers
                        provider_doc = providers_collection.find_one({"name": provider})

                        # 确定 API Key（优先级：模型配置 > 厂家配置 > 环境变量）
                        api_key = None
                        if (
                            model_api_key
                            and model_api_key.strip()
                            and model_api_key != "your-api-key"
                        ):
                            api_key = model_api_key
                            logger.info(f"✅ [同步查询] 使用模型配置的 API Key")
                        elif provider_doc and provider_doc.get("api_key"):
                            provider_api_key = provider_doc["api_key"]
                            if (
                                provider_api_key
                                and provider_api_key.strip()
                                and provider_api_key != "your-api-key"
                            ):
                                api_key = provider_api_key
                                logger.info(f"✅ [同步查询] 使用厂家配置的 API Key")

                        # 如果数据库中没有有效的 API Key，尝试从环境变量获取
                        if not api_key:
                            api_key = cls.get_env_api_key(provider)
                            if api_key:
                                logger.info(f"✅ [同步查询] 使用环境变量的 API Key")

                        # 确定 backend_url
                        backend_url = None
                        if api_base:
                            backend_url = api_base
                            logger.info(
                                f"✅ [同步查询] 模型 {model_name} 使用自定义 API: {api_base}"
                            )
                        elif provider_doc and provider_doc.get("default_base_url"):
                            backend_url = provider_doc["default_base_url"]
                            logger.info(
                                f"✅ [同步查询] 模型 {model_name} 使用厂家默认 API: {backend_url}"
                            )
                        else:
                            backend_url = cls.get_default_backend_url(provider)
                            logger.warning(
                                f"⚠️ [同步查询] 厂家 {provider} 没有配置 default_base_url，使用硬编码默认值"
                            )

                        client.close()
                        return {
                            "provider": provider,
                            "backend_url": backend_url,
                            "api_key": api_key,
                        }

            client.close()
            return None
        except Exception as e:
            logger.error(f"❌ 从数据库查询模型配置失败: {e}")
            return None

    @classmethod
    def _query_provider_fallback(cls, model_name: str) -> Dict[str, Any]:
        """查询失败时的降级处理"""
        provider = cls.get_default_provider(model_name)

        try:
            client = MongoClient(settings.MONGO_URI)
            db = client[settings.MONGO_DB]
            providers_collection = db.llm_providers
            provider_doc = providers_collection.find_one({"name": provider})

            backend_url = cls.get_default_backend_url(provider)
            api_key = None

            if provider_doc:
                if provider_doc.get("default_base_url"):
                    backend_url = provider_doc["default_base_url"]
                    logger.info(
                        f"✅ [同步查询] 使用厂家 {provider} 的 default_base_url: {backend_url}"
                    )

                if provider_doc.get("api_key"):
                    provider_api_key = provider_doc["api_key"]
                    if (
                        provider_api_key
                        and provider_api_key.strip()
                        and provider_api_key != "your-api-key"
                    ):
                        api_key = provider_api_key
                        logger.info(f"✅ [同步查询] 使用厂家 {provider} 的 API Key")

            # 如果厂家配置中没有 API Key，尝试从环境变量获取
            if not api_key:
                api_key = cls.get_env_api_key(provider)
                if api_key:
                    logger.info(f"✅ [同步查询] 使用环境变量的 API Key")

            client.close()
            return {
                "provider": provider,
                "backend_url": backend_url,
                "api_key": api_key,
            }
        except Exception as e:
            logger.warning(f"⚠️ [同步查询] 无法查询厂家配置: {e}")
            return {
                "provider": provider,
                "backend_url": cls.get_default_backend_url(provider),
                "api_key": cls.get_env_api_key(provider),
            }

    @classmethod
    @handle_errors(
        default_return=None, error_message="查找模型供应商失败", log_level="error"
    )
    def get_provider_and_url(cls, model_name: str) -> Dict[str, Any]:
        """根据模型名称从数据库配置中查找对应的供应商和 API URL（同步版本）

        Args:
            model_name: 模型名称，如 'qwen-turbo', 'gpt-4' 等

        Returns:
            dict: {"provider": "google", "backend_url": "https://...", "api_key": "xxx"}
        """
        # 首先尝试从数据库查询
        result = cls._query_provider_from_db(model_name)
        if result:
            return result

        # 如果数据库中没有找到模型配置，使用默认映射
        logger.warning(f"⚠️ [同步查询] 数据库中未找到模型 {model_name}，使用默认映射")
        return cls._query_provider_fallback(model_name)


# 模块级便捷函数


async def get_provider_by_model_name(model_name: str) -> str:
    """根据模型名称从数据库配置中查找对应的供应商（异步版本）"""
    try:
        # 从配置服务获取系统配置
        system_config = await config_service.get_system_config()
        if not system_config or not system_config.llm_configs:
            logger.warning(f"⚠️ 系统配置为空，使用默认供应商映射")
            return ModelProviderService.get_default_provider(model_name)

        # 在LLM配置中查找匹配的模型
        for llm_config in system_config.llm_configs:
            if llm_config.model_name == model_name:
                provider = (
                    llm_config.provider.value
                    if hasattr(llm_config.provider, "value")
                    else str(llm_config.provider)
                )
                logger.info(f"✅ 从数据库找到模型 {model_name} 的供应商: {provider}")
                return provider

        # 如果数据库中没有找到，使用默认映射
        logger.warning(f"⚠️ 数据库中未找到模型 {model_name}，使用默认映射")
        return ModelProviderService.get_default_provider(model_name)

    except Exception as e:
        logger.error(f"❌ 查找模型供应商失败: {e}")
        return ModelProviderService.get_default_provider(model_name)


def get_provider_by_model_name_sync(model_name: str) -> str:
    """根据模型名称从数据库配置中查找对应的供应商（同步版本）"""
    provider_info = get_provider_and_url_by_model_sync(model_name)
    return provider_info["provider"]


def get_provider_and_url_by_model_sync(model_name: str) -> Dict[str, Any]:
    """根据模型名称从数据库配置中查找对应的供应商和 API URL（同步版本）"""
    return ModelProviderService.get_provider_and_url(model_name)


def create_analysis_config(
    research_depth,
    selected_analysts: list,
    quick_model: str,
    deep_model: str,
    llm_provider: str,
    market_type: str = "A股",
    quick_model_config: dict = None,
    deep_model_config: dict = None,
) -> dict:
    """创建分析配置 - 支持数字等级和中文等级

    Args:
        research_depth: 研究深度，支持数字(1-5)或中文("快速", "基础", "标准", "深度", "全面")
        selected_analysts: 选中的分析师列表
        quick_model: 快速分析模型
        deep_model: 深度分析模型
        llm_provider: LLM供应商
        market_type: 市场类型
        quick_model_config: 快速模型的完整配置
        deep_model_config: 深度模型的完整配置

    Returns:
        dict: 完整的分析配置
    """
    # 数字等级到中文等级的映射
    numeric_to_chinese = {1: "快速", 2: "基础", 3: "标准", 4: "深度", 5: "全面"}

    # 标准化研究深度
    research_depth = _normalize_research_depth(research_depth, numeric_to_chinese)

    # 从DEFAULT_CONFIG开始
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = llm_provider
    config["deep_think_llm"] = deep_model
    config["quick_think_llm"] = quick_model

    # 根据研究深度调整配置
    depth_config = RESEARCH_DEPTH_CONFIG.get(research_depth)
    if depth_config:
        config["max_debate_rounds"] = depth_config["max_debate_rounds"]
        config["max_risk_discuss_rounds"] = depth_config["max_risk_discuss_rounds"]
        config["memory_enabled"] = depth_config["memory_enabled"]
        config["online_tools"] = depth_config["online_tools"]
        level = depth_config["level"]
        level_names = {1: "快速", 2: "基础", 3: "标准", 4: "深度", 5: "全面"}
        level_name = level_names.get(level, "标准")
        logger.info(f"🔧 [{level}级-{level_name}分析] {market_type}使用配置")
        logger.info(
            f"🔧 [{level}级-{level_name}分析] 使用用户配置的模型: quick={quick_model}, deep={deep_model}"
        )
    else:
        logger.warning(f"⚠️ 未知的研究深度: {research_depth}，使用标准分析")
        config["max_debate_rounds"] = 1
        config["max_risk_discuss_rounds"] = 2
        config["memory_enabled"] = True
        config["online_tools"] = True

    # 获取 backend_url 和 API Key
    try:
        quick_provider_info = (
            ModelProviderService.get_provider_and_url(quick_model) or {}
        )
        deep_provider_info = ModelProviderService.get_provider_and_url(deep_model) or {}

        config["backend_url"] = quick_provider_info.get("backend_url", "")
        config["quick_api_key"] = quick_provider_info.get("api_key")
        config["deep_api_key"] = deep_provider_info.get("api_key")

        logger.info(f"✅ 使用数据库配置的 backend_url: {config['backend_url']}")
        logger.info(
            f"🔑 快速模型 API Key: {'已配置' if config['quick_api_key'] else '未配置（将使用环境变量）'}"
        )
        logger.info(
            f"🔑 深度模型 API Key: {'已配置' if config['deep_api_key'] else '未配置（将使用环境变量）'}"
        )
    except Exception as e:
        logger.warning(f"⚠️ 无法从数据库获取 backend_url 和 API Key: {e}")
        _set_fallback_backend_url(config, llm_provider)

    # 添加分析师配置
    config["selected_analysts"] = selected_analysts
    config["debug"] = False
    config["research_depth"] = research_depth

    # 添加模型配置参数
    if quick_model_config:
        config["quick_model_config"] = quick_model_config
        logger.info(
            f"🔧 [快速模型配置] max_tokens={quick_model_config.get('max_tokens')}, "
            f"temperature={quick_model_config.get('temperature')}"
        )

    if deep_model_config:
        config["deep_model_config"] = deep_model_config
        logger.info(
            f"🔧 [深度模型配置] max_tokens={deep_model_config.get('max_tokens')}, "
            f"temperature={deep_model_config.get('temperature')}"
        )

    logger.info(f"📋 ========== 创建分析配置完成 ==========")
    logger.info(f"   🎯 研究深度: {research_depth}")
    logger.info(f"   🔥 辩论轮次: {config['max_debate_rounds']}")
    logger.info(f"   ⚖️ 风险讨论轮次: {config['max_risk_discuss_rounds']}")
    logger.info(f"   💾 记忆功能: {config['memory_enabled']}")
    logger.info(f"   🌐 在线工具: {config['online_tools']}")
    logger.info(f"   🤖 LLM供应商: {llm_provider}")
    logger.info(f"   ⚡ 快速模型: {config['quick_think_llm']}")
    logger.info(f"   🧠 深度模型: {config['deep_think_llm']}")
    logger.info(f"📋 ========================================")

    return config


def _normalize_research_depth(research_depth, numeric_to_chinese: dict) -> str:
    """标准化研究深度参数"""
    # 处理数字输入
    if isinstance(research_depth, (int, float)):
        research_depth = int(research_depth)
        if research_depth in numeric_to_chinese:
            chinese_depth = numeric_to_chinese[research_depth]
            logger.info(
                f"🔢 [等级转换] 数字等级 {research_depth} → 中文等级 '{chinese_depth}'"
            )
            return chinese_depth
        else:
            logger.warning(f"⚠️ 无效的数字等级: {research_depth}，使用默认标准分析")
            return "标准"

    # 处理字符串输入
    elif isinstance(research_depth, str):
        if research_depth.isdigit():
            numeric_level = int(research_depth)
            if numeric_level in numeric_to_chinese:
                chinese_depth = numeric_to_chinese[numeric_level]
                logger.info(
                    f"🔢 [等级转换] 字符串数字 '{research_depth}' → 中文等级 '{chinese_depth}'"
                )
                return chinese_depth
            else:
                logger.warning(
                    f"⚠️ 无效的字符串数字等级: {research_depth}，使用默认标准分析"
                )
                return "标准"
        elif research_depth in ["快速", "基础", "标准", "深度", "全面"]:
            logger.info(f"📝 [等级确认] 使用中文等级: '{research_depth}'")
            return research_depth
        else:
            logger.warning(f"⚠️ 未知的研究深度: {research_depth}，使用默认标准分析")
            return "标准"
    else:
        logger.warning(
            f"⚠️ 无效的研究深度类型: {type(research_depth)}，使用默认标准分析"
        )
        return "标准"


def _set_fallback_backend_url(config: dict, llm_provider: str):
    """设置回退的 backend_url"""
    fallback_urls = {
        "dashscope": "https://dashscope.aliyuncs.com/api/v1",
        "deepseek": "https://api.deepseek.com",
        "openai": "https://api.openai.com/v1",
        "google": "https://generativelanguage.googleapis.com/v1beta",
        "qianfan": "https://aip.baidubce.com",
    }

    if llm_provider in fallback_urls:
        config["backend_url"] = fallback_urls[llm_provider]
    else:
        # 尝试从数据库获取
        try:
            client = MongoClient(settings.MONGO_URI)
            db = client[settings.MONGO_DB]
            providers_collection = db.llm_providers
            provider_doc = providers_collection.find_one({"name": llm_provider})

            if provider_doc and provider_doc.get("default_base_url"):
                config["backend_url"] = provider_doc["default_base_url"]
                logger.info(
                    f"✅ 从数据库获取自定义厂家 {llm_provider} 的 backend_url: {config['backend_url']}"
                )
            else:
                config["backend_url"] = "https://api.openai.com/v1"
                logger.warning(
                    f"⚠️ 数据库中未找到厂家 {llm_provider} 的配置，使用默认 OpenAI 端点"
                )

            client.close()
        except Exception as e:
            logger.error(f"❌ 查询数据库失败: {e}，使用默认 OpenAI 端点")
            config["backend_url"] = "https://api.openai.com/v1"

    logger.info(f"⚠️ 使用回退的 backend_url: {config['backend_url']}")
