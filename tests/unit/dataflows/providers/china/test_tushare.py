# -*- coding: utf-8 -*-
"""
TushareProvider 单元测试

测试覆盖:
- 连接管理 (3个测试)
- 股票列表 (3个测试)
- 实时行情 (4个测试)
- 历史数据 (3个测试)
- 财务数据 (3个测试)
- 错误处理 (2个测试)

总计: 18个测试
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List

# 标记所有测试为unit类型
pytestmark = [
    pytest.mark.unit,
    pytest.mark.dataflow,
]


class TestTushareProviderConnection:
    """A. 连接管理测试 (3个测试)"""

    @pytest.fixture
    def mock_tushare_module(self):
        """创建模拟的tushare模块"""
        mock_ts = Mock()
        mock_pro = Mock()
        mock_ts.pro_api.return_value = mock_pro
        return mock_ts, mock_pro

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_tushare_module):
        """1. test_connect_success - 正常连接成功"""
        mock_ts, mock_pro = mock_tushare_module

        with patch.dict("os.environ", {"TUSHARE_TOKEN": "test_token"}):
            with patch("tradingagents.dataflows.providers.china.tushare.ts", mock_ts):
                with patch(
                    "tradingagents.dataflows.providers.china.tushare.TUSHARE_AVAILABLE",
                    True,
                ):
                    from tradingagents.dataflows.providers.china.tushare import (
                        TushareProvider,
                    )

                    # 先设置mock，再创建provider（__init__会调用connect_sync）
                    mock_pro.stock_basic.return_value = pd.DataFrame(
                        {"ts_code": ["000001.SZ"], "name": ["平安银行"]}
                    )

                    provider = TushareProvider()

                    result = await provider.connect()

                    assert result is True
                    assert provider.connected is True
                    assert provider.api is not None
                    mock_ts.pro_api.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_with_invalid_token(self, mock_tushare_module):
        """2. test_connect_with_invalid_token - Token无效"""
        mock_ts, mock_pro = mock_tushare_module

        with patch.dict("os.environ", {"TUSHARE_TOKEN": ""}):
            with patch("tradingagents.dataflows.providers.china.tushare.ts", mock_ts):
                with patch(
                    "tradingagents.dataflows.providers.china.tushare.TUSHARE_AVAILABLE",
                    True,
                ):
                    from tradingagents.dataflows.providers.china.tushare import (
                        TushareProvider,
                    )

                    provider = TushareProvider()

                    # Token为空时应该连接失败
                    assert provider.connected is False

    @pytest.mark.asyncio
    async def test_connect_when_disabled(self):
        """3. test_connect_when_disabled - 数据源被禁用"""
        with patch.dict(
            "os.environ", {"TUSHARE_ENABLED": "false", "TUSHARE_TOKEN": "test_token"}
        ):
            with patch(
                "tradingagents.dataflows.providers.china.tushare.TUSHARE_AVAILABLE",
                True,
            ):
                from tradingagents.dataflows.providers.china.tushare import (
                    TushareProvider,
                )

                provider = TushareProvider()

                # 当TUSHARE_ENABLED=false时，连接应该失败
                assert provider.connected is False


class TestTushareProviderStockList:
    """B. 股票列表测试 (3个测试)"""

    @pytest.fixture
    def provider_with_mock(self):
        """创建带有模拟的provider"""
        mock_ts = Mock()
        mock_pro = Mock()
        mock_ts.pro_api.return_value = mock_pro

        with patch.dict("os.environ", {"TUSHARE_TOKEN": "test_token"}):
            with patch("tradingagents.dataflows.providers.china.tushare.ts", mock_ts):
                with patch(
                    "tradingagents.dataflows.providers.china.tushare.TUSHARE_AVAILABLE",
                    True,
                ):
                    from tradingagents.dataflows.providers.china.tushare import (
                        TushareProvider,
                    )

                    provider = TushareProvider()
                    # 手动设置连接状态，模拟成功连接
                    provider.connected = True
                    provider.api = mock_pro
                    yield provider, mock_pro

    @pytest.mark.asyncio
    async def test_get_stock_list_success(self, provider_with_mock):
        """1. test_get_stock_list_success - 正常获取"""
        provider, mock_pro = provider_with_mock

        # 模拟返回的股票列表
        mock_df = pd.DataFrame(
            {
                "ts_code": ["000001.SZ", "600000.SH"],
                "name": ["平安银行", "浦发银行"],
                "industry": ["银行", "银行"],
                "market": ["主板", "主板"],
            }
        )
        mock_pro.stock_basic.return_value = mock_df

        result = await provider.get_stock_list()

        assert len(result) == 2
        assert result[0]["code"] == "000001"
        assert result[0]["name"] == "平安银行"
        assert result[1]["code"] == "600000"
        # stock_basic 被调用了多次（connect_sync + get_stock_list）
        assert mock_pro.stock_basic.called

    @pytest.mark.asyncio
    async def test_get_stock_list_empty(self, provider_with_mock):
        """2. test_get_stock_list_empty - 空数据返回"""
        provider, mock_pro = provider_with_mock

        # 模拟返回空DataFrame
        mock_pro.stock_basic.return_value = pd.DataFrame()

        result = await provider.get_stock_list()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_stock_list_api_error(self, provider_with_mock):
        """3. test_get_stock_list_api_error - API异常"""
        provider, mock_pro = provider_with_mock

        # 模拟API抛出异常
        mock_pro.stock_basic.side_effect = Exception("API Error")

        result = await provider.get_stock_list()

        assert result == []


class TestTushareProviderQuotes:
    """C. 实时行情测试 (4个测试)"""

    @pytest.fixture
    def provider_with_mock(self):
        """创建带有模拟的provider"""
        mock_ts = Mock()
        mock_pro = Mock()
        mock_ts.pro_api.return_value = mock_pro

        with patch.dict("os.environ", {"TUSHARE_TOKEN": "test_token"}):
            with patch("tradingagents.dataflows.providers.china.tushare.ts", mock_ts):
                with patch(
                    "tradingagents.dataflows.providers.china.tushare.TUSHARE_AVAILABLE",
                    True,
                ):
                    from tradingagents.dataflows.providers.china.tushare import (
                        TushareProvider,
                    )

                    provider = TushareProvider()
                    # 手动设置连接状态，模拟成功连接
                    provider.connected = True
                    provider.api = mock_pro
                    yield provider, mock_pro

    @pytest.mark.asyncio
    async def test_get_stock_quotes_success(self, provider_with_mock):
        """1. test_get_stock_quotes_success - 正常获取"""
        provider, mock_pro = provider_with_mock

        # 模拟返回的行情数据
        mock_df = pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "trade_date": ["20240101"],
                "open": [10.0],
                "high": [10.5],
                "low": [9.8],
                "close": [10.2],
                "pre_close": [10.0],
                "change": [0.2],
                "pct_chg": [2.0],
                "vol": [1000],
                "amount": [10200],
            }
        )
        mock_pro.daily.return_value = mock_df

        result = await provider.get_stock_quotes("000001")

        assert result is not None
        assert result["code"] == "000001"
        assert result["price"] == 10.2
        assert result["pct_chg"] == 2.0  # 涨跌幅字段名为 pct_chg

    @pytest.mark.asyncio
    async def test_get_stock_quotes_invalid_symbol(self, provider_with_mock):
        """2. test_get_stock_quotes_invalid_symbol - 无效代码"""
        provider, mock_pro = provider_with_mock

        # 模拟返回空DataFrame（无效代码）
        mock_pro.daily.return_value = pd.DataFrame()

        result = await provider.get_stock_quotes("999999")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stock_quotes_api_error(self, provider_with_mock):
        """3. test_get_stock_quotes_api_error - API失败"""
        provider, mock_pro = provider_with_mock

        # 模拟API抛出异常
        mock_pro.daily.side_effect = Exception("Network Error")

        result = await provider.get_stock_quotes("000001")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_batch_quotes(self, provider_with_mock):
        """4. test_get_batch_quotes - 批量获取"""
        provider, mock_pro = provider_with_mock

        # 模拟返回的批量行情数据 - get_realtime_quotes_batch 使用 rt_k 接口
        mock_df = pd.DataFrame(
            {
                "ts_code": ["000001.SZ", "600000.SH"],
                "open": [10.0, 20.0],
                "high": [10.5, 20.5],
                "low": [9.8, 19.8],
                "close": [10.2, 20.2],
                "pre_close": [10.0, 20.0],
                "vol": [1000, 2000],
                "amount": [10200, 40400],
                "name": ["平安银行", "浦发银行"],
            }
        )
        mock_pro.rt_k.return_value = mock_df

        # get_realtime_quotes_batch 不接受股票代码列表参数
        result = await provider.get_realtime_quotes_batch(force_refresh=True)

        assert result is not None
        assert len(result) == 2
        assert "000001" in result
        assert "600000" in result


class TestTushareProviderHistorical:
    """D. 历史数据测试 (3个测试)"""

    @pytest.fixture
    def provider_with_mock(self):
        """创建带有模拟的provider"""
        mock_ts = Mock()
        mock_pro = Mock()
        mock_ts.pro_api.return_value = mock_pro

        with patch.dict("os.environ", {"TUSHARE_TOKEN": "test_token"}):
            with patch("tradingagents.dataflows.providers.china.tushare.ts", mock_ts):
                with patch(
                    "tradingagents.dataflows.providers.china.tushare.TUSHARE_AVAILABLE",
                    True,
                ):
                    from tradingagents.dataflows.providers.china.tushare import (
                        TushareProvider,
                    )

                    provider = TushareProvider()
                    # 手动设置连接状态，模拟成功连接
                    provider.connected = True
                    provider.api = mock_pro
                    yield provider, mock_pro

    @pytest.mark.asyncio
    async def test_get_historical_data_daily(self, provider_with_mock):
        """1. test_get_historical_data_daily - 日K线"""
        provider, mock_pro = provider_with_mock

        # 模拟返回的历史数据
        mock_df = pd.DataFrame(
            {
                "ts_code": ["000001.SZ"] * 5,
                "trade_date": [
                    "20240101",
                    "20240102",
                    "20240103",
                    "20240104",
                    "20240105",
                ],
                "open": [10.0, 10.2, 10.1, 10.3, 10.5],
                "high": [10.5, 10.4, 10.6, 10.7, 10.8],
                "low": [9.8, 10.0, 10.0, 10.2, 10.3],
                "close": [10.2, 10.1, 10.3, 10.5, 10.4],
                "pre_close": [10.0, 10.2, 10.1, 10.3, 10.5],
                "change": [0.2, -0.1, 0.2, 0.2, -0.1],
                "pct_chg": [2.0, -1.0, 2.0, 2.0, -1.0],
                "vol": [1000, 1200, 1100, 1300, 1000],
                "amount": [10200, 12120, 11330, 13650, 10400],
            }
        )
        mock_pro.daily.return_value = mock_df

        result = await provider.get_historical_data(
            "000001", "2024-01-01", "2024-01-05", period="daily"
        )

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5
        assert "open" in result.columns
        assert "close" in result.columns
        assert "volume" in result.columns  # 标准化后的列名

    @pytest.mark.asyncio
    async def test_get_historical_data_different_periods(self, provider_with_mock):
        """2. test_get_historical_data_different_periods - 不同周期"""
        provider, mock_pro = provider_with_mock

        # 测试周线 - 使用 pro_bar 接口（实际实现使用 ts.pro_bar）
        mock_weekly_df = pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "trade_date": ["20240105"],
                "open": [10.0],
                "high": [10.8],
                "low": [9.8],
                "close": [10.4],
                "vol": [5600],
                "amount": [57700],
            }
        )

        # Mock ts.pro_bar 函数
        with patch("tradingagents.dataflows.providers.china.tushare.ts") as mock_ts:
            mock_ts.pro_bar.return_value = mock_weekly_df
            result = await provider.get_historical_data(
                "000001", "2024-01-01", "2024-01-05", period="weekly"
            )

            assert result is not None
            # pro_bar 应该被调用，传入 freq='W' 表示周线
            mock_ts.pro_bar.assert_called_once()
            call_kwargs = mock_ts.pro_bar.call_args.kwargs
            assert call_kwargs.get("freq") == "W"

    @pytest.mark.asyncio
    async def test_get_historical_data_empty_range(self, provider_with_mock):
        """3. test_get_historical_data_empty_range - 空日期范围"""
        provider, mock_pro = provider_with_mock

        # 模拟返回空DataFrame
        mock_pro.daily.return_value = pd.DataFrame()

        result = await provider.get_historical_data(
            "000001",
            "2024-01-01",
            "2023-01-01",
            period="daily",  # 无效范围
        )

        assert result is None


class TestTushareProviderFinancial:
    """E. 财务数据测试 (3个测试)"""

    @pytest.fixture
    def provider_with_mock(self):
        """创建带有模拟的provider"""
        mock_ts = Mock()
        mock_pro = Mock()
        mock_ts.pro_api.return_value = mock_pro

        with patch.dict("os.environ", {"TUSHARE_TOKEN": "test_token"}):
            with patch("tradingagents.dataflows.providers.china.tushare.ts", mock_ts):
                with patch(
                    "tradingagents.dataflows.providers.china.tushare.TUSHARE_AVAILABLE",
                    True,
                ):
                    from tradingagents.dataflows.providers.china.tushare import (
                        TushareProvider,
                    )

                    provider = TushareProvider()
                    # 手动设置连接状态，模拟成功连接
                    provider.connected = True
                    provider.api = mock_pro
                    yield provider, mock_pro

    @pytest.mark.asyncio
    async def test_get_financial_data_success(self, provider_with_mock):
        """1. test_get_financial_data_success - 正常获取"""
        provider, mock_pro = provider_with_mock

        # 模拟返回的财务数据
        mock_income_df = pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "ann_date": ["20240331"],
                "f_ann_date": ["20240331"],
                "end_date": ["20240331"],
                "revenue": [100000000],
                "n_income": [20000000],
            }
        )
        mock_balance_df = pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "ann_date": ["20240331"],
                "total_assets": [1000000000],
                "total_liab": [800000000],
                "total_hldr_eqy_exc_min_int": [200000000],
            }
        )

        mock_pro.income.return_value = mock_income_df
        mock_pro.balancesheet.return_value = mock_balance_df

        result = await provider.get_financial_data("000001")

        assert result is not None
        assert isinstance(result, dict)
        mock_pro.income.assert_called_once()
        mock_pro.balancesheet.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_financial_data_partial_missing(self, provider_with_mock):
        """2. test_get_financial_data_partial_missing - 部分缺失"""
        provider, mock_pro = provider_with_mock

        # 模拟收入数据存在，但资产负债表缺失
        mock_income_df = pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "revenue": [100000000],
                "n_income": [20000000],
            }
        )
        mock_pro.income.return_value = mock_income_df
        mock_pro.balancesheet.return_value = pd.DataFrame()  # 空数据

        result = await provider.get_financial_data("000001")

        # 应该返回部分数据
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_financial_data_all_missing(self, provider_with_mock):
        """3. test_get_financial_data_all_missing - 全部缺失"""
        provider, mock_pro = provider_with_mock

        # 模拟所有财务数据都缺失
        mock_pro.income.return_value = pd.DataFrame()
        mock_pro.balancesheet.return_value = pd.DataFrame()
        mock_pro.cashflow.return_value = pd.DataFrame()

        result = await provider.get_financial_data("000001")

        # 当所有财务数据都缺失时，返回None
        assert result is None


class TestTushareProviderErrorHandling:
    """F. 错误处理测试 (2个测试)"""

    @pytest.fixture
    def provider_with_mock(self):
        """创建带有模拟的provider"""
        mock_ts = Mock()
        mock_pro = Mock()
        mock_ts.pro_api.return_value = mock_pro

        with patch.dict("os.environ", {"TUSHARE_TOKEN": "test_token"}):
            with patch("tradingagents.dataflows.providers.china.tushare.ts", mock_ts):
                with patch(
                    "tradingagents.dataflows.providers.china.tushare.TUSHARE_AVAILABLE",
                    True,
                ):
                    from tradingagents.dataflows.providers.china.tushare import (
                        TushareProvider,
                    )

                    provider = TushareProvider()
                    # 手动设置连接状态，模拟成功连接
                    provider.connected = True
                    provider.api = mock_pro
                    yield provider, mock_pro

    @pytest.mark.asyncio
    async def test_error_handling_returns_none(self, provider_with_mock):
        """1. test_error_handling_returns_none - 返回None模式"""
        provider, mock_pro = provider_with_mock

        # 模拟各种API错误
        mock_pro.daily.side_effect = Exception("API Timeout")
        mock_pro.stock_basic.side_effect = Exception("Network Error")

        # 测试行情获取失败返回None
        quotes_result = await provider.get_stock_quotes("000001")
        assert quotes_result is None

        # 测试股票列表获取失败返回空列表
        list_result = await provider.get_stock_list()
        assert list_result == []

    @pytest.mark.asyncio
    async def test_error_handling_logs_error(self, provider_with_mock, caplog):
        """2. test_error_handling_logs_error - 错误日志记录"""
        import logging

        provider, mock_pro = provider_with_mock

        # 设置日志级别
        caplog.set_level(logging.ERROR)

        # 模拟API错误
        mock_pro.daily.side_effect = Exception("Test Error")

        # 调用方法
        await provider.get_stock_quotes("000001")

        # 验证错误被记录
        assert "Test Error" in caplog.text or "获取" in caplog.text


class TestTushareProviderAdditional:
    """额外测试 - 边界情况和特殊功能"""

    @pytest.fixture
    def provider_with_mock(self):
        """创建带有模拟的provider"""
        mock_ts = Mock()
        mock_pro = Mock()
        mock_ts.pro_api.return_value = mock_pro

        with patch.dict("os.environ", {"TUSHARE_TOKEN": "test_token"}):
            with patch("tradingagents.dataflows.providers.china.tushare.ts", mock_ts):
                with patch(
                    "tradingagents.dataflows.providers.china.tushare.TUSHARE_AVAILABLE",
                    True,
                ):
                    from tradingagents.dataflows.providers.china.tushare import (
                        TushareProvider,
                    )

                    provider = TushareProvider()
                    # 手动设置连接状态，模拟成功连接
                    provider.connected = True
                    provider.api = mock_pro
                    yield provider, mock_pro

    @pytest.mark.asyncio
    async def test_code_format_conversion(self, provider_with_mock):
        """测试股票代码格式转换"""
        provider, mock_pro = provider_with_mock

        # 测试各种代码格式的转换 - get_stock_quotes 使用 get_realtime_quotes
        with patch("tradingagents.dataflows.providers.china.tushare.ts") as mock_ts:
            mock_ts.get_realtime_quotes.return_value = pd.DataFrame(
                {
                    "name": ["平安银行"],
                    "open": [10.0],
                    "high": [10.5],
                    "low": [9.8],
                    "price": [10.2],
                    "pre_close": [10.0],
                    "volume": [100000],  # 股
                    "amount": [1020000],
                    "date": ["2024-01-01"],
                    "time": ["10:00:00"],
                }
            )

            # 传入不同格式的代码
            result = await provider.get_stock_quotes("000001.SZ")  # 带后缀

            # 验证结果
            assert result is not None
            assert result["symbol"] == "000001.SZ"
            assert result["price"] == 10.2
            # 验证 get_realtime_quotes 被调用，且传入的是6位代码
            mock_ts.get_realtime_quotes.assert_called_once_with("000001")

    @pytest.mark.asyncio
    async def test_batch_quotes_cache(self, provider_with_mock):
        """测试批量行情缓存机制"""
        provider, mock_pro = provider_with_mock

        mock_df = pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "close": [10.0],
                "vol": [1000],
                "amount": [10000],
            }
        )
        mock_pro.daily.return_value = mock_df

        # 第一次调用应该调用API
        result1 = await provider.get_realtime_quotes_batch(["000001"])

        # 验证缓存状态
        from tradingagents.dataflows.providers.china.tushare import (
            _is_batch_cache_valid,
        )

        # 缓存应该有效
        assert _is_batch_cache_valid() is True

    @pytest.mark.asyncio
    async def test_volume_unit_conversion(self, provider_with_mock):
        """测试成交量单位转换"""
        provider, mock_pro = provider_with_mock

        # Tushare返回的成交量单位是手
        mock_df = pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "trade_date": ["20240101"],
                "open": [10.0],
                "high": [10.5],
                "low": [9.8],
                "close": [10.2],
                "pre_close": [10.0],
                "change": [0.2],
                "pct_chg": [2.0],
                "vol": [1000],  # 单位：手
                "amount": [10200],
            }
        )
        mock_pro.daily.return_value = mock_df

        result = await provider.get_stock_quotes("000001")

        # 验证成交量单位保持为手（根据2026-01-30的修改）
        assert result["volume"] == 1000  # 手
        assert result["volume_unit"] == "lots"
