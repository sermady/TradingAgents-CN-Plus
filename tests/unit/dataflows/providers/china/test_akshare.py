# -*- coding: utf-8 -*-
"""
AKShareProvider 单元测试

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


class TestAKShareProviderConnection:
    """A. 连接管理测试 (3个测试)"""

    @pytest.fixture
    def mock_akshare_module(self):
        """创建模拟的akshare模块"""
        mock_ak = Mock()
        mock_ak.stock_info_a_code_name.return_value = pd.DataFrame(
            {"code": ["000001"], "name": ["平安银行"]}
        )
        return mock_ak

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_akshare_module):
        """1. test_connect_success - 正常连接成功"""
        mock_ak = mock_akshare_module

        with patch.dict("os.environ", {"AKSHARE_UNIFIED_ENABLED": "true"}):
            with patch(
                "tradingagents.dataflows.providers.china.akshare.ak", mock_ak
            ):
                from tradingagents.dataflows.providers.china.akshare import (
                    AKShareProvider,
                )

                provider = AKShareProvider()

                result = await provider.connect()

                assert result is True
                assert provider.connected is True

    @pytest.mark.asyncio
    async def test_connect_with_import_error(self):
        """2. test_connect_with_import_error - 导入错误"""
        from tradingagents.dataflows.providers.china.akshare import (
            AKShareProvider,
        )

        with patch.dict("os.environ", {"AKSHARE_UNIFIED_ENABLED": "true"}):
            with patch(
                "tradingagents.dataflows.providers.china.akshare.ak",
                None,
            ):
                with patch.object(
                    AKShareProvider,
                    "_initialize_akshare",
                    side_effect=ImportError("No module named 'akshare'"),
                ):
                    provider = AKShareProvider()
                    # 导入错误时应该设置connected为False
                    assert provider.connected is False

    @pytest.mark.asyncio
    async def test_connect_when_disabled(self):
        """3. test_connect_when_disabled - 数据源被禁用"""
        with patch.dict(
            "os.environ", {"AKSHARE_UNIFIED_ENABLED": "false"}
        ):
            from tradingagents.dataflows.providers.china.akshare import (
                AKShareProvider,
            )

            provider = AKShareProvider()

            # 当AKSHARE_UNIFIED_ENABLED=false时，连接应该失败
            assert provider.connected is False


class TestAKShareProviderStockList:
    """B. 股票列表测试 (3个测试)"""

    @pytest.fixture
    def provider_with_mock(self):
        """创建带有模拟的provider"""
        mock_ak = Mock()
        mock_ak.stock_info_a_code_name.return_value = pd.DataFrame(
            {"code": ["000001"], "name": ["平安银行"]}
        )

        with patch.dict("os.environ", {"AKSHARE_UNIFIED_ENABLED": "true"}):
            with patch(
                "tradingagents.dataflows.providers.china.akshare.ak", mock_ak
            ):
                from tradingagents.dataflows.providers.china.akshare import (
                    AKShareProvider,
                )

                provider = AKShareProvider()
                yield provider, mock_ak

    @pytest.mark.asyncio
    async def test_get_stock_list_success(self, provider_with_mock):
        """1. test_get_stock_list_success - 正常获取"""
        provider, mock_ak = provider_with_mock

        # 模拟返回的股票列表
        mock_df = pd.DataFrame(
            {
                "code": ["000001", "600000"],
                "name": ["平安银行", "浦发银行"],
            }
        )
        mock_ak.stock_info_a_code_name.return_value = mock_df

        result = await provider.get_stock_list()

        assert len(result) == 2
        assert result[0]["code"] == "000001"
        assert result[0]["name"] == "平安银行"
        assert result[1]["code"] == "600000"
        mock_ak.stock_info_a_code_name.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stock_list_empty(self, provider_with_mock):
        """2. test_get_stock_list_empty - 空数据返回"""
        provider, mock_ak = provider_with_mock

        # 模拟返回空DataFrame
        mock_ak.stock_info_a_code_name.return_value = pd.DataFrame()

        result = await provider.get_stock_list()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_stock_list_api_error(self, provider_with_mock):
        """3. test_get_stock_list_api_error - API异常"""
        provider, mock_ak = provider_with_mock

        # 模拟API抛出异常
        mock_ak.stock_info_a_code_name.side_effect = Exception("Network Error")

        result = await provider.get_stock_list()

        assert result == []


class TestAKShareProviderQuotes:
    """C. 实时行情测试 (4个测试)"""

    @pytest.fixture
    def provider_with_mock(self):
        """创建带有模拟的provider"""
        mock_ak = Mock()

        with patch.dict("os.environ", {"AKSHARE_UNIFIED_ENABLED": "true"}):
            with patch(
                "tradingagents.dataflows.providers.china.akshare.ak", mock_ak
            ):
                from tradingagents.dataflows.providers.china.akshare import (
                    AKShareProvider,
                )

                provider = AKShareProvider()
                yield provider, mock_ak

    @pytest.mark.asyncio
    async def test_get_stock_quotes_success(self, provider_with_mock):
        """1. test_get_stock_quotes_success - 正常获取"""
        provider, mock_ak = provider_with_mock

        # 模拟返回的行情数据
        mock_df = pd.DataFrame(
            {
                "item": ["最新", "涨跌", "涨幅", "总手", "金额", "今开", "最高", "最低", "昨收"],
                "value": ["10.2", "0.2", "2.0", "1000", "10200", "10.0", "10.5", "9.8", "10.0"],
            }
        )
        mock_ak.stock_bid_ask_em.return_value = mock_df

        result = await provider.get_stock_quotes("000001")

        assert result is not None
        assert result["code"] == "000001"
        assert result["price"] == 10.2
        assert result["change_percent"] == 2.0
        assert result["volume"] == 1000  # 手
        assert result["data_source"] == "akshare"

    @pytest.mark.asyncio
    async def test_get_stock_quotes_invalid_symbol(self, provider_with_mock):
        """2. test_get_stock_quotes_invalid_symbol - 无效代码"""
        provider, mock_ak = provider_with_mock

        # 模拟返回空DataFrame（无效代码）
        mock_ak.stock_bid_ask_em.return_value = pd.DataFrame()

        result = await provider.get_stock_quotes("999999")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_stock_quotes_api_error(self, provider_with_mock):
        """3. test_get_stock_quotes_api_error - API失败"""
        provider, mock_ak = provider_with_mock

        # 模拟API抛出异常
        mock_ak.stock_bid_ask_em.side_effect = Exception("API Error")

        result = await provider.get_stock_quotes("000001")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_batch_quotes(self, provider_with_mock):
        """4. test_get_batch_quotes - 批量获取"""
        provider, mock_ak = provider_with_mock

        # 模拟返回的批量行情数据
        mock_df = pd.DataFrame(
            {
                "代码": ["000001", "600000"],
                "名称": ["平安银行", "浦发银行"],
                "最新价": [10.2, 20.2],
                "涨跌额": [0.2, 0.2],
                "涨跌幅": [2.0, 1.0],
                "成交量": [1000, 2000],
                "成交额": [10200, 40400],
                "今开": [10.0, 20.0],
                "最高": [10.5, 20.5],
                "最低": [9.8, 19.8],
                "昨收": [10.0, 20.0],
            }
        )
        mock_ak.stock_zh_a_spot_em.return_value = mock_df

        result = await provider.get_batch_stock_quotes(["000001", "600000"])

        assert len(result) == 2
        assert "000001" in result
        assert "600000" in result
        assert result["000001"]["price"] == 10.2
        assert result["600000"]["price"] == 20.2


class TestAKShareProviderHistorical:
    """D. 历史数据测试 (3个测试)"""

    @pytest.fixture
    def provider_with_mock(self):
        """创建带有模拟的provider"""
        mock_ak = Mock()

        with patch.dict("os.environ", {"AKSHARE_UNIFIED_ENABLED": "true"}):
            with patch(
                "tradingagents.dataflows.providers.china.akshare.ak", mock_ak
            ):
                from tradingagents.dataflows.providers.china.akshare import (
                    AKShareProvider,
                )

                provider = AKShareProvider()
                yield provider, mock_ak

    @pytest.mark.asyncio
    async def test_get_historical_data_daily(self, provider_with_mock):
        """1. test_get_historical_data_daily - 日K线"""
        provider, mock_ak = provider_with_mock

        # 模拟返回的历史数据
        mock_df = pd.DataFrame(
            {
                "日期": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
                "开盘": [10.0, 10.2, 10.1],
                "收盘": [10.2, 10.1, 10.3],
                "最高": [10.5, 10.4, 10.6],
                "最低": [9.8, 10.0, 10.0],
                "成交量": [1000, 1200, 1100],
                "成交额": [10200, 12120, 11330],
                "振幅": [7.0, 3.9, 5.9],
                "涨跌幅": [2.0, -1.0, 2.0],
                "涨跌额": [0.2, -0.1, 0.2],
                "换手率": [1.5, 1.8, 1.6],
            }
        )
        mock_ak.stock_zh_a_hist.return_value = mock_df

        result = await provider.get_historical_data(
            "000001", "2024-01-01", "2024-01-03", period="daily"
        )

        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert "open" in result.columns  # 标准化后的列名
        assert "close" in result.columns
        assert "volume" in result.columns

    @pytest.mark.asyncio
    async def test_get_historical_data_different_periods(self, provider_with_mock):
        """2. test_get_historical_data_different_periods - 不同周期"""
        provider, mock_ak = provider_with_mock

        # 测试周线
        mock_weekly_df = pd.DataFrame(
            {
                "日期": pd.to_datetime(["2024-01-05"]),
                "开盘": [10.0],
                "收盘": [10.4],
                "最高": [10.8],
                "最低": [9.8],
                "成交量": [5600],
                "成交额": [57700],
            }
        )
        mock_ak.stock_zh_a_hist.return_value = mock_weekly_df

        result = await provider.get_historical_data(
            "000001", "2024-01-01", "2024-01-05", period="weekly"
        )

        assert result is not None
        mock_ak.stock_zh_a_hist.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_historical_data_empty_range(self, provider_with_mock):
        """3. test_get_historical_data_empty_range - 空日期范围"""
        provider, mock_ak = provider_with_mock

        # 模拟返回空DataFrame
        mock_ak.stock_zh_a_hist.return_value = pd.DataFrame()

        result = await provider.get_historical_data(
            "000001", "2024-01-01", "2023-01-01", period="daily"  # 无效范围
        )

        assert result is None


class TestAKShareProviderFinancial:
    """E. 财务数据测试 (3个测试)"""

    @pytest.fixture
    def provider_with_mock(self):
        """创建带有模拟的provider"""
        mock_ak = Mock()

        with patch.dict("os.environ", {"AKSHARE_UNIFIED_ENABLED": "true"}):
            with patch(
                "tradingagents.dataflows.providers.china.akshare.ak", mock_ak
            ):
                from tradingagents.dataflows.providers.china.akshare import (
                    AKShareProvider,
                )

                provider = AKShareProvider()
                yield provider, mock_ak

    @pytest.mark.asyncio
    async def test_get_financial_data_success(self, provider_with_mock):
        """1. test_get_financial_data_success - 正常获取"""
        provider, mock_ak = provider_with_mock

        # 模拟返回的财务数据
        mock_income_df = pd.DataFrame(
            {
                "REPORT_DATE": ["2024-03-31"],
                "TOTAL_OPERATE_INCOME": [100000000],
                "NETPROFIT": [20000000],
            }
        )
        mock_balance_df = pd.DataFrame(
            {
                "REPORT_DATE": ["2024-03-31"],
                "TOTAL_ASSETS": [1000000000],
                "TOTAL_LIABILITIES": [800000000],
            }
        )

        mock_ak.stock_financial_abstract.return_value = mock_income_df
        mock_ak.stock_balance_sheet_by_report_em.return_value = mock_balance_df
        mock_ak.stock_profit_sheet_by_report_em.return_value = pd.DataFrame()
        mock_ak.stock_cash_flow_sheet_by_report_em.return_value = pd.DataFrame()

        result = await provider.get_financial_data("000001")

        assert result is not None
        assert isinstance(result, dict)
        mock_ak.stock_financial_abstract.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_financial_data_partial_missing(self, provider_with_mock):
        """2. test_get_financial_data_partial_missing - 部分缺失"""
        provider, mock_ak = provider_with_mock

        # 模拟部分数据存在
        mock_ak.stock_financial_abstract.return_value = pd.DataFrame(
            {"REPORT_DATE": ["2024-03-31"], "TOTAL_OPERATE_INCOME": [100000000]}
        )
        mock_ak.stock_balance_sheet_by_report_em.side_effect = Exception(
            "Data not available"
        )
        mock_ak.stock_profit_sheet_by_report_em.return_value = pd.DataFrame()
        mock_ak.stock_cash_flow_sheet_by_report_em.return_value = pd.DataFrame()

        result = await provider.get_financial_data("000001")

        # 应该返回部分数据
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_financial_data_all_missing(self, provider_with_mock):
        """3. test_get_financial_data_all_missing - 全部缺失"""
        provider, mock_ak = provider_with_mock

        # 模拟所有财务数据都缺失
        mock_ak.stock_financial_abstract.return_value = pd.DataFrame()
        mock_ak.stock_balance_sheet_by_report_em.return_value = pd.DataFrame()
        mock_ak.stock_profit_sheet_by_report_em.return_value = pd.DataFrame()
        mock_ak.stock_cash_flow_sheet_by_report_em.return_value = pd.DataFrame()

        result = await provider.get_financial_data("000001")

        # 应该返回空字典
        assert isinstance(result, dict)


class TestAKShareProviderErrorHandling:
    """F. 错误处理测试 (2个测试)"""

    @pytest.fixture
    def provider_with_mock(self):
        """创建带有模拟的provider"""
        mock_ak = Mock()

        with patch.dict("os.environ", {"AKSHARE_UNIFIED_ENABLED": "true"}):
            with patch(
                "tradingagents.dataflows.providers.china.akshare.ak", mock_ak
            ):
                from tradingagents.dataflows.providers.china.akshare import (
                    AKShareProvider,
                )

                provider = AKShareProvider()
                yield provider, mock_ak

    @pytest.mark.asyncio
    async def test_error_handling_returns_none(self, provider_with_mock):
        """1. test_error_handling_returns_none - 返回None模式"""
        provider, mock_ak = provider_with_mock

        # 模拟各种API错误
        mock_ak.stock_bid_ask_em.side_effect = Exception("API Timeout")
        mock_ak.stock_info_a_code_name.side_effect = Exception("Network Error")

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

        provider, mock_ak = provider_with_mock

        # 设置日志级别
        caplog.set_level(logging.ERROR)

        # 模拟API错误
        mock_ak.stock_bid_ask_em.side_effect = Exception("Test Error")

        # 调用方法
        await provider.get_stock_quotes("000001")

        # 验证错误被记录
        assert "Test Error" in caplog.text or "获取" in caplog.text


class TestAKShareProviderCache:
    """额外测试 - AKShare缓存机制"""

    @pytest.fixture
    def provider_with_mock(self):
        """创建带有模拟的provider"""
        mock_ak = Mock()

        with patch.dict("os.environ", {"AKSHARE_UNIFIED_ENABLED": "true"}):
            with patch(
                "tradingagents.dataflows.providers.china.akshare.ak", mock_ak
            ):
                from tradingagents.dataflows.providers.china.akshare import (
                    AKShareProvider,
                )

                provider = AKShareProvider()
                yield provider, mock_ak

    @pytest.mark.asyncio
    async def test_quotes_cache(self, provider_with_mock):
        """测试行情缓存功能"""
        provider, mock_ak = provider_with_mock

        # 模拟返回的行情数据
        mock_df = pd.DataFrame(
            {
                "item": ["最新", "涨跌", "涨幅", "总手", "金额", "今开", "最高", "最低", "昨收"],
                "value": ["10.2", "0.2", "2.0", "1000", "10200", "10.0", "10.5", "9.8", "10.0"],
            }
        )
        mock_ak.stock_bid_ask_em.return_value = mock_df

        # 清空缓存
        from tradingagents.dataflows.providers.china.akshare import (
            AKSHARE_QUOTES_CACHE,
        )

        AKSHARE_QUOTES_CACHE.clear()

        # 第一次调用应该调用API
        result1 = await provider.get_stock_quotes_cached("000001")
        assert result1 is not None
        assert mock_ak.stock_bid_ask_em.call_count == 1

        # 第二次调用应该使用缓存（不增加API调用次数）
        result2 = await provider.get_stock_quotes_cached("000001")
        assert result2 is not None
        assert mock_ak.stock_bid_ask_em.call_count == 1  # 仍然是1次

        # 强制刷新应该再次调用API
        result3 = await provider.get_stock_quotes_cached("000001", force_refresh=True)
        assert result3 is not None
        assert mock_ak.stock_bid_ask_em.call_count == 2  # 增加到2次

    @pytest.mark.asyncio
    async def test_stock_list_cache(self, provider_with_mock):
        """测试股票列表缓存"""
        provider, mock_ak = provider_with_mock

        mock_df = pd.DataFrame(
            {
                "code": ["000001", "600000"],
                "name": ["平安银行", "浦发银行"],
            }
        )
        mock_ak.stock_info_a_code_name.return_value = mock_df

        # 第一次调用
        result1 = await provider._get_stock_list_cached()
        assert result1 is not None
        first_call_count = mock_ak.stock_info_a_code_name.call_count

        # 第二次调用应该使用缓存
        result2 = await provider._get_stock_list_cached()
        assert result2 is not None
        assert mock_ak.stock_info_a_code_name.call_count == first_call_count


class TestAKShareProviderNews:
    """额外测试 - AKShare新闻数据"""

    @pytest.fixture
    def provider_with_mock(self):
        """创建带有模拟的provider"""
        mock_ak = Mock()

        with patch.dict("os.environ", {"AKSHARE_UNIFIED_ENABLED": "true"}):
            with patch(
                "tradingagents.dataflows.providers.china.akshare.ak", mock_ak
            ):
                from tradingagents.dataflows.providers.china.akshare import (
                    AKShareProvider,
                )

                provider = AKShareProvider()
                yield provider, mock_ak

    @pytest.mark.asyncio
    async def test_get_stock_news_success(self, provider_with_mock):
        """测试获取新闻成功"""
        provider, mock_ak = provider_with_mock

        # 模拟返回的新闻数据
        mock_news_df = pd.DataFrame(
            {
                "新闻标题": ["平安银行发布年报", "平安银行股价上涨"],
                "新闻内容": ["内容1", "内容2"],
                "发布时间": ["2024-01-01 10:00:00", "2024-01-01 11:00:00"],
                "新闻链接": ["http://example.com/1", "http://example.com/2"],
                "文章来源": ["东方财富", "新浪财经"],
            }
        )
        mock_ak.stock_news_em.return_value = mock_news_df

        result = await provider.get_stock_news("000001", limit=10)

        assert result is not None
        assert len(result) == 2
        assert result[0]["title"] == "平安银行发布年报"
        assert result[0]["source"] == "东方财富"
        assert "sentiment" in result[0]
        assert "keywords" in result[0]

    @pytest.mark.asyncio
    async def test_get_stock_news_empty(self, provider_with_mock):
        """测试获取新闻为空"""
        provider, mock_ak = provider_with_mock

        # 模拟返回空DataFrame
        mock_ak.stock_news_em.return_value = pd.DataFrame()

        result = await provider.get_stock_news("000001")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_stock_news_api_error(self, provider_with_mock):
        """测试获取新闻API错误"""
        provider, mock_ak = provider_with_mock

        # 模拟API抛出异常
        mock_ak.stock_news_em.side_effect = Exception("API Error")

        result = await provider.get_stock_news("000001")

        # 应该返回None或空列表
        assert result is None or result == []

    def test_news_sentiment_analysis(self, provider_with_mock):
        """测试新闻情感分析"""
        provider, _ = provider_with_mock

        # 测试积极情感
        positive_sentiment = provider._analyze_news_sentiment(
            "公司业绩增长", "平安银行业绩增长"
        )
        assert positive_sentiment == "positive"

        # 测试消极情感
        negative_sentiment = provider._analyze_news_sentiment(
            "公司股价下跌", "平安银行股价下跌"
        )
        assert negative_sentiment == "negative"

        # 测试中性情感
        neutral_sentiment = provider._analyze_news_sentiment(
            "公司发布报告", "平安银行发布公告"
        )
        assert neutral_sentiment == "neutral"

    def test_news_importance_assessment(self, provider_with_mock):
        """测试新闻重要性评估"""
        provider, _ = provider_with_mock

        # 测试高重要性
        high_importance = provider._assess_news_importance(
            "公司发布年报", "平安银行年报"
        )
        assert high_importance == "high"

        # 测试中重要性
        medium_importance = provider._assess_news_importance(
            "公司获得买入评级", "平安银行评级"
        )
        assert medium_importance == "medium"

        # 测试低重要性
        low_importance = provider._assess_news_importance(
            "公司日常经营", "平安银行日常"
        )
        assert low_importance == "low"
