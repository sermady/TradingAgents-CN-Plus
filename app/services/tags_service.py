# -*- coding: utf-8 -*-
"""
用户自定义标签服务

使用 BaseCRUDService 基类重构，减少重复代码约 60%。
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

from app.services.crud import BaseCRUDService


class TagsService(BaseCRUDService):
    """用户自定义标签服务

    继承 BaseCRUDService 获得标准 CRUD 操作：
    - create: 创建标签
    - get_by_id: 根据 ID 获取标签
    - list: 列表查询
    - update: 更新标签
    - delete: 删除标签
    """

    @property
    def collection_name(self) -> str:
        """MongoDB 集合名称"""
        return "user_tags"

    def __init__(self) -> None:
        super().__init__()
        self._indexes_ensured = False

    async def ensure_indexes(self) -> None:
        """确保索引创建"""
        if self._indexes_ensured:
            return
        db = await self._get_db()
        # 每个用户的标签名唯一
        await db.user_tags.create_index([("user_id", 1), ("name", 1)], unique=True, name="uniq_user_tag_name")
        await db.user_tags.create_index([("user_id", 1), ("sort_order", 1)], name="idx_user_tag_sort")
        self._indexes_ensured = True

    def _normalize_user_id(self, user_id: str) -> str:
        """统一为字符串存储，便于兼容开源版(admin)与未来ObjectId"""
        return str(user_id)

    def _format_doc(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """格式化文档为 API 响应格式"""
        return {
            "id": str(doc.get("_id")),
            "name": doc.get("name"),
            "color": doc.get("color") or "#409EFF",
            "sort_order": doc.get("sort_order", 0),
            "created_at": (doc.get("created_at") or datetime.utcnow()).isoformat(),
            "updated_at": (doc.get("updated_at") or datetime.utcnow()).isoformat(),
        }

    # ===== 业务方法（使用基类 CRUD） =====

    async def list_tags(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有标签"""
        await self.ensure_indexes()
        docs = await self.list(
            filters={"user_id": self._normalize_user_id(user_id)},
            sort=[("sort_order", 1), ("name", 1)]
        )
        return [self._format_doc(d) for d in docs]

    async def create_tag(
        self,
        user_id: str,
        name: str,
        color: Optional[str] = None,
        sort_order: int = 0
    ) -> Optional[Dict[str, Any]]:
        """创建标签"""
        await self.ensure_indexes()
        doc_id = await self.create({
            "user_id": self._normalize_user_id(user_id),
            "name": name.strip(),
            "color": color or "#409EFF",
            "sort_order": int(sort_order or 0),
        })
        if doc_id:
            doc = await self.get_by_id(doc_id)
            return self._format_doc(doc) if doc else None
        return None

    async def update_tag(
        self,
        user_id: str,
        tag_id: str,
        *,
        name: Optional[str] = None,
        color: Optional[str] = None,
        sort_order: Optional[int] = None
    ) -> bool:
        """更新标签"""
        await self.ensure_indexes()

        # 构建更新数据
        update_data: Dict[str, Any] = {}
        if name is not None:
            update_data["name"] = name.strip()
        if color is not None:
            update_data["color"] = color
        if sort_order is not None:
            update_data["sort_order"] = int(sort_order)

        if not update_data:
            return True  # 无需更新

        # 先验证标签是否存在且属于该用户
        doc = await self.get_by_id(tag_id)
        if not doc or doc.get("user_id") != self._normalize_user_id(user_id):
            return False

        return await self.update(tag_id, update_data)

    async def delete_tag(self, user_id: str, tag_id: str) -> bool:
        """删除标签"""
        await self.ensure_indexes()

        # 先验证标签是否存在且属于该用户
        doc = await self.get_by_id(tag_id)
        if not doc or doc.get("user_id") != self._normalize_user_id(user_id):
            return False

        return await self.delete(tag_id)


# 全局实例
tags_service = TagsService()

