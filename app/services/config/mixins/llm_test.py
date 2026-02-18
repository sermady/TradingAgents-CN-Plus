# -*- coding: utf-8 -*-
"""LLM配置测试混入类

提供大模型配置的测试功能
"""

import time
import logging
from typing import Dict, Any

from app.utils.api_tester import LLMAPITester

logger = logging.getLogger(__name__)


class LLMTestMixin:
    """LLM配置测试混入类"""

    async def test_llm_config(self, llm_config) -> Dict[str, Any]:
        """测试大模型配置 - 真实调用API进行验证"""
        start_time = time.time()
        try:
            import requests

            # 获取 provider 字符串值（兼容枚举和字符串）
            provider_str = (
                llm_config.provider.value
                if hasattr(llm_config.provider, "value")
                else str(llm_config.provider)
            )

            logger.info(f"🧪 测试大模型配置: {provider_str} - {llm_config.model_name}")
            logger.info(f"📍 API基础URL (模型配置): {llm_config.api_base}")

            # 获取厂家配置（用于获取 API Key 和 default_base_url）
            db = await self._get_db()
            providers_collection = db.llm_providers
            provider_data = await providers_collection.find_one({"name": provider_str})

            # 1. 确定 API 基础 URL
            api_base = llm_config.api_base
            if not api_base:
                # 如果模型配置没有 api_base，从厂家配置获取 default_base_url
                if provider_data and provider_data.get("default_base_url"):
                    api_base = provider_data["default_base_url"]
                    logger.info(f"✅ 从厂家配置获取 API 基础 URL: {api_base}")
                else:
                    return {
                        "success": False,
                        "message": f"模型配置和厂家配置都未设置 API 基础 URL",
                        "response_time": time.time() - start_time,
                        "details": None,
                    }

            # 2. 验证 API Key
            api_key = None
            if llm_config.api_key:
                api_key = llm_config.api_key
            else:
                # 从厂家配置获取 API Key
                if provider_data and provider_data.get("api_key"):
                    api_key = provider_data["api_key"]
                    logger.info(f"✅ 从厂家配置获取到API密钥")
                else:
                    # 尝试从环境变量获取
                    api_key = self._llm_service._get_env_api_key(provider_str)
                    if api_key:
                        logger.info(f"✅ 从环境变量获取到API密钥")

            if not api_key or not self._llm_service._is_valid_api_key(api_key):
                return {
                    "success": False,
                    "message": f"{provider_str} 未配置有效的API密钥",
                    "response_time": time.time() - start_time,
                    "details": None,
                }

            # 3. 根据厂家类型选择测试方法
            # 使用 LLMAPITester 统一测试框架
            logger.info(f"🔍 使用 LLMAPITester 测试框架")

            # 对于 OpenAI 兼容的厂家，使用 test_openai_compatible
            openai_compatible_providers = [
                "openai", "anthropic", "qianfan", "zhipu", "siliconflow",
                "openrouter", "302ai", "oneapi", "newapi", "custom_aggregator"
            ]
            if provider_str in openai_compatible_providers:
                result = LLMAPITester.test_openai_compatible(
                    api_key=api_key,
                    display_name=f"{provider_str} {llm_config.model_name}",
                    base_url=api_base,
                    provider_name=provider_str,
                    model=llm_config.model_name,
                )
            else:
                # 其他厂家使用标准测试
                result = LLMAPITester.test_provider(
                    provider=provider_str,
                    api_key=api_key,
                    display_name=f"{provider_str} {llm_config.model_name}",
                    model_name=llm_config.model_name,
                    base_url=api_base if provider_str == "google" else None,
                )

            result["response_time"] = time.time() - start_time

            # 添加详细信息到成功的响应
            if result.get("success"):
                result["details"] = {
                    "provider": provider_str,
                    "model": llm_config.model_name,
                    "api_base": api_base,
                    "response_preview": result.get("message", "")[:100],
                }

            return result

        except requests.exceptions.Timeout:
            response_time = time.time() - start_time
            return {
                "success": False,
                "message": "连接超时，请检查API基础URL是否正确或网络是否可达",
                "response_time": response_time,
                "details": None,
            }
        except requests.exceptions.ConnectionError as e:
            response_time = time.time() - start_time
            return {
                "success": False,
                "message": f"连接失败，请检查API基础URL是否正确: {str(e)}",
                "response_time": response_time,
                "details": None,
            }
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"❌ 测试大模型配置失败: {e}")
            return {
                "success": False,
                "message": f"连接失败: {str(e)}",
                "response_time": response_time,
                "details": None,
            }
