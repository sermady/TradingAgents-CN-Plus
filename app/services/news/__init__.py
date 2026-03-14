# -*- coding: utf-8 -*-
"""新闻数据服务模块

提供统一的新闻数据存储、查询和管理功能。

导出:
    - NewsDataService: 新闻数据服务主类
    - NewsQueryParams: 新闻查询参数
    - NewsStats: 新闻统计信息
    - get_news_data_service: 获取服务实例的工厂函数
    - convert_objectid_to_str: ObjectId转字符串工具
"""

from .service import NewsDataService, get_news_data_service
from .models import NewsQueryParams, NewsStats
from .utils import convert_objectid_to_str, parse_datetime, safe_float

__all__ = [
    "NewsDataService",
    "get_news_data_service",
    "NewsQueryParams",
    "NewsStats",
    "convert_objectid_to_str",
    "parse_datetime",
    "safe_float",
]
