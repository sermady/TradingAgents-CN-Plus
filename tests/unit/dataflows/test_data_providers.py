# -*- coding: utf-8 -*-
"""
Data Provider 单元测试
测试所有数据提供者
"""

import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

os.environ["USE_MONGODB_STORAGE"] = "false"
os.environ["TRADINGAGENTS_SKIP_DB_INIT"] = "true"

# 测试标记
pytestmark = pytest.mark.unit


class TestBaseStockDataProvider:
    """基础股票数据提供者测试"""

    def test_base_provider_initialization(self):
        """测试基础提供者接口存在"""
        from tradingagents.dataflows.providers.base_provider import (
            BaseStockDataProvider,
        )

        assert hasattr(BaseStockDataProvider, "get_stock_basic_info")
        assert hasattr(BaseStockDataProvider, "get_stock_quotes")
        assert hasattr(BaseStockDataProvider, "get_historical_data")
        assert hasattr(BaseStockDataProvider, "get_stock_list")


class TestTushareProvider:
    """Tushare 数据提供者测试"""

    def test_tushare_provider_creation(self):
        """测试 Tushare 提供者创建"""
        from tradingagents.dataflows.providers.china.tushare import (
            TushareProvider,
        )

        assert TushareProvider is not None
        # Provider定义在类中
        assert hasattr(TushareProvider, "connect_sync") or hasattr(
            TushareProvider, "connect"
        )


class TestBaostockProvider:
    """Baostock 数据提供者测试"""

    def test_baostock_provider_creation(self):
        """测试 Baostock 提供者创建"""
        pytest.importorskip("baostock")
        from tradingagents.dataflows.providers.china.baostock import (
            BaoStockProvider,
        )

        provider = BaoStockProvider()
        assert provider.provider_name == "baostock"


class TestAkShareProvider:
    """AkShare 数据提供者测试"""

    def test_akshare_provider_creation(self):
        """测试 AkShare 提供者创建"""
        from tradingagents.dataflows.providers.china.akshare import (
            AKShareProvider,
        )

        provider = AKShareProvider()
        assert provider.provider_name == "AKShare"


class TestDataSourceManager:
    """数据源管理器测试"""

    def test_get_data_source_manager(self):
        """测试获取数据源管理器"""
        pytest.skip("此测试需要MongoDB连接，跳过")
