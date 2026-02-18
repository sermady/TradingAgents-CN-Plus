# -*- coding: utf-8 -*-
"""
测试数据源管理器功能

测试范围:
- 中国数据源枚举
- 数据源配置
- 简化的管理器功能测试
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock

os.environ["USE_MONGODB_STORAGE"] = "false"
os.environ["TRADINGAGENTS_SKIP_DB_INIT"] = "true"


@pytest.mark.unit
class TestChinaDataSourceEnum:
    """测试中国数据源枚举"""

    def test_enum_values(self):
        """测试枚举值"""
        from tradingagents.dataflows.data_sources.enums import ChinaDataSource

        assert ChinaDataSource.TUSHARE.value == "tushare"
        assert ChinaDataSource.AKSHARE.value == "akshare"
        assert ChinaDataSource.BAOSTOCK.value == "baostock"
        assert ChinaDataSource.MONGODB.value == "mongodb"

    def test_enum_comparison(self):
        """测试枚举比较"""
        from tradingagents.dataflows.data_sources.enums import ChinaDataSource

        source1 = ChinaDataSource.AKSHARE
        source2 = ChinaDataSource.AKSHARE
        source3 = ChinaDataSource.TUSHARE

        assert source1 == source2
        assert source1 != source3


@pytest.mark.unit
class TestDataSourceEnums:
    """测试数据源枚举模块"""

    def test_import_enums(self):
        """测试导入枚举"""
        from tradingagents.dataflows.data_sources.enums import ChinaDataSource

        # 验证所有枚举成员
        members = list(ChinaDataSource)
        assert len(members) >= 4

    def test_enum_string_representation(self):
        """测试枚举字符串表示"""
        from tradingagents.dataflows.data_sources.enums import ChinaDataSource

        assert str(ChinaDataSource.TUSHARE) == "ChinaDataSource.TUSHARE"
        assert ChinaDataSource.TUSHARE.value == "tushare"


@pytest.mark.unit
class TestDataSourceFactory:
    """测试数据源工厂"""

    def test_import_factory(self):
        """测试导入数据源工厂"""
        from tradingagents.dataflows.data_sources import factory

        assert factory is not None

    def test_factory_module_exists(self):
        """测试工厂模块存在"""
        import tradingagents.dataflows.data_sources.factory as factory_module

        # 验证模块存在
        assert factory_module is not None


@pytest.mark.unit
class TestBaseAdapter:
    """测试基础适配器"""

    def test_import_base_adapter(self):
        """测试导入基础适配器"""
        from tradingagents.dataflows.adapters.base_adapter import BaseDataAdapter

        assert BaseDataAdapter is not None


@pytest.mark.unit
class TestInterfaceModule:
    """测试接口模块"""

    def test_import_interface(self):
        """测试导入接口模块"""
        from tradingagents.dataflows import interface

        assert interface is not None

    def test_interface_has_required_functions(self):
        """测试接口模块包含必要函数"""
        from tradingagents.dataflows import interface

        # 检查一些关键函数是否存在
        expected_functions = [
            "get_chinese_social_sentiment",
        ]

        for func_name in expected_functions:
            assert hasattr(interface, func_name), f"缺少函数: {func_name}"


@pytest.mark.unit
class TestCacheModule:
    """测试缓存模块"""

    def test_import_cache_modules(self):
        """测试导入缓存模块"""
        from tradingagents.dataflows.cache import file_cache, db_cache, adaptive

        assert file_cache is not None
        assert db_cache is not None
        assert adaptive is not None


@pytest.mark.unit
class TestManagersModule:
    """测试管理器模块"""

    def test_import_cache_manager(self):
        """测试导入缓存管理器"""
        from tradingagents.dataflows.managers.cache_manager import CacheManager

        assert CacheManager is not None

    def test_import_fallback_manager(self):
        """测试导入降级管理器"""
        from tradingagents.dataflows.managers.fallback_manager import FallbackManager

        assert FallbackManager is not None

    def test_import_config_manager(self):
        """测试导入配置管理器"""
        from tradingagents.dataflows.managers.config_manager import ConfigManager

        assert ConfigManager is not None


@pytest.mark.unit
class TestProvidersModule:
    """测试数据提供者模块"""

    def test_import_china_providers(self):
        """测试导入中国数据提供者"""
        from tradingagents.dataflows.providers.china import tushare, akshare, baostock

        assert tushare is not None
        assert akshare is not None
        assert baostock is not None

    def test_import_base_provider(self):
        """测试导入基础提供者"""
        from tradingagents.dataflows.providers.base_provider import (
            BaseStockDataProvider,
        )

        assert BaseStockDataProvider is not None


@pytest.mark.unit
class TestNewsModule:
    """测试新闻模块"""

    def test_import_news_modules(self):
        """测试导入新闻模块"""
        from tradingagents.dataflows.news import google_news, chinese_finance

        assert google_news is not None
        assert chinese_finance is not None


@pytest.mark.unit
class TestTechnicalModule:
    """测试技术分析模块"""

    def test_import_technical_module(self):
        """测试导入技术分析模块"""
        from tradingagents.dataflows.technical import stockstats

        assert stockstats is not None


@pytest.mark.unit
class TestValidatorsModule:
    """测试验证器模块"""

    def test_import_validators(self):
        """测试导入验证器"""
        from tradingagents.dataflows.validators import (
            base_validator,
            fundamentals_validator,
            price_validator,
            volume_validator,
        )

        assert base_validator is not None
        assert fundamentals_validator is not None
        assert price_validator is not None
        assert volume_validator is not None


@pytest.mark.unit
class TestSchemasModule:
    """测试数据模式模块"""

    def test_import_schemas(self):
        """测试导入数据模式"""
        from tradingagents.dataflows.schemas import stock_basic_schema

        assert stock_basic_schema is not None


@pytest.mark.unit
class TestStandardizersModule:
    """测试数据标准化模块"""

    def test_import_standardizers(self):
        """测试导入数据标准化模块"""
        from tradingagents.dataflows.standardizers import (
            data_standardizer,
            stock_basic_standardizer,
        )

        assert data_standardizer is not None
        assert stock_basic_standardizer is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
