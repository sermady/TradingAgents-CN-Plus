# -*- coding: utf-8 -*-
"""
Config Service Tests
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime


class TestConfigService:
    """ConfigService 测试类"""

    def test_service_initialization(self):
        """测试服务初始化"""
        with patch("app.services.config_service.get_mongo_db"):
            from app.services.config_service import ConfigService

            service = ConfigService()
            assert service.db is None
            assert service.db_manager is None

    def test_service_initialization_with_db_manager(self):
        """测试带数据库管理器初始化"""
        with patch("app.services.config_service.get_mongo_db"):
            from app.services.config_service import ConfigService

            mock_db_manager = Mock()
            mock_db_manager.mongo_db = Mock()

            service = ConfigService(db_manager=mock_db_manager)
            assert service.db_manager is mock_db_manager

    @pytest.mark.asyncio
    async def test_get_db_with_db_manager(self):
        """测试从数据库管理器获取数据库连接"""
        with patch("app.services.config_service.get_mongo_db") as mock_get_db:
            from app.services.config_service import ConfigService

            mock_db_manager = Mock()
            mock_db = Mock()
            mock_db_manager.mongo_db = mock_db

            service = ConfigService(db_manager=mock_db_manager)

            db = await service._get_db()

            assert db is mock_db
            mock_get_db.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_db_without_db_manager(self):
        """测试从全局函数获取数据库连接"""
        with patch("app.services.config_service.get_mongo_db") as mock_get_db:
            from app.services.config_service import ConfigService

            mock_db = Mock()
            mock_get_db.return_value = mock_db

            service = ConfigService()

            db = await service._get_db()

            assert db is mock_db
            mock_get_db.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_market_categories_empty(self):
        """测试获取空的市场分类"""
        with patch("app.services.config_service.get_mongo_db") as mock_get_db:
            from app.services.config_service import ConfigService

            mock_db = Mock()
            mock_collection = Mock()
            mock_collection.find.return_value.to_list = AsyncMock(return_value=[])
            mock_db.market_categories = mock_collection
            mock_get_db.return_value = mock_db

            service = ConfigService()

            categories = await service.get_market_categories()

            assert isinstance(categories, list)

    @pytest.mark.asyncio
    async def test_get_market_categories_with_data(self):
        """测试获取有数据的市场分类"""
        with patch("app.services.config_service.get_mongo_db") as mock_get_db:
            from app.services.config_service import ConfigService

            mock_db = Mock()
            mock_collection = Mock()
            mock_collection.find.return_value.to_list = AsyncMock(
                return_value=[
                    {
                        "id": "a_shares",
                        "name": "a_shares",
                        "display_name": "A股",
                        "enabled": True,
                        "sort_order": 1,
                    }
                ]
            )
            mock_db.market_categories = mock_collection
            mock_get_db.return_value = mock_db

            service = ConfigService()

            categories = await service.get_market_categories()

            assert len(categories) == 1
            assert categories[0].id == "a_shares"

    @pytest.mark.asyncio
    async def test_add_market_category_success(self):
        """测试成功添加市场分类"""
        with patch("app.services.config_service.get_mongo_db") as mock_get_db:
            from app.services.config_service import ConfigService, MarketCategory

            mock_db = Mock()
            mock_collection = Mock()
            mock_collection.find_one = AsyncMock(return_value=None)
            mock_collection.insert_one = AsyncMock()
            mock_db.market_categories = mock_collection
            mock_get_db.return_value = mock_db

            service = ConfigService()

            category = MarketCategory(
                id="crypto",
                name="crypto",
                display_name="数字货币",
                enabled=True,
                sort_order=4,
            )

            result = await service.add_market_category(category)

            assert result is True
            mock_collection.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_market_category_duplicate(self):
        """测试添加重复的市场分类"""
        with patch("app.services.config_service.get_mongo_db") as mock_get_db:
            from app.services.config_service import ConfigService, MarketCategory

            mock_db = Mock()
            mock_collection = Mock()
            mock_collection.find_one = AsyncMock(return_value={"id": "crypto"})
            mock_db.market_categories = mock_collection
            mock_get_db.return_value = mock_db

            service = ConfigService()

            category = MarketCategory(
                id="crypto",
                name="crypto",
                display_name="数字货币",
                enabled=True,
                sort_order=4,
            )

            result = await service.add_market_category(category)

            assert result is False

    @pytest.mark.asyncio
    async def test_delete_market_category_success(self):
        """测试成功删除市场分类"""
        with patch("app.services.config_service.get_mongo_db") as mock_get_db:
            from app.services.config_service import ConfigService

            mock_db = Mock()
            mock_categories = Mock()
            mock_groupings = Mock()

            delete_result = Mock()
            delete_result.deleted_count = 1

            mock_categories.delete_one = AsyncMock(return_value=delete_result)
            mock_groupings.count_documents = AsyncMock(return_value=0)
            mock_db.market_categories = mock_categories
            mock_db.datasource_groupings = mock_groupings
            mock_get_db.return_value = mock_db

            service = ConfigService()

            result = await service.delete_market_category("crypto")

            assert result is True
            mock_categories.delete_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_market_category_with_groupings(self):
        """测试删除有关联数据源的分类"""
        with patch("app.services.config_service.get_mongo_db") as mock_get_db:
            from app.services.config_service import ConfigService

            mock_db = Mock()
            mock_categories = Mock()
            mock_groupings = Mock()

            mock_groupings.count_documents = AsyncMock(return_value=1)
            mock_db.market_categories = mock_categories
            mock_db.datasource_groupings = mock_groupings
            mock_get_db.return_value = mock_db

            service = ConfigService()

            result = await service.delete_market_category("crypto")

            assert result is False

    @pytest.mark.asyncio
    async def test_get_datasource_groupings(self):
        """测试获取数据源分组"""
        with patch("app.services.config_service.get_mongo_db") as mock_get_db:
            from app.services.config_service import ConfigService

            mock_db = Mock()
            mock_collection = Mock()
            mock_collection.find.return_value.to_list = AsyncMock(
                return_value=[
                    {
                        "data_source_name": "AKShare",
                        "market_category_id": "a_shares",
                        "priority": 1,
                    }
                ]
            )
            mock_db.datasource_groupings = mock_collection
            mock_get_db.return_value = mock_db

            service = ConfigService()

            groupings = await service.get_datasource_groupings()

            assert len(groupings) == 1
            assert groupings[0].data_source_name == "AKShare"


class TestConfigServiceSystemConfig:
    """系统配置相关测试"""

    @pytest.mark.asyncio
    async def test_get_system_config_not_exists(self):
        """测试获取不存在的系统配置"""
        with patch("app.services.config_service.get_mongo_db") as mock_get_db:
            from app.services.config_service import ConfigService

            mock_db = Mock()
            mock_collection = Mock()
            mock_collection.find_one = AsyncMock(return_value=None)
            mock_db.system_configs = mock_collection
            mock_get_db.return_value = mock_db

            with patch.object(
                ConfigService, "_create_default_config", new_callable=AsyncMock
            ) as mock_create:
                mock_create.return_value = Mock()

                service = ConfigService()

                config = await service.get_system_config()

                mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_system_config_exists(self):
        """测试获取已存在的系统配置"""
        with patch("app.services.config_service.get_mongo_db") as mock_get_db:
            from app.services.config_service import ConfigService

            mock_db = Mock()
            mock_collection = Mock()
            mock_collection.find_one = AsyncMock(
                return_value={
                    "config_name": "Test Config",
                    "version": 1,
                    "llm_configs": [],
                    "data_source_configs": [],
                    "database_configs": [],
                    "system_settings": {},
                }
            )
            mock_db.system_configs = mock_collection
            mock_get_db.return_value = mock_db

            service = ConfigService()

            config = await service.get_system_config()

            assert config is not None

    @pytest.mark.asyncio
    async def test_update_system_settings(self):
        """测试更新系统设置"""
        with patch("app.services.config_service.get_mongo_db") as mock_get_db:
            from app.services.config_service import ConfigService

            mock_db = Mock()
            mock_collection = Mock()

            mock_config = Mock()
            mock_config.system_settings = {"old_key": "old_value"}

            mock_db.system_configs = mock_collection
            mock_collection.find_one = AsyncMock(return_value=mock_config)
            mock_get_db.return_value = mock_db

            with patch.object(
                ConfigService, "save_system_config", new_callable=AsyncMock
            ) as mock_save:
                mock_save.return_value = True

                service = ConfigService()

                result = await service.update_system_settings({"new_key": "new_value"})

                assert result is True


class TestConfigServiceValidation:
    """配置验证相关测试"""

    def test_validate_config_data_valid(self):
        """测试有效配置数据验证"""
        with patch("app.services.config_service.get_mongo_db"):
            from app.services.config_service import ConfigService

            service = ConfigService()

            valid_data = {
                "llm_configs": [],
                "data_source_configs": [],
                "database_configs": [],
                "system_settings": {},
            }

            result = service._validate_config_data(valid_data)

            assert result is True

    def test_validate_config_data_missing_fields(self):
        """测试缺少字段的配置数据验证"""
        with patch("app.services.config_service.get_mongo_db"):
            from app.services.config_service import ConfigService

            service = ConfigService()

            invalid_data = {
                "llm_configs": []
                # missing other required fields
            }

            result = service._validate_config_data(invalid_data)

            assert result is False

    def test_truncate_api_key_short(self):
        """测试截断短API Key"""
        with patch("app.services.config_service.get_mongo_db"):
            from app.services.config_service import ConfigService

            service = ConfigService()

            result = service._truncate_api_key("short", 4, 4)

            assert result == "short"

    def test_truncate_api_key_long(self):
        """测试截断长API Key"""
        with patch("app.services.config_service.get_mongo_db"):
            from app.services.config_service import ConfigService

            service = ConfigService()

            result = service._truncate_api_key("0123456789abcdef", 4, 4)

            assert result == "0123...cdef"

    def test_truncate_api_key_empty(self):
        """测试截断空API Key"""
        with patch("app.services.config_service.get_mongo_db"):
            from app.services.config_service import ConfigService

            service = ConfigService()

            result = service._truncate_api_key("", 4, 4)

            assert result == ""
