# -*- coding: utf-8 -*-
"""模型能力管理服务模块

提供模型能力评估、验证和推荐功能。

导出:
    - ModelCapabilityService: 模型能力管理服务主类
    - get_model_capability_service: 获取服务实例的工厂函数
"""

from .service import ModelCapabilityService, get_model_capability_service

__all__ = [
    "ModelCapabilityService",
    "get_model_capability_service",
]
