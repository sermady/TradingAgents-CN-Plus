# -*- coding: utf-8 -*-
"""支持软删除的 CRUD 服务

在文档中添加 is_deleted 和 deleted_at 字段实现软删除，
默认查询会自动排除已删除的文档。
"""

from typing import TypeVar, List, Optional, Dict, Any
from datetime import datetime
import logging

from app.utils.error_handler import (
    async_handle_errors_none,
    async_handle_errors_false,
)

from .base import BaseCRUDService
from .utils import build_id_query

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SoftDeleteCRUDService(BaseCRUDService):
    """支持软删除的 CRUD 服务

    在文档中添加 is_deleted 和 deleted_at 字段实现软删除，
    默认查询会自动排除已删除的文档。

    Example:
        class ArticleService(SoftDeleteCRUDService):
            @property
            def collection_name(self) -> str:
                return "articles"

        service = ArticleService()
        await service.soft_delete(article_id)  # 软删除
        await service.restore(article_id)      # 恢复
    """

    async def list(
        self,
        filters: Dict[str, Any] = None,
        sort: List[tuple] = None,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> List[Dict[str, Any]]:
        """列表查询（默认排除已删除）

        Args:
            filters: 查询条件
            sort: 排序规则
            skip: 跳过文档数
            limit: 返回最大文档数
            include_deleted: 是否包含已删除的文档

        Returns:
            List[Dict]: 文档列表
        """
        filters = filters or {}
        if not include_deleted:
            filters["is_deleted"] = {"$ne": True}

        return await super().list(filters=filters, sort=sort, skip=skip, limit=limit)

    @async_handle_errors_none(error_message=f"获取文档失败")
    async def get_by_id(
        self, id: str, include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """根据 ID 获取文档

        Args:
            id: 文档 ID
            include_deleted: 是否包含已删除的文档

        Returns:
            Optional[Dict]: 文档数据
        """
        collection = await self._get_collection()
        query = build_id_query(id)

        if not include_deleted:
            query["is_deleted"] = {"$ne": True}

        doc = await collection.find_one(query)
        if doc:
            doc["id"] = str(doc.pop("_id"))
            return doc
        return None

    @async_handle_errors_false(error_message=f"软删除失败")
    async def soft_delete(self, id: str) -> bool:
        """软删除

        Args:
            id: 文档 ID

        Returns:
            bool: 是否删除成功
        """
        collection = await self._get_collection()
        query = build_id_query(id)

        result = await collection.update_one(
            query,
            {
                "$set": {
                    "is_deleted": True,
                    "deleted_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        if result.modified_count > 0:
            logger.debug(f"✅ 文档软删除成功: {self.collection_name}/{id}")
            return True
        else:
            logger.warning(f"⚠️ 文档不存在: {self.collection_name}/{id}")
            return False

    @async_handle_errors_false(error_message=f"恢复文档失败")
    async def restore(self, id: str) -> bool:
        """恢复软删除的文档

        Args:
            id: 文档 ID

        Returns:
            bool: 是否恢复成功
        """
        collection = await self._get_collection()
        query = build_id_query(id)

        result = await collection.update_one(
            query,
            {
                "$set": {"updated_at": datetime.utcnow()},
                "$unset": {"is_deleted": "", "deleted_at": ""},
            },
        )

        if result.modified_count > 0:
            logger.debug(f"✅ 文档恢复成功: {self.collection_name}/{id}")
            return True
        else:
            logger.warning(f"⚠️ 文档不存在: {self.collection_name}/{id}")
            return False

    async def list_deleted(
        self,
        filters: Dict[str, Any] = None,
        sort: List[tuple] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """列出已删除的文档

        Args:
            filters: 额外查询条件
            sort: 排序规则
            skip: 跳过文档数
            limit: 返回最大文档数

        Returns:
            List[Dict]: 已删除的文档列表
        """
        filters = filters or {}
        filters["is_deleted"] = True

        return await super().list(filters=filters, sort=sort, skip=skip, limit=limit)

    async def hard_delete(self, id: str) -> bool:
        """硬删除（彻底删除文档）

        警告：此操作不可恢复，请谨慎使用

        Args:
            id: 文档 ID

        Returns:
            bool: 是否删除成功
        """
        return await super().delete(id)
