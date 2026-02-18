# -*- coding: utf-8 -*-
"""
模型目录管理服务

提供模型目录的 CRUD 操作和默认模型数据
"""

import logging
from typing import List, Optional, Dict, Any

from app.utils.timezone import now_tz
from app.models.config import ModelCatalog, ModelInfo
from app.services.crud import BaseCRUDService
from ..base_config_service import BaseConfigService
from .data import get_default_model_catalog

logger = logging.getLogger(__name__)


class ModelCatalogService(BaseConfigService, BaseCRUDService):
    """模型目录管理服务"""

    def __init__(self, db_manager=None):
        BaseConfigService.__init__(self, db_manager)
        BaseCRUDService.__init__(self)

    @property
    def collection_name(self) -> str:
        """MongoDB 集合名称"""
        return "model_catalog"

    async def get_model_catalog(self) -> List[ModelCatalog]:
        """获取所有模型目录"""
        try:
            db = await self._get_db()
            catalog_collection = db.model_catalog

            catalogs = []
            async for doc in catalog_collection.find():
                catalogs.append(ModelCatalog(**doc))

            return catalogs
        except Exception as e:
            print(f"获取模型目录失败: {e}")
            return []

    async def get_provider_models(self, provider: str) -> Optional[ModelCatalog]:
        """获取指定厂家的模型目录"""
        try:
            db = await self._get_db()
            catalog_collection = db.model_catalog

            doc = await catalog_collection.find_one({"provider": provider})
            if doc:
                return ModelCatalog(**doc)
            return None
        except Exception as e:
            print(f"获取厂家模型目录失败: {e}")
            return None

    async def save_model_catalog(self, catalog: ModelCatalog) -> bool:
        """保存或更新模型目录"""
        try:
            db = await self._get_db()
            catalog_collection = db.model_catalog

            catalog.updated_at = now_tz()

            # 更新或插入
            result = await catalog_collection.replace_one(
                {"provider": catalog.provider},
                catalog.model_dump(by_alias=True, exclude={"id"}),
                upsert=True,
            )

            return result.acknowledged
        except Exception as e:
            print(f"保存模型目录失败: {e}")
            return False

    async def delete_model_catalog(self, provider: str) -> bool:
        """删除模型目录"""
        try:
            db = await self._get_db()
            catalog_collection = db.model_catalog

            result = await catalog_collection.delete_one({"provider": provider})
            return result.deleted_count > 0
        except Exception as e:
            print(f"删除模型目录失败: {e}")
            return False

    async def init_default_model_catalog(self) -> bool:
        """初始化默认模型目录"""
        try:
            db = await self._get_db()
            catalog_collection = db.model_catalog

            # 检查是否已有数据
            count = await catalog_collection.count_documents({})
            if count > 0:
                print("模型目录已存在，跳过初始化")
                return True

            # 创建默认目录
            default_catalogs = get_default_model_catalog()

            for catalog_data in default_catalogs:
                catalog = ModelCatalog(**catalog_data)
                await self.save_model_catalog(catalog)

            print(f"✅ 初始化了 {len(default_catalogs)} 个厂家的模型目录")
            return True
        except Exception as e:
            print(f"初始化模型目录失败: {e}")
            return False

    async def get_available_models(self) -> List[Dict[str, Any]]:
        """获取可用的模型列表（从数据库读取，如果为空则返回默认数据）"""
        try:
            catalogs = await self.get_model_catalog()

            # 如果数据库中没有数据，初始化默认目录
            if not catalogs:
                print("📦 模型目录为空，初始化默认目录...")
                await self.init_default_model_catalog()
                catalogs = await self.get_model_catalog()

            # 转换为API响应格式
            result = []
            for catalog in catalogs:
                result.append(
                    {
                        "provider": catalog.provider,
                        "provider_name": catalog.provider_name,
                        "models": [
                            {
                                "name": model.name,
                                "display_name": model.display_name,
                                "description": model.description,
                                "context_length": model.context_length,
                                "input_price_per_1k": model.input_price_per_1k,
                                "output_price_per_1k": model.output_price_per_1k,
                                "is_deprecated": model.is_deprecated,
                            }
                            for model in catalog.models
                        ],
                    }
                )

            return result
        except Exception as e:
            print(f"获取模型列表失败: {e}")
            # 失败时返回默认数据
            return get_default_model_catalog()

    async def fetch_provider_models(self, provider_id: str) -> dict:
        """从厂家 API 获取模型列表"""
        try:
            print(f"🔍 获取厂家模型列表 - provider_id: {provider_id}")

            db = await self._get_db()
            providers_collection = db.llm_providers

            # 兼容处理：尝试 ObjectId 和字符串两种类型
            from bson import ObjectId

            provider_data = None
            try:
                provider_data = await providers_collection.find_one(
                    {"_id": ObjectId(provider_id)}
                )
            except Exception:
                pass

            if not provider_data:
                provider_data = await providers_collection.find_one(
                    {"_id": provider_id}
                )

            if not provider_data:
                return {"success": False, "message": f"厂家不存在 (ID: {provider_id})"}

            provider_name = provider_data.get("name")
            api_key = provider_data.get("api_key")
            base_url = provider_data.get("default_base_url")
            display_name = provider_data.get("display_name", provider_name)

            # 判断数据库中的 API Key 是否有效
            if not self._is_valid_api_key(api_key):
                # 数据库中的 Key 无效，尝试从环境变量读取
                env_api_key = self._get_env_api_key(provider_name)
                if env_api_key:
                    api_key = env_api_key
                    print(
                        f"✅ 数据库配置无效，从环境变量读取到 {display_name} 的 API Key"
                    )
                else:
                    # 某些聚合平台（如 OpenRouter）的 /models 端点不需要 API Key
                    print(f"⚠️ {display_name} 未配置有效的API密钥，尝试无认证访问")
            else:
                print(f"✅ 使用数据库配置的 {display_name} API密钥")

            if not base_url:
                return {
                    "success": False,
                    "message": f"{display_name} 未配置 API 基础地址 (default_base_url)",
                }

            # 调用 OpenAI 兼容的 /v1/models 端点
            import asyncio

            result = await asyncio.get_event_loop().run_in_executor(
                None, self._fetch_models_from_api, api_key, base_url, display_name
            )

            return result

        except Exception as e:
            print(f"获取模型列表失败: {e}")
            import traceback

            traceback.print_exc()
            return {"success": False, "message": f"获取模型列表失败: {str(e)}"}

    def _fetch_models_from_api(
        self, api_key: str, base_url: str, display_name: str
    ) -> dict:
        """从 API 获取模型列表"""
        try:
            import requests
            import re

            # 智能版本号处理：只有在没有版本号的情况下才添加 /v1
            # 避免对已有版本号的URL（如智谱AI的 /v4）重复添加 /v1
            base_url = base_url.rstrip("/")
            if not re.search(r"/v\d+$", base_url):
                # URL末尾没有版本号，添加 /v1（OpenAI标准）
                base_url = base_url + "/v1"
                logger.info(f"   [获取模型列表] 添加 /v1 版本号: {base_url}")
            else:
                # URL已包含版本号（如 /v4），不添加
                logger.info(f"   [获取模型列表] 检测到已有版本号，保持原样: {base_url}")

            url = f"{base_url}/models"

            # 构建请求头
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
                print(f"🔍 请求 URL: {url} (with API Key)")
            else:
                print(f"🔍 请求 URL: {url} (without API Key)")

            response = requests.get(url, headers=headers, timeout=15)

            print(f"📊 响应状态码: {response.status_code}")
            print(f"📊 响应内容: {response.text[:500]}...")

            if response.status_code == 200:
                result = response.json()
                print(f"📊 响应 JSON 结构: {list(result.keys())}")

                if "data" in result and isinstance(result["data"], list):
                    all_models = result["data"]
                    print(f"📊 API 返回 {len(all_models)} 个模型")

                    # 过滤：只保留主流大厂的常用模型
                    filtered_models = self._filter_popular_models(all_models)
                    print(f"✅ 过滤后保留 {len(filtered_models)} 个常用模型")

                    # 转换模型格式，包含价格信息
                    formatted_models = self._format_models_with_pricing(filtered_models)

                    return {
                        "success": True,
                        "models": formatted_models,
                        "message": f"成功获取 {len(formatted_models)} 个常用模型（已过滤）",
                    }
                else:
                    print(f"❌ 响应格式异常，期望 'data' 字段为列表")
                    return {
                        "success": False,
                        "message": f"{display_name} API 响应格式异常（缺少 data 字段或格式不正确）",
                    }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "message": f"{display_name} API密钥无效或已过期",
                }
            elif response.status_code == 403:
                return {"success": False, "message": f"{display_name} API权限不足"}
            else:
                try:
                    error_detail = response.json()
                    error_msg = error_detail.get("error", {}).get(
                        "message", f"HTTP {response.status_code}"
                    )
                    print(f"❌ API 错误: {error_msg}")
                    return {
                        "success": False,
                        "message": f"{display_name} API请求失败: {error_msg}",
                    }
                except:
                    print(f"❌ HTTP 错误: {response.status_code}")
                    return {
                        "success": False,
                        "message": f"{display_name} API请求失败: HTTP {response.status_code}, 响应: {response.text[:200]}",
                    }

        except Exception as e:
            print(f"❌ 异常: {e}")
            import traceback

            traceback.print_exc()
            return {
                "success": False,
                "message": f"{display_name} API请求异常: {str(e)}",
            }

    def _format_models_with_pricing(self, models: list) -> list:
        """
        格式化模型列表，包含价格信息

        支持多种价格格式：
        1. OpenRouter: pricing.prompt/completion (USD per token)
        2. 302.ai: price.prompt/completion 或 price.input/output
        3. 其他: 可能没有价格信息
        """
        formatted = []
        for model in models:
            model_id = model.get("id", "")
            model_name = model.get("name", model_id)

            # 尝试从多个字段获取价格信息
            input_price_per_1k = None
            output_price_per_1k = None

            # 方式1：OpenRouter 格式 (pricing.prompt/completion)
            pricing = model.get("pricing", {})
            if pricing:
                prompt_price = pricing.get("prompt", "0")  # USD per token
                completion_price = pricing.get("completion", "0")  # USD per token

                try:
                    if prompt_price and float(prompt_price) > 0:
                        input_price_per_1k = float(prompt_price) * 1000
                    if completion_price and float(completion_price) > 0:
                        output_price_per_1k = float(completion_price) * 1000
                except (ValueError, TypeError):
                    pass

            # 方式2：302.ai 格式 (price.prompt/completion 或 price.input/output)
            if not input_price_per_1k and not output_price_per_1k:
                price = model.get("price", {})
                if price and isinstance(price, dict):
                    # 尝试 prompt/completion 字段
                    prompt_price = price.get("prompt") or price.get("input")
                    completion_price = price.get("completion") or price.get("output")

                    try:
                        if prompt_price and float(prompt_price) > 0:
                            # 假设是 per token，转换为 per 1K tokens
                            input_price_per_1k = float(prompt_price) * 1000
                        if completion_price and float(completion_price) > 0:
                            output_price_per_1k = float(completion_price) * 1000
                    except (ValueError, TypeError):
                        pass

            # 获取上下文长度
            context_length = model.get("context_length")
            if not context_length:
                # 尝试从 top_provider 获取
                top_provider = model.get("top_provider", {})
                context_length = top_provider.get("context_length")

            # 如果还是没有，尝试从 max_completion_tokens 推断
            if not context_length:
                max_tokens = model.get("max_completion_tokens")
                if max_tokens and max_tokens > 0:
                    # 通常上下文长度是最大输出的 4-8 倍
                    context_length = max_tokens * 4

            formatted_model = {
                "id": model_id,
                "name": model_name,
                "context_length": context_length,
                "input_price_per_1k": input_price_per_1k,
                "output_price_per_1k": output_price_per_1k,
            }

            formatted.append(formatted_model)

            # 打印价格信息（用于调试）
            if input_price_per_1k or output_price_per_1k:
                print(
                    f"💰 {model_id}: 输入=${input_price_per_1k:.6f}/1K, 输出=${output_price_per_1k:.6f}/1K"
                )

        return formatted

    def _filter_popular_models(self, models: list) -> list:
        """过滤模型列表，只保留主流大厂的常用模型"""
        import re

        # 只保留三大厂：OpenAI、Anthropic、Google
        popular_providers = [
            "openai",  # OpenAI
            "anthropic",  # Anthropic
            "google",  # Google
        ]

        # 常见模型名称前缀（用于识别不带厂商前缀的模型）
        model_prefixes = {
            "gpt-": "openai",  # gpt-3.5-turbo, gpt-4, gpt-4o
            "o1-": "openai",  # o1-preview, o1-mini
            "claude-": "anthropic",  # claude-3-opus, claude-3-sonnet
            "gemini-": "google",  # gemini-pro, gemini-1.5-pro
            "gemini": "google",  # gemini (不带连字符)
        }

        # 排除的关键词
        exclude_keywords = [
            "preview",
            "experimental",
            "alpha",
            "beta",
            "free",
            "extended",
            "nitro",
            ":free",
            ":extended",
            "online",  # 排除带在线搜索的版本
            "instruct",  # 排除 instruct 版本
        ]

        # 日期格式正则表达式（匹配 2024-05-13 这种格式）
        date_pattern = re.compile(r"\d{4}-\d{2}-\d{2}")

        filtered = []
        for model in models:
            model_id = model.get("id", "").lower()
            model_name = model.get("name", "").lower()

            # 检查是否属于三大厂
            # 方式1：模型ID中包含厂商名称（如 openai/gpt-4）
            is_popular_provider = any(
                provider in model_id for provider in popular_providers
            )

            # 方式2：模型ID以常见前缀开头（如 gpt-4, claude-3-sonnet）
            if not is_popular_provider:
                for prefix, provider in model_prefixes.items():
                    if model_id.startswith(prefix):
                        is_popular_provider = True
                        print(f"🔍 识别模型前缀: {model_id} -> {provider}")
                        break

            if not is_popular_provider:
                continue

            # 检查是否包含日期（排除带日期的旧版本）
            if date_pattern.search(model_id):
                print(f"⏭️ 跳过带日期的旧版本: {model_id}")
                continue

            # 检查是否包含排除关键词
            has_exclude_keyword = any(
                keyword in model_id or keyword in model_name
                for keyword in exclude_keywords
            )

            if has_exclude_keyword:
                print(f"⏭️ 跳过排除关键词: {model_id}")
                continue

            # 保留该模型
            print(f"✅ 保留模型: {model_id}")
            filtered.append(model)

        return filtered
