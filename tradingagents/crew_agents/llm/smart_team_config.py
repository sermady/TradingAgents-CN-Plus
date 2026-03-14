# -*- coding: utf-8 -*-
"""
多模型智能团队配置系统
为不同AI角色分配最优模型，提升分析效率和质量
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .simple_config_manager import ProviderType, SimpleLLMConfigManager


class AgentRole(Enum):
    """AI代理角色"""
    MARKET_ANALYST = "market_analyst"           # 市场分析师
    FUNDAMENTAL_ANALYST = "fundamental_analyst"  # 基本面分析师
    TECHNICAL_ANALYST = "technical_analyst"     # 技术分析师
    RISK_MANAGER = "risk_manager"               # 风险管理师
    STRATEGY_ANALYST = "strategy_analyst"       # 策略分析师
    PORTFOLIO_MANAGER = "portfolio_manager"     # 投资组合管理师


@dataclass
class ModelAssignment:
    """模型分配"""
    provider: ProviderType
    model_name: str
    reason: str  # 分配理由


@dataclass
class TeamConfiguration:
    """团队配置"""
    mode: str  # "unified" 或 "smart"
    unified_provider: Optional[ProviderType] = None
    unified_model: Optional[str] = None
    role_assignments: Optional[Dict[AgentRole, ModelAssignment]] = None


class SmartTeamConfig:
    """智能团队配置管理器"""
    
    def __init__(self):
        self.config_manager = SimpleLLMConfigManager()
        self._initialize_role_model_assignments()
    
    def _initialize_role_model_assignments(self):
        """初始化角色-模型分配 - 优先从环境变量读取，否则使用默认配置"""
        self.optimal_assignments = {}
        
        # 角色配置映射：角色名 -> (环境变量前缀, 默认提供商, 默认模型, 分配理由)
        role_configs = {
            AgentRole.MARKET_ANALYST: (
                "SMART_MARKET_ANALYST",
                ProviderType.DEEPSEEK,
                "deepseek-chat",
                "市场分析需要强推理能力和成本效率，DeepSeek-Chat在逻辑推理方面表现优异"
            ),
            AgentRole.FUNDAMENTAL_ANALYST: (
                "SMART_FUNDAMENTAL_ANALYST", 
                ProviderType.DASHSCOPE,
                "qwen-max",
                "基本面分析需要深度理解财务数据，Qwen-Max在中文金融分析方面表现最佳"
            ),
            AgentRole.TECHNICAL_ANALYST: (
                "SMART_TECHNICAL_ANALYST",
                ProviderType.GEMINI,
                "gemini-2.0-flash-exp",
                "技术分析需要处理图表数据，Gemini 2.0 Flash具备优秀的多模态能力"
            ),
            AgentRole.RISK_MANAGER: (
                "SMART_RISK_MANAGER",
                ProviderType.SILICONFLOW,
                "deepseek-ai/DeepSeek-R1",
                "风险管理需要严谨的逻辑推理，DeepSeek-R1在复杂推理任务中表现突出"
            ),
            AgentRole.STRATEGY_ANALYST: (
                "SMART_STRATEGY_ANALYST",
                ProviderType.DASHSCOPE,
                "qwen-plus",
                "策略制定需要综合多维度信息，Qwen-Plus在策略分析方面经验丰富"
            ),
            AgentRole.PORTFOLIO_MANAGER: (
                "SMART_PORTFOLIO_MANAGER",
                ProviderType.SILICONFLOW,
                "deepseek-ai/DeepSeek-V3",
                "投资组合管理涉及复杂计算，DeepSeek-V3在数学推理方面能力强大"
            )
        }
        
        # 为每个角色创建配置
        for role, (env_prefix, default_provider, default_model, default_reason) in role_configs.items():
            # 尝试从环境变量读取配置
            env_provider = os.getenv(f"{env_prefix}_PROVIDER", "").strip().upper()
            env_model = os.getenv(f"{env_prefix}_MODEL", "").strip()
            
            # 确定使用的提供商和模型
            if env_provider and env_model:
                try:
                    # 验证提供商是否有效
                    provider = ProviderType(env_provider.lower())
                    model_name = env_model
                    reason = f"环境变量配置: {env_provider}/{env_model}"
                    source = "环境变量"
                except ValueError:
                    # 无效的提供商，使用默认配置
                    provider = default_provider
                    model_name = default_model
                    reason = f"默认配置(无效环境变量): {default_reason}"
                    source = "默认配置"
            else:
                # 使用默认配置
                provider = default_provider
                model_name = default_model
                reason = f"默认配置: {default_reason}"
                source = "默认配置"
            
            # 创建模型分配
            self.optimal_assignments[role] = ModelAssignment(
                provider=provider,
                model_name=model_name,
                reason=reason
            )
            
            # 静默模式下不输出调试信息
            quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
            if not quiet_mode:
                print(f"[SMART_CONFIG] {role.value}: {source} -> {provider.value}/{model_name}")
    
    def get_team_configuration(self) -> TeamConfiguration:
        """获取当前团队配置"""
        provider_env = os.getenv('PROVIDER', '').upper()
        
        if provider_env == 'SMART':
            # 智能模式：使用角色特定模型
            return TeamConfiguration(
                mode="smart",
                role_assignments=self.optimal_assignments
            )
        else:
            # 统一模式：所有角色使用相同模型
            config = self.config_manager.get_openai_compatible_config()
            provider_type = ProviderType(config['provider'].lower())
            
            return TeamConfiguration(
                mode="unified",
                unified_provider=provider_type,
                unified_model=config['model']
            )
    
    def get_model_for_role(self, role: AgentRole) -> Dict[str, Any]:
        """获取指定角色的模型配置"""
        team_config = self.get_team_configuration()
        
        if team_config.mode == "smart" and team_config.role_assignments:
            # 智能模式：返回角色特定模型
            assignment = team_config.role_assignments.get(role)
            if assignment:
                # 创建临时配置管理器获取该提供商的配置
                temp_manager = SimpleLLMConfigManager()
                
                # 临时设置环境变量获取配置
                original_provider = os.getenv('PROVIDER', '')
                os.environ['PROVIDER'] = assignment.provider.value.upper()
                
                try:
                    config = temp_manager._load_provider_based_config()
                    if config:
                        # 返回字典格式而非ModelConfig对象
                        return {
                            'provider': config.provider.value,
                            'model': assignment.model_name,  # 使用分配的具体模型
                            'api_key': config.api_key,
                            'base_url': config.base_url,
                            'assignment_reason': assignment.reason
                        }
                    else:
                        # 配置加载失败，使用基本信息
                        return {
                            'provider': assignment.provider.value,
                            'model': assignment.model_name,
                            'api_key': '',
                            'base_url': '',
                            'assignment_reason': f"配置加载失败: {assignment.reason}"
                        }
                finally:
                    # 恢复原始设置
                    if original_provider:
                        os.environ['PROVIDER'] = original_provider
                    else:
                        os.environ.pop('PROVIDER', None)
        
        # 统一模式或智能模式回退：使用统一配置
        config = self.config_manager.get_openai_compatible_config()
        config['assignment_reason'] = f"统一模式使用 {config['provider']}/{config['model']}"
        return config
    
    def get_crewai_llm_for_role(self, role: AgentRole):
        """获取指定角色的CrewAI LLM对象"""
        config = self.get_model_for_role(role)
        
        # 角色名称中文映射
        role_names = {
            "market_analyst": "市场分析师",
            "fundamental_analyst": "基本面分析师", 
            "technical_analyst": "技术分析师",
            "risk_manager": "风险管理师",
            "strategy_analyst": "策略分析师",
            "portfolio_manager": "投资组合管理师"
        }
        
        chinese_name = role_names.get(role.value, role.value)
        provider = config['provider']
        model = config['model']
        
        # 显示详细的LLM调用信息
        quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
        if not quiet_mode:
            print(f"[SMART_TEAM] 👤 {chinese_name} -> {provider.upper()}/{model} -> 正在初始化AI模型")
        
        # 根据提供商创建LLM对象
        provider = config['provider'].lower()
        
        if provider == 'deepseek':
            from crewai import LLM
            return LLM(
                model=f"deepseek/{config['model']}",
                api_key=config['api_key'],
                base_url=config.get('base_url')
            )
        elif provider == 'dashscope':
            from crewai import LLM
            return LLM(
                model=f"openai/{config['model']}",
                api_key=config['api_key'],
                base_url=config.get('base_url', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
            )
        elif provider == 'gemini':
            from crewai import LLM
            return LLM(
                model=f"gemini/{config['model']}",
                api_key=config['api_key']
            )
        elif provider == 'siliconflow':
            from crewai import LLM
            # 设置环境变量（SiliconFlow需要OpenAI兼容模式）
            os.environ['OPENAI_API_KEY'] = config['api_key']
            os.environ['OPENAI_API_BASE'] = config['base_url']
            return LLM(
                model=f"openai/{config['model']}",
                api_key=config['api_key'],
                base_url=config['base_url'],
                provider="openai"
            )
        else:
            # 其他提供商使用原有逻辑
            return self.config_manager.get_crewai_llm_object()
    
    def get_team_summary(self) -> Dict[str, Any]:
        """获取团队配置总结"""
        team_config = self.get_team_configuration()
        
        summary = {
            "mode": team_config.mode,
            "total_roles": len(AgentRole),
            "configurations": {}
        }
        
        if team_config.mode == "unified":
            # 统一模式信息
            summary["unified_provider"] = team_config.unified_provider.value if team_config.unified_provider else "unknown"
            summary["unified_model"] = team_config.unified_model or "unknown"
            
            for role in AgentRole:
                config = self.get_model_for_role(role)
                summary["configurations"][role.value] = {
                    "provider": config["provider"],
                    "model": config["model"],
                    "reason": config.get("assignment_reason", "统一配置")
                }
        else:
            # 智能模式信息
            summary["providers_used"] = set()
            summary["models_used"] = set()
            
            for role in AgentRole:
                config = self.get_model_for_role(role)
                summary["configurations"][role.value] = {
                    "provider": config["provider"],
                    "model": config["model"],
                    "reason": config.get("assignment_reason", "智能分配")
                }
                
                summary["providers_used"].add(config["provider"])
                summary["models_used"].add(f"{config['provider']}/{config['model']}")
            
            summary["providers_used"] = list(summary["providers_used"])
            summary["models_used"] = list(summary["models_used"])
        
        return summary
    
    def validate_smart_mode_requirements(self) -> Dict[str, Any]:
        """验证智能模式所需的环境配置"""
        validation = {
            "valid": True,
            "missing_configs": [],
            "invalid_configs": [],
            "warnings": [],
            "provider_status": {},
            "role_config_status": {}
        }
        
        # 检查角色配置的有效性
        for role, assignment in self.optimal_assignments.items():
            role_name = role.value
            provider_name = assignment.provider.value.upper()
            model_name = assignment.model_name
            
            # 检查API密钥
            api_key_env = f"{provider_name}_API_KEY"
            if not os.getenv(api_key_env):
                validation["valid"] = False
                validation["missing_configs"].append(api_key_env)
                validation["provider_status"][assignment.provider.value] = "missing_api_key"
            else:
                validation["provider_status"][assignment.provider.value] = "configured"
            
            # 检查模型是否在提供商的模型列表中
            models_env = f"{provider_name}_MODELS"
            available_models = os.getenv(models_env, "")
            if available_models:
                model_list = [m.strip() for m in available_models.split(",")]
                if model_name not in model_list:
                    validation["invalid_configs"].append(f"{role_name}: 模型 '{model_name}' 不在 {provider_name} 的可用模型列表中")
                    validation["role_config_status"][role_name] = "invalid_model"
                else:
                    validation["role_config_status"][role_name] = "valid"
            else:
                validation["warnings"].append(f"{models_env}未配置，无法验证{role_name}的模型有效性")
                validation["role_config_status"][role_name] = "unverified"
        
        # 检查环境变量配置完整性
        role_env_prefixes = [
            "SMART_MARKET_ANALYST", "SMART_FUNDAMENTAL_ANALYST", "SMART_TECHNICAL_ANALYST",
            "SMART_RISK_MANAGER", "SMART_STRATEGY_ANALYST", "SMART_PORTFOLIO_MANAGER"
        ]
        
        for prefix in role_env_prefixes:
            provider_env = f"{prefix}_PROVIDER"
            model_env = f"{prefix}_MODEL"
            
            if not os.getenv(provider_env) or not os.getenv(model_env):
                validation["warnings"].append(f"{prefix} 环境变量配置不完整，使用默认配置")
        
        # 如果有无效配置，整体验证失败
        if validation["invalid_configs"]:
            validation["valid"] = False
        
        return validation
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """获取完整的配置总结信息"""
        summary = self.get_team_summary()
        validation = self.validate_smart_mode_requirements()
        
        return {
            "team_info": summary,
            "validation": validation,
            "config_source": "environment_variables" if any(
                os.getenv(f"SMART_{role.name}_PROVIDER") for role in AgentRole
            ) else "defaults"
        }


# 全局实例
smart_team_config = SmartTeamConfig()


def get_agent_llm(role: AgentRole):
    """便捷函数：获取指定角色的LLM对象"""
    return smart_team_config.get_crewai_llm_for_role(role)


def get_team_info() -> Dict[str, Any]:
    """便捷函数：获取团队配置信息"""
    return smart_team_config.get_team_summary()


def validate_smart_setup() -> Dict[str, Any]:
    """便捷函数：验证智能模式配置"""
    return smart_team_config.validate_smart_mode_requirements()


if __name__ == "__main__":
    # 测试代码
    print("=== 智能团队配置测试 ===")
    
    # 获取团队信息
    team_info = get_team_info()
    print(f"当前模式: {team_info['mode']}")
    print(f"角色数量: {team_info['total_roles']}")
    
    if team_info['mode'] == 'smart':
        print(f"使用提供商数量: {len(team_info.get('providers_used', []))}")
        print(f"使用模型数量: {len(team_info.get('models_used', []))}")
    
    # 验证智能模式配置
    validation = validate_smart_setup()
    print(f"\n智能模式配置有效性: {validation['valid']}")
    
    if validation['missing_configs']:
        print(f"缺失配置: {validation['missing_configs']}")
    
    print("\n各角色模型配置:")
    for role in AgentRole:
        config = smart_team_config.get_model_for_role(role)
        print(f"{role.value}: {config['provider']}/{config['model']}")
        print(f"  理由: {config.get('assignment_reason', '未知')}")