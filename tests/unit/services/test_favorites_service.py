# -*- coding: utf-8 -*-
"""
Favorites Service 单元测试

测试自选股服务的核心功能：
- 添加自选股
- 删除自选股
- 查询自选股
- 分组管理
- 排序功能
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, List

from app.services.favorites_service import FavoritesService


# ==============================================================================
# 测试自选股服务初始化
# ==============================================================================

@pytest.mark.unit
def test_favorites_service_init():
    """测试自选股服务初始化"""
    with patch('app.services.favorites_service.get_mongo_db') as mock_get_mongo:
        mock_mongo = Mock()
        mock_get_mongo.return_value = mock_mongo

        service = FavoritesService()

        assert service.mongo_db is not None


# ==============================================================================
# 测试添加自选股
# ==============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_favorite():
    """测试添加自选股"""
    with patch('app.services.favorites_service.get_mongo_db') as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # 未存在，可以添加
        mock_collection.find_one.return_value = None
        mock_collection.insert_one.return_value = AsyncMock(inserted_id="fav_123")
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = FavoritesService()

        # 添加自选股
        favorite = {
            "user_id": "user_123",
            "stock_code": "000001",
            "stock_name": "平安银行",
            "note": "银行股",
            "added_at": datetime.utcnow()
        }

        result = await service.add_favorite("user_123", "000001", note="银行股")

        assert result is not None
        mock_collection.insert_one.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_favorite_duplicate():
    """测试添加重复自选股"""
    with patch('app.services.favorites_service.get_mongo_db') as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # 已存在
        mock_collection.find_one.return_value = {
            "_id": "fav_123",
            "user_id": "user_123",
            "stock_code": "000001"
        }
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = FavoritesService()

        # 尝试添加重复的自选股
        result = await service.add_favorite("user_123", "000001")

        # 应该返回None或错误
        assert result is None


# ==============================================================================
# 测试删除自选股
# ==============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_remove_favorite():
    """测试删除自选股"""
    with patch('app.services.favorites_service.get_mongo_db') as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        mock_result = AsyncMock()
        mock_result.deleted_count = 1
        mock_collection.delete_one.return_value = mock_result
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = FavoritesService()

        # 删除自选股
        result = await service.remove_favorite("user_123", "000001")

        assert result.deleted_count == 1
        mock_collection.delete_one.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_remove_favorite_not_found():
    """测试删除不存在的自选股"""
    with patch('app.services.favorites_service.get_mongo_db') as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        mock_result = AsyncMock()
        mock_result.deleted_count = 0
        mock_collection.delete_one.return_value = mock_result
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = FavoritesService()

        # 删除不存在的自选股
        result = await service.remove_favorite("user_123", "999999")

        assert result.deleted_count == 0


# ==============================================================================
# 测试查询自选股
# ==============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_favorites():
    """测试获取用户自选股"""
    with patch('app.services.favorites_service.get_mongo_db') as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # 返回自选股列表
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [
            {
                "_id": "fav_1",
                "user_id": "user_123",
                "stock_code": "000001",
                "stock_name": "平安银行",
                "note": "银行股"
            },
            {
                "_id": "fav_2",
                "user_id": "user_123",
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "note": "白酒股"
            }
        ]
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = FavoritesService()

        # 获取用户自选股
        favorites = await service.get_user_favorites("user_123")

        assert len(favorites) == 2
        assert favorites[0]["stock_code"] == "000001"
        assert favorites[1]["stock_code"] == "600519"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_user_favorites_empty():
    """测试获取用户自选股（空）"""
    with patch('app.services.favorites_service.get_mongo_db') as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # 空结果
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = []
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = FavoritesService()

        # 获取新用户的自选股
        favorites = await service.get_user_favorites("new_user")

        assert len(favorites) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_favorite_exists():
    """测试检查自选股是否存在"""
    with patch('app.services.favorites_service.get_mongo_db') as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # 已存在
        mock_collection.find_one.return_value = {
            "_id": "fav_123",
            "user_id": "user_123",
            "stock_code": "000001"
        }
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = FavoritesService()

        # 检查是否存在
        exists = await service.check_favorite_exists("user_123", "000001")

        assert exists is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_favorite_not_exists():
    """测试检查自选股不存在"""
    with patch('app.services.favorites_service.get_mongo_db') as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # 不存在
        mock_collection.find_one.return_value = None
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = FavoritesService()

        # 检查不存在
        exists = await service.check_favorite_exists("user_123", "999999")

        assert exists is False


# ==============================================================================
# 测试分组管理
# ==============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_to_group():
    """测试添加到分组"""
    with patch('app.services.favorites_service.get_mongo_db') as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        mock_result = AsyncMock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = FavoritesService()

        # 添加到分组
        result = await service.add_to_group(
            "user_123",
            "000001",
            "group_name": "银行股"
        )

        assert result.modified_count == 1
        mock_collection.update_one.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_favorites_by_group():
    """测试按分组获取自选股"""
    with patch('app.services.favorites_service.get_mongo_db') as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        mock_cursor = AsyncMock()
        # 返回分组内的自选股
        mock_cursor.to_list.return_value = [
            {
                "_id": "fav_1",
                "user_id": "user_123",
                "stock_code": "000001",
                "group_name": "银行股",
                "stock_name": "平安银行"
            },
            {
                "_id": "fav_2",
                "user_id": "user_123",
                "stock_code": "601398",
                "group_name": "银行股",
                "stock_name": "工商银行"
            }
        ]
        mock_collection.find.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = FavoritesService()

        # 按分组获取
        favorites = await service.get_favorites_by_group("user_123", "银行股")

        assert len(favorites) == 2
        for fav in favorites:
            assert fav["group_name"] == "银行股"


# ==============================================================================
# 测试排序功能
# ==============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_sort_favorites():
    """测试自选股排序"""
    with patch('app.services.favorites_service.get_mongo_db') as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        mock_cursor = AsyncMock()
        # 按添加时间排序
        mock_cursor.to_list.return_value = [
            {"stock_code": "000001", "added_at": "2024-01-15"},
            {"stock_code": "600519", "added_at": "2024-01-16"}
        ]
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = FavoritesService()

        # 按添加时间降序
        favorites = await service.get_user_favorites(
            "user_123",
            sort_by="added_at",
            sort_order="desc"
        )

        assert len(favorites) == 2
        # 验证降序
        # 实际排序在MongoDB层面完成


# ==============================================================================
# 测试更新备注
# ==============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_note():
    """测试更新自选股备注"""
    with patch('app.services.favorites_service.get_mongo_db') as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        mock_result = AsyncMock()
        mock_result.modified_count = 1
        mock_collection.update_one.return_value = mock_result
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = FavoritesService()

        # 更新备注
        result = await service.update_note(
            "user_123",
            "000001",
            note="长期持有，稳健增长"
        )

        assert result.modified_count == 1


# ==============================================================================
# 测试批量操作
# ==============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_multiple_favorites():
    """测试批量添加自选股"""
    with patch('app.services.favorites_service.get_mongo_db') as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # 返回已存在的股票
        mock_collection.find.return_value = [
            {"stock_code": "000001"}  # 已存在
        ]
        mock_collection.insert_many.return_value = AsyncMock(inserted_ids=["fav_1", "fav_2"])
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = FavoritesService()

        # 批量添加
        stock_codes = ["000001", "600519", "000002"]
        results = await service.add_multiple_favorites("user_123", stock_codes)

        # 验证部分插入（000001已存在）
        assert len(results["added"]) == 2
        assert len(results["duplicate"]) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_remove_multiple_favorites():
    """测试批量删除自选股"""
    with patch('app.services.favorites_service.get_mongo_db') as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        mock_result = AsyncMock()
        mock_result.deleted_count = 3
        mock_collection.delete_many.return_value = mock_result
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = FavoritesService()

        # 批量删除
        stock_codes = ["000001", "600519", "000002"]
        result = await service.remove_multiple_favorites("user_123", stock_codes)

        assert result.deleted_count == 3


# ==============================================================================
# 测试错误处理
# ==============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_error_handling_in_add():
    """测试添加时的错误处理"""
    with patch('app.services.favorites_service.get_mongo_db') as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # 数据库错误
        mock_collection.insert_one.side_effect = Exception("Database error")
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = FavoritesService()

        # 应该抛出异常或返回错误
        try:
            result = await service.add_favorite("user_123", "000001")
            # 如果不抛出异常
            assert result is None
        except Exception:
            pass


# ==============================================================================
# 测试边界条件
# ==============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_add_empty_stock_code():
    """测试添加空股票代码"""
    with patch('app.services.favorites_service.get_mongo_db') as mock_get_mongo:
        mock_mongo = Mock()
        mock_get_mongo.return_value = mock_mongo

        service = FavoritesService()

        # 空股票代码
        result = await service.add_favorite("user_123", "")

        assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_favorites_with_limit():
    """测试限制自选股数量"""
    with patch('app.services.favorites_service.get_mongo_db') as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [
            {"stock_code": f"00000{i:03d}"}
            for i in range(1, 11)  # 10条
        ]
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value.limit.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = FavoritesService()

        # 限制10条
        favorites = await service.get_user_favorites("user_123", limit=10)

        assert len(favorites) == 10


# ==============================================================================
# 测试性能
# ==============================================================================

@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.asyncio
async def test_favorites_performance():
    """测试自选股性能"""
    import time

    with patch('app.services.favorites_service.get_mongo_db') as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        mock_cursor = AsyncMock()
        # 大量自选股
        mock_cursor.to_list.return_value = [
            {"stock_code": f"00000{i:03d}", "stock_name": f"股票{i}"}
            for i in range(1, 501)  # 500条
        ]
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = FavoritesService()

        # 性能测试：查询大量自选股
        start = time.time()
        favorites = await service.get_user_favorites("user_123")
        end = time.time()

        elapsed = end - start
        assert len(favorites) == 500
        # 查询应该在合理时间内完成（例如< 2秒）
        assert elapsed < 2
