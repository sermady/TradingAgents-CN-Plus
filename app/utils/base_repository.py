# -*- coding: utf-8 -*-
"""通用数据库操作基类"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from bson import ObjectId
import logging

from app.utils.timezone import now_tz

logger = logging.getLogger(__name__)


class BaseRepository:
    """通用数据库操作基类

    封装常见的 CRUD 操作模式，减少重复代码。
    """

    def __init__(self, db, collection_name: str):
        self.db = db
        self.collection_name = collection_name

    @property
    def collection(self):
        """获取集合对象"""
        return getattr(self.db, self.collection_name)

    def _to_object_id(self, id: Union[str, ObjectId]) -> ObjectId:
        """将字符串ID转换为ObjectId"""
        if isinstance(id, ObjectId):
            return id
        return ObjectId(id)

    def _build_id_query(self, id: Union[str, ObjectId]) -> Dict[str, Any]:
        """构建ID查询条件，兼容字符串和ObjectId"""
        try:
            return {"_id": self._to_object_id(id)}
        except Exception:
            # 如果转换失败，尝试按字符串查询
            return {"_id": id}

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """查找单个文档

        Args:
            query: 查询条件

        Returns:
            匹配的文档，未找到返回None
        """
        try:
            return await self.collection.find_one(query)
        except Exception as e:
            logger.error(f"查找文档失败: {e}, query={query}")
            return None

    async def find_by_id(self, id: Union[str, ObjectId]) -> Optional[Dict[str, Any]]:
        """兼容 ObjectId 和字符串 ID 的查询

        Args:
            id: 文档ID（字符串或ObjectId）

        Returns:
            匹配的文档，未找到返回None
        """
        query = self._build_id_query(id)
        return await self.find_one(query)

    async def find_many(
        self,
        query: Optional[Dict[str, Any]] = None,
        sort: Optional[List[tuple]] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """查找多个文档

        Args:
            query: 查询条件，默认为空（查询所有）
            sort: 排序条件，如 [("created_at", -1)]
            limit: 限制返回数量
            skip: 跳过前N条

        Returns:
            匹配的文档列表
        """
        try:
            cursor = self.collection.find(query or {})

            if sort:
                cursor = cursor.sort(sort)
            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)

            return await cursor.to_list(length=None)
        except Exception as e:
            logger.error(f"查找多个文档失败: {e}, query={query}")
            return []

    async def insert(self, data: Dict[str, Any]) -> Optional[str]:
        """插入文档，返回插入的 ID

        Args:
            data: 要插入的文档数据

        Returns:
            插入文档的ID字符串，失败返回None
        """
        try:
            # 自动添加创建时间
            if "created_at" not in data:
                data["created_at"] = now_tz()
            if "updated_at" not in data:
                data["updated_at"] = now_tz()

            result = await self.collection.insert_one(data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"插入文档失败: {e}")
            return None

    async def insert_many(self, data_list: List[Dict[str, Any]]) -> List[str]:
        """批量插入文档

        Args:
            data_list: 要插入的文档列表

        Returns:
            插入文档的ID列表
        """
        try:
            now = now_tz()
            for data in data_list:
                if "created_at" not in data:
                    data["created_at"] = now
                if "updated_at" not in data:
                    data["updated_at"] = now

            result = await self.collection.insert_many(data_list)
            return [str(id) for id in result.inserted_ids]
        except Exception as e:
            logger.error(f"批量插入文档失败: {e}")
            return []

    async def update(
        self,
        query: Dict[str, Any],
        data: Dict[str, Any],
        set_updated_at: bool = True,
        upsert: bool = False,
    ) -> bool:
        """更新文档

        Args:
            query: 查询条件
            data: 更新的数据
            set_updated_at: 是否自动设置updated_at字段
            upsert: 如果不存在是否插入

        Returns:
            是否更新成功
        """
        try:
            update_data = {"$set": data}
            if set_updated_at:
                data["updated_at"] = now_tz()

            result = await self.collection.update_one(query, update_data, upsert=upsert)
            return result.modified_count > 0 or (upsert and result.upserted_id)
        except Exception as e:
            logger.error(f"更新文档失败: {e}, query={query}")
            return False

    async def update_by_id(
        self, id: Union[str, ObjectId], data: Dict[str, Any], set_updated_at: bool = True
    ) -> bool:
        """兼容 ObjectId 的更新

        Args:
            id: 文档ID
            data: 更新的数据
            set_updated_at: 是否自动设置updated_at字段

        Returns:
            是否更新成功
        """
        query = self._build_id_query(id)
        return await self.update(query, data, set_updated_at)

    async def update_many(
        self,
        query: Dict[str, Any],
        data: Dict[str, Any],
        set_updated_at: bool = True,
    ) -> int:
        """批量更新文档

        Args:
            query: 查询条件
            data: 更新的数据
            set_updated_at: 是否自动设置updated_at字段

        Returns:
            更新的文档数量
        """
        try:
            update_data = {"$set": data}
            if set_updated_at:
                data["updated_at"] = now_tz()

            result = await self.collection.update_many(query, update_data)
            return result.modified_count
        except Exception as e:
            logger.error(f"批量更新文档失败: {e}, query={query}")
            return 0

    async def delete(self, query: Dict[str, Any]) -> bool:
        """删除文档

        Args:
            query: 查询条件

        Returns:
            是否删除成功
        """
        try:
            result = await self.collection.delete_one(query)
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"删除文档失败: {e}, query={query}")
            return False

    async def delete_by_id(self, id: Union[str, ObjectId]) -> bool:
        """兼容 ObjectId 的删除

        Args:
            id: 文档ID

        Returns:
            是否删除成功
        """
        query = self._build_id_query(id)
        return await self.delete(query)

    async def delete_many(self, query: Dict[str, Any]) -> int:
        """批量删除文档

        Args:
            query: 查询条件

        Returns:
            删除的文档数量
        """
        try:
            result = await self.collection.delete_many(query)
            return result.deleted_count
        except Exception as e:
            logger.error(f"批量删除文档失败: {e}, query={query}")
            return 0

    async def count(self, query: Optional[Dict[str, Any]] = None) -> int:
        """计数文档

        Args:
            query: 查询条件，默认为空（计数所有）

        Returns:
            文档数量
        """
        try:
            return await self.collection.count_documents(query or {})
        except Exception as e:
            logger.error(f"计数文档失败: {e}, query={query}")
            return 0

    async def exists(self, query: Dict[str, Any]) -> bool:
        """检查是否存在匹配的文档

        Args:
            query: 查询条件

        Returns:
            是否存在
        """
        try:
            count = await self.collection.count_documents(query, limit=1)
            return count > 0
        except Exception as e:
            logger.error(f"检查文档存在失败: {e}, query={query}")
            return False

    async def find_one_and_update(
        self,
        query: Dict[str, Any],
        data: Dict[str, Any],
        set_updated_at: bool = True,
        upsert: bool = False,
        return_document: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """查找并更新文档

        Args:
            query: 查询条件
            data: 更新的数据
            set_updated_at: 是否自动设置updated_at字段
            upsert: 如果不存在是否插入
            return_document: 是否返回更新后的文档

        Returns:
            更新后的文档（如果return_document为True）
        """
        try:
            from pymongo import ReturnDocument

            update_data = {"$set": data}
            if set_updated_at:
                data["updated_at"] = now_tz()

            result = await self.collection.find_one_and_update(
                query,
                update_data,
                upsert=upsert,
                return_document=ReturnDocument.AFTER if return_document else ReturnDocument.BEFORE,
            )
            return result
        except Exception as e:
            logger.error(f"查找并更新文档失败: {e}, query={query}")
            return None


class ConfigRepositoryMixin:
    """配置管理专用的 Repository 混合类

    针对配置列表（如 llm_configs, data_source_configs）的操作封装
    """

    async def add_to_config_list(
        self,
        config_id: Union[str, ObjectId],
        list_attr: str,
        item: Dict[str, Any],
        key_attr: str = "name",
    ) -> bool:
        """添加项目到配置的列表中

        Args:
            config_id: 配置文档ID
            list_attr: 列表属性名（如"llm_configs"）
            item: 要添加的项目
            key_attr: 用于判断重复的属性名

        Returns:
            是否添加成功
        """
        try:
            # 先检查是否已存在
            existing = await self.find_one(
                {
                    "_id": self._to_object_id(config_id),
                    f"{list_attr}.{key_attr}": item.get(key_attr),
                }
            )
            if existing:
                logger.warning(f"项目已存在: {item.get(key_attr)}")
                return False

            # 添加项目到列表
            result = await self.collection.update_one(
                {"_id": self._to_object_id(config_id)},
                {
                    "$push": {list_attr: item},
                    "$set": {"updated_at": now_tz()},
                },
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"添加项目到配置列表失败: {e}")
            return False

    async def update_in_config_list(
        self,
        config_id: Union[str, ObjectId],
        list_attr: str,
        item_id: str,
        updates: Dict[str, Any],
        key_attr: str = "name",
    ) -> bool:
        """更新配置列表中的项目

        Args:
            config_id: 配置文档ID
            list_attr: 列表属性名
            item_id: 项目标识值（如name）
            updates: 更新的字段
            key_attr: 用于定位项目的属性名

        Returns:
            是否更新成功
        """
        try:
            # 构建更新字段
            update_fields = {}
            for key, value in updates.items():
                update_fields[f"{list_attr}.$.{key}"] = value
            update_fields["updated_at"] = now_tz()

            result = await self.collection.update_one(
                {
                    "_id": self._to_object_id(config_id),
                    f"{list_attr}.{key_attr}": item_id,
                },
                {"$set": update_fields},
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"更新配置列表项目失败: {e}")
            return False

    async def delete_from_config_list(
        self,
        config_id: Union[str, ObjectId],
        list_attr: str,
        item_id: str,
        key_attr: str = "name",
    ) -> bool:
        """从配置列表中删除项目

        Args:
            config_id: 配置文档ID
            list_attr: 列表属性名
            item_id: 项目标识值
            key_attr: 用于定位项目的属性名

        Returns:
            是否删除成功
        """
        try:
            result = await self.collection.update_one(
                {"_id": self._to_object_id(config_id)},
                {
                    "$pull": {list_attr: {key_attr: item_id}},
                    "$set": {"updated_at": now_tz()},
                },
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"从配置列表删除项目失败: {e}")
            return False

    async def get_config_list_item(
        self,
        config_id: Union[str, ObjectId],
        list_attr: str,
        item_id: str,
        key_attr: str = "name",
    ) -> Optional[Dict[str, Any]]:
        """获取配置列表中的单个项目

        Args:
            config_id: 配置文档ID
            list_attr: 列表属性名
            item_id: 项目标识值
            key_attr: 用于定位项目的属性名

        Returns:
            项目数据，未找到返回None
        """
        try:
            config = await self.find_by_id(config_id)
            if not config:
                return None

            items = config.get(list_attr, [])
            for item in items:
                if isinstance(item, dict) and item.get(key_attr) == item_id:
                    return item
                # 支持Pydantic模型
                if hasattr(item, key_attr) and getattr(item, key_attr) == item_id:
                    return item.model_dump() if hasattr(item, "model_dump") else item

            return None
        except Exception as e:
            logger.error(f"获取配置列表项目失败: {e}")
            return None

    async def replace_config_list(
        self,
        config_id: Union[str, ObjectId],
        list_attr: str,
        new_list: List[Dict[str, Any]],
    ) -> bool:
        """完全替换配置列表

        Args:
            config_id: 配置文档ID
            list_attr: 列表属性名
            new_list: 新的列表数据

        Returns:
            是否替换成功
        """
        try:
            result = await self.collection.update_one(
                {"_id": self._to_object_id(config_id)},
                {
                    "$set": {
                        list_attr: new_list,
                        "updated_at": now_tz(),
                    },
                },
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"替换配置列表失败: {e}")
            return False
