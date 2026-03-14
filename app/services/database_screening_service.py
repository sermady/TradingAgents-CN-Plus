# -*- coding: utf-8 -*-
"""基于MongoDB的股票筛选服务 - 向后兼容入口

此文件已重构，所有功能已迁移到 app/services/screening/ 目录下的模块：
- query.py: QueryBuilderMixin (查询条件构建)
- sort.py: SortMixin (排序条件构建)
- enrichment.py: EnrichmentMixin (财务数据填充)
- formatter.py: FormatterMixin (结果格式化)
- service.py: DatabaseScreeningService 主类

为了保持向后兼容，请从 app.services.screening 导入：
    from app.services.screening import DatabaseScreeningService, get_database_screening_service
"""

# 从新的模块位置重新导出所有内容
from app.services.screening import (
    DatabaseScreeningService,
    get_database_screening_service,
)

__all__ = [
    "DatabaseScreeningService",
    "get_database_screening_service",
]
