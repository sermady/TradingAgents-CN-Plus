# -*- coding: utf-8 -*-
"""
简化的LLM配置管理器
统一使用OpenAI兼容接口，大幅简化配置复杂度
"""

import os
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
from loguru import logger
from dotenv import load_dotenv
from typing import Any, Union, Callable

# 确保加载环境变量
load_dotenv()

class ProviderType(Enum):
    """AI提供商类型"""
    DEEPSEEK = "deepseek"
    DASHSCOPE = "dashscope"  # 阿里百炼
    OPENAI = "openai"
    GEMINI = "gemini"
    SILICONFLOW = "siliconflow"
    OPENROUTER = "openrouter"
    ZHIPU = "zhipu"  # 智谱AI

@dataclass
class ModelConfig:
    """模型配置"""
    provider: ProviderType
    model_name: str
    api_key: str
    base_url: str
    description: str = ""
    
    def to_openai_format(self) -> str:
        """转换为OpenAI兼容格式"""
        if self.provider == ProviderType.OPENAI:
            return self.model_name
        else:
            return f"{self.provider.value}/{self.model_name}"

class SimpleLLMConfigManager:
    """简化的LLM配置管理器 - 统一OpenAI兼容接口"""
    
    # 从.env文件动态读取提供商配置模板
    @property
    def PROVIDER_TEMPLATES(self):
        """从环境变量动态读取提供商配置模板"""
        return {
            ProviderType.DEEPSEEK: {
                "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
                "default_model": os.getenv("DEEPSEEK_DEFAULT_MODEL", "deepseek-chat"),
                "api_key_env": "DEEPSEEK_API_KEY"
            },
            ProviderType.DASHSCOPE: {
                "base_url": os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"), 
                "default_model": os.getenv("DASHSCOPE_DEFAULT_MODEL", "qwen-plus"),
                "api_key_env": "DASHSCOPE_API_KEY"
            },
            ProviderType.OPENAI: {
                "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                "default_model": os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini"), 
                "api_key_env": "OPENAI_API_KEY"
            },
            ProviderType.GEMINI: {
                "base_url": os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"),
                "default_model": os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.5-flash"),
                "api_key_env": "GEMINI_API_KEY"
            },
            ProviderType.SILICONFLOW: {
                "base_url": os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
                "default_model": os.getenv("SILICONFLOW_DEFAULT_MODEL", "deepseek-ai/DeepSeek-V3"),
                "api_key_env": "SILICONFLOW_API_KEY"
            },
            ProviderType.OPENROUTER: {
                "base_url": os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                "default_model": os.getenv("OPENROUTER_DEFAULT_MODEL", "deepseek/deepseek-chat-v3.1:free"),
                "api_key_env": "OPENROUTER_API_KEY"
            },
            ProviderType.ZHIPU: {
                "base_url": os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/"),
                "default_model": os.getenv("ZHIPU_DEFAULT_MODEL", "glm-4.5-air"),
                "api_key_env": "ZHIPU_API_KEY"
            }
        }
    
    def __init__(self):
        self.current_config = self._load_current_config()
        quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
        if not quiet_mode:
            logger.info(f"[SIMPLE_LLM] 使用统一OpenAI兼容接口: {self.current_config.provider.value}/{self.current_config.model_name}")
    
    def verify_api_key_with_provider(self, api_key: str, provider: ProviderType) -> bool:
        """通过实际API调用验证API密钥是否属于指定提供商"""
        
        try:
            import requests
            
            template = self.PROVIDER_TEMPLATES[provider]
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # 根据不同提供商使用不同的验证端点
            if provider == ProviderType.DEEPSEEK:
                url = f"{template['base_url']}/models"
            elif provider == ProviderType.DASHSCOPE:
                url = f"{template['base_url']}/models"  
            elif provider == ProviderType.GEMINI:
                url = f"{template['base_url']}/models?key={api_key}"
                headers = {}  # Gemini使用URL参数认证
            elif provider == ProviderType.OPENROUTER:
                url = f"{template['base_url']}/models"
            elif provider == ProviderType.SILICONFLOW:
                url = f"{template['base_url']}/models"
            elif provider == ProviderType.ZHIPU:
                url = f"{template['base_url']}/models"
            else:
                return False
            
            # 发送验证请求 (超时5秒)
            response = requests.get(url, headers=headers, timeout=5)
            
            # 检查响应状态
            if response.status_code == 200:
                return True
            elif response.status_code == 401:  # 认证失败
                return False
            else:
                # 其他错误可能是网络问题，不确定
                return False
                
        except Exception as e:
            logger.debug(f"[API_VERIFY] API验证失败 ({provider.value}): {e}")
            return False

    def detect_provider_from_api_key(self, api_key: str) -> Optional[ProviderType]:
        """根据API密钥通过实际验证自动识别提供商"""
        
        if not api_key or len(api_key) < 10:
            return None
            
        api_key = api_key.strip()
        
        # 1. 基于格式的快速预判（避免不必要的API调用）
        quick_candidates = []
        
        if api_key.startswith('AIza') and len(api_key) == 39:
            quick_candidates = [ProviderType.GEMINI]
        elif api_key.startswith('sk-or-') and len(api_key) >= 64:
            quick_candidates = [ProviderType.OPENROUTER]
        elif api_key.startswith('sk-'):
            # 基于关键词和长度的预判
            if 'deepseek' in api_key.lower():
                quick_candidates = [ProviderType.DEEPSEEK]
            elif 'dashscope' in api_key.lower() or 'aliyun' in api_key.lower():
                quick_candidates = [ProviderType.DASHSCOPE]
            elif 'silicon' in api_key.lower():
                quick_candidates = [ProviderType.SILICONFLOW]
            else:
                # 按长度推测可能的提供商
                if len(api_key) == 32:
                    quick_candidates = [ProviderType.DASHSCOPE, ProviderType.DEEPSEEK]
                elif 40 <= len(api_key) <= 50:
                    quick_candidates = [ProviderType.DEEPSEEK, ProviderType.DASHSCOPE]
                elif len(api_key) >= 56:
                    quick_candidates = [ProviderType.SILICONFLOW, ProviderType.DEEPSEEK]
                else:
                    quick_candidates = [ProviderType.DEEPSEEK, ProviderType.SILICONFLOW]
        
        # 2. 如果没有快速候选，尝试所有提供商
        if not quick_candidates:
            quick_candidates = list(ProviderType)
        
        # 3. 通过实际API调用验证
        quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
        if not quiet_mode:
            logger.info(f"[API_VERIFY] 开始验证API密钥，候选提供商: {[p.value for p in quick_candidates]}")
        
        for provider in quick_candidates:
            if self.verify_api_key_with_provider(api_key, provider):
                if not quiet_mode:
                    logger.info(f"[API_VERIFY] 验证成功: {provider.value}")
                return provider
        
        # 4. 如果验证都失败，回退到格式判断和环境变量匹配
        logger.warning("[API_VERIFY] 所有API验证失败，回退到格式判断")
        
        # 首先尝试匹配环境变量中的专用API密钥
        if api_key == os.getenv('DASHSCOPE_API_KEY'):
            return ProviderType.DASHSCOPE
        elif api_key == os.getenv('GEMINI_API_KEY'):
            return ProviderType.GEMINI
        elif api_key == os.getenv('DEEPSEEK_API_KEY'):
            return ProviderType.DEEPSEEK
        elif api_key == os.getenv('OPENROUTER_API_KEY'):
            return ProviderType.OPENROUTER
        elif api_key == os.getenv('SILICONFLOW_API_KEY'):
            return ProviderType.SILICONFLOW
        elif api_key == os.getenv('ZHIPU_API_KEY'):
            return ProviderType.ZHIPU
        
        # 然后根据格式判断
        if api_key.startswith('AIza'):
            return ProviderType.GEMINI
        elif api_key.startswith('sk-or-'):
            return ProviderType.OPENROUTER
        elif api_key.startswith('sk-'):
            # 对于sk-开头的密钥，再次检查是否匹配DASHSCOPE
            if api_key == os.getenv('DASHSCOPE_API_KEY'):
                return ProviderType.DASHSCOPE
            return ProviderType.DEEPSEEK  # 最后默认DeepSeek
                
        return None
    
    def _get_smart_mode_fallback_provider(self) -> ProviderType:
        """获取SMART模式的fallback提供商（选择第一个可用的）"""
        priority_order = [
            ProviderType.DEEPSEEK,      # 性价比最高
            ProviderType.DASHSCOPE,     # 中文优化
            ProviderType.SILICONFLOW,   # 免费额度
            ProviderType.GEMINI,        # Google
            ProviderType.OPENROUTER,    # 备选
            ProviderType.ZHIPU          # 智谱AI
        ]
        
        for provider in priority_order:
            template = self.PROVIDER_TEMPLATES[provider]
            api_key = os.getenv(template["api_key_env"])
            if api_key and len(api_key) > 10:
                return provider
        
        # 如果都没有，返回DeepSeek作为默认
        return ProviderType.DEEPSEEK
    
    def is_smart_mode(self) -> bool:
        """检查是否为SMART模式"""
        return os.getenv('PROVIDER', '').strip().lower() == 'smart'
    
    def _load_provider_based_config(self) -> Optional[ModelConfig]:
        """基于 PROVIDER 环境变量自动加载配置"""
        
        # 读取主 PROVIDER 配置
        provider_name = os.getenv('PROVIDER', '').strip().lower()
        if not provider_name:
            return None
        
        # 特殊处理: smart 模式
        if provider_name == 'smart':
            quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
            if not quiet_mode:
                logger.info("[PROVIDER_CONFIG] 检测到SMART模式，将使用智能团队配置")
            
            # SMART模式下返回一个占位配置，实际模型选择由smart_team_config负责
            # 这里使用默认配置作为fallback
            fallback_provider = self._get_smart_mode_fallback_provider()
            template = self.PROVIDER_TEMPLATES[fallback_provider]
            api_key = os.getenv(template["api_key_env"], '')
            
            return ModelConfig(
                provider=fallback_provider,
                model_name=template["default_model"],
                api_key=api_key,
                base_url=template["base_url"],
                description="SMART模式基础配置 - 实际模型由角色决定"
            )
        
        try:
            # 验证提供商是否支持
            provider = ProviderType(provider_name)
        except ValueError:
            quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
            if not quiet_mode:
                logger.warning(f"[PROVIDER_CONFIG] 未知提供商: {provider_name}")
            return None
        
        # 构建配置变量名（大写）
        provider_upper = provider_name.upper()
        api_key = os.getenv(f'{provider_upper}_API_KEY', '').strip()
        default_model = os.getenv(f'{provider_upper}_DEFAULT_MODEL', '').strip()
        base_url = os.getenv(f'{provider_upper}_BASE_URL', '').strip()
        
        # 必须有 API 密钥
        if not api_key:
            quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
            if not quiet_mode:
                logger.warning(f"[PROVIDER_CONFIG] 未找到 {provider_upper}_API_KEY")
            return None
        
        # 从模板获取默认值
        template = self.PROVIDER_TEMPLATES[provider]
        if not default_model:
            default_model = template["default_model"]
        if not base_url:
            base_url = template["base_url"]
        
        quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
        if not quiet_mode:
            logger.info(f"[PROVIDER_CONFIG] 自动配置 {provider_name}: {default_model}")
        
        return ModelConfig(
            provider=provider,
            model_name=default_model,
            api_key=api_key,
            base_url=base_url,
            description=f"PROVIDER自动配置: {provider_name}/{default_model}"
        )
    
    def _load_current_config(self) -> ModelConfig:
        """从环境变量加载当前配置"""
        
        # 1. 最高优先级：基于 PROVIDER 的自动配置（新功能）
        provider_config = self._load_provider_based_config()
        if provider_config:
            return provider_config
        
        # 2. 使用默认配置
        return self._get_default_config()
    
    def _load_legacy_config(self) -> Optional[ModelConfig]:
        """加载旧的环境变量配置（向后兼容）"""
        
        # 检查MODEL环境变量
        model = os.getenv('MODEL', '').strip()
        if not model:
            return None
        
        # 按优先级检查可用的提供商配置
        for provider, template in self.PROVIDER_TEMPLATES.items():
            api_key = os.getenv(template["api_key_env"])
            if not api_key:
                continue
            
            # 检查模型名称是否匹配这个提供商
            if provider == ProviderType.DEEPSEEK and 'deepseek' in model.lower():
                return ModelConfig(
                    provider=provider,
                    model_name=model,
                    api_key=api_key,
                    base_url=template["base_url"],
                    description=f"兼容模式: {model}"
                )
            elif provider == ProviderType.DASHSCOPE and ('qwen' in model.lower() or 'dashscope' in model.lower()):
                return ModelConfig(
                    provider=provider,
                    model_name=model.replace('dashscope/', ''),
                    api_key=api_key,
                    base_url=template["base_url"],
                    description=f"兼容模式: {model}"
                )
            elif provider == ProviderType.SILICONFLOW and 'siliconflow' in model.lower():
                return ModelConfig(
                    provider=provider,
                    model_name=model.replace('siliconflow/', ''),
                    api_key=api_key,
                    base_url=template["base_url"],
                    description=f"兼容模式: {model}"
                )
        
        return None
    
    def _get_default_config(self) -> ModelConfig:
        """获取默认配置"""
        # 按优先级查找可用的提供商
        priority_order = [
            ProviderType.DEEPSEEK,      # 性价比最高
            ProviderType.SILICONFLOW,   # 免费额度
            ProviderType.OPENROUTER,    # 免费模型
            ProviderType.DASHSCOPE,     # 中文优化
            ProviderType.GEMINI,        # Google
            ProviderType.OPENAI         # 标准
        ]
        
        for provider in priority_order:
            template = self.PROVIDER_TEMPLATES[provider]
            api_key = os.getenv(template["api_key_env"])
            
            if api_key and len(api_key) > 10:  # 基本的API密钥验证
                return ModelConfig(
                    provider=provider,
                    model_name=template["default_model"],
                    api_key=api_key,
                    base_url=template["base_url"],
                    description=f"默认配置: {provider.value}"
                )
        
        # 如果没有找到任何配置，返回一个错误配置
        logger.error("[SIMPLE_LLM] 未找到任何可用的AI模型配置！")
        return ModelConfig(
            provider=ProviderType.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key="",
            base_url="https://api.openai.com/v1",
            description="错误配置 - 需要设置API密钥"
        )
    
    def get_crewai_llm_config(self) -> str:
        """获取CrewAI格式的LLM配置"""
        return self.current_config.to_openai_format()
    
    def get_openai_compatible_config(self) -> Dict[str, str]:
        """获取OpenAI兼容的配置字典"""
        return {
            "api_key": self.current_config.api_key,
            "base_url": self.current_config.base_url,
            "model": self.current_config.model_name,
            "provider": self.current_config.provider.value
        }
    
    def switch_model(self, provider: str, model_name: str, api_key: Optional[str] = None, base_url: Optional[str] = None) -> bool:
        """动态切换模型"""
        try:
            provider_enum = ProviderType(provider.lower())
            template = self.PROVIDER_TEMPLATES[provider_enum]
            
            # 使用提供的API密钥或从环境变量获取
            if not api_key:
                api_key = os.getenv(template["api_key_env"])
                if not api_key:
                    logger.error(f"[SIMPLE_LLM] 未找到 {template['api_key_env']} 环境变量")
                    return False
            
            # 使用提供的base_url或模板默认值
            if not base_url:
                base_url = template["base_url"]
            
            self.current_config = ModelConfig(
                provider=provider_enum,
                model_name=model_name,
                api_key=api_key,
                base_url=base_url,
                description=f"动态切换: {provider}/{model_name}"
            )
            
            logger.info(f"[SIMPLE_LLM] 成功切换到: {provider}/{model_name}")
            return True
            
        except ValueError:
            logger.error(f"[SIMPLE_LLM] 不支持的提供商: {provider}")
            return False
        except Exception as e:
            logger.error(f"[SIMPLE_LLM] 切换模型失败: {e}")
            return False
    
    def get_available_providers(self) -> Dict[str, Dict[str, Any]]:
        """获取可用的提供商列表"""
        available = {}
        
        for provider, template in self.PROVIDER_TEMPLATES.items():
            api_key = os.getenv(template["api_key_env"])
            available[provider.value] = {
                "default_model": template["default_model"],
                "base_url": template["base_url"],
                "available": bool(api_key and len(api_key) > 10),
                "api_key_env": template["api_key_env"]
            }
        
        return available
    
    def get_status(self) -> Dict[str, Any]:
        """获取配置状态"""
        return {
            "current_provider": self.current_config.provider.value,
            "current_model": self.current_config.model_name,
            "base_url": self.current_config.base_url,
            "description": self.current_config.description,
            "api_key_configured": bool(self.current_config.api_key),
            "available_providers": list(self.get_available_providers().keys())
        }

# 创建全局实例
simple_llm_manager = SimpleLLMConfigManager()

# 系统初始化完成 - 使用纯简化配置模式
quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
if not quiet_mode:
    logger.info("[SIMPLE_LLM] 使用纯简化配置模式")

# 兼容性函数
def get_current_llm() -> str:
    """获取当前LLM配置（CrewAI格式）- 返回字符串格式"""
    return simple_llm_manager.get_crewai_llm_config()

def get_crewai_llm_object():
    """获取CrewAI格式的LLM对象（不是字符串）"""
    import os
    from crewai import LLM

    # 检查是否为SMART模式
    if simple_llm_manager.is_smart_mode():
        quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
        if not quiet_mode:
            logger.info("[SMART_MODE] 使用智能团队配置，返回默认LLM对象")
        # SMART模式下，返回一个默认的LLM对象
        # 实际的角色特定LLM由smart_team_config.py管理
        config = simple_llm_manager.get_openai_compatible_config()
    else:
        # 统一模式
        config = simple_llm_manager.get_openai_compatible_config()

    # 根据提供商设置相应的环境变量，让CrewAI能够识别
    if config['provider'] == 'deepseek':
        # DeepSeek 作为 OpenAI 兼容接口，直接设置 OPENAI 环境变量
        os.environ['OPENAI_API_KEY'] = config['api_key']
        os.environ['OPENAI_API_BASE'] = config['base_url']
        # 同时保留 DEEPSEEK 环境变量
        os.environ['DEEPSEEK_API_KEY'] = config['api_key']
        os.environ['DEEPSEEK_API_BASE'] = config['base_url']
    elif config['provider'] == 'dashscope':
        os.environ['DASHSCOPE_API_KEY'] = config['api_key']
        os.environ['DASHSCOPE_API_BASE'] = config['base_url']
    elif config['provider'] == 'openai':
        os.environ['OPENAI_API_KEY'] = config['api_key']
        os.environ['OPENAI_API_BASE'] = config['base_url']
    else:
        # 对于其他提供商，仍设置OpenAI兼容变量（用于兼容）
        os.environ['OPENAI_API_KEY'] = config['api_key']
        os.environ['OPENAI_API_BASE'] = config['base_url']

    # 创建原始LLM对象
    llm_instance = None

    # 对于特殊提供商，使用直接配置方式
    if config['provider'] == 'gemini':
        # 确保GEMINI_API_KEY设置正确
        os.environ['GEMINI_API_KEY'] = config['api_key']

        # 直接指定provider，避免路由问题
        llm_instance = LLM(
            model=config['model'],  # 直接使用模型名，如 gemini-2.5-flash
            api_key=config['api_key'],
            base_url=config['base_url'],
            # 明确指定provider，这比依赖模型名路由更可靠
            provider="gemini"
        )
    elif config['provider'] == 'deepseek':
        # DeepSeek 使用 OpenAI 兼容接口，环境变量已在上面设置
        llm_instance = LLM(
            model=config['model'],  # 直接使用模型名如 deepseek-chat
            api_key=config['api_key'],
            base_url=config['base_url'],
            provider="openai"  # 明确指定为 openai 提供商以支持兼容接口
        )
    elif config['provider'] == 'siliconflow':
        # SiliconFlow 作为 OpenAI 兼容接口，使用 openai/ 前缀让 LiteLLM 识别
        os.environ['OPENAI_API_KEY'] = config['api_key']
        os.environ['OPENAI_API_BASE'] = config['base_url']

        llm_instance = LLM(
            model=f"openai/{config['model']}",  # 使用 openai/ 前缀
            api_key=config['api_key'],
            base_url=config['base_url'],
            provider="openai"  # 明确指定为 openai 提供商
        )
    elif config['provider'] == 'zhipu':
        # 智谱AI 使用 OpenAI 兼容接口
        os.environ['OPENAI_API_KEY'] = config['api_key']
        os.environ['OPENAI_API_BASE'] = config['base_url']
        
        # 确保使用正确的模型名称格式
        model_name = config['model']
        if not model_name.startswith('openai/'):
            model_name = f"openai/{model_name}"
        
        llm_instance = LLM(
            model=model_name,  # 使用openai/前缀确保正确路由
            api_key=config['api_key'],
            base_url=config['base_url'],
            provider="openai"  # 明确指定provider为openai
        )
    else:
        # 其他提供商使用标准格式
        model_name = f"{config['provider']}/{config['model']}"
        llm_instance = LLM(
            model=model_name,
            api_key=config['api_key'],
            base_url=config['base_url']
        )

    # 包装LLM以支持主动消息格式修复（关键改进！）
    wrapped_llm = create_proactive_message_fixing_llm(llm_instance, config['provider'])

    quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
    if not quiet_mode:
        logger.info(f"[MESSAGE_FIX] LLM已包装支持主动消息格式修复 (Provider: {config['provider']})")

    return wrapped_llm

def get_openai_config() -> Dict[str, str]:
    """获取OpenAI兼容配置"""
    return simple_llm_manager.get_openai_compatible_config()

def switch_llm_provider(provider: str, model: str) -> bool:
    """切换LLM提供商"""
    return simple_llm_manager.switch_model(provider, model)

def get_llm_status() -> Dict[str, Any]:
    """获取LLM状态"""
    return simple_llm_manager.get_status()

# 消息格式验证和修复工具函数
def validate_and_fix_message_sequence(messages: list) -> list:
    """
    验证并修复OpenAI API消息序列格式
    增强版：支持更智能的消息修复策略

    Args:
        messages: 消息列表，每个消息是包含role和content的字典

    Returns:
        修复后的消息列表
    """
    if not messages or not isinstance(messages, list):
        return messages

    fixed_messages = []
    last_role = None

    for i, message in enumerate(messages):
        if not isinstance(message, dict) or 'role' not in message:
            continue

        current_role = message.get('role')
        content = message.get('content', '')

        # 处理空内容
        if not content and current_role != 'system':
            content = "[空消息]"
            message = message.copy()
            message['content'] = content

        # 特殊处理：确保tool消息前面有对应的tool_calls
        if current_role == 'tool':
            # 检查前面是否有包含tool_calls的assistant消息
            has_tool_call = False
            for j in range(len(fixed_messages) - 1, -1, -1):
                prev_msg = fixed_messages[j]
                if prev_msg.get('role') == 'assistant' and 'tool_calls' in prev_msg:
                    has_tool_call = True
                    break
                # 如果遇到其他assistant消息但没有tool_calls，则需要插入
                if prev_msg.get('role') == 'assistant':
                    break
            
            # 如果没有对应的tool_calls，需要修正
            if not has_tool_call and fixed_messages:
                # 在前面插入一个包含tool_calls的assistant消息
                tool_call_msg = {
                    "role": "assistant",
                    "content": "执行工具调用",
                    "tool_calls": [
                        {
                            "id": message.get("tool_call_id", f"call_{i}"),
                            "type": "function",
                            "function": {
                                "name": "unknown_tool",
                                "arguments": "{}"
                            }
                        }
                    ]
                }
                fixed_messages.append(tool_call_msg)
                logger.debug("[MESSAGE_FIX] 在tool消息前插入缺失的tool_calls")

        # 处理连续的assistant消息
        if current_role == 'assistant' and last_role == 'assistant':
            # 智能判断插入什么类型的分隔消息
            if 'tool' in content.lower() or 'function' in content.lower() or 'tool_calls' in message:
                # 如果内容涉及工具调用，插入tool消息
                tool_separator = {
                    "role": "tool",
                    "content": "工具调用已完成",
                    "tool_call_id": f"call_{i}"  # 生成一个临时ID
                }
                fixed_messages.append(tool_separator)
                logger.debug("[MESSAGE_FIX] 在连续assistant消息间插入tool分隔符")
            else:
                # 否则插入user消息
                user_separator = {
                    "role": "user",
                    "content": "请继续分析。"
                }
                fixed_messages.append(user_separator)
                logger.debug("[MESSAGE_FIX] 在连续assistant消息间插入user分隔符")

        fixed_messages.append(message.copy())
        last_role = current_role

    # 检查第一条消息
    if fixed_messages and fixed_messages[0].get('role') == 'assistant':
        # 如果第一条就是assistant消息，在前面添加一个system或user消息
        starter = {
            "role": "system",
            "content": "你是一个专业的投资分析助手。"
        }
        fixed_messages.insert(0, starter)
        logger.debug("[MESSAGE_FIX] 在开头assistant消息前添加system消息")

    # 最终检查：确保消息序列不以单独的assistant消息结尾（除非有tool_calls）
    if len(fixed_messages) > 1:
        last_msg = fixed_messages[-1]
        if last_msg.get('role') == 'assistant' and 'tool_calls' not in last_msg:
            # 如果最后一条消息是assistant但没有tool_calls，添加用户确认
            user_confirm = {
                "role": "user",
                "content": "继续。"
            }
            fixed_messages.append(user_confirm)
            logger.debug("[MESSAGE_FIX] 在末尾assistant消息后添加user确认")

    # 确保有tool_calls的assistant消息后面跟着tool消息
    i = 0
    while i < len(fixed_messages) - 1:
        msg = fixed_messages[i]
        next_msg = fixed_messages[i + 1]

        if msg.get('role') == 'assistant' and 'tool_calls' in msg:
            if next_msg.get('role') != 'tool':
                # 插入一个tool响应
                tool_call_id = msg.get('tool_calls', [{}])[0].get('id') if msg.get('tool_calls') else f"call_{i}"
                tool_response = {
                    "role": "tool",
                    "content": "工具执行完成",
                    "tool_call_id": tool_call_id
                }
                fixed_messages.insert(i + 1, tool_response)
                logger.debug("[MESSAGE_FIX] 在tool_calls后插入tool响应")
                i += 1  # 跳过刚插入的消息
        i += 1

    if len(fixed_messages) != len(messages):
        logger.info(f"[MESSAGE_FIX] 消息序列已修复: {len(messages)} -> {len(fixed_messages)} 条消息")

    return fixed_messages

def validate_conversation_format(messages: list) -> tuple[bool, str]:
    """
    验证对话格式是否符合OpenAI API要求

    Args:
        messages: 消息列表

    Returns:
        (is_valid, error_message)
    """
    if not messages:
        return True, ""

    for i, message in enumerate(messages):
        if not isinstance(message, dict):
            return False, f"消息 {i} 不是字典格式"

        if 'role' not in message:
            return False, f"消息 {i} 缺少role字段"

        if 'content' not in message:
            return False, f"消息 {i} 缺少content字段"

        role = message['role']
        if role not in ['system', 'user', 'assistant', 'tool']:
            return False, f"消息 {i} 包含无效角色: {role}"

        # 检查连续的assistant消息
        if role == 'assistant' and i < len(messages) - 1:
            next_message = messages[i + 1]
            if isinstance(next_message, dict) and next_message.get('role') == 'assistant':
                return False, f"消息 {i} 和 {i+1} 是连续的assistant消息，违反OpenAI API规则"

    return True, ""

class MessageFixingLLMWrapper:
    """
    LLM包装器，自动修复消息格式问题
    增强版：支持更全面的消息拦截和修复
    """
    def __init__(self, llm_instance):
        self.llm = llm_instance
        self._in_fixing = False  # 防止递归修复

    def __getattr__(self, name):
        """代理所有属性和方法调用到底层LLM"""
        attr = getattr(self.llm, name)
        if callable(attr):
            return self._wrap_method(attr)
        return attr

    def invoke(self, messages, **kwargs):
        """兼容性方法：invoke调用实际映射到call方法"""
        return self.call(messages, **kwargs)

    def call(self, messages, **kwargs):
        """主要的LLM调用方法，带消息格式修复"""
        if not self._in_fixing and messages:
            try:
                # 验证并修复消息格式
                is_valid, error_msg = validate_conversation_format(messages)
                if not is_valid:
                    logger.debug(f"[MESSAGE_FIX] 在call中检测到消息格式问题: {error_msg}")  # 改为DEBUG级别
                    self._in_fixing = True
                    fixed_messages = validate_and_fix_message_sequence(messages)
                    logger.info("[MESSAGE_FIX] 已在call中应用消息修复")
                    result = self.llm.call(fixed_messages, **kwargs)
                    self._in_fixing = False
                    return result
            except Exception as e:
                self._in_fixing = False
                logger.debug(f"[MESSAGE_FIX] call方法修复过程出错: {e}")

        return self.llm.call(messages, **kwargs)

    def __call__(self, *args, **kwargs):
        """使包装器可调用，自动修复消息格式"""
        # 尝试从参数中提取消息
        messages = None
        if args and isinstance(args[0], list):
            messages = args[0]
        elif 'messages' in kwargs:
            messages = kwargs['messages']

        if messages and not self._in_fixing:
            try:
                # 验证并修复消息格式
                is_valid, error_msg = validate_conversation_format(messages)
                if not is_valid:
                    logger.debug(f"[MESSAGE_FIX] 在__call__中检测到消息格式问题: {error_msg}")
                    self._in_fixing = True
                    fixed_messages = validate_and_fix_message_sequence(messages)

                    # 更新参数
                    if args and isinstance(args[0], list):
                        args = (fixed_messages,) + args[1:]
                    elif 'messages' in kwargs:
                        kwargs['messages'] = fixed_messages

                    result = self.llm(*args, **kwargs)
                    self._in_fixing = False
                    return result
            except Exception as e:
                self._in_fixing = False
                # 如果修复失败，尝试原始调用
                pass

        return self.llm(*args, **kwargs)

    def _get_attr_with_method_wrapping(self, name):
        """委托所有属性访问给原始LLM，但拦截所有可能的调用方法"""
        attr = getattr(self.llm, name)

        # 拦截所有可能的LLM调用方法，包括LiteLLM内部方法
        intercept_methods = [
            'invoke', 'generate', 'ainvoke', 'agenerate', 'chat', 'complete',
            'completion', 'chat_completion', 'achat_completion', 'acompletion',
            'predict', 'apredict', 'call', 'acall', '_call', '_acall',
            'run', 'arun', 'execute', 'aexecute'
        ]

        if name in intercept_methods and callable(attr):
            return self._wrap_method(attr)

        return attr

    def _wrap_method(self, method):
        """包装方法以支持消息格式修复 - 增强版"""
        def wrapped(*args, **kwargs):
            # 深度检查所有可能包含消息的参数
            messages = None
            messages_key = None
            messages_index = None

            # 检查各种可能的消息传递方式
            possible_message_keys = ['messages', 'prompt', 'input', 'query', 'text']

            # 首先检查位置参数
            for i, arg in enumerate(args):
                if isinstance(arg, list) and len(arg) > 0:
                    # 检查是否是消息列表
                    if isinstance(arg[0], dict) and 'role' in arg[0]:
                        messages = arg
                        messages_index = i
                        break

            # 然后检查关键字参数
            if not messages:
                for key in possible_message_keys:
                    if key in kwargs:
                        value = kwargs[key]
                        if isinstance(value, list) and len(value) > 0:
                            if isinstance(value[0], dict) and 'role' in value[0]:
                                messages = value
                                messages_key = key
                                break

            # 如果找到消息，进行修复
            if messages and not self._in_fixing:
                try:
                    is_valid, error_msg = validate_conversation_format(messages)
                    if not is_valid:
                        logger.debug(f"[MESSAGE_FIX] 在{method.__name__}中棅测到消息格式问题: {error_msg}")
                        self._in_fixing = True
                        fixed_messages = validate_and_fix_message_sequence(messages)

                        # 根据发现位置更新参数
                        if messages_index is not None:
                            # 更新位置参数
                            args = list(args)
                            args[messages_index] = fixed_messages
                            args = tuple(args)
                        elif messages_key is not None:
                            # 更新关键字参数
                            kwargs[messages_key] = fixed_messages

                        logger.info(f"[MESSAGE_FIX] 已在{method.__name__}中应用消息修复")

                        try:
                            result = method(*args, **kwargs)
                            self._in_fixing = False
                            return result
                        except Exception as method_error:
                            self._in_fixing = False
                            # 如果修复后仍然出错，可能是其他问题
                            error_str = str(method_error).lower()
                            if any(keyword in error_str for keyword in [
                                'after assistant message', 'next must be user or tool message'
                            ]):
                                # 仍然是消息格式问题，尝试更激进的修复
                                logger.warning(f"[MESSAGE_FIX] 标准修复后仍有错误，尝试激进修复: {method_error}")
                                final_messages = self._aggressive_message_fix(fixed_messages)

                                if messages_index is not None:
                                    args = list(args)
                                    args[messages_index] = final_messages
                                    args = tuple(args)
                                elif messages_key is not None:
                                    kwargs[messages_key] = final_messages

                                return method(*args, **kwargs)
                            else:
                                raise method_error

                except Exception as fix_error:
                    self._in_fixing = False
                    logger.debug(f"[MESSAGE_FIX] 修复过程出错: {fix_error}")
                    # 修复失败，继续原始调用
                    pass

            return method(*args, **kwargs)

        return wrapped

    def _aggressive_message_fix(self, messages):
        """更激进的消息修复策略"""
        if not messages:
            return messages

        logger.info("[MESSAGE_FIX] 应用激进修复策略")
        fixed = []

        for i, msg in enumerate(messages):
            if not isinstance(msg, dict):
                continue

            role = msg.get('role', '')
            content = msg.get('content', '')

            # 确保内容不为空
            if not content and role != 'system':
                content = f"[{role}消息]"

            fixed_msg = {
                'role': role,
                'content': content
            }

            # 保留其他字段
            for key, value in msg.items():
                if key not in ['role', 'content']:
                    fixed_msg[key] = value

            fixed.append(fixed_msg)

            # 在每个assistant消息后强制插入user消息
            if role == 'assistant' and i < len(messages) - 1:
                next_role = messages[i + 1].get('role') if i + 1 < len(messages) else ''
                if next_role == 'assistant':
                    separator = {
                        'role': 'user',
                        'content': '继续。'
                    }
                    fixed.append(separator)
                    logger.debug("[MESSAGE_FIX] 激进修复：插入强制user分隔符")

        # 确保开头不是assistant
        if fixed and fixed[0].get('role') == 'assistant':
            system_msg = {
                'role': 'system',
                'content': '你是一个专业的投资分析助手。'
            }
            fixed.insert(0, system_msg)
            logger.debug("[MESSAGE_FIX] 激进修复：添加system开头")

        # 确保结尾正确
        if len(fixed) > 1 and fixed[-1].get('role') == 'assistant':
            user_end = {
                'role': 'user',
                'content': '好的。'
            }
            fixed.append(user_end)
            logger.debug("[MESSAGE_FIX] 激进修复：添加user结尾")

        logger.info(f"[MESSAGE_FIX] 激进修复完成: {len(messages)} -> {len(fixed)} 条消息")
        return fixed

    def chat_completion(self, messages, **kwargs):
        """包装chat completion调用，自动修复消息格式"""
        try:
            # 验证消息格式
            is_valid, error_msg = validate_conversation_format(messages)

            if not is_valid:
                logger.debug(f"[MESSAGE_FIX] 检测到消息格式问题: {error_msg}")
                # 修复消息格式
                fixed_messages = validate_and_fix_message_sequence(messages)
                logger.info(f"[MESSAGE_FIX] 消息格式已自动修复")
                return self.llm.chat_completion(fixed_messages, **kwargs)
            else:
                # 消息格式正确，直接调用
                return self.llm.chat_completion(messages, **kwargs)

        except Exception as e:
            # 如果发生错误且包含消息格式相关的错误，尝试修复
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in [
                'after assistant message',
                'next must be user or tool message',
                'invalid message sequence',
                'message format'
            ]):
                logger.warning(f"[MESSAGE_FIX] 捕获到消息格式错误，尝试修复: {e}")
                try:
                    fixed_messages = validate_and_fix_message_sequence(messages)
                    logger.info(f"[MESSAGE_FIX] 消息格式修复后重试")
                    return self.llm.chat_completion(fixed_messages, **kwargs)
                except Exception as retry_error:
                    logger.error(f"[MESSAGE_FIX] 消息修复后仍然失败: {retry_error}")
                    raise retry_error
            else:
                # 非消息格式问题，直接抛出原始异常
                raise e

    def completion(self, **kwargs):
        """包装completion调用（如果LLM支持）"""
        if hasattr(self.llm, 'completion'):
            return self.llm.completion(**kwargs)
        else:
            # 如果不支持completion，尝试转换为chat_completion
            if 'prompt' in kwargs:
                messages = [{"role": "user", "content": kwargs.pop('prompt')}]
                return self.chat_completion(messages, **kwargs)
            return self.llm(**kwargs)

def create_message_fixing_llm(llm_instance):
    """创建支持消息修复的LLM包装器（兼容性保留）"""
    return MessageFixingLLMWrapper(llm_instance)

class ProactiveMessageFixingLLMWrapper:
    """
    主动式消息格式修复LLM包装器
    关键改进：在发送到API之前就构建正确的消息格式，避免400错误
    """
    def __init__(self, llm_instance, provider_type="deepseek"):
        self.llm = llm_instance
        self.provider_type = provider_type.lower()
        self.is_deepseek = self.provider_type == "deepseek"
        self._call_count = 0

        # DeepSeek特殊要求：tool消息前必须有tool_calls
        if self.is_deepseek:
            logger.info("[PROACTIVE_FIX] 启用DeepSeek消息格式主动修复")

    def __getattr__(self, name):
        """代理所有属性和方法调用到底层LLM"""
        attr = getattr(self.llm, name)
        if callable(attr):
            return self._wrap_method(attr, name)
        return attr

    def _construct_proper_message_sequence(self, messages):
        """主动构建符合DeepSeek要求的消息序列"""
        if not messages or not self.is_deepseek:
            return messages

        self._call_count += 1
        logger.debug(f"[PROACTIVE_FIX] 开始构建正确消息序列 (调用#{self._call_count})")

        fixed_messages = []
        i = 0

        while i < len(messages):
            msg = messages[i].copy() if isinstance(messages[i], dict) else messages[i]

            # 确保内容不为空
            if isinstance(msg, dict):
                if not msg.get('content') and msg.get('role') != 'system':
                    msg['content'] = f"[{msg.get('role', 'unknown')}消息]"

                # 核心修复：处理tool消息
                if msg.get('role') == 'tool':
                    # 检查前面是否有对应的tool_calls
                    if not self._has_preceding_tool_calls(fixed_messages):
                        # 主动插入包含tool_calls的assistant消息
                        tool_call_msg = {
                            "role": "assistant",
                            "content": "正在执行工具调用",
                            "tool_calls": [
                                {
                                    "id": msg.get("tool_call_id", f"proactive_call_{self._call_count}_{i}"),
                                    "type": "function",
                                    "function": {
                                        "name": self._infer_tool_name(msg),
                                        "arguments": "{}"
                                    }
                                }
                            ]
                        }
                        fixed_messages.append(tool_call_msg)
                        logger.debug(f"[PROACTIVE_FIX] 主动插入tool_calls消息")

                # 处理连续assistant消息
                elif msg.get('role') == 'assistant' and fixed_messages:
                    last_msg = fixed_messages[-1]
                    if last_msg.get('role') == 'assistant':
                        # 插入user分隔符
                        separator = {
                            "role": "user",
                            "content": "请继续。"
                        }
                        fixed_messages.append(separator)
                        logger.debug(f"[PROACTIVE_FIX] 分离连续assistant消息")

            fixed_messages.append(msg)
            i += 1

        # 确保开头不是assistant（除非有tool_calls）
        if fixed_messages and fixed_messages[0].get('role') == 'assistant':
            if 'tool_calls' not in fixed_messages[0]:
                system_starter = {
                    "role": "system",
                    "content": "你是一个专业的投资分析助手。"
                }
                fixed_messages.insert(0, system_starter)
                logger.debug(f"[PROACTIVE_FIX] 添加system开头消息")

        # 确保有tool_calls的assistant消息后面有tool响应
        self._ensure_tool_call_responses(fixed_messages)

        if len(fixed_messages) != len(messages):
            logger.info(f"[PROACTIVE_FIX] 消息序列主动修复: {len(messages)} -> {len(fixed_messages)} 条消息")

        return fixed_messages

    def _has_preceding_tool_calls(self, messages):
        """检查前面是否有包含tool_calls的assistant消息"""
        for msg in reversed(messages):
            if msg.get('role') == 'assistant':
                return 'tool_calls' in msg
            elif msg.get('role') in ['user', 'system']:
                return False
        return False

    def _infer_tool_name(self, tool_msg):
        """从tool消息内容推断工具名称"""
        content = tool_msg.get('content', '').lower()

        # 常见工具名称推断
        if '股票' in content or 'stock' in content:
            return "get_stock_data"
        elif '新闻' in content or 'news' in content:
            return "get_news"
        elif '分析' in content or 'analysis' in content:
            return "analyze_data"
        elif '搜索' in content or 'search' in content:
            return "search_tool"
        else:
            return "general_tool"

    def _ensure_tool_call_responses(self, messages):
        """确保每个tool_calls都有对应的tool响应"""
        i = 0
        while i < len(messages):
            msg = messages[i]
            if isinstance(msg, dict) and msg.get('role') == 'assistant' and 'tool_calls' in msg:
                # 检查下一条消息是否是tool响应
                if i + 1 < len(messages):
                    next_msg = messages[i + 1]
                    if next_msg.get('role') != 'tool':
                        # 插入tool响应
                        tool_calls = msg.get('tool_calls', [])
                        for j, tool_call in enumerate(tool_calls):
                            tool_response = {
                                "role": "tool",
                                "content": "工具执行完成",
                                "tool_call_id": tool_call.get('id', f"call_{i}_{j}")
                            }
                            messages.insert(i + 1 + j, tool_response)
                        logger.debug(f"[PROACTIVE_FIX] 补充tool响应")
                        i += len(tool_calls)  # 跳过插入的响应
                else:
                    # 在末尾添加tool响应
                    tool_calls = msg.get('tool_calls', [])
                    for tool_call in tool_calls:
                        tool_response = {
                            "role": "tool",
                            "content": "工具执行完成",
                            "tool_call_id": tool_call.get('id', f"call_{i}")
                        }
                        messages.append(tool_response)
                    logger.debug(f"[PROACTIVE_FIX] 在末尾添加tool响应")
            i += 1

    def _wrap_method(self, method, method_name):
        """包装方法以支持主动消息格式修复"""
        def wrapped(*args, **kwargs):
            # 查找并修复消息参数
            args, kwargs = self._fix_messages_in_args(args, kwargs)

            try:
                # 直接调用，因为消息已经预先修复了
                result = method(*args, **kwargs)
                logger.debug(f"[PROACTIVE_FIX] {method_name}调用成功 (无需重试)")
                return result

            except Exception as e:
                # 如果仍然有消息格式错误，记录但不做过多重试
                error_str = str(e).lower()
                if any(keyword in error_str for keyword in [
                    'tool must be a response', 'tool_calls', 'after assistant message'
                ]):
                    logger.warning(f"[PROACTIVE_FIX] 尽管主动修复，仍有格式错误: {e}")
                    # 尝试一次更保守的修复
                    return self._conservative_retry(method, args, kwargs, e)
                else:
                    # 非消息格式问题，直接抛出
                    raise e

        return wrapped

    def _fix_messages_in_args(self, args, kwargs):
        """在参数中查找并修复消息"""
        # 检查位置参数
        args_list = list(args)
        for i, arg in enumerate(args_list):
            if self._is_message_list(arg):
                args_list[i] = self._construct_proper_message_sequence(arg)
        args = tuple(args_list)

        # 检查关键字参数
        message_keys = ['messages', 'prompt', 'input', 'query']
        for key in message_keys:
            if key in kwargs and self._is_message_list(kwargs[key]):
                kwargs[key] = self._construct_proper_message_sequence(kwargs[key])

        return args, kwargs

    def _is_message_list(self, obj):
        """检查对象是否是消息列表"""
        return (isinstance(obj, list) and len(obj) > 0 and
                isinstance(obj[0], dict) and 'role' in obj[0])

    def _conservative_retry(self, method, args, kwargs, original_error):
        """保守的重试策略"""
        logger.info("[PROACTIVE_FIX] 尝试保守重试策略")

        try:
            # 应用最简单的修复：确保基本的user-assistant交替
            args, kwargs = self._apply_minimal_fix(args, kwargs)
            return method(*args, **kwargs)

        except Exception as retry_error:
            logger.error(f"[PROACTIVE_FIX] 保守重试失败: {retry_error}")
            # 抛出原始错误
            raise original_error

    def _apply_minimal_fix(self, args, kwargs):
        """应用最小化修复"""
        # 这里可以实现更简单的消息修复逻辑
        # 目前先返回原参数
        return args, kwargs

    def call(self, messages, **kwargs):
        """主要的call方法"""
        if messages:
            fixed_messages = self._construct_proper_message_sequence(messages)
            return self.llm.call(fixed_messages, **kwargs)
        return self.llm.call(messages, **kwargs)

    def invoke(self, messages, **kwargs):
        """invoke方法（与call等价）"""
        return self.call(messages, **kwargs)

    def __call__(self, *args, **kwargs):
        """使包装器可调用"""
        args, kwargs = self._fix_messages_in_args(args, kwargs)
        return self.llm(*args, **kwargs)

def create_proactive_message_fixing_llm(llm_instance, provider_type="deepseek"):
    """创建支持主动消息格式修复的LLM包装器"""
    return ProactiveMessageFixingLLMWrapper(llm_instance, provider_type)

# 内容长度控制工具函数
def check_and_truncate_content(content: str, max_length: int = 30000) -> str:
    """
    检查并截断内容以符合AI模型长度限制
    为30720字符限制预留一些安全边界
    """
    if not content or not isinstance(content, str):
        return ""
    
    if len(content) <= max_length:
        return content
    
    # 截断内容并添加说明
    truncated = content[:max_length-200]  # 预留200字符给说明
    truncated += f"\n\n[CONTENT_TRUNCATED] 内容已截断，原长度: {len(content)} 字符，当前长度: {len(truncated)} 字符。"
    
    logger.warning(f"[LLM] 内容长度超限已截断: {len(content)} -> {len(truncated)} 字符")
    return truncated

def extract_key_information(content: str, max_length: int = 30000) -> str:
    """
    从长内容中提取关键信息，而不是简单截断
    """
    if len(content) <= max_length:
        return content
    
    # 查找关键信息部分
    key_sections = []
    
    # 保留错误信息部分
    if "[ERROR]" in content:
        error_lines = [line for line in content.split('\n') if "[ERROR]" in line]
        key_sections.extend(error_lines[-5:])  # 最后5个错误
    
    # 保留关键数据部分
    if "股票" in content or "代码" in content:
        data_lines = [line for line in content.split('\n') 
                     if any(keyword in line for keyword in ["股票", "代码", "数据", "分析"])]
        key_sections.extend(data_lines[-10:])  # 最后10个数据行
    
    # 如果没有找到关键信息，使用智能截断
    if not key_sections:
        return check_and_truncate_content(content, max_length)
    
    # 构建精简内容
    extracted = "\n".join(key_sections)
    if len(extracted) > max_length:
        extracted = check_and_truncate_content(extracted, max_length)
    
    extracted += f"\n\n[INFO_EXTRACTED] 已从 {len(content)} 字符中提取关键信息: {len(extracted)} 字符"
    
    logger.info(f"[LLM] 内容智能提取: {len(content)} -> {len(extracted)} 字符")
    return extracted

quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
if not quiet_mode:
    logger.info("[SIMPLE_LLM] 简化的LLM配置管理器已加载 - 统一OpenAI兼容接口")
    logger.info("[SIMPLE_LLM] 已启用内容长度控制功能 - 最大30000字符")