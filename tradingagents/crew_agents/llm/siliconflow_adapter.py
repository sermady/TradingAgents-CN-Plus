# -*- coding: utf-8 -*-
"""
SiliconFlow API适配器
由于litellm不直接支持SiliconFlow，需要自定义适配器
"""
import os
import sys
from typing import Dict, List, Any, Optional
from openai import OpenAI
from loguru import logger

class SiliconFlowAdapter:
    """SiliconFlow API适配器"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        """初始化SiliconFlow客户端"""
        self.api_key = api_key or os.getenv('SiliconFlow_API_KEY')
        self.base_url = base_url or os.getenv('SiliconFlow_BASE_URL', 'https://api.siliconflow.cn/v1')
        
        if not self.api_key:
            raise ValueError("SiliconFlow API密钥未配置")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def completion(self, 
                   model: str,
                   messages: List[Dict[str, str]], 
                   max_tokens: int = 1000,
                   temperature: float = 0.7,
                   stream: bool = False,
                   **kwargs) -> Any:
        """
        兼容litellm的completion接口
        """
        try:
            # 移除模型前缀（如果有）
            if '/' in model:
                model = model.split('/')[-1]
            
            # 确保使用正确的模型名
            if 'deepseek' in model.lower() and 'v3' in model.lower():
                model = "deepseek-ai/DeepSeek-V3"
            
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=stream,
                **kwargs
            )
            
            return response
            
        except Exception as e:
            logger.error(f"SiliconFlow API调用失败: {e}")
            raise e
    
    def is_available(self) -> bool:
        """检查SiliconFlow服务是否可用"""
        try:
            response = self.completion(
                model="deepseek-ai/DeepSeek-V3",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            logger.error(f"SiliconFlow服务不可用: {e}")
            return False

# 创建全局实例
try:
    siliconflow_adapter = SiliconFlowAdapter()
    SILICONFLOW_AVAILABLE = True
except Exception:
    siliconflow_adapter = None
    SILICONFLOW_AVAILABLE = False