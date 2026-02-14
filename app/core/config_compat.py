# -*- coding: utf-8 -*-
"""
配置系统兼容层

为旧的 tradingagents 库提供配置兼容接口，
使其能够使用新的配置系统而无需修改代码。

⚠️ 此模块仅用于向后兼容，新代码应直接使用 ConfigService
"""

import os
import asyncio
from typing import Dict, Any, Optional, List
import warnings


def _run_async_safely(coro, default=None, warning_msg: Optional[str] = None):
    """
    安全地运行异步协程（用于在同步上下文中调用异步代码）

    Args:
        coro: 异步协程
        default: 如果运行失败返回的默认值
        warning_msg: 失败时的警告消息

    Returns:
        协程结果或默认值
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            if warning_msg:
                warnings.warn(warning_msg, RuntimeWarning)
            return default
        return loop.run_until_complete(coro)
    except Exception as e:
        if warning_msg:
            warnings.warn(f"{warning_msg}: {e}", RuntimeWarning)
        return default


class ConfigManagerCompat:
    """
    ConfigManager 兼容类

    提供与旧 ConfigManager 相同的接口，但使用新的配置系统。
    """

    def __init__(self):
        """初始化兼容层"""
        self._warned = False
        self._emit_deprecation_warning()

    def _emit_deprecation_warning(self):
        """发出废弃警告（仅一次）"""
        if not self._warned:
            warnings.warn(
                "ConfigManagerCompat is a compatibility layer for legacy code. "
                "Please migrate to app.services.config_service.ConfigService. "
                "See docs/DEPRECATION_NOTICE.md for details.",
                DeprecationWarning,
                stacklevel=3,
            )
            self._warned = True

    def _get_config_service(self):
        """获取配置服务（延迟导入避免循环依赖）"""
        from app.services.config_service import config_service
        return config_service

    def get_data_dir(self) -> str:
        """获取数据目录"""
        return os.getenv("DATA_DIR") or "./data"

    def load_settings(self) -> Dict[str, Any]:
        """加载系统设置"""
        config = _run_async_safely(
            self._get_config_service().get_system_config(),
            default=None
        )
        if config and config.system_settings:
            return config.system_settings
        return self._get_default_settings()

    def save_settings(self, settings_dict: Dict[str, Any]) -> bool:
        """保存系统设置"""
        result = _run_async_safely(
            self._get_config_service().update_system_settings(settings_dict),
            default=False,
            warning_msg="Cannot save settings in running event loop"
        )
        return result if result is not None else False

    def get_models(self) -> List[Dict[str, Any]]:
        """获取模型配置列表"""
        config = _run_async_safely(
            self._get_config_service().get_system_config(),
            default=None
        )
        if config and config.llm_configs:
            return [
                {
                    "provider": llm.provider,
                    "model_name": llm.model_name,
                    "api_key": llm.api_key or "",
                    "base_url": llm.api_base,
                    "max_tokens": llm.max_tokens,
                    "temperature": llm.temperature,
                    "enabled": llm.enabled,
                }
                for llm in config.llm_configs
            ]
        return []

    def get_model_config(
        self, provider: str, model_name: str
    ) -> Optional[Dict[str, Any]]:
        """获取指定模型的配置"""
        models = self.get_models()
        return next(
            (m for m in models if m["provider"] == provider and m["model_name"] == model_name),
            None
        )

    def _get_default_settings(self) -> Dict[str, Any]:
        """
        获取默认系统设置

        Returns:
            Dict[str, Any]: 默认设置
        """
        return {
            "max_debate_rounds": 1,
            "max_risk_discuss_rounds": 1,
            "online_tools": True,
            "online_news": True,
            "realtime_data": False,
            "memory_enabled": True,
            "debug": False,
        }


class TokenTrackerCompat:
    """
    TokenTracker 兼容类

    提供与旧 TokenTracker 相同的接口。
    """

    def __init__(self):
        """初始化兼容层"""
        self._usage_data = {}

    def track_usage(
        self,
        provider: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        cost: float = 0.0,
    ):
        """
        记录 Token 使用量

        Args:
            provider: 提供商名称
            model_name: 模型名称
            input_tokens: 输入 Token 数
            output_tokens: 输出 Token 数
            cost: 成本
        """
        key = f"{provider}:{model_name}"

        if key not in self._usage_data:
            self._usage_data[key] = {
                "provider": provider,
                "model_name": model_name,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost": 0.0,
                "call_count": 0,
            }

        self._usage_data[key]["total_input_tokens"] += input_tokens
        self._usage_data[key]["total_output_tokens"] += output_tokens
        self._usage_data[key]["total_cost"] += cost
        self._usage_data[key]["call_count"] += 1

        # 注意：此兼容层仅提供内存缓存，不持久化到数据库
        # 如需持久化，请使用 app.services.llm_service 中的相关功能

    def get_usage_summary(self) -> Dict[str, Any]:
        """
        获取使用统计摘要

        Returns:
            Dict[str, Any]: 使用统计摘要
        """
        return self._usage_data.copy()

    def reset_usage(self):
        """重置使用统计"""
        self._usage_data.clear()


# 创建全局实例（用于向后兼容）
config_manager_compat = ConfigManagerCompat()
token_tracker_compat = TokenTrackerCompat()


# 便捷函数
def get_config_manager() -> ConfigManagerCompat:
    """
    获取配置管理器兼容实例

    Returns:
        ConfigManagerCompat: 配置管理器兼容实例
    """
    return config_manager_compat


def get_token_tracker() -> TokenTrackerCompat:
    """
    获取 Token 跟踪器兼容实例

    Returns:
        TokenTrackerCompat: Token 跟踪器兼容实例
    """
    return token_tracker_compat
