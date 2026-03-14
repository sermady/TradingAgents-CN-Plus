# -*- coding: utf-8 -*-
"""数据同步模型模块

提供同步相关的数据类和枚举。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional


class SyncStatus(Enum):
    """同步状态枚举"""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DataType(Enum):
    """支持的数据类型"""

    STOCK_BASICS = "stock_basics"
    STOCK_DAILY = "stock_daily"
    STOCK_MINUTE = "stock_minute"
    FUNDAMENTALS = "fundamentals"
    INDEX_BASICS = "index_basics"
    INDEX_DAILY = "index_daily"
    NEWS = "news"
    SOCIAL_MEDIA = "social_media"


@dataclass
class SyncJob:
    """同步作业信息"""

    id: str
    data_type: DataType
    status: SyncStatus
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    total_records: int = 0
    inserted: int = 0
    updated: int = 0
    errors: int = 0
    skipped: int = 0  # 新增字段
    data_source: str = "auto"
    message: Optional[str] = None
    created_by: Optional[str] = None


@dataclass
class SyncStatistics:
    """同步统计信息"""

    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    total_records_synced: int = 0
    last_sync_time: Optional[str] = None
    data_source_usage: Dict[str, int] = field(default_factory=dict)
