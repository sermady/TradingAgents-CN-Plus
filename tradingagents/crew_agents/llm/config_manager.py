# -*- coding: utf-8 -*-
"""
LLM配置管理器
支持多种AI模型的配置和切换
"""

import os
import sys
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass
from loguru import logger
from dotenv import load_dotenv

# 确保加载环境变量
load_dotenv()

# 配置logger编码
logger.remove()
logger.add(sys.stderr, enqueue=True)

class ModelProvider(Enum):
    """AI模型提供商枚举"""
    GEMINI = "gemini"
    DASHSCOPE = "dashscope"  # 阿里百炼
    DEEPSEEK = "deepseek"
    OPENROUTER = "openrouter"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    SILICONFLOW = "siliconflow"  # 硅基流动
    ZHIPU = "zhipu"  # 新增：智谱AI

@dataclass
class ModelConfig:
    """模型配置类"""
    provider: ModelProvider
    model_name: str
    api_key_env: str
    base_url: Optional[str] = None
    description: str = ""
    supports_chinese: bool = True
    cost_level: str = "medium"  # low, medium, high
    performance_level: str = "good"  # basic, good, excellent

class LLMConfigManager:
    """LLM配置管理器"""
    
    def __init__(self):
        self.available_models = self._init_model_configs()
        self.current_model = None
        self._setup_current_model()
    
    def _init_model_configs(self) -> Dict[str, ModelConfig]:
        """初始化模型配置 - 按提供商分组支持多模型
        支持.env中为每个提供商配置多个模型选择
        """
        configs = {}
        
        # ==================== 阿里百炼/通义千问系列 ====================
        # 基础模型配置
        dashscope_models = {
            "qwen-turbo": {
                "description": "通义千问Turbo - 快速响应，成本较低",
                "cost_level": "low",
                "performance_level": "good"
            },
            "qwen-plus": {
                "description": "通义千问Plus - 中文优化，推荐用于A股分析",
                "cost_level": "medium", 
                "performance_level": "excellent"
            },
            "qwen-max": {
                "description": "通义千问Max - 最强性能，深度分析",
                "cost_level": "high",
                "performance_level": "excellent"
            },
            "qwen2.5-72b-instruct": {
                "description": "通义千问2.5-72B - 超大参数模型，极强推理",
                "cost_level": "high",
                "performance_level": "excellent"
            },
            "qwen2.5-32b-instruct": {
                "description": "通义千问2.5-32B - 中等规模，平衡性能与成本",
                "cost_level": "medium",
                "performance_level": "excellent"
            }
        }
        
        # 从.env获取用户选择的DASHSCOPE模型列表
        env_dashscope_models = os.getenv('DASHSCOPE_MODELS', 'qwen-plus,qwen-turbo,qwen-max').split(',')
        for model_name in env_dashscope_models:
            model_name = model_name.strip()
            if model_name in dashscope_models:
                model_info = dashscope_models[model_name]
                configs[model_name] = ModelConfig(
                    provider=ModelProvider.DASHSCOPE,
                    model_name=model_name,
                    api_key_env="DASHSCOPE_API_KEY",
                    base_url=os.getenv('DASHSCOPE_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1'),
                    description=model_info["description"],
                    supports_chinese=True,
                    cost_level=model_info["cost_level"],
                    performance_level=model_info["performance_level"]
                )
        
        # ==================== DeepSeek系列 ====================
        deepseek_models = {
            "deepseek-chat": {
                "description": "DeepSeek Chat - 性价比极高的国产模型",
                "cost_level": "low",
                "performance_level": "excellent"
            },
            "deepseek-coder": {
                "description": "DeepSeek Coder - 专业代码生成与分析",
                "cost_level": "low",
                "performance_level": "excellent"
            },
            "deepseek-reasoner": {
                "description": "DeepSeek Reasoner - 推理专家模型",
                "cost_level": "medium",
                "performance_level": "excellent"
            }
        }
        
        env_deepseek_models = os.getenv('DEEPSEEK_MODELS', 'deepseek-chat').split(',')
        for model_name in env_deepseek_models:
            model_name = model_name.strip()
            if model_name in deepseek_models:
                model_info = deepseek_models[model_name]
                configs[model_name] = ModelConfig(
                    provider=ModelProvider.DEEPSEEK,
                    model_name=model_name,
                    api_key_env="DEEPSEEK_API_KEY",
                    base_url=os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com'),
                    description=model_info["description"],
                    supports_chinese=True,
                    cost_level=model_info["cost_level"],
                    performance_level=model_info["performance_level"]
                )
        
        # ==================== Google Gemini系列 ====================
        gemini_models = {
            # Gemini 1.5 系列
            "gemini-1.5-flash": {
                "description": "Gemini 1.5 Flash - 快速响应版本",
                "cost_level": "low",
                "performance_level": "good"
            },
            "gemini-1.5-pro": {
                "description": "Gemini 1.5 Pro - 平衡性能与成本",
                "cost_level": "medium",
                "performance_level": "excellent"
            },
            # Gemini 2.0 系列 - 最新一代模型
            "gemini-2.0-flash-001": {
                "description": "Gemini 2.0 Flash - 谷歌最新多模态模型，支持更大上下文窗口",
                "cost_level": "medium",
                "performance_level": "excellent"
            },
            "gemini-2.0-flash-thinking-exp-1219": {
                "description": "Gemini 2.0 Flash Thinking - 推理增强实验版，适合复杂分析任务",
                "cost_level": "high",
                "performance_level": "excellent"
            },
            "gemini-2.0-flash-exp": {
                "description": "Gemini 2.0 Flash Experimental - 最新实验特性版本",
                "cost_level": "medium",
                "performance_level": "excellent"
            }
        }
        
        env_gemini_models = os.getenv('GEMINI_MODELS', 'gemini-2.0-flash-001,gemini-1.5-flash').split(',')
        for model_name in env_gemini_models:
            model_name = model_name.strip()
            if model_name in gemini_models:
                model_info = gemini_models[model_name]
                configs[model_name] = ModelConfig(
                    provider=ModelProvider.GEMINI,
                    model_name=model_name,
                    api_key_env="GEMINI_API_KEY",
                    base_url=os.getenv('GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta'),
                    description=model_info["description"],
                    supports_chinese=True,
                    cost_level=model_info["cost_level"],
                    performance_level=model_info["performance_level"]
                )
        
        # ==================== OpenRouter系列 ====================
        openrouter_models = {
            "meta-llama/llama-3.1-8b-instruct": {
                "description": "Llama 3.1 8B Instruct - 免费模型，中文支持优秀",
                "cost_level": "free",
                "performance_level": "excellent"
            },
            "meta-llama/llama-3.2-90b-vision-instruct": {
                "description": "Llama 3.2 90B Vision - 多模态免费模型",
                "cost_level": "free",
                "performance_level": "excellent"
            },
            "deepseek/deepseek-chat-v3.1:free": {
                "description": "DeepSeek Chat V3.1 免费版 - 推理能力强",
                "cost_level": "free",
                "performance_level": "excellent"
            },
            "z-ai/glm-4.5-air:free": {
                "description": "GLM 4.5 Air 免费版 - 智谱AI，中文优化",
                "cost_level": "free",
                "performance_level": "good"
            },
            "anthropic/claude-3.5-sonnet": {
                "description": "Claude 3.5 Sonnet - 顶级文本模型",
                "cost_level": "high",
                "performance_level": "excellent"
            },
            "openai/gpt-4o": {
                "description": "GPT-4o - OpenAI多模态旗舰",
                "cost_level": "high",
                "performance_level": "excellent"
            }
        }
        
        env_openrouter_models = os.getenv('OPENROUTER_MODELS', 'meta-llama/llama-3.1-8b-instruct,deepseek/deepseek-chat-v3.1:free').split(',')
        for model_name in env_openrouter_models:
            model_name = model_name.strip()
            if model_name in openrouter_models:
                model_info = openrouter_models[model_name]
                configs[model_name] = ModelConfig(
                    provider=ModelProvider.OPENROUTER,
                    model_name=model_name,
                    api_key_env="OPENROUTER_API_KEY",
                    base_url=os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1'),
                    description=model_info["description"],
                    supports_chinese=True,
                    cost_level=model_info["cost_level"],
                    performance_level=model_info["performance_level"]
                )
        
        # ==================== SiliconFlow系列 ====================
        siliconflow_models = {
            "deepseek-ai/DeepSeek-V3": {
                "description": "DeepSeek-V3 - 推理能力极强的国产模型",
                "cost_level": "low",
                "performance_level": "excellent"
            },
            "alibaba/Qwen2.5-72B-Instruct": {
                "description": "通义千问2.5-72B - 阿里巴巴开源旗舰",
                "cost_level": "medium",
                "performance_level": "excellent"
            },
            "meta-llama/Llama-3.1-70B-Instruct": {
                "description": "Llama 3.1 70B - Meta开源大模型",
                "cost_level": "medium",
                "performance_level": "excellent"
            },
            "01-ai/Yi-1.5-34B-Chat": {
                "description": "零一万物Yi-1.5-34B - 中英双语优化",
                "cost_level": "low",
                "performance_level": "good"
            }
        }
        
        env_siliconflow_models = os.getenv('SILICONFLOW_MODELS', 'deepseek-ai/DeepSeek-V3').split(',')
        for model_name in env_siliconflow_models:
            model_name = model_name.strip()
            if model_name in siliconflow_models:
                model_info = siliconflow_models[model_name]
                configs[model_name] = ModelConfig(
                    provider=ModelProvider.SILICONFLOW,
                    model_name=model_name,
                    api_key_env="SiliconFlow_API_KEY",
                    base_url=os.getenv('SiliconFlow_BASE_URL', 'https://api.siliconflow.cn/v1'),
                    description=model_info["description"],
                    supports_chinese=True,
                    cost_level=model_info["cost_level"],
                    performance_level=model_info["performance_level"]
                )
        
        # ==================== 智谱AI系列 ====================
        zhipu_models = {
            "glm-4": {
                "description": "智谱AI GLM-4 - 中文优化基础模型",
                "cost_level": "low",
                "performance_level": "good"
            },
            "glm-4.5": {
                "description": "智谱AI GLM-4.5 - 支持深度思考的增强模型",
                "cost_level": "medium",
                "performance_level": "excellent"
            },
            "glm-4-plus": {
                "description": "智谱AI GLM-4 Plus - 高级模型，中文金融分析专家",
                "cost_level": "medium",
                "performance_level": "excellent"
            },
            "glm-4-flash": {
                "description": "智谱AI GLM-4 Flash - 快速响应版本",
                "cost_level": "low",
                "performance_level": "good"
            },
            "glm-4-air": {
                "description": "智谱AI GLM-4 Air - 轻量级版本",
                "cost_level": "low",
                "performance_level": "good"
            }
        }

        env_zhipu_models = os.getenv('ZHIPU_MODELS', 'glm-4.5,glm-4').split(',')
        for model_name in env_zhipu_models:
            model_name = model_name.strip()
            if model_name in zhipu_models:
                model_info = zhipu_models[model_name]
                configs[model_name] = ModelConfig(
                    provider=ModelProvider.ZHIPU,
                    model_name=model_name,
                    api_key_env="ZHIPU_API_KEY",
                    base_url=None,  # 智谱AI使用自定义适配器，不需要base_url
                    description=model_info["description"],
                    supports_chinese=True,
                    cost_level=model_info["cost_level"],
                    performance_level=model_info["performance_level"]
                )

        # ==================== Anthropic系列 ====================
        anthropic_models = {
            "claude-3.5-sonnet-20241022": {
                "description": "Claude 3.5 Sonnet - Anthropic最新旗舰模型",
                "cost_level": "high",
                "performance_level": "excellent"
            },
            "claude-3.5-haiku-20241022": {
                "description": "Claude 3.5 Haiku - 快速响应版本",
                "cost_level": "medium",
                "performance_level": "good"
            }
        }
        
        env_anthropic_models = os.getenv('ANTHROPIC_MODELS', '').split(',')
        for model_name in env_anthropic_models:
            model_name = model_name.strip()
            if model_name and model_name in anthropic_models:
                model_info = anthropic_models[model_name]
                configs[model_name] = ModelConfig(
                    provider=ModelProvider.ANTHROPIC,
                    model_name=model_name,
                    api_key_env="ANTHROPIC_API_KEY",
                    base_url=None,  # Anthropic使用默认端点
                    description=model_info["description"],
                    supports_chinese=True,
                    cost_level=model_info["cost_level"],
                    performance_level=model_info["performance_level"]
                )
        
        # ==================== OpenAI系列 ====================
        openai_models = {
            "gpt-4o": {
                "description": "GPT-4o - OpenAI多模态旗舰模型",
                "cost_level": "high",
                "performance_level": "excellent"
            },
            "gpt-4o-mini": {
                "description": "GPT-4o Mini - 成本优化版本",
                "cost_level": "medium",
                "performance_level": "good"
            },
            "gpt-4-turbo": {
                "description": "GPT-4 Turbo - 快速响应版本",
                "cost_level": "high",
                "performance_level": "excellent"
            }
        }
        
        env_openai_models = os.getenv('OPENAI_MODELS', '').split(',')
        for model_name in env_openai_models:
            model_name = model_name.strip()
            if model_name and model_name in openai_models:
                model_info = openai_models[model_name]
                configs[model_name] = ModelConfig(
                    provider=ModelProvider.OPENAI,
                    model_name=model_name,
                    api_key_env="OPENAI_API_KEY",
                    base_url=os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
                    description=model_info["description"],
                    supports_chinese=True,
                    cost_level=model_info["cost_level"],
                    performance_level=model_info["performance_level"]
                )
        
        return configs
    
    def _setup_current_model(self):
        """设置当前使用的模型 - 支持每个提供商的默认模型配置"""
        # 1. 优先使用.env中指定的MODEL
        env_model = os.getenv('MODEL', '').strip()
        env_provider = os.getenv('MODEL_PROVIDER', '').strip()
        
        # 如果指定了供应商，尝试查找该供应商下的模型
        if env_model and env_provider:
            # 查找指定供应商下的模型
            for model_key, config in self.available_models.items():
                if config.provider.value == env_provider.lower() and env_model in model_key:
                    if self.is_model_available(model_key):
                        self.current_model = model_key
                        return
            logger.warning(f"未找到供应商 {env_provider} 下的模型 {env_model}，尝试自动匹配")
        
        # 2. 标准匹配：直接使用MODEL值
        if env_model and self.is_model_available(env_model):
            self.current_model = env_model
            config = self.available_models[env_model]
            return
        elif env_model:
            logger.warning(f".env指定的模型 {env_model} 不可用，将使用备选模型")
        
        # 3. 检查每个供应商的默认模型配置
        provider_defaults = {
            'ZHIPU': os.getenv('ZHIPU_DEFAULT_MODEL', 'glm-4.5'),
            'DASHSCOPE': os.getenv('DASHSCOPE_DEFAULT_MODEL', 'qwen-plus'),
            'DEEPSEEK': os.getenv('DEEPSEEK_DEFAULT_MODEL', 'deepseek-chat'),
            'GEMINI': os.getenv('GEMINI_DEFAULT_MODEL', 'gemini-2.0-flash-001'),
            'OPENROUTER': os.getenv('OPENROUTER_DEFAULT_MODEL', 'meta-llama/llama-3.1-8b-instruct'),
            'SILICONFLOW': os.getenv('SILICONFLOW_DEFAULT_MODEL', 'deepseek-ai/DeepSeek-V3'),
            'ANTHROPIC': os.getenv('ANTHROPIC_DEFAULT_MODEL', 'claude-3.5-sonnet-20241022'),
            'OPENAI': os.getenv('OPENAI_DEFAULT_MODEL', 'gpt-4o-mini')
        }
        
        # 4. 按供应商优先级和默认模型选择
        provider_priority = ['ZHIPU', 'SILICONFLOW', 'OPENROUTER', 'DASHSCOPE', 'DEEPSEEK', 'GEMINI', 'ANTHROPIC', 'OPENAI']
        
        for provider in provider_priority:
            default_model = provider_defaults.get(provider)
            if default_model and self.is_model_available(default_model):
                self.current_model = default_model
                return
        
        # 5. 如果没有找到默认模型，按通用优先级选择
        priority_models = [
            "glm-4.5",                            # 智谱AI GLM-4.5优先（深度思考+中文金融专家）
            "glm-4",                              # 智谱AI GLM-4备选（中文金融优化）
            "deepseek-ai/DeepSeek-V3",       # SiliconFlow DeepSeek-V3优先（推理能力最强）
            "meta-llama/llama-3.1-8b-instruct",    # OpenRouter免费Llama（中文支持优秀）
            "deepseek/deepseek-chat-v3.1:free",    # OpenRouter免费DeepSeek（推理能力强）
            "z-ai/glm-4.5-air:free",               # OpenRouter免费GLM（中文优化）
            "glm-4-flash",                        # 智谱AI快速版本
            "deepseek-chat",                       # 原DeepSeek次选（稳定可用）
            "gemini-2.0-flash-001",               # Gemini备选（默认）
            "qwen-plus",                          # 阿里百炼备选
            "qwen-turbo",                         # 快速版本
            "gemini-1.5-flash"                    # 快速备选
        ]
        
        for model_key in priority_models:
            if self.is_model_available(model_key):
                self.current_model = model_key
                break
        
        # 6. 尝试备用模型
        if not self.current_model:
            fallback_model = os.getenv('FALLBACK_MODEL', 'meta-llama/llama-3.1-8b-instruct')
            if self.is_model_available(fallback_model):
                self.current_model = fallback_model
            else:
                logger.error("未找到任何可用的AI模型配置")
    
    def is_model_available(self, model_key: str) -> bool:
        """检查模型是否可用"""
        if model_key not in self.available_models:
            return False
        
        config = self.available_models[model_key]
        api_key = os.getenv(config.api_key_env)
        
        # 检查API密钥是否配置
        if not api_key:
            return False
        
        # 检查密钥格式是否正确
        if config.provider == ModelProvider.DASHSCOPE:
            # 验证DashScope URL格式并强制纠正错误配置
            self._validate_dashscope_config()
            return api_key.startswith('sk-')
        elif config.provider == ModelProvider.DEEPSEEK:
            return api_key.startswith('sk-') and os.getenv('DEEPSEEK_ENABLED', '').lower() == 'true'
        elif config.provider == ModelProvider.GEMINI:
            # Gemini AI Studio API密钥格式检查
            return len(api_key) > 30 and api_key.startswith('AIza') and api_key != 'your_gemini_api_key_here'
        elif config.provider == ModelProvider.OPENROUTER:
            return api_key.startswith('sk-or-')
        elif config.provider == ModelProvider.SILICONFLOW:
            # SiliconFlow API密钥格式检查
            return api_key.startswith('sk-') and len(api_key) > 20
        elif config.provider == ModelProvider.ZHIPU:
            # 智谱AI API密钥格式检查（通常以特定格式开头）
            return len(api_key) > 20 and '.' in api_key  # 智谱AI密钥包含点号
        else:
            return len(api_key) > 10
    
    def _validate_dashscope_config(self):
        """验证和纠正DashScope配置"""
        correct_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        current_base_url = os.getenv('DASHSCOPE_BASE_URL', '')
        
        # 检查是否存在常见的错误URL
        wrong_urls = [
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        ]
        
        if current_base_url in wrong_urls or not current_base_url:
            logger.warning(f"[CONFIG] 检测到错误的DashScope URL配置: {current_base_url}")
            logger.info(f"[CONFIG] 强制纠正为正确URL: {correct_base_url}")
            
            # 强制设置正确的环境变量
            os.environ['DASHSCOPE_BASE_URL'] = correct_base_url
            
            # 同时设置LiteLLM相关的环境变量以确保覆盖
            os.environ['DASHSCOPE_API_BASE'] = correct_base_url
            
        # 验证API密钥并设置相关环境变量
        api_key = os.getenv('DASHSCOPE_API_KEY')
        if api_key:
            # 设置OpenAI兼容性密钥（CrewAI需要）
            os.environ['OPENAI_API_KEY'] = api_key
            logger.info("[CONFIG] DashScope配置验证完成")
    
    def get_available_models(self) -> Dict[str, ModelConfig]:
        """获取所有可用的模型"""
        return {k: v for k, v in self.available_models.items() if self.is_model_available(k)}
    
    def get_current_model(self) -> Optional[str]:
        """获取当前选择的模型"""
        return self.current_model
    
    def get_model_config(self, model_key: str) -> Optional[ModelConfig]:
        """获取指定模型的配置"""
        return self.available_models.get(model_key)
    
    def set_current_model(self, model_key: str) -> bool:
        """设置当前使用的模型"""
        if self.is_model_available(model_key):
            self.current_model = model_key
            return True
        else:
            logger.error(f"模型不可用: {model_key}")
            return False
    
    def get_crewai_llm_config(self, model_key: Optional[str] = None) -> str:
        """获取CrewAI格式的LLM配置"""
        target_model = model_key or self.current_model
        
        if not target_model:
            return "gemini-2.0-flash-001"  # 默认模型
        
        config = self.available_models.get(target_model)
        if not config:
            return "gemini-2.0-flash-001"
        
        # 根据提供商返回不同的格式
        if config.provider == ModelProvider.DASHSCOPE:
            # 在返回配置前确保DashScope配置正确
            self._validate_dashscope_config()
            return f"dashscope/{config.model_name}"
        elif config.provider == ModelProvider.DEEPSEEK:
            return f"deepseek/{config.model_name}"
        elif config.provider == ModelProvider.GEMINI:
            # 使用AI Studio格式，避免Vertex AI认证问题
            return f"gemini/{config.model_name}"
        elif config.provider == ModelProvider.OPENROUTER:
            return f"openrouter/{config.model_name}"
        elif config.provider == ModelProvider.SILICONFLOW:
            # SiliconFlow使用OpenAI兼容的调用方式
            return self._create_siliconflow_llm(config)
        elif config.provider == ModelProvider.ZHIPU:
            # 智谱AI使用自定义适配器
            return self._create_zhipu_llm(config)
        else:
            return config.model_name
    
    def _create_siliconflow_llm(self, config: ModelConfig):
        """创建SiliconFlow LLM实例"""
        try:
            from crewai.llm import LLM
            
            api_key = os.getenv(config.api_key_env)
            if not api_key:
                logger.error(f"SiliconFlow API密钥未配置: {config.api_key_env}")
                return f"gemini/{config.model_name}"  # 降级处理
            
            # 创建兼容OpenAI的LLM实例
            return LLM(
                model=f"openai/{config.model_name}",
                api_key=api_key,
                base_url=config.base_url or "https://api.siliconflow.cn/v1"
            )
        except Exception as e:
            logger.error(f"创建SiliconFlow LLM失败: {e}")
            return f"gemini/{config.model_name}"  # 降级处理

    def _create_zhipu_llm(self, config: ModelConfig):
        """创建智谱AI LLM实例"""
        try:
            # 导入智谱AI适配器
            from .zhipu_adapter import get_zhipu_adapter

            api_key = os.getenv(config.api_key_env)
            if not api_key:
                logger.error(f"智谱AI API密钥未配置: {config.api_key_env}")
                return f"gemini/{config.model_name}"  # 降级处理

            # 测试智谱AI连接
            try:
                adapter = get_zhipu_adapter()
                if adapter.test_connection():
                    logger.info(f"[ZHIPU] {config.model_name} 连接测试成功")
                    # 返回智谱AI适配器标识符
                    return f"zhipu/{config.model_name}"
                else:
                    logger.warning(f"[ZHIPU] {config.model_name} 连接测试失败，降级到备用模型")
                    return f"gemini/{config.model_name}"
            except Exception as conn_e:
                logger.error(f"[ZHIPU] 连接测试异常: {conn_e}")
                return f"gemini/{config.model_name}"

        except ImportError:
            logger.error("智谱AI适配器模块导入失败，请检查zai-sdk是否正确安装")
            return f"gemini/{config.model_name}"  # 降级处理
        except Exception as e:
            logger.error(f"创建智谱AI LLM失败: {e}")
            return f"gemini/{config.model_name}"  # 降级处理

    def get_model_stats(self) -> Dict[str, Any]:
        """获取模型统计信息"""
        available_models = self.get_available_models()
        
        stats = {
            "total_configured": len(self.available_models),
            "available_count": len(available_models),
            "current_model": self.current_model,
            "providers": {}
        }
        
        # 按提供商统计
        for config in available_models.values():
            provider = config.provider.value
            if provider not in stats["providers"]:
                stats["providers"][provider] = {"count": 0, "models": []}
            
            stats["providers"][provider]["count"] += 1
            stats["providers"][provider]["models"].append(config.model_name)
        
        return stats
    
    def get_recommended_model(self, use_case: str = "chinese_stock_analysis") -> Optional[str]:
        """根据使用场景推荐模型"""
        available = self.get_available_models()
        
        if not available:
            return None
        
        if use_case == "chinese_stock_analysis":
            # A股分析推荐中文优化模型
            priority = ["glm-4.5", "glm-4", "qwen-plus", "deepseek-chat", "qwen-turbo"]
        elif use_case == "fast_analysis":
            # 快速分析推荐低延迟模型
            priority = ["glm-4-flash", "qwen-turbo", "gemini-1.5-flash", "deepseek-chat"]
        elif use_case == "high_quality":
            # 高质量分析推荐强模型
            priority = ["glm-4.5", "glm-4-plus", "anthropic/claude-3.5-sonnet", "qwen-plus", "gemini-2.0-flash-001"]
        elif use_case == "cost_effective":
            # 成本优化推荐低成本模型
            priority = ["glm-4", "deepseek-chat", "qwen-turbo", "glm-4-flash", "gemini-1.5-flash"]
        else:
            priority = ["glm-4.5", "qwen-plus", "deepseek-chat", "gemini-2.0-flash-001"]
        
        for model in priority:
            if model in available:
                return model
        
        # 如果没有匹配，返回第一个可用模型
        return list(available.keys())[0] if available else None

# 创建全局配置管理器实例
llm_config_manager = LLMConfigManager()

def get_current_llm() -> str:
    """获取当前LLM配置（供CrewAI使用）"""
    return llm_config_manager.get_crewai_llm_config()

def get_available_models() -> List[str]:
    """获取可用模型列表"""
    return list(llm_config_manager.get_available_models().keys())

def switch_model(model_key: str) -> bool:
    """切换模型"""
    return llm_config_manager.set_current_model(model_key)

def get_model_info() -> Dict[str, Any]:
    """获取模型信息"""
    stats = llm_config_manager.get_model_stats()
    current_config = None
    
    if stats["current_model"]:
        current_config = llm_config_manager.get_model_config(stats["current_model"])
    
    return {
        "stats": stats,
        "current_config": current_config,
        "recommendation": llm_config_manager.get_recommended_model()
    }