# -*- coding: utf-8 -*-
"""
DataSyncManager - Unified Data Synchronization Manager

Provides a unified interface for all data synchronization operations
across multiple data sources.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_mongo_db
from .models import SyncJob, SyncStatus, DataType
from .status import SyncStatusQueries
from .executor import SyncExecutor

logger = logging.getLogger(__name__)


class DataSyncManager:
    """
    统一数据同步管理器

    提供对所有数据同步操作的统一管理和监控接口。
    """

    def __init__(self):
        self._db: Optional[AsyncIOMotorDatabase] = None
        self._running_jobs: Dict[str, SyncJob] = {}
        self._sync_lock = asyncio.Lock()

    async def _get_db(self) -> AsyncIOMotorDatabase:
        """获取MongoDB连接"""
        if self._db is None:
            self._db = get_mongo_db()
        return self._db

    async def _persist_sync_job(self, job: SyncJob) -> None:
        """持久化同步作业记录"""
        db = await self._get_db()
        collection = db["sync_history"]

        job_data = {
            "job_id": job.id,
            "data_type": job.data_type.value,
            "status": job.status.value,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "total_records": job.total_records,
            "inserted": job.inserted,
            "updated": job.updated,
            "errors": job.errors,
            "data_source": job.data_source,
            "message": job.message,
            "created_by": job.created_by,
        }

        await collection.insert_one(job_data)

        # 更新状态集合
        status_collection = db["sync_status"]
        await status_collection.update_one(
            {"data_type": job.data_type.value}, {"$set": job_data}, upsert=True
        )

    # 状态查询方法（代理到SyncStatusQueries）
    async def get_sync_status(self, data_type: DataType) -> Dict[str, Any]:
        """获取指定数据类型的同步状态"""
        return await SyncStatusQueries.get_sync_status(self, data_type)

    async def get_all_sync_status(self) -> list[Dict[str, Any]]:
        """获取所有数据类型同步状态"""
        return await SyncStatusQueries.get_all_sync_status(self)

    async def get_sync_history(
        self, data_type: Optional[DataType] = None, limit: int = 50
    ) -> list[Dict[str, Any]]:
        """获取同步历史记录"""
        return await SyncStatusQueries.get_sync_history(self, data_type, limit)

    async def get_statistics(self) -> Dict[str, Any]:
        """获取同步统计信息"""
        return await SyncStatusQueries.get_statistics(self)

    async def cleanup_old_history(self, days: int = 30) -> int:
        """清理旧的同步历史记录"""
        return await SyncStatusQueries.cleanup_old_history(self, days)

    # 同步触发和取消
    async def trigger_sync(
        self, data_type: DataType, force: bool = False, created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        触发数据同步

        Args:
            data_type: 数据类型
            force: 是否强制重新同步
            created_by: 触发者

        Returns:
            触发结果信息
        """
        async with self._sync_lock:
            # 检查是否已有运行中的同步
            for job_id, job in self._running_jobs.items():
                if job.data_type == data_type and job.status == SyncStatus.RUNNING:
                    return {
                        "success": False,
                        "message": f"Sync for {data_type.value} is already running",
                        "job_id": job_id,
                    }

            # 创建新的同步作业
            job_id = f"sync_{data_type.value}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            job = SyncJob(
                id=job_id,
                data_type=data_type,
                status=SyncStatus.RUNNING,
                started_at=datetime.now().isoformat(),
                data_source="auto",
                created_by=created_by,
            )
            self._running_jobs[job_id] = job

            # 在后台执行同步
            asyncio.create_task(self._execute_sync(job, force))

            return {
                "success": True,
                "message": f"Sync job started for {data_type.value}",
                "job_id": job_id,
            }

    async def cancel_sync(self, job_id: str) -> Dict[str, Any]:
        """
        取消同步作业

        Args:
            job_id: 作业ID

        Returns:
            取消结果
        """
        if job_id in self._running_jobs:
            job = self._running_jobs[job_id]
            if job.status == SyncStatus.RUNNING:
                job.status = SyncStatus.CANCELLED
                job.finished_at = datetime.now().isoformat()
                job.message = "Cancelled by user"
                return {"success": True, "message": f"Job {job_id} cancelled"}

        return {"success": False, "message": f"Job {job_id} not found or not running"}

    async def _execute_sync(self, job: SyncJob, force: bool) -> None:
        """
        执行同步作业

        Args:
            job: 同步作业
            force: 是否强制重新同步
        """
        try:
            # 根据数据类型选择合适的同步服务
            if job.data_type == DataType.STOCK_BASICS:
                await SyncExecutor.sync_stock_basics(self, job, force)
            elif job.data_type == DataType.STOCK_DAILY:
                await SyncExecutor.sync_stock_daily(self, job, force)
            elif job.data_type == DataType.FUNDAMENTALS:
                await SyncExecutor.sync_fundamentals(self, job, force)
            else:
                job.status = SyncStatus.FAILED
                job.message = f"Unsupported data type: {job.data_type.value}"
                job.errors = 1

        except Exception as e:
            logger.exception(f"Sync job {job.id} failed")
            job.status = SyncStatus.FAILED
            job.message = str(e)
            job.errors = 1
        finally:
            job.finished_at = datetime.now().isoformat()
            await self._persist_sync_job(job)
            self._running_jobs.pop(job.id, None)


# 全局实例
_sync_manager: Optional[DataSyncManager] = None


def get_sync_manager() -> DataSyncManager:
    """获取DataSyncManager单例"""
    global _sync_manager
    if _sync_manager is None:
        _sync_manager = DataSyncManager()
    return _sync_manager
