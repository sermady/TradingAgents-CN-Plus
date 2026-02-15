# -*- coding: utf-8 -*-
"""
通知服务：持久化 + 列表 + 已读 + WebSocket 发布

使用 BaseCRUDService 基类重构，减少重复代码约 50%。
"""
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from app.services.base_crud_service import BaseCRUDService
from app.core.database import get_mongo_db
from app.models.notification import (
    NotificationCreate, NotificationOut, NotificationList
)
from app.utils.timezone import now_tz

logger = logging.getLogger("webapi.notifications")


class NotificationsService(BaseCRUDService):
    """通知服务

    继承 BaseCRUDService 获得标准 CRUD 操作，
    同时保留 WebSocket 发布、清理策略等业务逻辑。
    """

    @property
    def collection_name(self) -> str:
        """MongoDB 集合名称"""
        return "notifications"

    def __init__(self):
        super().__init__()
        self.channel_prefix = "notifications:"
        self.retain_days = 90
        self.max_per_user = 1000

    async def _ensure_indexes(self):
        """确保索引创建"""
        try:
            db = await self._get_db()
            await db[self.collection_name].create_index([("user_id", 1), ("created_at", -1)])
            await db[self.collection_name].create_index([("user_id", 1), ("status", 1)])
        except Exception as e:
            logger.warning(f"创建索引失败(忽略): {e}")

    # ===== 业务方法 =====

    async def create_and_publish(self, payload: NotificationCreate) -> Optional[str]:
        """创建通知并发布到 WebSocket"""
        await self._ensure_indexes()

        # 使用基类的 create 方法
        doc_id = await self.create({
            "user_id": payload.user_id,
            "type": payload.type,
            "title": payload.title,
            "content": payload.content,
            "link": payload.link,
            "source": payload.source,
            "severity": payload.severity or "info",
            "status": "unread",
            "metadata": payload.metadata or {},
            "created_at": now_tz(),
        })

        if not doc_id:
            logger.error("创建通知失败")
            return None

        # 构建发布数据
        payload_to_publish = {
            "id": doc_id,
            "type": payload.type,
            "title": payload.title,
            "content": payload.content,
            "link": payload.link,
            "source": payload.source,
            "status": "unread",
            "created_at": now_tz().isoformat(),
        }

        # 使用 WebSocket 发送通知
        try:
            from app.routers.websocket_notifications import send_notification_via_websocket
            await send_notification_via_websocket(payload.user_id, payload_to_publish)
            logger.debug(f"✅ [WS] 通知已通过 WebSocket 发送: user={payload.user_id}")
        except Exception as e:
            logger.warning(f"⚠️ [WS] WebSocket 发送失败: {e}")

        # 清理策略：保留最近N天/最多M条
        await self._cleanup_old_notifications(payload.user_id)

        return doc_id

    async def _cleanup_old_notifications(self, user_id: str):
        """清理旧通知"""
        try:
            db = await self._get_db()

            # 删除超过保留天数的通知
            cutoff_date = now_tz() - timedelta(days=self.retain_days)
            await db[self.collection_name].delete_many({
                "user_id": user_id,
                "created_at": {"$lt": cutoff_date}
            })

            # 超过配额按时间删旧
            count = await self.count({"user_id": user_id})
            if count > self.max_per_user:
                skip = count - self.max_per_user
                ids = []
                async for d in db[self.collection_name].find(
                    {"user_id": user_id}, {"_id": 1}
                ).sort("created_at", 1).limit(skip):
                    ids.append(d["_id"])
                if ids:
                    await db[self.collection_name].delete_many({"_id": {"$in": ids}})

        except Exception as e:
            logger.warning(f"通知清理失败(忽略): {e}")

    async def unread_count(self, user_id: str) -> int:
        """获取未读通知数量"""
        return await self.count({"user_id": user_id, "status": "unread"})

    async def list(
        self,
        user_id: str,
        *,
        status: Optional[str] = None,
        ntype: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> NotificationList:
        """获取通知列表"""
        filters: Dict[str, Any] = {"user_id": user_id}

        if status in ("read", "unread"):
            filters["status"] = status
        if ntype in ("analysis", "alert", "system"):
            filters["type"] = ntype

        # 使用基类的 list 方法
        total = await self.count(filters)
        docs = await super().list(
            filters=filters,
            sort=[("created_at", -1)],
            skip=(page - 1) * page_size,
            limit=page_size
        )

        items: List[NotificationOut] = []
        for d in docs:
            items.append(NotificationOut(
                id=d.get("id"),
                type=d.get("type"),
                title=d.get("title"),
                content=d.get("content"),
                link=d.get("link"),
                source=d.get("source"),
                status=d.get("status", "unread"),
                created_at=d.get("created_at") or now_tz(),
            ))

        return NotificationList(items=items, total=total, page=page, page_size=page_size)

    async def mark_read(self, user_id: str, notif_id: str) -> bool:
        """标记单条通知为已读"""
        # 先验证通知是否存在且属于该用户
        doc = await self.get_by_id(notif_id)
        if not doc or doc.get("user_id") != user_id:
            return False

        return await self.update(notif_id, {"status": "read"})

    async def mark_all_read(self, user_id: str) -> int:
        """标记用户所有通知为已读"""
        try:
            db = await self._get_db()
            res = await db[self.collection_name].update_many(
                {"user_id": user_id, "status": "unread"},
                {"$set": {"status": "read", "updated_at": now_tz()}}
            )
            return res.modified_count
        except Exception as e:
            logger.error(f"标记全部已读失败: {e}")
            return 0


_notifications_service: Optional[NotificationsService] = None


def get_notifications_service() -> NotificationsService:
    global _notifications_service
    if _notifications_service is None:
        _notifications_service = NotificationsService()
    return _notifications_service
