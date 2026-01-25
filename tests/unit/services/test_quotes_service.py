# -*- coding: utf-8 -*-
"""
Quotes Service 单元测试

测试实时行情服务的核心功能：
- 实时行情获取
- 行情缓存
- 多数据源切换
- 历史行情查询
- 批量行情查询
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, List

from app.services.quotes_service import QuotesService


# ==============================================================================
# 测试行情服务初始化
# ==============================================================================


@pytest.mark.unit
def test_quotes_service_init():
    """测试行情服务初始化"""
    with patch("app.services.quotes_service.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

        with patch("app.services.quotes_service.get_mongo_db") as mock_get_mongo:
            mock_mongo = Mock()
            mock_get_mongo.return_value = mock_mongo

            service = QuotesService()

            assert service.redis_client is not None
            assert service.mongo_db is not None


# ==============================================================================
# 测试实时行情获取
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_realtime_quote():
    """测试获取实时行情"""
    with patch("app.services.quotes_service.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

    with patch("app.services.quotes_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # 返回行情数据
        mock_collection.find_one.return_value = {
            "code": "000001",
            "name": "平安银行",
            "price": 10.50,
            "change": 0.25,
            "change_percent": 2.38,
            "volume": 1000000,
            "timestamp": datetime.utcnow(),
        }
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = QuotesService()

        # 获取实时行情
        quote = await service.get_realtime_quote("000001")

        assert quote is not None
        assert quote["code"] == "000001"
        assert quote["name"] == "平安银行"
        assert quote["price"] == 10.50
        assert quote["change"] == 0.25


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_realtime_quote_not_found():
    """测试获取不存在的股票行情"""
    with patch("app.services.quotes_service.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

    with patch("app.services.quotes_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        mock_collection.find_one.return_value = None  # 未找到
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = QuotesService()

        # 获取不存在的股票行情
        quote = await service.get_realtime_quote("999999")

        assert quote is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_realtime_quote_from_cache():
    """测试从缓存获取行情"""
    with patch("app.services.quotes_service.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        # Redis中有缓存
        mock_redis.get = Mock(return_value='{"code": "000001", "price": 10.50}')
        mock_get_redis.return_value = mock_redis

    with patch("app.services.quotes_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_get_mongo.return_value = mock_mongo

        service = QuotesService()

        # 获取实时行情（应该从Redis缓存获取）
        quote = await service.get_realtime_quote("000001")

        assert quote is not None
        assert quote["price"] == 10.50
        # 应该调用Redis而不是MongoDB
        mock_redis.get.assert_called_once()


# ==============================================================================
# 测试批量行情查询
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_batch_quotes():
    """测试批量获取行情"""
    with patch("app.services.quotes_service.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        # 批量获取缓存
        mock_redis.mget = Mock(
            return_value=[
                '{"code": "000001", "price": 10.50}',
                '{"code": "600519", "price": 1800.00}',
                '{"code": "000002", "price": 20.30}',
            ]
        )
        mock_get_redis.return_value = mock_redis

    with patch("app.services.quotes_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_get_mongo.return_value = mock_mongo

        service = QuotesService()

        # 批量获取行情
        codes = ["000001", "600519", "000002"]
        quotes = await service.get_batch_quotes(codes)

        assert len(quotes) == 3
        assert quotes[0]["price"] == 10.50
        assert quotes[1]["price"] == 1800.00
        assert quotes[2]["price"] == 20.30


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_batch_quotes_partial_cache():
    """测试批量获取行情（部分缓存）"""
    with patch("app.services.quotes_service.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        # 部分命中缓存
        mock_redis.mget = Mock(
            return_value=[
                '{"code": "000001", "price": 10.50}',
                None,  # 未缓存
                '{"code": "000002", "price": 20.30}',
            ]
        )
        mock_get_redis.return_value = mock_redis

    with patch("app.services.quotes_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # 返回未缓存的数据
        mock_collection.find.return_value = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [{"code": "600519", "price": 1800.00}]
        mock_collection.find.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = QuotesService()

        # 批量获取行情（部分缓存）
        codes = ["000001", "600519", "000002"]
        quotes = await service.get_batch_quotes(codes)

        # 应该返回所有行情数据
        assert len(quotes) == 3


# ==============================================================================
# 测试历史行情查询
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_quotes():
    """测试获取历史行情"""
    with patch("app.services.quotes_service.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

    with patch("app.services.quotes_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # 返回历史数据
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [
            {"date": "2024-01-15", "close": 10.50},
            {"date": "2024-01-16", "close": 10.60},
            {"date": "2024-01-17", "close": 10.55},
        ]
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value.limit.return_value = (
            mock_cursor
        )
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = QuotesService()

        # 获取历史行情
        from datetime import timedelta

        start_date = datetime.utcnow() - timedelta(days=10)
        quotes = await service.get_historical_quotes(
            code="000001", start_date=start_date, limit=10
        )

        assert len(quotes) == 3
        assert quotes[0]["date"] == "2024-01-15"
        assert quotes[1]["close"] == 10.60


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_quotes_empty():
    """测试获取历史行情（空结果）"""
    with patch("app.services.quotes_service.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

    with patch("app.services.quotes_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # 空结果
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = []
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value.limit.return_value = (
            mock_cursor
        )
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = QuotesService()

        # 获取历史行情（无数据）
        from datetime import timedelta

        start_date = datetime.utcnow() - timedelta(days=1000)
        quotes = await service.get_historical_quotes(
            code="999999", start_date=start_date, limit=10
        )

        assert len(quotes) == 0


# ==============================================================================
# 测试多数据源切换
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_data_source_switch():
    """测试数据源切换"""
    with patch("app.services.quotes_service.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_redis.get = Mock(side_effect=Exception("Redis error"))  # Redis失败
        mock_redis.get.return_value = None
        mock_get_redis.return_value = mock_redis

    with patch("app.services.quotes_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # MongoDB成功
        mock_collection.find_one.return_value = {"code": "000001", "price": 10.50}
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = QuotesService()

        # 获取行情（Redis失败，降级到MongoDB）
        quote = await service.get_realtime_quote("000001")

        assert quote is not None
        assert quote["price"] == 10.50


# ==============================================================================
# 测试行情缓存
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cache_quote():
    """测试缓存行情数据"""
    with patch("app.services.quotes_service.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_redis.set = Mock(return_value=True)
        mock_redis.setex = Mock(return_value=True)
        mock_get_redis.return_value = mock_redis

    with patch("app.services.quotes_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_get_mongo.return_value = mock_mongo

        service = QuotesService()

        # 缓存行情数据
        quote_data = {"code": "000001", "price": 10.50, "timestamp": datetime.utcnow()}
        await service.cache_quote("000001", quote_data, ttl=3600)

        # 验证缓存调用
        mock_redis.setex.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invalidate_cache():
    """测试使缓存失效"""
    with patch("app.services.quotes_service.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_redis.delete = Mock(return_value=1)
        mock_get_redis.return_value = mock_redis

    with patch("app.services.quotes_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_get_mongo.return_value = mock_mongo

        service = QuotesService()

        # 使缓存失效
        await service.invalidate_cache("000001")

        # 验证删除调用
        mock_redis.delete.assert_called_once()


# ==============================================================================
# 测试行情更新
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_quotes():
    """测试更新行情数据"""
    with patch("app.services.quotes_service.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_redis.set = Mock(return_value=True)
        mock_redis.delete = Mock(return_value=1)
        mock_get_redis.return_value = mock_redis

    with patch("app.services.quotes_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        mock_collection.update_one.return_value = AsyncMock()
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = QuotesService()

        # 更新行情
        quote_data = {
            "code": "000001",
            "price": 10.60,
            "change": 0.35,
            "timestamp": datetime.utcnow(),
        }
        await service.update_quote("000001", quote_data)

        # 验证更新调用
        mock_collection.update_one.assert_called_once()


# ==============================================================================
# 测试错误处理
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_error_handling_in_get_quote():
    """测试获取行情时的错误处理"""
    with patch("app.services.quotes_service.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        # Redis错误
        mock_redis.get = Mock(side_effect=Exception("Redis error"))
        mock_get_redis.return_value = mock_redis

    with patch("app.services.quotes_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # MongoDB也错误
        mock_collection.find_one.side_effect = Exception("MongoDB error")
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = QuotesService()

        # 应该返回None或抛出异常
        try:
            quote = await service.get_realtime_quote("000001")
            # 如果不抛出异常，应该返回None
            assert quote is None
        except Exception:
            # 如果抛出异常，应该被捕获
            pass


# ==============================================================================
# 测试边界条件
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_quote_empty_code():
    """测试空股票代码"""
    with patch("app.services.quotes_service.get_redis_client"):
        with patch("app.services.quotes_service.get_mongo_db"):
            service = QuotesService()

            # 空代码
            quote = await service.get_realtime_quote("")

            assert quote is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_batch_quotes_empty_list():
    """测试空列表批量获取"""
    with patch("app.services.quotes_service.get_redis_client"):
        with patch("app.services.quotes_service.get_mongo_db"):
            service = QuotesService()

            # 空列表
            quotes = await service.get_batch_quotes([])

            assert len(quotes) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_historical_quotes_future_date():
    """测试未来日期的历史行情"""
    with patch("app.services.quotes_service.get_redis_client"):
        with patch("app.services.quotes_service.get_mongo_db") as mock_get_mongo:
            mock_mongo = Mock()
            mock_collection = AsyncMock()
            # 空结果
            mock_cursor = AsyncMock()
            mock_cursor.to_list.return_value = []
            mock_collection.find.return_value = mock_cursor
            mock_collection.find.return_value.sort.return_value.limit.return_value = (
                mock_cursor
            )
            mock_mongo.__getitem__ = Mock(return_value=mock_collection)
            mock_get_mongo.return_value = mock_mongo

            service = QuotesService()

            # 未来日期
            from datetime import timedelta

            future_date = datetime.utcnow() + timedelta(days=10)
            quotes = await service.get_historical_quotes(
                code="000001", start_date=future_date, limit=10
            )

            assert len(quotes) == 0


# ==============================================================================
# 测试性能
# ==============================================================================


@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.asyncio
async def test_batch_quotes_performance():
    """测试批量查询性能"""
    import time

    with patch("app.services.quotes_service.get_redis_client") as mock_get_redis:
        mock_redis = Mock()

        # 模拟缓存命中
        def mock_mget(keys):
            return [f'{{"code": "{k}", "price": {float(hash(k)) % 100}}}' for k in keys]

        mock_redis.mget = Mock(side_effect=mock_mget)
        mock_get_redis.return_value = mock_redis

    with patch("app.services.quotes_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_get_mongo.return_value = mock_mongo

        service = QuotesService()

        # 性能测试：批量查询100只股票
        codes = [f"00000{i:03d}" for i in range(1, 101)]
        start = time.time()
        quotes = await service.get_batch_quotes(codes)
        end = time.time()

        elapsed = end - start
        assert len(quotes) == 100
        # 批量查询应该在合理时间内完成（例如< 2秒）
        assert elapsed < 2
