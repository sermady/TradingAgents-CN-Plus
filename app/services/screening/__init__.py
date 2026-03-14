# -*- coding: utf-8 -*-
"""数据库筛选服务模块

提供基于 MongoDB 的股票筛选功能。

导出:
    - DatabaseScreeningService: 筛选服务主类
    - get_database_screening_service: 获取服务实例

示例:
    from app.services.screening import DatabaseScreeningService, get_database_screening_service

    service = get_database_screening_service()
    results, total = await service.screen_stocks(conditions=[...])
"""

from .service import DatabaseScreeningService, get_database_screening_service

__all__ = ["DatabaseScreeningService", "get_database_screening_service"]
