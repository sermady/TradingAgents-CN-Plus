# -*- coding: utf-8 -*-
"""支持审计日志的 CRUD 服务

在创建和更新时自动记录操作人信息。
"""

from typing import TypeVar, List, Optional, Dict, Any
from datetime import datetime
import logging

from app.utils.error_handler import async_handle_errors_false

from .base import BaseCRUDService
from .soft_delete import SoftDeleteCRUDService
from .utils import build_id_query

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AuditedCRUDService(BaseCRUDService):
    """支持审计日志的 CRUD 服务

    在创建和更新时自动记录操作人信息。

    Example:
        class OrderService(AuditedCRUDService):
            @property
            def collection_name(self) -> str:
                return "orders"

        service = OrderService()
        order_id = await service.create({"amount": 100}, user_id="user123")
    """

    async def create(
        self, data: Dict[str, Any], user_id: str = None
    ) -> Optional[str]:
        """创建，记录操作人

        Args:
            data: 要创建的文档数据
            user_id: 操作人 ID

        Returns:
            Optional[str]: 创建成功的文档 ID
        """
        if user_id:
            data["created_by"] = user_id
            data["updated_by"] = user_id

        return await super().create(data)

    async def update(
        self, id: str, data: Dict[str, Any], user_id: str = None
    ) -> bool:
        """更新，记录操作人

        Args:
            id: 文档 ID
            data: 要更新的数据
            user_id: 操作人 ID

        Returns:
            bool: 是否更新成功
        """
        if user_id:
            data["updated_by"] = user_id

        return await super().update(id, data)

    async def batch_create(
        self, data_list: List[Dict[str, Any]], user_id: str = None
    ) -> List[str]:
        """批量创建，记录操作人

        Args:
            data_list: 要创建的文档列表
            user_id: 操作人 ID

        Returns:
            List[str]: 成功创建的文档 ID 列表
        """
        if user_id:
            for data in data_list:
                data["created_by"] = user_id
                data["updated_by"] = user_id

        return await super().batch_create(data_list)

    async def batch_update(
        self, ids: List[str], data: Dict[str, Any], user_id: str = None
    ) -> int:
        """批量更新，记录操作人

        Args:
            ids: 文档 ID 列表
            data: 要更新的数据
            user_id: 操作人 ID

        Returns:
            int: 更新的文档数量
        """
        if user_id:
            data["updated_by"] = user_id

        return await super().batch_update(ids, data)


class AuditedSoftDeleteCRUDService(SoftDeleteCRUDService, AuditedCRUDService):
    """同时支持软删除和审计日志的 CRUD 服务

    结合 SoftDeleteCRUDService 和 AuditedCRUDService 的功能。

    Example:
        class ProductService(AuditedSoftDeleteCRUDService):
            @property
            def collection_name(self) -> str:
                return "products"

        service = ProductService()
        product_id = await service.create({"name": "Product A"}, user_id="admin123")
        await service.soft_delete(product_id, user_id="admin123")
    """

    @async_handle_errors_false(error_message=f"软删除失败")
    async def soft_delete(self, id: str, user_id: str = None) -> bool:
        """软删除，记录删除人

        Args:
            id: 文档 ID
            user_id: 操作人 ID

        Returns:
            bool: 是否删除成功
        """
        collection = await self._get_collection()
        query = build_id_query(id)

        update_data = {
            "is_deleted": True,
            "deleted_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        if user_id:
            update_data["deleted_by"] = user_id
            update_data["updated_by"] = user_id

        result = await collection.update_one(query, {"$set": update_data})

        if result.modified_count > 0:
            logger.debug(f"✅ 文档软删除成功: {self.collection_name}/{id}")
            return True
        else:
            logger.warning(f"⚠️ 文档不存在: {self.collection_name}/{id}")
            return False

    @async_handle_errors_false(error_message=f"恢复文档失败")
    async def restore(self, id: str, user_id: str = None) -> bool:
        """恢复软删除的文档，记录恢复人

        Args:
            id: 文档 ID
            user_id: 操作人 ID

        Returns:
            bool: 是否恢复成功
        """
        collection = await self._get_collection()
        query = build_id_query(id)

        update_data = {"updated_at": datetime.utcnow()}
        unset_data = {"is_deleted": "", "deleted_at": "", "deleted_by": ""}

        if user_id:
            update_data["updated_by"] = user_id
            update_data["restored_by"] = user_id
            update_data["restored_at"] = datetime.utcnow()

        result = await collection.update_one(
            query, {"$set": update_data, "$unset": unset_data}
        )

        if result.modified_count > 0:
            logger.debug(f"✅ 文档恢复成功: {self.collection_name}/{id}")
            return True
        else:
            logger.warning(f"⚠️ 文档不存在: {self.collection_name}/{id}")
            return False
