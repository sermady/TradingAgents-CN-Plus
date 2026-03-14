# -*- coding: utf-8 -*-
"""同步状态查询模块

提供同步状态查询和历史记录功能。
"""

from typing import Dict, Any, List, Optional, TYPE_CHECKING

from app.utils.error_handler import (
    async_handle_errors_empty_dict,
    async_handle_errors_empty_list,
    async_handle_errors_zero,
)

if TYPE_CHECKING:
    from .manager import DataSyncManager


class SyncStatusQueries:
    """同步状态查询器"""

    @staticmethod
    @async_handle_errors_empty_dict(error_message="获取同步状态失败")
    async def get_sync_status(manager: "DataSyncManager", data_type) -> Dict[str, Any]:
        """
        获取指定数据类型的同步状态

        Args:
            manager: 数据同步管理器
            data_type: 数据类型

        Returns:
            同步状态信息字典
        """
        db = await manager._get_db()
        collection = db["sync_status"]

        result = await collection.find_one({"data_type": data_type.value})
        if result:
            result.pop("_id", None)
            return result

        return {"data_type": data_type.value, "status": "never_run", "last_sync": None}

    @staticmethod
    @async_handle_errors_empty_list(error_message="获取所有同步状态失败")
    async def get_all_sync_status(manager: "DataSyncManager") -> List[Dict[str, Any]]:
        """
        获取所有数据类型同步状态

        Returns:
            所有数据类型的同步状态列表
        """
        db = await manager._get_db()
        collection = db["sync_status"]

        results = []
        async for doc in collection.find({}):
            doc.pop("_id", None)
            results.append(doc)

        return results

    @staticmethod
    @async_handle_errors_empty_list(error_message="获取同步历史记录失败")
    async def get_sync_history(
        manager: "DataSyncManager", data_type=None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取同步历史记录

        Args:
            manager: 数据同步管理器
            data_type: 可选的数据类型过滤
            limit: 返回记录数量限制

        Returns:
            同步历史记录列表
        """
        db = await manager._get_db()
        collection = db["sync_history"]

        query = {}
        if data_type:
            query["data_type"] = data_type.value

        results = []
        async for doc in collection.find(query).sort("started_at", -1).limit(limit):
            doc.pop("_id", None)
            results.append(doc)

        return results

    @staticmethod
    @async_handle_errors_empty_dict(error_message="获取同步统计信息失败")
    async def get_statistics(manager: "DataSyncManager") -> Dict[str, Any]:
        """
        获取同步统计信息

        Returns:
            统计信息字典
        """
        db = await manager._get_db()
        history_collection = db["sync_history"]

        # 统计历史记录
        total_jobs = await history_collection.count_documents({})
        completed_jobs = await history_collection.count_documents(
            {"status": "completed"}
        )
        failed_jobs = await history_collection.count_documents({"status": "failed"})

        # 统计总记录数
        pipeline = [{"$group": {"_id": None, "total": {"$sum": "$inserted"}}}]
        result = await history_collection.aggregate(pipeline).to_list(length=1)
        total_records = result[0]["total"] if result else 0

        # 获取最近同步时间
        last_sync = await history_collection.find_one({}, sort=[("started_at", -1)])

        # 统计数据源使用情况
        source_pipeline = [{"$group": {"_id": "$data_source", "count": {"$sum": 1}}}]
        source_results = await history_collection.aggregate(
            source_pipeline
        ).to_list(length=100)
        source_usage = {r["_id"]: r["count"] for r in source_results if r["_id"]}

        return {
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "total_records_synced": total_records,
            "last_sync_time": last_sync["started_at"] if last_sync else None,
            "data_source_usage": source_usage,
            "success_rate": round(completed_jobs / total_jobs * 100, 2)
            if total_jobs > 0
            else 0,
        }

    @staticmethod
    @async_handle_errors_zero(error_message="清理旧同步历史记录失败")
    async def cleanup_old_history(manager: "DataSyncManager", days: int = 30) -> int:
        """
        清理旧的同步历史记录

        Args:
            manager: 数据同步管理器
            days: 保留天数

        Returns:
            删除的记录数量
        """
        db = await manager._get_db()
        collection = db["sync_history"]

        cutoff_date = datetime.now()

        result = await collection.delete_many(
            {"finished_at": {"$lt": cutoff_date.isoformat()}}
        )

        return result.deleted_count


from datetime import datetime
