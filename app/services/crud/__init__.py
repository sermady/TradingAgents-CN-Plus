# -*- coding: utf-8 -*-
"""通用 CRUD 服务模块

提供标准化的 MongoDB CRUD 操作，支持软删除和审计日志。

导出:
    - BaseCRUDService: 基础 CRUD 服务
    - SoftDeleteCRUDService: 支持软删除的 CRUD 服务
    - AuditedCRUDService: 支持审计日志的 CRUD 服务
    - AuditedSoftDeleteCRUDService: 同时支持软删除和审计的 CRUD 服务
    - utils: 工具函数模块
"""

from .base import BaseCRUDService
from .soft_delete import SoftDeleteCRUDService
from .audited import AuditedCRUDService, AuditedSoftDeleteCRUDService
from .utils import to_object_id, build_id_query, add_timestamps

__all__ = [
    "BaseCRUDService",
    "SoftDeleteCRUDService",
    "AuditedCRUDService",
    "AuditedSoftDeleteCRUDService",
    "to_object_id",
    "build_id_query",
    "add_timestamps",
]
