# -*- coding: utf-8 -*-
"""通用 API 测试框架

用于替代 config_service.py 中重复的 API 测试方法，提供统一的测试接口。
"""

from dataclasses import dataclass, field
from typing import Callable, Optional, Any, Dict, List
import requests
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class APITestConfig:
    """API 测试配置

    Attributes:
        url: API 请求地址
        headers: 请求头
        data: 请求体数据
        timeout: 超时时间（秒）
        success_field: 判断成功的字段名
        content_extractor: 自定义内容提取函数
        error_extractor: 自定义错误信息提取函数
        display_name: 显示名称（用于错误信息）
        provider_name: 提供商名称（用于特殊处理）
    """
    url: str
    headers: dict
    data: dict
    timeout: int = 10
    success_field: str = "choices"
    content_extractor: Optional[Callable[[dict], Optional[str]]] = None
    error_extractor: Optional[Callable[[dict], str]] = None
    display_name: str = "API"
    provider_name: Optional[str] = None


@dataclass
class APIResponse:
    """API 响应结果"""
    success: bool
    message: str
    raw_response: Optional[dict] = None
    status_code: Optional[int] = None


class APITester:
    """通用 API 测试器

    提供统一的 API 测试接口，支持自定义配置和响应处理。
    """

    def __init__(self, config: APITestConfig):
        self.config = config

    def test(self) -> APIResponse:
        """执行 API 测试

        Returns:
            APIResponse: 包含测试结果的对象
        """
        try:
            response = requests.post(
                self.config.url,
                json=self.config.data,
                headers=self.config.headers,
                timeout=self.config.timeout
            )

            # 保存状态码
            status_code = response.status_code

            # 处理 HTTP 错误状态码
            if status_code != 200:
                return self._handle_error_response(response, status_code)

            # 解析响应
            try:
                result = response.json()
            except Exception as e:
                return APIResponse(
                    success=False,
                    message=f"{self.config.display_name} API响应解析失败: {str(e)}",
                    status_code=status_code
                )

            # 使用自定义内容提取器或默认提取逻辑
            if self.config.content_extractor:
                content = self.config.content_extractor(result)
            else:
                content = self._default_content_extractor(result)

            if content and len(str(content).strip()) > 0:
                return APIResponse(
                    success=True,
                    message=f"{self.config.display_name} API连接测试成功",
                    raw_response=result,
                    status_code=status_code
                )
            else:
                return APIResponse(
                    success=False,
                    message=f"{self.config.display_name} API响应为空",
                    raw_response=result,
                    status_code=status_code
                )

        except requests.exceptions.Timeout:
            return APIResponse(
                success=False,
                message=f"{self.config.display_name} API请求超时"
            )
        except requests.exceptions.ConnectionError:
            return APIResponse(
                success=False,
                message=f"{self.config.display_name} API连接失败，请检查网络"
            )
        except Exception as e:
            return APIResponse(
                success=False,
                message=f"{self.config.display_name} API测试异常: {str(e)}"
            )

    def _default_content_extractor(self, result: dict) -> Optional[str]:
        """默认内容提取逻辑"""
        if self.config.success_field == "choices":
            # OpenAI 兼容格式
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"]
            return None
        elif self.config.success_field == "content":
            # Anthropic 格式
            if "content" in result and len(result["content"]) > 0:
                return result["content"][0].get("text", "")
            return None
        elif self.config.success_field == "candidates":
            # Google AI 格式
            if "candidates" in result and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if len(parts) > 0:
                        return parts[0].get("text", "")
            return None
        return None

    def _handle_error_response(self, response, status_code: int) -> APIResponse:
        """处理错误响应"""
        display_name = self.config.display_name

        # 使用自定义错误提取器
        if self.config.error_extractor:
            try:
                error_msg = self.config.error_extractor(response.json())
                return APIResponse(
                    success=False,
                    message=f"{display_name} API测试失败: {error_msg}",
                    status_code=status_code
                )
            except:
                pass

        # 标准 HTTP 状态码处理
        if status_code == 401:
            return APIResponse(
                success=False,
                message=f"{display_name} API密钥无效或已过期",
                status_code=status_code
            )
        elif status_code == 403:
            return APIResponse(
                success=False,
                message=f"{display_name} API权限不足或配额已用完",
                status_code=status_code
            )
        elif status_code == 400:
            try:
                error_detail = response.json()
                error_msg = error_detail.get("error", {}).get("message", "请求格式错误")
                return APIResponse(
                    success=False,
                    message=f"{display_name} API请求错误: {error_msg}",
                    status_code=status_code
                )
            except:
                return APIResponse(
                    success=False,
                    message=f"{display_name} API请求格式错误",
                    status_code=status_code
                )
        elif status_code == 503:
            try:
                error_detail = response.json()
                error_code = error_detail.get("code", "")
                error_msg = error_detail.get("message", "服务暂时不可用")

                if error_code == "NO_KEYS_AVAILABLE":
                    return APIResponse(
                        success=False,
                        message=f"{display_name} 中转服务暂时无可用密钥，请稍后重试或联系中转服务提供商",
                        status_code=status_code
                    )
                else:
                    return APIResponse(
                        success=False,
                        message=f"{display_name} 服务暂时不可用: {error_msg}",
                        status_code=status_code
                    )
            except:
                return APIResponse(
                    success=False,
                    message=f"{display_name} 服务暂时不可用 (HTTP 503)",
                    status_code=status_code
                )
        else:
            try:
                error_detail = response.json()
                error_msg = error_detail.get("error", {}).get("message", f"HTTP {status_code}")
                return APIResponse(
                    success=False,
                    message=f"{display_name} API测试失败: {error_msg}",
                    status_code=status_code
                )
            except:
                return APIResponse(
                    success=False,
                    message=f"{display_name} API测试失败: HTTP {status_code}",
                    status_code=status_code
                )


class LLMAPITester:
    """LLM 提供商 API 测试器

    提供针对各 LLM 提供商的预配置测试方法。
    """

    # 预定义的提供商配置
    PROVIDER_CONFIGS: Dict[str, Dict[str, Any]] = {
        "openai": {
            "url": "https://api.openai.com/v1/chat/completions",
            "default_model": "gpt-3.5-turbo",
            "success_field": "choices",
            "timeout": 10,
        },
        "deepseek": {
            "url": "https://api.deepseek.com/chat/completions",
            "default_model": "deepseek-chat",
            "success_field": "choices",
            "timeout": 10,
        },
        "dashscope": {
            "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            "default_model": "qwen-turbo",
            "success_field": "choices",
            "timeout": 10,
        },
        "openrouter": {
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "default_model": "meta-llama/llama-3.2-3b-instruct:free",
            "success_field": "choices",
            "timeout": 15,
            "extra_headers": {
                "HTTP-Referer": "https://tradingagents.cn",
                "X-Title": "TradingAgents-CN",
            },
        },
        "anthropic": {
            "url": "https://api.anthropic.com/v1/messages",
            "default_model": "claude-3-haiku-20240307",
            "success_field": "content",
            "timeout": 10,
            "header_format": "anthropic",  # 特殊头部格式
        },
        "qianfan": {
            "url": "https://qianfan.baidubce.com/v2/chat/completions",
            "default_model": "ernie-3.5-8k",
            "success_field": "choices",
            "timeout": 15,
        },
        "google": {
            "url_template": "{base_url}/models/{model}:generateContent?key={api_key}",
            "default_model": "gemini-2.0-flash-exp",
            "default_base_url": "https://generativelanguage.googleapis.com/v1beta",
            "success_field": "candidates",
            "timeout": 15,
            "request_format": "google",  # 特殊请求格式
        },
    }

    # 提供商特定的测试模型映射
    PROVIDER_TEST_MODELS: Dict[str, Dict[str, str]] = {
        "siliconflow": {"default": "Qwen/Qwen2.5-7B-Instruct"},
        "zhipu": {"default": "glm-4"},
    }

    @classmethod
    def test_provider(
        cls,
        provider: str,
        api_key: str,
        display_name: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs
    ) -> dict:
        """测试指定提供商的 API

        Args:
            provider: 提供商标识（如 openai, deepseek 等）
            api_key: API 密钥
            display_name: 显示名称（可选）
            model_name: 模型名称（可选，使用默认模型）
            **kwargs: 额外参数（如 base_url）

        Returns:
            dict: {"success": bool, "message": str}
        """
        display_name = display_name or provider.upper()

        if provider not in cls.PROVIDER_CONFIGS:
            return {
                "success": False,
                "message": f"不支持的提供商: {provider}",
            }

        config = cls.PROVIDER_CONFIGS[provider]

        # 确定模型名称
        if not model_name:
            model_name = config.get("default_model", "gpt-3.5-turbo")
            logger.info(f"⚠️ 未指定模型，使用默认模型: {model_name}")

        logger.info(f"🔍 [{display_name} 测试] 使用模型: {model_name}")

        # 构建请求配置
        if config.get("request_format") == "google":
            return cls._test_google_api(api_key, display_name, model_name, kwargs.get("base_url"), config)

        # 标准 OpenAI 兼容格式
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        # 特殊头部格式（如 Anthropic）
        if config.get("header_format") == "anthropic":
            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            }

        # 添加额外头部（如 OpenRouter）
        if "extra_headers" in config:
            headers.update(config["extra_headers"])

        # 构建请求数据
        if config.get("header_format") == "anthropic":
            # Anthropic 格式
            data = {
                "model": model_name,
                "max_tokens": 50,
                "messages": [
                    {"role": "user", "content": "你好，请简单介绍一下你自己。"}
                ],
            }
        else:
            # 标准 OpenAI 兼容格式
            data = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": "你好，请简单介绍一下你自己。"}
                ],
                "max_tokens": 50,
                "temperature": 0.1,
            }

        # 创建测试配置
        test_config = APITestConfig(
            url=config["url"],
            headers=headers,
            data=data,
            timeout=config.get("timeout", 10),
            success_field=config.get("success_field", "choices"),
            display_name=display_name,
            provider_name=provider,
        )

        # 执行测试
        tester = APITester(test_config)
        result = tester.test()

        return {"success": result.success, "message": result.message}

    @classmethod
    def _test_google_api(
        cls,
        api_key: str,
        display_name: str,
        model_name: str,
        base_url: Optional[str],
        config: Dict[str, Any]
    ) -> dict:
        """测试 Google AI API（特殊处理）"""
        try:
            logger.info(f"🔍 [Google AI 测试] 开始测试")
            logger.info(f"   display_name: {display_name}")
            logger.info(f"   model_name: {model_name}")
            logger.info(f"   api_key 长度: {len(api_key) if api_key else 0}")

            # 使用配置的 base_url 或默认值
            if not base_url:
                base_url = config.get("default_base_url", "https://generativelanguage.googleapis.com/v1beta")
                logger.info(f"   ⚠️ base_url 为空，使用默认值: {base_url}")

            # 移除末尾的斜杠
            base_url = base_url.rstrip("/")
            logger.info(f"   base_url (去除斜杠): {base_url}")

            # 如果 base_url 以 /v1 结尾，替换为 /v1beta
            if base_url.endswith("/v1"):
                base_url = base_url[:-3] + "/v1beta"
                logger.info(f"   ✅ 将 /v1 替换为 /v1beta: {base_url}")

            # 构建完整的 API 端点
            url = f"{base_url}/models/{model_name}:generateContent?key={api_key}"
            logger.info(f"🔗 [Google AI 测试] 最终请求 URL: {url.replace(api_key, '***')}")

            headers = {"Content-Type": "application/json"}

            data = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": "Hello, please respond with 'OK' if you can read this."
                            }
                        ]
                    }
                ],
                "generationConfig": {"maxOutputTokens": 2000, "temperature": 0.1},
            }

            response = requests.post(url, json=data, headers=headers, timeout=config.get("timeout", 15))
            status_code = response.status_code

            print(f"📥 [Google AI 测试] 响应状态码: {status_code}")

            if status_code == 200:
                result = response.json()
                print(f"📥 [Google AI 测试] 响应内容（前1000字符）: {response.text[:1000]}")
                print(f"📥 [Google AI 测试] 解析后的 JSON 结构:")
                print(f"   - 顶层键: {list(result.keys())}")
                print(f"   - 是否包含 'candidates': {'candidates' in result}")

                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    print(f"📥 [Google AI 测试] candidate 结构: {candidate}")

                    finish_reason = candidate.get("finishReason", "")
                    print(f"📥 [Google AI 测试] finishReason: {finish_reason}")

                    if "content" in candidate:
                        content = candidate["content"]

                        if "parts" in content and len(content["parts"]) > 0:
                            text = content["parts"][0].get("text", "")
                            print(f"📥 [Google AI 测试] 提取的文本: {text}")

                            if text and len(text.strip()) > 0:
                                return {
                                    "success": True,
                                    "message": f"{display_name} API连接测试成功",
                                }
                            else:
                                print(f"❌ [Google AI 测试] 文本为空")
                                return {
                                    "success": False,
                                    "message": f"{display_name} API响应内容为空",
                                }
                        else:
                            print(f"❌ [Google AI 测试] content 中没有 parts")
                            print(f"   content 的键: {list(content.keys())}")

                            if finish_reason == "MAX_TOKENS":
                                return {
                                    "success": False,
                                    "message": f"{display_name} API响应被截断（MAX_TOKENS），请增加 maxOutputTokens 配置",
                                }
                            else:
                                return {
                                    "success": False,
                                    "message": f"{display_name} API响应格式异常（缺少 parts，finishReason: {finish_reason}）",
                                }
                    else:
                        print(f"❌ [Google AI 测试] candidate 中缺少 'content'")
                        print(f"   candidate 的键: {list(candidate.keys())}")
                        return {
                            "success": False,
                            "message": f"{display_name} API响应格式异常（缺少 content）",
                        }
                else:
                    print(f"❌ [Google AI 测试] 缺少 candidates 或 candidates 为空")
                    return {
                        "success": False,
                        "message": f"{display_name} API无有效候选响应",
                    }
            elif status_code == 400:
                print(f"❌ [Google AI 测试] 400 错误，响应内容: {response.text[:500]}")
                try:
                    error_detail = response.json()
                    error_msg = error_detail.get("error", {}).get("message", "未知错误")
                    return {
                        "success": False,
                        "message": f"{display_name} API请求错误: {error_msg}",
                    }
                except:
                    return {
                        "success": False,
                        "message": f"{display_name} API请求格式错误",
                    }
            elif status_code == 403:
                print(f"❌ [Google AI 测试] 403 错误，响应内容: {response.text[:500]}")
                return {
                    "success": False,
                    "message": f"{display_name} API密钥无效或权限不足",
                }
            elif status_code == 503:
                print(f"❌ [Google AI 测试] 503 错误，响应内容: {response.text[:500]}")
                try:
                    error_detail = response.json()
                    error_code = error_detail.get("code", "")
                    error_msg = error_detail.get("message", "服务暂时不可用")

                    if error_code == "NO_KEYS_AVAILABLE":
                        return {
                            "success": False,
                            "message": f"{display_name} 中转服务暂时无可用密钥，请稍后重试或联系中转服务提供商",
                        }
                    else:
                        return {
                            "success": False,
                            "message": f"{display_name} 服务暂时不可用: {error_msg}",
                        }
                except:
                    return {
                        "success": False,
                        "message": f"{display_name} 服务暂时不可用 (HTTP 503)",
                    }
            else:
                print(f"❌ [Google AI 测试] {status_code} 错误，响应内容: {response.text[:500]}")
                return {
                    "success": False,
                    "message": f"{display_name} API测试失败: HTTP {status_code}",
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"{display_name} API测试异常: {str(e)}",
            }

    @classmethod
    def test_openai_compatible(
        cls,
        api_key: str,
        display_name: str,
        base_url: str,
        provider_name: Optional[str] = None,
        model: Optional[str] = None
    ) -> dict:
        """测试 OpenAI 兼容 API

        用于聚合渠道和自定义厂家的 API 测试。

        Args:
            api_key: API 密钥
            display_name: 显示名称
            base_url: API 基础地址
            provider_name: 提供商名称（用于选择特定测试模型）
            model: 指定测试模型（可选）

        Returns:
            dict: {"success": bool, "message": str}
        """
        try:
            if not base_url:
                return {
                    "success": False,
                    "message": f"{display_name} 未配置 API 基础地址 (default_base_url)",
                }

            # 智能版本号处理
            logger.info(f"   [测试API] 原始 base_url: {base_url}")
            base_url = base_url.rstrip("/")
            logger.info(f"   [测试API] 去除斜杠后: {base_url}")

            if not re.search(r"/v\d+$", base_url):
                base_url = base_url + "/v1"
                logger.info(f"   [测试API] 添加 /v1 版本号: {base_url}")
            else:
                logger.info(f"   [测试API] 检测到已有版本号，保持原样: {base_url}")

            url = f"{base_url}/chat/completions"
            logger.info(f"   [测试API] 最终请求URL: {url}")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }

            # 确定测试模型
            test_model = model or "gpt-3.5-turbo"
            if not model and provider_name:
                provider_models = cls.PROVIDER_TEST_MODELS.get(provider_name, {})
                test_model = provider_models.get("default", "gpt-3.5-turbo")
                logger.info(f"🔍 {display_name}使用测试模型: {test_model}")

            data = {
                "model": test_model,
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello, please respond with 'OK' if you can read this.",
                    }
                ],
                "max_tokens": 200,
                "temperature": 0.1,
            }

            test_config = APITestConfig(
                url=url,
                headers=headers,
                data=data,
                timeout=15,
                success_field="choices",
                display_name=display_name,
                provider_name=provider_name,
            )

            tester = APITester(test_config)
            result = tester.test()

            return {"success": result.success, "message": result.message}

        except Exception as e:
            return {
                "success": False,
                "message": f"{display_name} API测试异常: {str(e)}",
            }


# 便捷函数
def test_llm_api(
    provider: str,
    api_key: str,
    display_name: Optional[str] = None,
    model_name: Optional[str] = None,
    **kwargs
) -> dict:
    """便捷函数：测试 LLM API

    Args:
        provider: 提供商标识
        api_key: API 密钥
        display_name: 显示名称
        model_name: 模型名称
        **kwargs: 额外参数

    Returns:
        dict: 测试结果
    """
    return LLMAPITester.test_provider(provider, api_key, display_name, model_name, **kwargs)


def test_openai_compatible_api(
    api_key: str,
    display_name: str,
    base_url: str,
    provider_name: Optional[str] = None,
    model: Optional[str] = None
) -> dict:
    """便捷函数：测试 OpenAI 兼容 API

    Args:
        api_key: API 密钥
        display_name: 显示名称
        base_url: API 基础地址
        provider_name: 提供商名称
        model: 指定测试模型

    Returns:
        dict: 测试结果
    """
    return LLMAPITester.test_openai_compatible(api_key, display_name, base_url, provider_name, model)
