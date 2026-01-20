# -*- coding: utf-8 -*-
"""
MetricsCollector - System Metrics Collection Service

Collects and aggregates system metrics for monitoring and analysis.

Features:
- System resource monitoring (CPU, memory, disk)
- Application performance metrics (request latency, throughput)
- Business metrics (analysis count, token usage)
- Time-series data storage
- Metrics aggregation and reporting
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_mongo_db
from app.core.unified_config_service import get_config_manager

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型枚举"""

    SYSTEM_CPU = "system_cpu"
    SYSTEM_MEMORY = "system_memory"
    SYSTEM_DISK = "system_disk"
    SYSTEM_NETWORK = "system_network"
    APP_REQUEST_COUNT = "app_request_count"
    APP_REQUEST_LATENCY = "app_request_latency"
    APP_ERROR_COUNT = "app_error_count"
    ANALYSIS_COUNT = "analysis_count"
    ANALYSIS_DURATION = "analysis_duration"
    TOKEN_USAGE = "token_usage"
    CACHE_HIT_RATE = "cache_hit_rate"
    DATA_SYNC_COUNT = "data_sync_count"


@dataclass
class MetricPoint:
    """指标数据点"""

    metric_type: MetricType
    value: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: Dict[str, str] = field(default_factory=dict)
    source: str = "system"


@dataclass
class MetricsSummary:
    """指标汇总信息"""

    metric_type: MetricType
    count: int = 0
    sum: float = 0.0
    avg: float = 0.0
    min: float = 0.0
    max: float = 0.0
    last_value: float = 0.0
    last_updated: Optional[str] = None


class MetricsCollector:
    """
    系统指标收集器

    收集和存储系统及应用程序的各类指标数据。
    """

    def __init__(self):
        self._db: Optional[AsyncIOMotorDatabase] = None
        self._collection_name = "system_metrics"
        self._summary_collection = "metrics_summary"
        self._collection_lock = asyncio.Lock()
        self._initialized = False

    async def _get_db(self) -> AsyncIOMotorDatabase:
        """获取MongoDB连接"""
        if self._db is None:
            self._db = get_mongo_db()
        return self._db

    async def initialize(self) -> None:
        """初始化指标收集器"""
        if self._initialized:
            return

        async with self._collection_lock:
            if self._initialized:
                return

            db = await self._get_db()

            # 创建指标集合
            await db[self._collection_name].create_index(
                [("metric_type", 1), ("timestamp", -1)]
            )
            await db[self._collection_name].create_index("timestamp")

            # 创建汇总集合
            await db[self._summary_collection].create_index("metric_type", unique=True)

            self._initialized = True
            logger.info("MetricsCollector initialized")

    async def record_metric(
        self,
        metric_type: MetricType,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        source: str = "app",
    ) -> None:
        """
        记录单个指标

        Args:
            metric_type: 指标类型
            value: 指标值
            tags: 标签字典
            source: 数据来源
        """
        if not self._initialized:
            await self.initialize()

        db = await self._get_db()

        metric_point = {
            "metric_type": metric_type.value,
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "tags": tags or {},
            "source": source,
        }

        await db[self._collection_name].insert_one(metric_point)

        # 更新汇总
        await self._update_summary(metric_type, value)

    async def record_batch(self, metrics: List[MetricPoint]) -> None:
        """
        批量记录指标

        Args:
            metrics: 指标点列表
        """
        if not self._initialized:
            await self.initialize()

        if not metrics:
            return

        db = await self._get_db()

        documents = []
        for m in metrics:
            documents.append(
                {
                    "metric_type": m.metric_type.value,
                    "value": m.value,
                    "timestamp": m.timestamp,
                    "tags": m.tags,
                    "source": m.source,
                }
            )

        await db[self._collection_name].insert_many(documents)

        # 更新汇总
        for m in metrics:
            await self._update_summary(m.metric_type, m.value)

    async def _update_summary(self, metric_type: MetricType, value: float) -> None:
        """更新指标汇总"""
        db = await self._get_db()

        await db[self._summary_collection].update_one(
            {"metric_type": metric_type.value},
            {
                "$inc": {"count": 1, "sum": value},
                "$min": {"min": value},
                "$max": {"max": value},
                "$set": {
                    "last_value": value,
                    "last_updated": datetime.now().isoformat(),
                },
                "$setOnInsert": {
                    "metric_type": metric_type.value,
                    "avg": value,  # 会在查询时计算
                },
            },
            upsert=True,
        )

    async def query_metrics(
        self,
        metric_type: MetricType,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        查询指标数据

        Args:
            metric_type: 指标类型
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制

        Returns:
            指标数据列表
        """
        if not self._initialized:
            await self.initialize()

        db = await self._get_db()

        query = {"metric_type": metric_type.value}

        if start_time or end_time:
            query["timestamp"] = {}
            if start_time:
                query["timestamp"]["$gte"] = start_time.isoformat()
            if end_time:
                query["timestamp"]["$lte"] = end_time.isoformat()

        results = []
        async for doc in (
            db[self._collection_name].find(query).sort("timestamp", -1).limit(limit)
        ):
            doc["_id"] = str(doc["_id"])
            results.append(doc)

        return results

    async def get_summary(self, metric_type: MetricType) -> Optional[MetricsSummary]:
        """
        获取指标汇总

        Args:
            metric_type: 指标类型

        Returns:
            汇总信息
        """
        if not self._initialized:
            await self.initialize()

        db = await self._get_db()

        doc = await db[self._summary_collection].find_one(
            {"metric_type": metric_type.value}
        )
        if not doc:
            return None

        # 计算平均值
        count = doc.get("count", 0)
        avg = doc.get("sum", 0) / count if count > 0 else 0

        return MetricsSummary(
            metric_type=metric_type,
            count=count,
            sum=doc.get("sum", 0),
            avg=avg,
            min=doc.get("min", 0),
            max=doc.get("max", 0),
            last_value=doc.get("last_value", 0),
            last_updated=doc.get("last_updated"),
        )

    async def get_all_summaries(self) -> List[MetricsSummary]:
        """
        获取所有指标汇总

        Returns:
            汇总信息列表
        """
        if not self._initialized:
            await self.initialize()

        db = await self._get_db()

        results = []
        async for doc in db[self._summary_collection].find({}):
            count = doc.get("count", 0)
            avg = doc.get("sum", 0) / count if count > 0 else 0

            results.append(
                MetricsSummary(
                    metric_type=MetricType(doc["metric_type"]),
                    count=count,
                    sum=doc.get("sum", 0),
                    avg=avg,
                    min=doc.get("min", 0),
                    max=doc.get("max", 0),
                    last_value=doc.get("last_value", 0),
                    last_updated=doc.get("last_updated"),
                )
            )

        return results

    async def get_system_metrics(self) -> Dict[str, Any]:
        """
        获取当前系统指标

        Returns:
            系统指标字典
        """
        metrics = {}

        # CPU使用率
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=1)
            metrics["cpu_percent"] = cpu_percent
            await self.record_metric(MetricType.SYSTEM_CPU, cpu_percent)
        except ImportError:
            metrics["cpu_percent"] = "psutil not installed"

        # 内存使用率
        try:
            memory = psutil.virtual_memory()
            metrics["memory_percent"] = memory.percent
            await self.record_metric(MetricType.SYSTEM_MEMORY, memory.percent)
        except ImportError:
            metrics["memory_percent"] = "psutil not installed"

        # 磁盘使用率
        try:
            disk = psutil.disk_usage("/")
            metrics["disk_percent"] = disk.percent
            await self.record_metric(MetricType.SYSTEM_DISK, disk.percent)
        except ImportError:
            metrics["disk_percent"] = "psutil not installed"

        return metrics

    async def cleanup_old_metrics(self, days: int = 7) -> int:
        """
        清理旧的指标数据

        Args:
            days: 保留天数

        Returns:
            删除的记录数量
        """
        if not self._initialized:
            await self.initialize()

        db = await self._get_db()

        cutoff = datetime.now() - timedelta(days=days)

        result = await db[self._collection_name].delete_many(
            {"timestamp": {"$lt": cutoff.isoformat()}}
        )

        return result.deleted_count

    async def get_health_status(self) -> Dict[str, Any]:
        """
        获取系统健康状态

        Returns:
            健康状态信息
        """
        system_metrics = await self.get_system_metrics()

        # 检查各项指标是否正常
        health = {
            "status": "healthy",
            "cpu_percent": system_metrics.get("cpu_percent"),
            "memory_percent": system_metrics.get("memory_percent"),
            "disk_percent": system_metrics.get("disk_percent"),
            "issues": [],
        }

        # CPU检查
        cpu = health.get("cpu_percent")
        if isinstance(cpu, (int, float)) and cpu > 90:
            health["status"] = "degraded"
            health["issues"].append("High CPU usage")

        # 内存检查
        memory = health.get("memory_percent")
        if isinstance(memory, (int, float)) and memory > 90:
            health["status"] = "degraded"
            health["issues"].append("High memory usage")

        return health


# 全局实例
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """获取MetricsCollector单例"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


# 便捷函数
async def record_analysis_metric(
    analysis_type: str, duration: float, tokens_used: int = 0
) -> None:
    """记录分析指标"""
    collector = get_metrics_collector()
    await collector.record_metric(
        MetricType.ANALYSIS_COUNT, 1, tags={"analysis_type": analysis_type}
    )
    await collector.record_metric(
        MetricType.ANALYSIS_DURATION, duration, tags={"analysis_type": analysis_type}
    )
    if tokens_used > 0:
        await collector.record_metric(
            MetricType.TOKEN_USAGE,
            float(tokens_used),
            tags={"analysis_type": analysis_type},
        )


async def record_request_metric(
    endpoint: str, method: str, duration: float, status_code: int
) -> None:
    """记录请求指标"""
    collector = get_metrics_collector()
    await collector.record_metric(
        MetricType.APP_REQUEST_COUNT,
        1,
        tags={"endpoint": endpoint, "method": method, "status": str(status_code)},
    )
    await collector.record_metric(
        MetricType.APP_REQUEST_LATENCY,
        duration,
        tags={"endpoint": endpoint, "method": method},
    )
    if status_code >= 400:
        await collector.record_metric(
            MetricType.APP_ERROR_COUNT, 1, tags={"endpoint": endpoint, "method": method}
        )
