# -*- coding: utf-8 -*-
"""
Database Service 单元测试

测试数据库服务的核心功能：
- CRUD操作
- 查询优化
- 事务处理
- 数据验证
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from bson import ObjectId
from typing import Dict, Any, List

from app.services.database_service import DatabaseService
from app.models.base import PyObjectId


# ==============================================================================
# 测试数据库服务初始化
# ==============================================================================


@pytest.mark.unit
def test_database_service_init():
    """测试数据库服务初始化"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        assert service.db is not None
        assert service.db == mock_db


# ==============================================================================
# 测试基本CRUD操作
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_insert_one():
    """测试插入单条记录"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_collection.insert_one.return_value = AsyncMock(inserted_id="doc_123")
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        document = {"name": "test", "value": 123}
        result = await service.insert_one("test_collection", document)

        assert result == "doc_123"
        mock_collection.insert_one.assert_called_once_with(document)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_one():
    """测试查找单条记录"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        expected_doc = {"_id": "doc_123", "name": "test"}
        mock_collection.find_one.return_value = expected_doc
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        query = {"name": "test"}
        result = await service.find_one("test_collection", query)

        assert result == expected_doc
        mock_collection.find_one.assert_called_once_with(query, projection=None)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_many():
    """测试查找多条记录"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_cursor = AsyncMock()
        expected_docs = [
            {"_id": "doc_1", "name": "test1"},
            {"_id": "doc_2", "name": "test2"},
        ]
        mock_cursor.to_list.return_value = expected_docs
        mock_collection.find.return_value = mock_cursor
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        query = {"status": "active"}
        result = await service.find_many("test_collection", query, limit=10)

        assert result == expected_docs
        mock_collection.find.assert_called_once_with(
            query, projection=None, limit=10, skip=0
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_one():
    """测试更新单条记录"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_result = AsyncMock()
        mock_result.modified_count = 1
        mock_result.matched_count = 1
        mock_collection.update_one.return_value = mock_result
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        query = {"_id": "doc_123"}
        update = {"$set": {"name": "updated"}}
        result = await service.update_one("test_collection", query, update)

        assert result.modified_count == 1
        assert result.matched_count == 1
        mock_collection.update_one.assert_called_once_with(query, update, upsert=False)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_one_upsert():
    """测试插入或更新"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_result = AsyncMock()
        mock_result.upserted_id = "doc_456"
        mock_result.modified_count = 0
        mock_result.matched_count = 0
        mock_collection.update_one.return_value = mock_result
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        query = {"name": "new_doc"}
        update = {"$set": {"value": 123}}
        result = await service.update_one("test_collection", query, update, upsert=True)

        assert result.upserted_id == "doc_456"
        mock_collection.update_one.assert_called_once_with(query, update, upsert=True)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_one():
    """测试删除单条记录"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_result = AsyncMock()
        mock_result.deleted_count = 1
        mock_collection.delete_one.return_value = mock_result
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        query = {"_id": "doc_123"}
        result = await service.delete_one("test_collection", query)

        assert result.deleted_count == 1
        mock_collection.delete_one.assert_called_once_with(query)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_count():
    """测试统计记录数"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_collection.count_documents.return_value = 100
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        query = {"status": "active"}
        result = await service.count("test_collection", query)

        assert result == 100
        mock_collection.count_documents.assert_called_once_with(query)


# ==============================================================================
# 测试批量操作
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_insert_many():
    """测试批量插入"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_result = AsyncMock()
        mock_result.inserted_ids = ["doc_1", "doc_2", "doc_3"]
        mock_collection.insert_many.return_value = mock_result
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        documents = [{"name": "test1"}, {"name": "test2"}, {"name": "test3"}]
        result = await service.insert_many("test_collection", documents)

        assert len(result.inserted_ids) == 3
        mock_collection.insert_many.assert_called_once_with(documents)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_many():
    """测试批量更新"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_result = AsyncMock()
        mock_result.modified_count = 5
        mock_collection.update_many.return_value = mock_result
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        query = {"status": "inactive"}
        update = {"$set": {"status": "active"}}
        result = await service.update_many("test_collection", query, update)

        assert result.modified_count == 5
        mock_collection.update_many.assert_called_once_with(query, update)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_many():
    """测试批量删除"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_result = AsyncMock()
        mock_result.deleted_count = 10
        mock_collection.delete_many.return_value = mock_result
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        query = {"status": "deleted"}
        result = await service.delete_many("test_collection", query)

        assert result.deleted_count == 10
        mock_collection.delete_many.assert_called_once_with(query)


# ==============================================================================
# 测试查询优化
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_with_projection():
    """测试带投影的查询"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_cursor = AsyncMock()
        expected_doc = {"_id": "doc_1", "name": "test"}
        mock_cursor.to_list.return_value = [expected_doc]
        mock_collection.find.return_value = mock_cursor
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        query = {"status": "active"}
        projection = {"name": 1, "_id": 1}
        result = await service.find_many(
            "test_collection", query, projection=projection
        )

        assert len(result) == 1
        assert result[0] == expected_doc
        mock_collection.find.assert_called_once_with(
            query, projection=projection, limit=0, skip=0, sort=None
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_with_sort():
    """测试带排序的查询"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_cursor = AsyncMock()
        expected_docs = [{"_id": "doc_1", "name": "a"}, {"_id": "doc_2", "name": "b"}]
        mock_cursor.to_list.return_value = expected_docs
        mock_collection.find.return_value = mock_cursor
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        query = {}
        sort = [("name", 1)]  # 升序
        result = await service.find_many("test_collection", query, sort=sort)

        assert len(result) == 2
        mock_collection.find.assert_called_once_with(
            query, projection=None, limit=0, skip=0, sort=sort
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_with_pagination():
    """测试分页查询"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_cursor = AsyncMock()
        expected_docs = [{"_id": f"doc_{i}", "name": f"test{i}"} for i in range(20, 30)]
        mock_cursor.to_list.return_value = expected_docs
        mock_collection.find.return_value = mock_cursor
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        query = {}
        result = await service.find_many("test_collection", query, skip=20, limit=10)

        assert len(result) == 10
        mock_collection.find.assert_called_once_with(
            query, projection=None, limit=10, skip=20, sort=None
        )


# ==============================================================================
# 测试数据验证
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_insert_with_validation_success():
    """测试带验证的插入（成功）"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_collection.insert_one.return_value = AsyncMock(inserted_id="doc_123")
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        document = {"name": "test", "value": 123}
        schema = {"required": ["name", "value"], "types": {"name": str, "value": int}}

        result = await service.insert_with_validation(
            "test_collection", document, schema
        )

        assert result == "doc_123"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_insert_with_validation_failure():
    """测试带验证的插入（失败）"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_collection.insert_one.return_value = AsyncMock(inserted_id="doc_123")
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        # 缺少必需字段
        document = {"name": "test"}  # 缺少value
        schema = {"required": ["name", "value"], "types": {"name": str, "value": int}}

        # 应该抛出验证错误
        with pytest.raises(Exception):
            await service.insert_with_validation("test_collection", document, schema)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_insert_with_validation_wrong_type():
    """测试带验证的插入（类型错误）"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_collection.insert_one.return_value = AsyncMock(inserted_id="doc_123")
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        # 类型错误
        document = {"name": "test", "value": "wrong"}  # value应该是int
        schema = {"required": ["name", "value"], "types": {"name": str, "value": int}}

        # 应该抛出验证错误
        with pytest.raises(Exception):
            await service.insert_with_validation("test_collection", document, schema)


# ==============================================================================
# 测试错误处理
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_error_handling_in_insert():
    """测试插入时的错误处理"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        # 模拟数据库错误
        mock_collection.insert_one.side_effect = Exception("Database error")
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        document = {"name": "test"}

        # 应该抛出异常
        with pytest.raises(Exception) as exc_info:
            await service.insert_one("test_collection", document)

        assert "Database error" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_error_handling_in_find():
    """测试查找时的错误处理"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        # 模拟数据库错误
        mock_collection.find_one.side_effect = Exception("Connection error")
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        query = {"name": "test"}

        # 应该抛出异常
        with pytest.raises(Exception) as exc_info:
            await service.find_one("test_collection", query)

        assert "Connection error" in str(exc_info.value)


# ==============================================================================
# 测试边界条件
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_empty_result():
    """测试查询空结果"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_collection.find_one.return_value = None
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        query = {"name": "nonexistent"}
        result = await service.find_one("test_collection", query)

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_count_zero():
    """测试统计零条记录"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_collection.count_documents.return_value = 0
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        query = {"status": "nonexistent"}
        result = await service.count("test_collection", query)

        assert result == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_nonexistent():
    """测试删除不存在的记录"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_result = AsyncMock()
        mock_result.deleted_count = 0
        mock_collection.delete_one.return_value = mock_result
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        query = {"_id": "nonexistent"}
        result = await service.delete_one("test_collection", query)

        assert result.deleted_count == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_nonexistent():
    """测试更新不存在的记录"""
    with patch("app.services.database_service.get_mongo_db") as mock_get_db:
        mock_db = Mock()
        mock_collection = AsyncMock()
        mock_result = AsyncMock()
        mock_result.modified_count = 0
        mock_result.matched_count = 0
        mock_collection.update_one.return_value = mock_result
        mock_db.__getitem__ = Mock(return_value=mock_collection)
        mock_get_db.return_value = mock_db

        service = DatabaseService()

        query = {"_id": "nonexistent"}
        update = {"$set": {"name": "updated"}}
        result = await service.update_one("test_collection", query, update)

        assert result.modified_count == 0
        assert result.matched_count == 0
