# -*- coding: utf-8 -*-
"""通用 CRUD 服务基类

提供标准化的 MongoDB CRUD 操作，旨在替代项目中 842 处重复的 CRUD 模式。

使用示例:
    class UserService(BaseCRUDService[User]):
        @property
        def collection_name(self) -> str:
            return "users"

    # 使用服务
    service = UserService()
    user_id = await service.create({"username": "test", "email": "test@example.com"})
    user = await service.get_by_id(user_id)
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Dict, Any
import logging

from app.core.database import get_mongo_db
from app.utils.error_handler import (
    async_handle_errors_none,
    async_handle_errors_false,
    async_handle_errors_empty_list,
    async_handle_errors_zero,
)

from .utils import to_object_id, build_id_query, add_timestamps

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseCRUDService(Generic[T], ABC):
    """通用 CRUD 服务基类

    子类只需指定 collection_name 即可自动获得标准 CRUD 操作。
    支持异步 MongoDB 操作，包含完整的错误处理和日志记录。

    Attributes:
        collection_name: MongoDB 集合名称，由子类实现
    """

    def __init__(self, db=None):
        """初始化 CRUD 服务

        Args:
            db: 可选的数据库实例，如果未提供则使用默认连接
        """
        self._db = db
        self._collection = None

    @property
    @abstractmethod
    def collection_name(self) -> str:
        """MongoDB 集合名称

        Returns:
            str: 集合名称

        Raises:
            NotImplementedError: 必须由子类实现
        """
        raise NotImplementedError("子类必须实现 collection_name 属性")

    async def _get_db(self):
        """获取数据库连接

        Returns:
            AsyncIOMotorDatabase: MongoDB 数据库实例

        Raises:
            RuntimeError: 如果数据库未初始化
        """
        if self._db is None:
            self._db = get_mongo_db()
        return self._db

    async def _get_collection(self):
        """获取 MongoDB 集合

        Returns:
            AsyncIOMotorCollection: MongoDB 集合实例
        """
        if self._collection is None:
            db = await self._get_db()
            self._collection = getattr(db, self.collection_name)
        return self._collection

    # ===== 基础 CRUD 方法 =====

    @async_handle_errors_none(error_message=f"创建文档失败")
    async def create(self, data: Dict[str, Any]) -> Optional[str]:
        """创建文档，返回 ID

        Args:
            data: 要创建的文档数据

        Returns:
            Optional[str]: 创建成功的文档 ID，失败返回 None

        Example:
            user_id = await service.create({"username": "test", "email": "test@test.com"})
        """
        collection = await self._get_collection()
        data = add_timestamps(data, is_update=False)

        result = await collection.insert_one(data)
        doc_id = str(result.inserted_id)

        logger.debug(f"✅ 文档创建成功: {self.collection_name}/{doc_id}")
        return doc_id

    @async_handle_errors_none(error_message=f"获取文档失败")
    async def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """根据 ID 获取文档

        支持 ObjectId 和字符串 ID 兼容

        Args:
            id: 文档 ID（字符串或 ObjectId）

        Returns:
            Optional[Dict]: 文档数据，不存在或失败返回 None

        Example:
            user = await service.get_by_id("507f1f77bcf86cd799439011")
        """
        collection = await self._get_collection()
        query = build_id_query(id)

        doc = await collection.find_one(query)
        if doc:
            doc["id"] = str(doc.pop("_id"))
            return doc
        return None

    @async_handle_errors_none(error_message=f"获取文档失败")
    async def get_by_field(
        self, field: str, value: Any
    ) -> Optional[Dict[str, Any]]:
        """根据字段获取单个文档

        Args:
            field: 字段名
            value: 字段值

        Returns:
            Optional[Dict]: 文档数据，不存在或失败返回 None

        Example:
            user = await service.get_by_field("email", "test@test.com")
        """
        collection = await self._get_collection()
        doc = await collection.find_one({field: value})

        if doc:
            doc["id"] = str(doc.pop("_id"))
            return doc
        return None

    @async_handle_errors_empty_list(error_message=f"列表查询失败")
    async def list(
        self,
        filters: Dict[str, Any] = None,
        sort: List[tuple] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """列表查询

        Args:
            filters: 查询条件，默认 None（查询全部）
            sort: 排序规则，如 [("created_at", -1)] 表示按创建时间倒序
            skip: 跳过文档数，用于分页
            limit: 返回最大文档数

        Returns:
            List[Dict]: 文档列表

        Example:
            # 查询最近10个活跃用户
            users = await service.list(
                filters={"is_active": True},
                sort=[("created_at", -1)],
                limit=10
            )
        """
        collection = await self._get_collection()
        filters = filters or {}

        cursor = collection.find(filters)

        if sort:
            cursor = cursor.sort(sort)
        if skip > 0:
            cursor = cursor.skip(skip)
        if limit > 0:
            cursor = cursor.limit(limit)

        docs = await cursor.to_list(length=limit)

        # 统一转换 _id 为 id
        for doc in docs:
            doc["id"] = str(doc.pop("_id"))

        return docs

    @async_handle_errors_false(error_message=f"更新文档失败")
    async def update(self, id: str, data: Dict[str, Any]) -> bool:
        """更新文档

        Args:
            id: 文档 ID
            data: 要更新的数据

        Returns:
            bool: 是否更新成功

        Example:
            success = await service.update(user_id, {"email": "new@test.com"})
        """
        collection = await self._get_collection()
        query = build_id_query(id)
        data = add_timestamps(data, is_update=True)

        # 移除不能更新的字段
        data.pop("_id", None)
        data.pop("id", None)
        data.pop("created_at", None)

        result = await collection.update_one(query, {"$set": data})

        if result.modified_count > 0:
            logger.debug(f"✅ 文档更新成功: {self.collection_name}/{id}")
            return True
        else:
            logger.warning(f"⚠️ 文档未更新: {self.collection_name}/{id}")
            return False

    @async_handle_errors_zero(error_message=f"批量更新失败")
    async def update_by_field(
        self, field: str, value: Any, data: Dict[str, Any]
    ) -> int:
        """根据字段批量更新

        Args:
            field: 字段名
            value: 字段值
            data: 要更新的数据

        Returns:
            int: 更新的文档数量

        Example:
            count = await service.update_by_field("status", "pending", {"status": "done"})
        """
        collection = await self._get_collection()
        data = add_timestamps(data, is_update=True)

        # 移除不能更新的字段
        data.pop("_id", None)
        data.pop("id", None)
        data.pop("created_at", None)

        result = await collection.update_many({field: value}, {"$set": data})

        logger.debug(f"✅ 批量更新成功: {self.collection_name}.{field}={value}, 更新 {result.modified_count} 条")
        return result.modified_count

    @async_handle_errors_false(error_message=f"删除文档失败")
    async def delete(self, id: str) -> bool:
        """删除文档

        Args:
            id: 文档 ID

        Returns:
            bool: 是否删除成功

        Example:
            success = await service.delete(user_id)
        """
        collection = await self._get_collection()
        query = build_id_query(id)

        result = await collection.delete_one(query)

        if result.deleted_count > 0:
            logger.debug(f"✅ 文档删除成功: {self.collection_name}/{id}")
            return True
        else:
            logger.warning(f"⚠️ 文档不存在: {self.collection_name}/{id}")
            return False

    @async_handle_errors_zero(error_message=f"批量删除失败")
    async def delete_by_field(self, field: str, value: Any) -> int:
        """根据字段批量删除

        Args:
            field: 字段名
            value: 字段值

        Returns:
            int: 删除的文档数量

        Example:
            count = await service.delete_by_field("status", "deleted")
        """
        collection = await self._get_collection()
        result = await collection.delete_many({field: value})

        logger.debug(f"✅ 批量删除成功: {self.collection_name}.{field}={value}, 删除 {result.deleted_count} 条")
        return result.deleted_count

    @async_handle_errors_zero(error_message=f"计数失败")
    async def count(self, filters: Dict[str, Any] = None) -> int:
        """计数

        Args:
            filters: 查询条件，默认 None（统计全部）

        Returns:
            int: 文档数量

        Example:
            total = await service.count({"is_active": True})
        """
        collection = await self._get_collection()
        filters = filters or {}
        return await collection.count_documents(filters)

    @async_handle_errors_false(error_message=f"检查存在性失败")
    async def exists(self, filters: Dict[str, Any]) -> bool:
        """检查是否存在

        Args:
            filters: 查询条件

        Returns:
            bool: 是否存在符合条件的文档

        Example:
            exists = await service.exists({"email": "test@test.com"})
        """
        collection = await self._get_collection()
        doc = await collection.find_one(filters, {"_id": 1})
        return doc is not None

    # ===== 批量操作 =====

    @async_handle_errors_empty_list(error_message=f"批量创建失败")
    async def batch_create(
        self, data_list: List[Dict[str, Any]]
    ) -> List[str]:
        """批量创建

        Args:
            data_list: 要创建的文档列表

        Returns:
            List[str]: 成功创建的文档 ID 列表

        Example:
            ids = await service.batch_create([
                {"username": "user1"},
                {"username": "user2"}
            ])
        """
        if not data_list:
            return []

        collection = await self._get_collection()

        # 添加时间戳
        for data in data_list:
            add_timestamps(data, is_update=False)

        result = await collection.insert_many(data_list)
        ids = [str(oid) for oid in result.inserted_ids]

        logger.debug(f"✅ 批量创建成功: {self.collection_name}, 创建 {len(ids)} 条")
        return ids

    @async_handle_errors_zero(error_message=f"批量更新失败")
    async def batch_update(
        self, ids: List[str], data: Dict[str, Any]
    ) -> int:
        """批量更新

        Args:
            ids: 文档 ID 列表
            data: 要更新的数据

        Returns:
            int: 更新的文档数量

        Example:
            count = await service.batch_update([id1, id2], {"status": "active"})
        """
        if not ids:
            return 0

        collection = await self._get_collection()
        data = add_timestamps(data, is_update=True)

        # 移除不能更新的字段
        data.pop("_id", None)
        data.pop("id", None)
        data.pop("created_at", None)

        # 转换所有 ID 为 ObjectId
        object_ids = []
        for id in ids:
            oid = to_object_id(id)
            if oid:
                object_ids.append(oid)

        if not object_ids:
            logger.warning(f"⚠️ 没有有效的 ID 用于批量更新")
            return 0

        result = await collection.update_many(
            {"_id": {"$in": object_ids}}, {"$set": data}
        )

        logger.debug(f"✅ 批量更新成功: {self.collection_name}, 更新 {result.modified_count} 条")
        return result.modified_count

    @async_handle_errors_zero(error_message=f"批量删除失败")
    async def batch_delete(self, ids: List[str]) -> int:
        """批量删除

        Args:
            ids: 文档 ID 列表

        Returns:
            int: 删除的文档数量

        Example:
            count = await service.batch_delete([id1, id2, id3])
        """
        if not ids:
            return 0

        collection = await self._get_collection()

        # 转换所有 ID 为 ObjectId
        object_ids = []
        for id in ids:
            oid = to_object_id(id)
            if oid:
                object_ids.append(oid)

        if not object_ids:
            logger.warning(f"⚠️ 没有有效的 ID 用于批量删除")
            return 0

        result = await collection.delete_many({"_id": {"$in": object_ids}})

        logger.debug(f"✅ 批量删除成功: {self.collection_name}, 删除 {result.deleted_count} 条")
        return result.deleted_count
