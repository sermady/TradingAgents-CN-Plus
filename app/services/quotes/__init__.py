# -*- coding: utf-8 -*-
"""行情采集服务模块

提供全市场近实时行情的采集、入库和数据回填功能。

导出:
    - QuotesIngestionService: 行情采集服务主类
    - get_quotes_ingestion_service: 获取服务实例的工厂函数
    - normalize_stock_code: 股票代码标准化工具
"""

from .service import QuotesIngestionService, get_quotes_ingestion_service
from .utils import normalize_stock_code

__all__ = [
    "QuotesIngestionService",
    "get_quotes_ingestion_service",
    "normalize_stock_code",
]
