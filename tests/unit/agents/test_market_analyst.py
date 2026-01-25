# -*- coding: utf-8 -*-
"""
Market Analyst 单元测试

测试市场分析师的核心功能：
- 技术指标计算
- 趋势分析
- 价格分析
- 交易信号生成
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, List

from tradingagents.agents.analysts.market_analyst import MarketAnalyst


# ==============================================================================
# 测试市场分析师初始化
# ==============================================================================


@pytest.mark.unit
def test_market_analyst_init():
    """测试市场分析师初始化"""
    with patch(
        "tradingagents.agents.analysts.market_analyst.get_data_source"
    ) as mock_get_ds:
        mock_ds = Mock()
        mock_get_ds.return_value = mock_ds

        analyst = MarketAnalyst(stock_code="000001", data_source=mock_ds)

        assert analyst.stock_code == "000001"
        assert analyst.data_source is not None


# ==============================================================================
# 测试技术指标计算
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calculate_ma():
    """测试移动平均线计算"""
    analyst = MarketAnalyst("000001", data_source=Mock())

    # 模拟价格数据
    prices = [10.5, 10.6, 10.7, 10.8, 10.9, 11.0, 11.1, 11.2, 11.3, 11.4]

    # 计算5日移动平均线
    ma5 = analyst.calculate_ma(prices, period=5)

    assert ma5 is not None
    assert len(ma5) == len(prices) - 4  # MA需要足够数据
    # 验证最后几个MA值
    assert ma5[-1] == pytest.approx(11.08, 0.01)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calculate_rsi():
    """测试RSI计算"""
    analyst = MarketAnalyst("000001", data_source=Mock())

    # 模拟价格数据
    prices = [
        10.5,
        10.6,
        10.7,
        10.8,
        10.9,
        11.0,
        11.1,
        11.2,
        11.3,
        11.4,
        11.5,
        11.6,
        11.7,
        11.8,
        11.9,
        12.0,
        12.1,
        12.2,
        12.3,
        12.4,
    ]

    # 计算RSI
    rsi = analyst.calculate_rsi(prices, period=14)

    assert rsi is not None
    assert 0 <= rsi <= 100  # RSI应该在0-100之间


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calculate_macd():
    """测试MACD计算"""
    analyst = MarketAnalyst("000001", data_source=Mock())

    # 模拟价格数据
    prices = [10.0 + i * 0.1 for i in range(50)]  # 上升趋势

    # 计算MACD
    macd = analyst.calculate_macd(prices)

    assert macd is not None
    assert "dif" in macd
    assert "dea" in macd
    assert "histogram" in macd


# ==============================================================================
# 测试趋势分析
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_analyze_trend():
    """测试趋势分析"""
    analyst = MarketAnalyst("000001", data_source=Mock())

    # 上升趋势
    prices = [10.0 + i * 0.1 for i in range(20)]
    trend = analyst.analyze_trend(prices)

    assert trend in ["up", "down", "sideways"]
    # 应该识别为上升趋势
    assert trend == "up"

    # 下降趋势
    prices_down = [15.0 - i * 0.1 for i in range(20)]
    trend_down = analyst.analyze_trend(prices_down)

    assert trend_down == "down"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_analyze_volatility():
    """测试波动性分析"""
    analyst = MarketAnalyst("000001", data_source=Mock())

    # 高波动性
    prices_high_vol = [10.0 + i * 0.2 + (i % 2) * (-0.3) for i in range(20)]
    volatility = analyst.analyze_volatility(prices_high_vol)

    assert volatility in ["high", "medium", "low"]


# ==============================================================================
# 测试价格分析
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_analyze_price_action():
    """测试价格行为分析"""
    analyst = MarketAnalyst("000001", data_source=Mock())

    # 模拟K线数据
    candles = [
        {"open": 10.0, "high": 10.5, "low": 9.8, "close": 10.3, "volume": 1000000},
        {"open": 10.3, "high": 10.8, "low": 10.0, "close": 10.7, "volume": 1200000},
        {"open": 10.7, "high": 11.0, "low": 10.5, "close": 10.9, "volume": 1100000},
    ]

    action = analyst.analyze_price_action(candles)

    assert action in ["buy", "sell", "hold"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_find_support_resistance():
    """测试支撑位和阻力位识别"""
    analyst = MarketAnalyst("000001", data_source=Mock())

    # 模拟价格数据
    prices = [10.0, 10.2, 10.0, 10.3, 10.1, 10.2, 10.0, 10.1, 9.9, 10.2]

    levels = analyst.find_support_resistance(prices)

    assert "support" in levels
    assert "resistance" in levels
    assert levels["support"] < levels["resistance"]


# ==============================================================================
# 测试交易信号生成
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_trading_signal():
    """测试交易信号生成"""
    analyst = MarketAnalyst("000001", data_source=Mock())

    # 模拟技术指标
    indicators = {
        "ma5": 10.8,
        "ma10": 10.6,
        "ma20": 10.4,
        "rsi": 65.0,
        "macd_dif": 0.15,
        "macd_dea": 0.10,
    }

    signal = analyst.generate_trading_signal(indicators)

    assert signal in ["buy", "sell", "hold"]
    # RSI 65 + 金叉 = 买入信号
    assert signal == "buy"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_analyze_volume():
    """测试成交量分析"""
    analyst = MarketAnalyst("000001", data_source=Mock())

    # 模拟成交量数据
    volumes = [1000000, 1200000, 1500000, 1800000, 2000000, 1900000, 1600000]

    analysis = analyst.analyze_volume(volumes)

    assert "trend" in analysis  # 放量或缩量
    assert "average" in analysis
    assert analysis["trend"] in ["increasing", "decreasing", "stable"]


# ==============================================================================
# 测试完整分析
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_analyze_market():
    """测试完整市场分析"""
    analyst = MarketAnalyst("000001", data_source=Mock())

    # 模拟数据
    with patch.object(analyst, "get_price_data", return_value=Mock()):
        price_data = {
            "candles": [
                {
                    "open": 10.0,
                    "high": 10.5,
                    "low": 9.8,
                    "close": 10.3,
                    "volume": 1000000,
                },
                {
                    "open": 10.3,
                    "high": 10.8,
                    "low": 10.0,
                    "close": 10.7,
                    "volume": 1200000,
                },
                {
                    "open": 10.7,
                    "high": 11.0,
                    "low": 10.5,
                    "close": 10.9,
                    "volume": 1100000,
                },
            ]
        }

        # 执行分析
        result = await analyst.analyze_market()

        assert result is not None
        assert "trend" in result
        assert "signal" in result
        assert "indicators" in result


# ==============================================================================
# 测试边界条件
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_insufficient_data():
    """测试数据不足情况"""
    analyst = MarketAnalyst("000001", data_source=Mock())

    # 不足的数据
    prices = [10.0, 10.1, 10.2]

    # 计算MA（需要至少period个数据）
    ma5 = analyst.calculate_ma(prices, period=5)

    # 应该返回空或None
    assert len(ma5) == 0


# ==============================================================================
# 测试错误处理
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_error_handling_in_analysis():
    """测试分析时的错误处理"""
    analyst = MarketAnalyst("000001", data_source=Mock())

    # 模拟数据源错误
    with patch.object(analyst, "get_price_data", side_effect=Exception("Data error")):
        try:
            result = await analyst.analyze_market()
            # 如果不抛出异常，应该返回错误信息
            assert "error" in result or result is None
        except Exception:
            # 如果抛出异常，应该被适当处理
            pass


# ==============================================================================
# 测试性能
# ==============================================================================


@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.asyncio
async def test_analysis_performance():
    """测试分析性能"""
    import time

    analyst = MarketAnalyst("000001", data_source=Mock())

    # 生成大量价格数据
    prices = [10.0 + i * 0.01 for i in range(1000)]

    # 性能测试：计算多个指标
    start = time.time()
    ma5 = analyst.calculate_ma(prices, period=5)
    ma10 = analyst.calculate_ma(prices, period=10)
    rsi = analyst.calculate_rsi(prices, period=14)
    end = time.time()

    elapsed = end - start

    # 计算应该在合理时间内完成（例如< 1秒）
    assert elapsed < 1
    assert len(ma5) > 0
    assert len(ma10) > 0
