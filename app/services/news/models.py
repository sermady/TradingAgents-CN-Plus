# -*- coding: utf-8 -*-
"""新闻数据服务模型

定义新闻查询参数和统计数据的数据类。
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class NewsQueryParams:
    """新闻查询参数"""
    symbol: Optional[str] = None
    symbols: Optional[List[str]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    category: Optional[str] = None
    sentiment: Optional[str] = None
    importance: Optional[str] = None
    data_source: Optional[str] = None
    keywords: Optional[List[str]] = None
    limit: int = 50
    skip: int = 0
    sort_by: str = "publish_time"
    sort_order: int = -1  # -1 for desc, 1 for asc


@dataclass
class NewsStats:
    """新闻统计信息"""
    total_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    high_importance_count: int = 0
    medium_importance_count: int = 0
    low_importance_count: int = 0
    categories: Dict[str, int] = field(default_factory=dict)
    sources: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        if self.categories is None:
            self.categories = {}
        if self.sources is None:
            self.sources = {}
