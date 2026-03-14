# -*- coding: utf-8 -*-
"""
智谱AI API适配器
支持GLM-4/GLM-4.5等智谱AI模型，专为中文金融文本分析优化
"""
import os
import sys
from typing import Dict, List, Any, Optional, Union
from loguru import logger
import json
import time


class ZhipuAdapter:
    """智谱AI API适配器"""

    def __init__(self, api_key: str = None):
        """初始化智谱AI客户端"""
        self.api_key = api_key or os.getenv('ZHIPU_API_KEY')

        if not self.api_key:
            raise ValueError("智谱AI API密钥未配置，请设置ZHIPU_API_KEY环境变量")

        try:
            from zai import ZhipuAiClient
            self.client = ZhipuAiClient(api_key=self.api_key)
            logger.info("[ZHIPU] 智谱AI客户端初始化成功")
        except ImportError:
            raise ImportError("zai-sdk未安装，请运行: pip install zai-sdk")
        except Exception as e:
            logger.error(f"[ZHIPU] 智谱AI客户端初始化失败: {e}")
            raise

    def completion(self,
                   model: str,
                   messages: List[Dict[str, str]],
                   max_tokens: int = 4096,
                   temperature: float = 0.6,
                   stream: bool = False,
                   thinking: bool = True,
                   **kwargs) -> Any:
        """
        兼容litellm的completion接口

        Args:
            model: 模型名称 (glm-4, glm-4.5等)
            messages: 对话消息列表
            max_tokens: 最大输出tokens
            temperature: 温度参数
            stream: 是否流式输出
            thinking: 是否启用深度思考模式
            **kwargs: 其他参数
        """
        try:
            # 处理模型名称
            if '/' in model:
                model = model.split('/')[-1]

            # 智谱AI模型映射
            model_mapping = {
                'glm-4': 'glm-4',
                'glm-4.5': 'glm-4.5',
                'glm-4-plus': 'glm-4-plus',
                'glm-4-flash': 'glm-4-flash',
                'zhipu': 'glm-4.5',  # 默认映射
                'zhipu-4': 'glm-4',
                'zhipu-4.5': 'glm-4.5'
            }

            final_model = model_mapping.get(model.lower(), model)
            logger.info(f"[ZHIPU] 使用模型: {final_model} (原始: {model})")

            # 构建请求参数
            request_params = {
                "model": final_model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            # 添加深度思考模式（智谱AI特色功能）
            if thinking and final_model in ['glm-4.5', 'glm-4-plus']:
                request_params["thinking"] = {"type": "enabled"}
                logger.info("[ZHIPU] 启用深度思考模式")

            # 添加其他参数
            if kwargs:
                # 过滤不支持的参数
                supported_params = {
                    'top_p', 'top_k', 'do_sample', 'repetition_penalty',
                    'presence_penalty', 'frequency_penalty', 'stop'
                }
                for key, value in kwargs.items():
                    if key in supported_params:
                        request_params[key] = value

            start_time = time.time()

            if stream:
                # 流式输出支持
                return self._handle_stream_response(request_params, start_time)
            else:
                # 标准输出
                response = self.client.chat.completions.create(**request_params)

                end_time = time.time()
                response_time = end_time - start_time

                # 记录性能指标
                if hasattr(response, 'usage'):
                    usage = response.usage
                    logger.info(f"[ZHIPU] 响应时间: {response_time:.2f}s, "
                              f"输入tokens: {getattr(usage, 'prompt_tokens', 0)}, "
                              f"输出tokens: {getattr(usage, 'completion_tokens', 0)}")

                return response

        except Exception as e:
            logger.error(f"[ZHIPU] API调用失败: {e}")
            logger.error(f"[ZHIPU] 请求参数: {json.dumps(request_params, ensure_ascii=False, indent=2)}")
            raise

    def _handle_stream_response(self, request_params: Dict, start_time: float):
        """处理流式响应"""
        try:
            stream = self.client.chat.completions.create(
                stream=True,
                **request_params
            )

            logger.info("[ZHIPU] 开始流式响应")
            return stream

        except Exception as e:
            logger.error(f"[ZHIPU] 流式响应失败: {e}")
            raise

    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return [
            'glm-4',
            'glm-4.5',
            'glm-4-plus',
            'glm-4-flash',
            'glm-4-0520',
            'glm-4-air',
            'glm-4-airx'
        ]

    def validate_model(self, model: str) -> bool:
        """验证模型是否支持"""
        available_models = self.get_available_models()
        return model in available_models or any(model.endswith(m) for m in available_models)

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """获取模型信息"""
        model_info = {
            'glm-4': {
                'description': '智谱AI GLM-4基础模型',
                'max_tokens': 8192,
                'chinese_optimized': True,
                'financial_trained': True
            },
            'glm-4.5': {
                'description': '智谱AI GLM-4.5增强模型，支持深度思考',
                'max_tokens': 8192,
                'chinese_optimized': True,
                'financial_trained': True,
                'thinking_mode': True
            },
            'glm-4-plus': {
                'description': '智谱AI GLM-4 Plus高级模型',
                'max_tokens': 8192,
                'chinese_optimized': True,
                'financial_trained': True,
                'thinking_mode': True
            },
            'glm-4-flash': {
                'description': '智谱AI GLM-4 Flash快速模型',
                'max_tokens': 4096,
                'chinese_optimized': True,
                'financial_trained': True,
                'fast_response': True
            }
        }

        return model_info.get(model, {
            'description': f'智谱AI {model}模型',
            'max_tokens': 4096,
            'chinese_optimized': True
        })

    def test_connection(self) -> bool:
        """测试API连接"""
        try:
            test_response = self.completion(
                model="glm-4",
                messages=[{"role": "user", "content": "你好"}],
                max_tokens=10,
                temperature=0.1
            )

            if hasattr(test_response, 'choices') and len(test_response.choices) > 0:
                logger.info("[ZHIPU] API连接测试成功")
                return True
            else:
                logger.warning("[ZHIPU] API连接测试响应异常")
                return False

        except Exception as e:
            logger.error(f"[ZHIPU] API连接测试失败: {e}")
            return False


# 创建全局实例（延迟初始化）
_zhipu_adapter = None

def get_zhipu_adapter() -> ZhipuAdapter:
    """获取智谱AI适配器实例（单例模式）"""
    global _zhipu_adapter
    if _zhipu_adapter is None:
        try:
            _zhipu_adapter = ZhipuAdapter()
        except Exception as e:
            logger.error(f"[ZHIPU] 适配器初始化失败: {e}")
            raise
    return _zhipu_adapter


# 兼容性函数（与litellm风格一致）
def zhipu_completion(model: str, messages: List[Dict], **kwargs):
    """智谱AI completion函数（兼容litellm接口）"""
    adapter = get_zhipu_adapter()
    return adapter.completion(model=model, messages=messages, **kwargs)


# 注册到litellm（如果需要）
def register_zhipu_provider():
    """将智谱AI注册为litellm提供商"""
    try:
        import litellm

        # 注册自定义提供商
        litellm.custom_provider_map["zhipu"] = {
            "completion": zhipu_completion,
            "supports_function_calling": False,
            "supports_system_messages": True
        }

        logger.info("[ZHIPU] 已注册为litellm提供商")
        return True

    except ImportError:
        logger.warning("[ZHIPU] litellm未安装，跳过提供商注册")
        return False
    except Exception as e:
        logger.error(f"[ZHIPU] 提供商注册失败: {e}")
        return False


if __name__ == "__main__":
    # 测试代码
    try:
        adapter = ZhipuAdapter()
        print("智谱AI适配器初始化成功")

        # 测试连接
        if adapter.test_connection():
            print("API连接测试通过")
        else:
            print("API连接测试失败")

        # 显示可用模型
        models = adapter.get_available_models()
        print(f"可用模型: {models}")

    except Exception as e:
        print(f"测试失败: {e}")