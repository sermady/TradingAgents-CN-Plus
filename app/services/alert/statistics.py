# -*- coding: utf-8 -*-
"""
Alert统计和历史管理

处理告警查询、确认、解决和历史记录。
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.utils.error_handler import async_handle_errors_none, async_handle_errors_false
from app.services.alert.models import (
    Alert,
    AlertStatus,
    AlertLevel,
    AlertCategory,
    doc_to_alert,
)

logger = logging.getLogger(__name__)


class StatisticsService:
    """告警统计和历史服务"""

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        初始化统计服务

        Args:
            db: MongoDB数据库实例
        """
        self._db = db
        self._alerts_collection = "alerts"
        self._history_collection = "alert_history"

    @async_handle_errors_none(error_message="检查冷却状态失败")
    async def is_in_cooldown(self, rule_id: str) -> bool:
        """检查规则是否在冷却期内"""
        recent_alert = await self._db[self._alerts_collection].find_one(
            {
                "rule_id": rule_id,
                "triggered_at": {
                    "$gte": datetime.now()
                    .fromtimestamp(
                        time.time() - 300  # 默认5分钟冷却
                    )
                    .isoformat()
                },
            }
        )

        return recent_alert is not None

    @async_handle_errors_none(error_message="设置冷却时间失败")
    async def set_cooldown(self, rule_id: str) -> None:
        """设置冷却时间（通过记录最近告警时间实现）"""
        # 冷却由MongoDB查询中的时间窗口控制
        pass

    @async_handle_errors_none(error_message="添加告警历史记录失败")
    async def add_to_history(
        self, alert_id: str, action: str, data: Dict[str, Any]
    ) -> None:
        """添加告警历史记录"""
        history_entry = {
            "alert_id": alert_id,
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }

        await self._db[self._history_collection].insert_one(history_entry)

    async def get_active_alerts(
        self,
        level: Optional[AlertLevel] = None,
        category: Optional[AlertCategory] = None,
        limit: int = 50,
    ) -> List[Alert]:
        """
        获取活跃告警列表

        Args:
            level: 按级别过滤
            category: 按类别过滤
            limit: 返回数量限制

        Returns:
            活跃告警列表（失败时返回空列表）
        """
        try:
            query = {"status": AlertStatus.ACTIVE.value}
            if level:
                query["level"] = level.value
            if category:
                query["category"] = category.value

            alerts = []
            async for doc in (
                self._db[self._alerts_collection]
                .find(query)
                .sort("triggered_at", -1)
                .limit(limit)
            ):
                alerts.append(doc_to_alert(doc))

            return alerts
        except Exception as e:
            logger.error(f"获取活跃告警失败: {e}", exc_info=True)
            return []

    @async_handle_errors_false(error_message="确认告警失败")
    async def acknowledge_alert(
        self, alert_id: str, user_id: Optional[str] = None
    ) -> bool:
        """
        确认告警

        Args:
            alert_id: 告警ID
            user_id: 确认用户

        Returns:
            是否确认成功
        """
        result = await self._db[self._alerts_collection].update_one(
            {"_id": alert_id, "status": AlertStatus.ACTIVE.value},
            {
                "$set": {
                    "status": AlertStatus.ACKNOWLEDGED.value,
                    "acknowledged_at": datetime.now().isoformat(),
                    "acknowledged_by": user_id,
                }
            },
        )

        if result.modified_count > 0:
            await self.add_to_history(alert_id, "acknowledged", {"user_id": user_id})
            return True

        return False

    @async_handle_errors_false(error_message="解决告警失败")
    async def resolve_alert(
        self,
        alert_id: str,
        user_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """
        解决告警

        Args:
            alert_id: 告警ID
            user_id: 解决用户
            notes: 解决备注

        Returns:
            是否解决成功
        """
        result = await self._db[self._alerts_collection].update_one(
            {"_id": alert_id},
            {
                "$set": {
                    "status": AlertStatus.RESOLVED.value,
                    "resolved_at": datetime.now().isoformat(),
                    "resolved_by": user_id,
                }
            },
        )

        if result.modified_count > 0:
            await self.add_to_history(
                alert_id, "resolved", {"user_id": user_id, "notes": notes}
            )
            return True

        return False

    async def get_alert_history(
        self, alert_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取告警历史

        Args:
            alert_id: 告警ID
            limit: 返回数量限制

        Returns:
            历史记录列表（失败时返回空列表）
        """
        try:
            history = []
            async for doc in (
                self._db[self._history_collection]
                .find({"alert_id": alert_id})
                .sort("timestamp", -1)
                .limit(limit)
            ):
                doc["_id"] = str(doc["_id"])
                history.append(doc)

            return history
        except Exception as e:
            logger.error(f"获取告警历史失败: {e}", exc_info=True)
            return []

    async def cleanup_old_alerts(self, days: int = 30) -> int:
        """
        清理旧的已解决告警

        Args:
            days: 保留天数

        Returns:
            删除的记录数量（失败时返回0）
        """
        try:
            cutoff = datetime.now()

            # 只删除已解决的告警
            result = await self._db[self._alerts_collection].delete_many(
                {
                    "status": {
                        "$in": [
                            AlertStatus.RESOLVED.value,
                            AlertStatus.SUPPRESSED.value,
                        ]
                    },
                    "resolved_at": {"$lt": cutoff.isoformat()},
                }
            )

            return result.deleted_count
        except Exception as e:
            logger.error(f"清理旧告警失败: {e}", exc_info=True)
            return 0

    async def get_statistics(self) -> Dict[str, Any]:
        """
        获取告警统计信息

        Returns:
            统计信息（失败时返回空字典）
        """
        try:
            # 统计各状态告警数量
            status_pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
            status_results = (
                await self._db[self._alerts_collection]
                .aggregate_pipeline(status_pipeline)
                .to_list(length=10)
            )

            status_counts = {r["_id"]: r["count"] for r in status_results}

            # 统计各级别告警数量
            level_pipeline = [{"$group": {"_id": "$level", "count": {"$sum": 1}}}]
            level_results = (
                await self._db[self._alerts_collection]
                .aggregate_pipeline(level_pipeline)
                .to_list(length=10)
            )

            level_counts = {r["_id"]: r["count"] for r in level_results}

            return {
                "total_alerts": sum(status_counts.values()),
                "active_alerts": status_counts.get("active", 0),
                "acknowledged_alerts": status_counts.get("acknowledged", 0),
                "resolved_alerts": status_counts.get("resolved", 0),
                "by_level": level_counts,
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}", exc_info=True)
            return {}
