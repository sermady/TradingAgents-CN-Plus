# -*- coding: utf-8 -*-
"""API分析服务模块

将TradingAgents分析功能包装成API服务。

导出:
    - AnalysisAPIService: API分析服务主类
    - get_analysis_api_service: 获取服务实例的工厂函数
"""

from .service import AnalysisAPIService

# 全局分析服务实例（延迟初始化）
_analysis_api_service_instance = None


def get_analysis_api_service() -> AnalysisAPIService:
    """获取API分析服务实例（延迟初始化）"""
    global _analysis_api_service_instance
    if _analysis_api_service_instance is None:
        _analysis_api_service_instance = AnalysisAPIService()
    return _analysis_api_service_instance


# 向后兼容
get_analysis_service = get_analysis_api_service
AnalysisService = AnalysisAPIService

__all__ = [
    "AnalysisAPIService",
    "get_analysis_api_service",
    # 向后兼容
    "AnalysisService",
    "get_analysis_service",
]
