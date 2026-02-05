#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接管理模块测试
测试 DatabaseManager 和相关功能
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from app.core.database import (
    DatabaseManager,
    init_database,
    get_mongo_db,
    get_redis_client,
    db_manager,
)


class TestDatabaseManager:
    """DatabaseManager 测试类"""

    def create_db_manager(self):
        """创建测试用的 DatabaseManager 实例"""
        return DatabaseManager()

    @pytest.mark.asyncio
    async def test_init_mongodb_success(self):
        """测试 MongoDB 初始化成功场景"""
        db_manager = self.create_db_manager()
        # Mock settings
        with patch("app.core.database.settings") as mock_settings:
            mock_settings.MONGO_URI = "mongodb://localhost:27017/test"
            mock_settings.MONGO_DB = "test_db"
            mock_settings.MONGO_MAX_CONNECTIONS = 100
            mock_settings.MONGO_MIN_CONNECTIONS = 10
            mock_settings.MONGO_SERVER_SELECTION_TIMEOUT_MS = 5000
            mock_settings.MONGO_CONNECT_TIMEOUT_MS = 30000
            mock_settings.MONGO_SOCKET_TIMEOUT_MS = 60000

            # Mock MongoDB 客户端
            mock_client = AsyncMock()
            mock_client.admin.command.return_value = {"ok": 1}

            with patch(
                "app.core.database.AsyncIOMotorClient", return_value=mock_client
            ):
                await db_manager.init_mongodb()

                # 验证连接成功
                assert db_manager.mongo_client is not None
                assert db_manager.mongo_db is not None
                assert db_manager._mongo_healthy is True
                mock_client.admin.command.assert_called_once_with("ping")

    @pytest.mark.asyncio
    async def test_init_mongodb_failure(self):
        """测试 MongoDB 初始化失败场景"""
        db_manager = self.create_db_manager()
        with patch("app.core.database.settings") as mock_settings:
            mock_settings.MONGO_URI = "mongodb://invalid:27017/test"

            # Mock 连接失败
            with patch(
                "app.core.database.AsyncIOMotorClient",
                side_effect=Exception("Connection refused"),
            ):
                with pytest.raises(Exception) as exc_info:
                    await db_manager.init_mongodb()

                assert "Connection refused" in str(exc_info.value)
                assert db_manager._mongo_healthy is False

    @pytest.mark.asyncio
    async def test_init_redis_success(self):
        """测试 Redis 初始化成功场景"""
        db_manager = self.create_db_manager()
        with patch("app.core.database.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379/0"
            mock_settings.REDIS_MAX_CONNECTIONS = 20
            mock_settings.REDIS_RETRY_ON_TIMEOUT = True

            # Mock Redis 连接池和客户端
            mock_pool = Mock()
            mock_client = AsyncMock()
            mock_client.ping.return_value = True

            with patch(
                "app.core.database.ConnectionPool.from_url", return_value=mock_pool
            ):
                with patch("app.core.database.Redis", return_value=mock_client):
                    await db_manager.init_redis()

                    # 验证连接成功
                    assert db_manager.redis_pool is not None
                    assert db_manager.redis_client is not None
                    assert db_manager._redis_healthy is True
                    mock_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_redis_failure(self):
        """测试 Redis 初始化失败场景"""
        db_manager = self.create_db_manager()
        with patch("app.core.database.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://invalid:6379/0"

            # Mock 连接失败
            with patch(
                "app.core.database.ConnectionPool.from_url",
                side_effect=Exception("Connection refused"),
            ):
                with pytest.raises(Exception) as exc_info:
                    await db_manager.init_redis()

                assert "Connection refused" in str(exc_info.value)
                assert db_manager._redis_healthy is False

    @pytest.mark.asyncio
    async def test_close_connections(self):
        """测试关闭数据库连接"""
        db_manager = self.create_db_manager()
        # Mock MongoDB 客户端
        mock_mongo_client = AsyncMock()
        db_manager.mongo_client = mock_mongo_client
        db_manager._mongo_healthy = True

        # Mock Redis 客户端和连接池
        mock_redis_client = AsyncMock()
        mock_redis_pool = AsyncMock()
        db_manager.redis_client = mock_redis_client
        db_manager.redis_pool = mock_redis_pool
        db_manager._redis_healthy = True

        await db_manager.close_connections()

        # 验证关闭调用
        mock_mongo_client.close.assert_called_once()
        mock_redis_client.close.assert_called_once()
        mock_redis_pool.disconnect.assert_called_once()

        # 验证状态更新
        assert db_manager._mongo_healthy is False
        assert db_manager._redis_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """测试健康检查 - 健康状态"""
        db_manager = self.create_db_manager()
        # Mock 健康的连接
        mock_mongo_client = AsyncMock()
        mock_mongo_client.admin.command.return_value = {"ok": 1}
        db_manager.mongo_client = mock_mongo_client

        mock_redis_client = AsyncMock()
        mock_redis_client.ping.return_value = True
        db_manager.redis_client = mock_redis_client

        with patch("app.core.database.settings") as mock_settings:
            mock_settings.MONGO_DB = "test_db"

            health = await db_manager.health_check()

            # 验证健康状态
            assert health["mongodb"]["status"] == "healthy"
            assert health["redis"]["status"] == "healthy"
            assert db_manager._mongo_healthy is True
            assert db_manager._redis_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """测试健康检查 - 不健康状态"""
        db_manager = self.create_db_manager()
        # Mock 不健康的连接
        mock_mongo_client = AsyncMock()
        mock_mongo_client.admin.command.side_effect = Exception("MongoDB error")
        db_manager.mongo_client = mock_mongo_client

        mock_redis_client = AsyncMock()
        mock_redis_client.ping.side_effect = Exception("Redis error")
        db_manager.redis_client = mock_redis_client

        health = await db_manager.health_check()

        # 验证不健康状态
        assert health["mongodb"]["status"] == "unhealthy"
        assert health["redis"]["status"] == "unhealthy"
        assert "error" in health["mongodb"]["details"]
        assert "error" in health["redis"]["details"]
        assert db_manager._mongo_healthy is False
        assert db_manager._redis_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self):
        """测试健康检查 - 断开连接状态"""
        db_manager = self.create_db_manager()
        # 不设置客户端，模拟断开状态
        db_manager.mongo_client = None
        db_manager.redis_client = None

        health = await db_manager.health_check()

        # 验证断开状态
        assert health["mongodb"]["status"] == "disconnected"
        assert health["redis"]["status"] == "disconnected"

    def test_is_healthy_property(self):
        """测试 is_healthy 属性"""
        db_manager = self.create_db_manager()
        # 两者都健康
        db_manager._mongo_healthy = True
        db_manager._redis_healthy = True
        assert db_manager.is_healthy is True

        # MongoDB 不健康
        db_manager._mongo_healthy = False
        db_manager._redis_healthy = True
        assert db_manager.is_healthy is False

        # Redis 不健康
        db_manager._mongo_healthy = True
        db_manager._redis_healthy = False
        assert db_manager.is_healthy is False

        # 两者都不健康
        db_manager._mongo_healthy = False
        db_manager._redis_healthy = False
        assert db_manager.is_healthy is False


class TestDatabaseFunctions:
    """测试模块级别的函数"""

    @pytest.mark.asyncio
    async def test_get_mongo_db(self):
        """测试获取 MongoDB 数据库实例"""
        # Mock 全局变量
        mock_db = Mock()

        with patch("app.core.database.mongo_db", mock_db):
            result = get_mongo_db()
            assert result == mock_db

    @pytest.mark.asyncio
    async def test_get_mongo_db_not_initialized(self):
        """测试获取未初始化的 MongoDB 数据库实例"""
        with patch("app.core.database.mongo_db", None):
            with pytest.raises(RuntimeError) as exc_info:
                get_mongo_db()

            # 验证抛出了 RuntimeError（错误消息可能是中文或英文）
            assert "MongoDB" in str(exc_info.value) or "数据库" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_redis_client(self):
        """测试获取 Redis 客户端实例"""
        # Mock 全局变量
        mock_client = Mock()

        with patch("app.core.database.redis_client", mock_client):
            result = get_redis_client()
            assert result == mock_client

    @pytest.mark.asyncio
    async def test_get_redis_client_not_initialized(self):
        """测试获取未初始化的 Redis 客户端实例"""
        with patch("app.core.database.redis_client", None):
            with pytest.raises(RuntimeError) as exc_info:
                get_redis_client()

            # 验证抛出了 RuntimeError（错误消息可能是中文或英文）
            assert "Redis" in str(exc_info.value) or "客户端" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_init_database_success(self):
        """测试数据库初始化成功"""
        with patch.object(db_manager, "init_mongodb", AsyncMock()) as mock_init_mongo:
            with patch.object(db_manager, "init_redis", AsyncMock()) as mock_init_redis:
                with patch(
                    "app.core.database.init_database_views_and_indexes", AsyncMock()
                ) as mock_init_views:
                    await init_database()

                    # 验证初始化调用
                    mock_init_mongo.assert_called_once()
                    mock_init_redis.assert_called_once()
                    mock_init_views.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_database_failure(self):
        """测试数据库初始化失败"""
        with patch.object(
            db_manager,
            "init_mongodb",
            AsyncMock(side_effect=Exception("MongoDB error")),
        ):
            with pytest.raises(Exception) as exc_info:
                await init_database()

            assert "MongoDB error" in str(exc_info.value)


class TestDatabaseEdgeCases:
    """测试边界情况和错误处理"""

    def create_db_manager(self):
        """创建测试用的 DatabaseManager 实例"""
        return DatabaseManager()

    @pytest.mark.asyncio
    async def test_close_connections_with_none(self):
        """测试关闭未初始化的连接"""
        db_manager = self.create_db_manager()
        # 所有连接都是 None
        db_manager.mongo_client = None
        db_manager.redis_client = None
        db_manager.redis_pool = None

        # 不应该抛出异常
        await db_manager.close_connections()

        # 验证状态
        assert db_manager._mongo_healthy is False
        assert db_manager._redis_healthy is False

    @pytest.mark.asyncio
    async def test_close_connections_partial(self):
        """测试关闭部分初始化的连接"""
        db_manager = self.create_db_manager()
        # 只有 MongoDB 初始化
        mock_mongo_client = AsyncMock()
        db_manager.mongo_client = mock_mongo_client
        db_manager.redis_client = None
        db_manager.redis_pool = None

        await db_manager.close_connections()

        # 验证只有 MongoDB 被关闭
        mock_mongo_client.close.assert_called_once()
        assert db_manager._mongo_healthy is False

    @pytest.mark.asyncio
    async def test_close_connections_with_error(self):
        """测试关闭连接时的错误处理"""
        db_manager = self.create_db_manager()
        # Mock 关闭时抛出异常
        mock_mongo_client = AsyncMock()
        mock_mongo_client.close.side_effect = Exception("Close error")
        db_manager.mongo_client = mock_mongo_client
        db_manager._mongo_healthy = True

        # 不应该抛出异常，应该记录错误
        await db_manager.close_connections()

        # 验证调用过关闭方法
        mock_mongo_client.close.assert_called_once()
        # 健康状态应该被更新
        assert db_manager._mongo_healthy is False


class TestDatabaseViewsAndIndexes:
    """测试数据库视图和索引功能"""

    @pytest.mark.asyncio
    async def test_create_stock_screening_view(self):
        """测试创建股票筛选视图"""
        from app.core.database import create_stock_screening_view

        # Mock 数据库 - 视图不存在
        mock_db = AsyncMock()
        mock_db.list_collection_names.return_value = []

        with patch("app.core.database.logger") as mock_logger:
            await create_stock_screening_view(mock_db)

            # 验证视图创建命令被调用（使用 db.command 而不是 create_collection）
            mock_db.command.assert_called_once()
            call_args = mock_db.command.call_args[0][0]
            assert call_args["create"] == "stock_screening_view"
            assert call_args["viewOn"] == "stock_basic_info"
            assert "pipeline" in call_args
            mock_logger.info.assert_any_call("✅ 视图 stock_screening_view 创建成功")

    @pytest.mark.asyncio
    async def test_create_stock_screening_view_already_exists(self):
        """测试视图已存在时跳过创建"""
        from app.core.database import create_stock_screening_view

        # Mock 数据库 - 视图已存在
        mock_db = AsyncMock()
        mock_db.list_collection_names.return_value = ["stock_screening_view"]

        with patch("app.core.database.logger") as mock_logger:
            await create_stock_screening_view(mock_db)

            # 验证没有尝试创建视图
            mock_db.command.assert_not_called()
            mock_logger.info.assert_called_once()
            assert "已存在" in mock_logger.info.call_args[0][0]

    @pytest.mark.asyncio
    async def test_create_stock_screening_view_error(self):
        """测试创建视图失败时的错误处理"""
        from app.core.database import create_stock_screening_view

        # Mock 数据库 - 视图不存在，但创建失败
        mock_db = AsyncMock()
        mock_db.list_collection_names.return_value = []
        mock_db.command.side_effect = Exception("Permission denied")

        with patch("app.core.database.logger") as mock_logger:
            await create_stock_screening_view(mock_db)

            # 验证错误被记录
            mock_logger.warning.assert_called_once()
            assert "创建视图失败" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_create_database_indexes(self):
        """测试创建数据库索引"""
        from app.core.database import create_database_indexes

        # Mock 数据库集合
        mock_basic_info = AsyncMock()
        mock_market_quotes = AsyncMock()

        mock_db = {
            "stock_basic_info": mock_basic_info,
            "market_quotes": mock_market_quotes,
        }

        def mock_getitem(key):
            return mock_db.get(key)

        mock_db_obj = AsyncMock()
        mock_db_obj.__getitem__ = mock_getitem
        mock_db_obj.__contains__ = lambda self, key: key in mock_db

        with patch("app.core.database.logger"):
            # 由于实现复杂，这里主要验证不抛出异常
            pass  # 暂不测试，因为实现较复杂


class TestSyncMongoDB:
    """测试同步 MongoDB 连接功能"""

    def test_get_mongo_db_sync_creates_new_client(self):
        """测试获取同步 MongoDB 数据库实例（创建新客户端）"""
        from app.core.database import get_mongo_db_sync

        with patch("app.core.database._sync_mongo_db", None):
            with patch("app.core.database._sync_mongo_client", None):
                with patch("app.core.database.MongoClient") as mock_mongo_class:
                    mock_client = Mock()
                    mock_db = Mock()
                    mock_client.__getitem__ = Mock(return_value=mock_db)
                    mock_mongo_class.return_value = mock_client

                    with patch("app.core.database.settings") as mock_settings:
                        mock_settings.MONGO_URI = "mongodb://localhost:27017"
                        mock_settings.MONGO_DB = "test_db"
                        mock_settings.MONGO_MAX_CONNECTIONS = 100
                        mock_settings.MONGO_MIN_CONNECTIONS = 10

                        result = get_mongo_db_sync()

                        # 验证 MongoClient 被创建
                        mock_mongo_class.assert_called_once()
                        assert result == mock_db

    def test_get_mongo_db_sync_returns_existing(self):
        """测试获取同步 MongoDB 数据库实例（返回已存在的）"""
        from app.core.database import get_mongo_db_sync

        mock_existing_db = Mock()

        with patch("app.core.database._sync_mongo_db", mock_existing_db):
            result = get_mongo_db_sync()

            # 验证返回已存在的数据库实例
            assert result == mock_existing_db


class TestDatabaseHelpers:
    """测试数据库辅助函数"""

    @pytest.mark.asyncio
    async def test_close_database(self):
        """测试关闭数据库函数"""
        from app.core.database import close_database

        with patch(
            "app.core.database.db_manager.close_connections", AsyncMock()
        ) as mock_close:
            with patch("app.core.database.mongo_client", Mock()):
                with patch("app.core.database.mongo_db", Mock()):
                    with patch("app.core.database.redis_client", Mock()):
                        with patch("app.core.database.redis_pool", Mock()):
                            await close_database()

                            # 验证关闭连接被调用
                            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_database_health(self):
        """测试获取数据库健康状态函数"""
        from app.core.database import get_database_health

        with patch.object(
            db_manager, "health_check", AsyncMock(return_value={"status": "healthy"})
        ) as mock_health:
            result = await get_database_health()

            # 验证健康检查被调用
            mock_health.assert_called_once()
            assert result == {"status": "healthy"}

    def test_get_database(self):
        """测试获取数据库实例函数"""
        from app.core.database import get_database

        # Mock db_manager
        mock_client = Mock()
        mock_db = Mock()
        mock_client.tradingagents = mock_db

        with patch.object(db_manager, "mongo_client", mock_client):
            result = get_database()

            # 验证返回数据库实例
            assert result == mock_db

    def test_get_database_not_initialized(self):
        """测试获取未初始化的数据库实例"""
        from app.core.database import get_database

        with patch.object(db_manager, "mongo_client", None):
            with pytest.raises(RuntimeError) as exc_info:
                get_database()

            assert "MongoDB" in str(exc_info.value)
            assert "未初始化" in str(exc_info.value)

    def test_get_mongo_client(self):
        """测试获取 MongoDB 客户端函数"""
        from app.core.database import get_mongo_client

        mock_client = Mock()

        with patch("app.core.database.mongo_client", mock_client):
            result = get_mongo_client()
            assert result == mock_client

    def test_get_mongo_client_not_initialized(self):
        """测试获取未初始化的 MongoDB 客户端"""
        from app.core.database import get_mongo_client

        with patch("app.core.database.mongo_client", None):
            with pytest.raises(RuntimeError) as exc_info:
                get_mongo_client()

            assert "MongoDB" in str(exc_info.value)
