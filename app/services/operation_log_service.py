# -*- coding: utf-8 -*-
"""
操作日志服务

使用 BaseCRUDService 基类重构，复用标准 CRUD 方法。
保留复杂查询和统计逻辑。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from app.services.crud import BaseCRUDService
from app.core.database import get_mongo_db
from app.models.operation_log import (
    OperationLogCreate,
    OperationLogResponse,
    OperationLogQuery,
    OperationLogStats,
    convert_objectid_to_str,
)
from app.utils.timezone import now_tz

logger = logging.getLogger("webapi")


class OperationLogService(BaseCRUDService):
    """操作日志服务

    继承 BaseCRUDService 获得标准 CRUD 操作。
    保留复杂查询和聚合统计逻辑。
    """

    @property
    def collection_name(self) -> str:
        """MongoDB 集合名称"""
        return "operation_logs"

    async def create_log(
        self,
        user_id: str,
        username: str,
        log_data: OperationLogCreate,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[str]:
        """创建操作日志"""
        # 使用 naive datetime（不带时区信息），MongoDB 会按原样存储
        current_time = now_tz().replace(tzinfo=None)

        doc_id = await self.create({
            "user_id": user_id,
            "username": username,
            "action_type": log_data.action_type,
            "action": log_data.action,
            "details": log_data.details or {},
            "success": log_data.success,
            "error_message": log_data.error_message,
            "duration_ms": log_data.duration_ms,
            "ip_address": ip_address or log_data.ip_address,
            "user_agent": user_agent or log_data.user_agent,
            "session_id": log_data.session_id,
            "timestamp": current_time,
            "created_at": current_time
        })

        if doc_id:
            logger.info(f"[LOG] 操作日志已记录: {username} - {log_data.action}")
        return doc_id

    async def get_logs(self, query: OperationLogQuery) -> Tuple[List[OperationLogResponse], int]:
        """获取操作日志列表（保留复杂查询逻辑）"""
        # 构建查询条件
        filter_query = {}

        # 时间范围筛选
        if query.start_date or query.end_date:
            time_filter = {}
            if query.start_date:
                start_str = query.start_date.replace('Z', '')
                time_filter["$gte"] = datetime.fromisoformat(start_str)
            if query.end_date:
                end_str = query.end_date.replace('Z', '')
                time_filter["$lte"] = datetime.fromisoformat(end_str)
            filter_query["timestamp"] = time_filter

        # 操作类型筛选
        if query.action_type:
            filter_query["action_type"] = query.action_type

        # 成功状态筛选
        if query.success is not None:
            filter_query["success"] = query.success

        # 用户筛选
        if query.user_id:
            filter_query["user_id"] = query.user_id

        # 关键词搜索
        if query.keyword:
            filter_query["$or"] = [
                {"action": {"$regex": query.keyword, "$options": "i"}},
                {"username": {"$regex": query.keyword, "$options": "i"}},
                {"details.stock_symbol": {"$regex": query.keyword, "$options": "i"}}
            ]

        # 使用基类的 count 和 list 方法
        total = await self.count(filter_query)
        skip = (query.page - 1) * query.page_size
        docs = await super().list(
            filters=filter_query,
            sort=[("timestamp", -1)],
            skip=skip,
            limit=query.page_size
        )

        logs = []
        for doc in docs:
            doc = convert_objectid_to_str(doc)
            logs.append(OperationLogResponse(**doc))

        logger.info(f"[LOG] 获取操作日志: 总数={total}, 返回={len(logs)}")
        return logs, total

    async def get_stats(self, days: int = 30) -> OperationLogStats:
        """获取操作日志统计（保留聚合逻辑）"""
        try:
            db = await self._get_db()

            # 时间范围
            start_date = now_tz() - timedelta(days=days)
            time_filter = {"timestamp": {"$gte": start_date}}

            # 基础统计
            total_logs = await self.count(time_filter)
            success_logs = await self.count({**time_filter, "success": True})
            failed_logs = total_logs - success_logs
            success_rate = (success_logs / total_logs * 100) if total_logs > 0 else 0

            # 操作类型分布（聚合管道）
            action_type_pipeline = [
                {"$match": time_filter},
                {"$group": {"_id": "$action_type", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            action_type_distribution = {}
            async for doc in db[self.collection_name].aggregate(action_type_pipeline):
                action_type_distribution[doc["_id"]] = doc["count"]

            # 小时分布统计
            hourly_pipeline = [
                {"$match": time_filter},
                {"$group": {"_id": {"$hour": "$timestamp"}, "count": {"$sum": 1}}},
                {"$sort": {"_id": 1}}
            ]
            hourly_data = {i: 0 for i in range(24)}
            async for doc in db[self.collection_name].aggregate(hourly_pipeline):
                hourly_data[doc["_id"]] = doc["count"]

            hourly_distribution = [
                {"hour": f"{hour:02d}:00", "count": count}
                for hour, count in hourly_data.items()
            ]

            stats = OperationLogStats(
                total_logs=total_logs,
                success_logs=success_logs,
                failed_logs=failed_logs,
                success_rate=round(success_rate, 2),
                action_type_distribution=action_type_distribution,
                hourly_distribution=hourly_distribution
            )

            logger.info(f"[LOG] 统计: 总数={total_logs}, 成功率={success_rate:.1f}%")
            return stats

        except Exception as e:
            logger.error(f"获取操作日志统计失败: {e}")
            raise

    async def clear_logs(self, days: Optional[int] = None, action_type: Optional[str] = None) -> Dict[str, Any]:
        """清空操作日志"""
        delete_filter = {}

        if days is not None:
            cutoff_date = datetime.now() - timedelta(days=days)
            delete_filter["timestamp"] = {"$lt": cutoff_date}

        if action_type:
            delete_filter["action_type"] = action_type

        # 使用基类的 delete_by_field 或自定义删除
        deleted_count = await self._delete_many(delete_filter)

        logger.info(f"[LOG] 清空操作日志: 删除了 {deleted_count} 条记录")
        return {"deleted_count": deleted_count, "filter": delete_filter}

    async def _delete_many(self, filter_query: Dict[str, Any]) -> int:
        """批量删除（内部方法）"""
        try:
            db = await self._get_db()
            result = await db[self.collection_name].delete_many(filter_query)
            return result.deleted_count
        except Exception as e:
            logger.error(f"批量删除失败: {e}")
            return 0

    async def get_log_by_id(self, log_id: str) -> Optional[OperationLogResponse]:
        """根据ID获取操作日志"""
        doc = await self.get_by_id(log_id)
        if not doc:
            return None

        doc = convert_objectid_to_str(doc)
        return OperationLogResponse(**doc)


# 全局服务实例
_operation_log_service: Optional[OperationLogService] = None


def get_operation_log_service() -> OperationLogService:
    """获取操作日志服务实例"""
    global _operation_log_service
    if _operation_log_service is None:
        _operation_log_service = OperationLogService()
    return _operation_log_service


# 便捷函数
async def log_operation(
    user_id: str,
    username: str,
    action_type: str,
    action: str,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    duration_ms: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_id: Optional[str] = None
) -> Optional[str]:
    """记录操作日志的便捷函数"""
    service = get_operation_log_service()
    log_data = OperationLogCreate(
        action_type=action_type,
        action=action,
        details=details,
        success=success,
        error_message=error_message,
        duration_ms=duration_ms,
        ip_address=ip_address,
        user_agent=user_agent,
        session_id=session_id
    )
    return await service.create_log(user_id, username, log_data, ip_address, user_agent)
