# -*- coding: utf-8 -*-
"""
Data Provider 单元测试
测试所有数据提供者
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from tests.conftest import pytest


# 测试标记
pytestmark = pytest.mark.unit


class TestBaseStockDataProvider:
    """基础股票数据提供者测试"""

    @pytest.mark.asyncio
    async def test_base_provider_initialization(self):
        """测试基础提供者初始化"""
        from tradingagents.dataflows.providers.base_provider import (
            BaseStockDataProvider,
        )

        # BaseStockDataProvider 是抽象类，不能直接实例化
        # 只能测试其存在性和接口
        assert hasattr(BaseStockDataProvider, "get_stock_info")
        assert hasattr(BaseStockDataProvider, "get_stock_quote")
        assert hasattr(BaseStockDataProvider, "get_historical_data")
        assert hasattr(BaseStockDataProvider, "search_stocks")


class TestTushareProvider:
    """Tushare 数据提供者测试"""

    @pytest.mark.asyncio
    async def test_tushare_provider_initialization(self):
        """测试 Tushare 提供者初始化"""
        from tradingagents.dataflows.providers.china.tushare_provider import (
            TushareProvider,
        )

        provider = TushareProvider(token="test_token")

        assert provider.token == "test_token"

    @pytest.mark.asyncio
    @patch("tushare.pro_api")
    async def test_get_stock_info_success(self, mock_ts):
        """测试获取股票信息 - 成功场景"""
        from tradingagents.dataflows.providers.china.tushare_provider import (
            TushareProvider,
        )

        # Mock Tushare API 响应
        mock_api = Mock()
        mock_result = {
            "items": [
                {
                    "ts_code": "600519.SH",
                    "name": "贵州茅台",
                    "industry": "白酒",
                    "list_date": "20010827",
                }
            ]
        }
        mock_api.query = Mock(return_value=mock_result)
        mock_ts.return_value = mock_api

        provider = TushareProvider(token="test_token")
        result = await provider.get_stock_info("600519")

        assert result is not None
        assert result["name"] == "贵州茅台"

    @pytest.mark.asyncio
    @patch("tushare.pro_api")
    async def test_get_stock_quote_success(self, mock_ts):
        """测试获取股票报价 - 成功场景"""
        from tradingagents.dataflows.providers.china.tushare_provider import (
            TushareProvider,
        )

        mock_api = Mock()
        mock_result = {
            "items": [
                {
                    "ts_code": "600519.SH",
                    "trade_date": "20240115",
                    "open": 1800.0,
                    "high": 1850.0,
                    "low": 1790.0,
                    "close": 1835.0,
                    "vol": 100000,
                    "amount": 183500000.0,
                }
            ]
        }
        mock_api.daily = Mock(return_value=mock_result)
        mock_ts.return_value = mock_api

        provider = TushareProvider(token="test_token")
        result = await provider.get_stock_quote("600519", "2024-01-15", "2024-01-15")

        assert result is not None
        assert len(result) > 0

    @pytest.mark.asyncio
    @patch("tushare.pro_api")
    async def test_get_historical_data_success(self, mock_ts):
        """测试获取历史数据 - 成功场景"""
        from tradingagents.dataflows.providers.china.tushare_provider import (
            TushareProvider,
        )

        mock_api = Mock()
        mock_result = {
            "items": [
                {
                    "ts_code": "600519.SH",
                    "trade_date": "20240110",
                    "open": 1800.0,
                    "close": 1820.0,
                },
                {
                    "ts_code": "600519.SH",
                    "trade_date": "20240111",
                    "open": 1820.0,
                    "close": 1835.0,
                },
            ]
        }
        mock_api.daily = Mock(return_value=mock_result)
        mock_ts.return_value = mock_api

        provider = TushareProvider(token="test_token")
        result = await provider.get_historical_data(
            "600519", "2024-01-10", "2024-01-11"
        )

        assert result is not None
        assert len(result) == 2


class TestBaostockProvider:
    """Baostock 数据提供者测试"""

    @pytest.mark.asyncio
    async def test_baostock_provider_initialization(self):
        """测试 Baostock 提供者初始化"""
        from tradingagents.dataflows.providers.china.baostock_provider import (
            BaostockProvider,
        )

        provider = BaostockProvider()

        assert provider is not None

    @pytest.mark.asyncio
    @patch("baostock.login")
    @patch("baostock.query_history_k_data_plus")
    @patch("baostock.logout")
    async def test_get_stock_quote_success(self, mock_logout, mock_query, mock_login):
        """测试获取股票报价 - 成功场景"""
        from tradingagents.dataflows.providers.china.baostock_provider import (
            BaostockProvider,
        )
        import baostock as bs

        # Mock 登录成功
        mock_login.return_value = ("success", "登录成功")

        # Mock 查询结果
        mock_query.return_value = (
            "success",
            bs.rs.ResultSet(
                data=["2024-01-15,1800.0,1850.0,1790.0,1835.0,100000,183500000.0"],
                fields=["date", "open", "high", "low", "close", "volume", "amount"],
            ),
        )

        provider = BaostockProvider()
        result = await provider.get_stock_quote("600519", "2024-01-15", "2024-01-15")

        assert result is not None
        assert len(result) > 0


class TestAkShareProvider:
    """AkShare 数据提供者测试"""

    @pytest.mark.asyncio
    async def test_akshare_provider_initialization(self):
        """测试 AkShare 提供者初始化"""
        from tradingagents.dataflows.providers.china.akshare_provider import (
            AkShareProvider,
        )

        provider = AkShareProvider()

        assert provider is not None

    @pytest.mark.asyncio
    @patch("ak.stock_zh_a_hist")
    async def test_get_historical_data_success(self, mock_ak):
        """测试获取历史数据 - 成功场景"""
        from tradingagents.dataflows.providers.china.akshare_provider import (
            AkShareProvider,
        )
        import pandas as pd

        # Mock AkShare 响应
        mock_df = pd.DataFrame(
            {
                "日期": ["2024-01-10", "2024-01-11"],
                "开盘": [1800.0, 1820.0],
                "收盘": [1820.0, 1835.0],
            }
        )
        mock_ak.return_value = mock_df

        provider = AkShareProvider()
        result = await provider.get_historical_data(
            "600519", "2024-01-10", "2024-01-11"
        )

        assert result is not None
        assert len(result) == 2


class TestHKStockProvider:
    """港股数据提供者测试"""

    @pytest.mark.asyncio
    async def test_hk_provider_initialization(self):
        """测试港股提供者初始化"""
        from tradingagents.dataflows.providers.hk.akshare_hk_provider import (
            AkShareHKProvider,
        )

        provider = AkShareHKProvider()

        assert provider is not None

    @pytest.mark.asyncio
    @patch("ak.stock_hk_hist")
    async def test_get_hk_stock_quote_success(self, mock_ak):
        """测试获取港股报价 - 成功场景"""
        from tradingagents.dataflows.providers.hk.akshare_hk_provider import (
            AkShareHKProvider,
        )
        import pandas as pd

        mock_df = pd.DataFrame(
            {"date": ["2024-01-10"], "open": [300.0], "close": [305.0]}
        )
        mock_ak.return_value = mock_df

        provider = AkShareHKProvider()
        result = await provider.get_stock_quote("00700", "2024-01-10", "2024-01-10")

        assert result is not None


class TestUSStockProvider:
    """美股数据提供者测试"""

    @pytest.mark.asyncio
    async def test_us_provider_initialization(self):
        """测试美股提供者初始化"""
        from tradingagents.dataflows.providers.us.yfinance_provider import (
            YFinanceProvider,
        )

        provider = YFinanceProvider()

        assert provider is not None

    @pytest.mark.asyncio
    @patch("yfinance.download")
    async def test_get_us_stock_quote_success(self, mock_yf):
        """测试获取美股报价 - 成功场景"""
        from tradingagents.dataflows.providers.us.yfinance_provider import (
            YFinanceProvider,
        )
        import pandas as pd

        mock_df = pd.DataFrame(
            {
                "Open": [150.0],
                "High": [155.0],
                "Low": [148.0],
                "Close": [152.0],
                "Volume": [1000000],
            }
        )
        mock_yf.return_value = mock_df

        provider = YFinanceProvider()
        result = await provider.get_stock_quote("AAPL", "2024-01-10", "2024-01-10")

        assert result is not None


class TestDataSourceManager:
    """数据源管理器测试"""

    @pytest.mark.asyncio
    async def test_manager_initialization(self):
        """测试管理器初始化"""
        from tradingagents.dataflows.providers.base_provider import (
            get_data_source_manager,
        )

        manager = get_data_source_manager()

        assert manager is not None

    @pytest.mark.asyncio
    async def test_get_provider_by_market_type(self):
        """测试根据市场类型获取提供者"""
        from tradingagents.dataflows.providers.base_provider import (
            get_data_source_manager,
            MarketType,
        )

        manager = get_data_source_manager()

        # 获取 A股提供者
        provider = manager.get_provider(MarketType.CHINA_A)
        assert provider is not None

        # 获取港股提供者
        provider = manager.get_provider(MarketType.HK)
        assert provider is not None

    @pytest.mark.asyncio
    async def test_auto_fallback_mechanism(self):
        """测试自动降级机制"""
        from tradingagents.dataflows.providers.base_provider import (
            get_data_source_manager,
        )

        manager = get_data_source_manager()

        # 测试自动切换数据源
        # 这里我们只验证管理器有多数据源支持
        assert len(manager.available_sources) > 0

    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查"""
        from tradingagents.dataflows.providers.base_provider import (
            get_data_source_manager,
        )

        manager = get_data_source_manager()

        # 检查所有数据源的健康状态
        health_status = await manager.health_check()

        assert isinstance(health_status, dict)


class TestMultiSourceStrategy:
    """多源策略测试"""

    @pytest.mark.asyncio
    async def test_priority_order(self):
        """测试优先级顺序"""
        from tradingagents.dataflows.providers.base_provider import DataSourceType

        # 验证数据源的优先级顺序
        # Priority 1: Tushare
        # Priority 2: Baostock
        # Priority 3: AkShare

        assert DataSourceType.TUSHARE.value < DataSourceType.BAOSTOCK.value
        assert DataSourceType.BAOSTOCK.value < DataSourceType.AKSHARE.value

    @pytest.mark.asyncio
    async def test_auto_mode_selection(self):
        """测试自动模式选择"""
        from tradingagents.dataflows.providers.base_provider import (
            DataSourceManager,
            DataSourceType,
        )

        manager = DataSourceManager()

        # 测试自动模式：根据 API key 可用性选择最佳数据源
        selected = manager.auto_select_source()

        assert selected in manager.available_sources
