# -*- coding: utf-8 -*-
"""
Market Analyst 单元测试

测试市场分析师的核心功能：
- 技术指标计算
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch

from tradingagents.technical.indicators import TechnicalIndicators


@pytest.mark.unit
def test_technical_indicators_init():
    """测试技术指标计算器初始化"""
    indicator = TechnicalIndicators()
    assert indicator is not None


@pytest.mark.unit
def test_rsi_calculation():
    """测试RSI计算"""
    indicator = TechnicalIndicators()

    prices = [10.0 + i * 0.1 for i in range(50)]
    df = pd.DataFrame({"close": prices})

    result = indicator.calculate_rsi(df, period=14)

    assert result is not None
    assert "rsi14" in result.columns
    rsi_value = result["rsi14"].iloc[-1]
    if not pd.isna(rsi_value):
        assert 0 <= rsi_value <= 100


@pytest.mark.unit
def test_macd_calculation():
    """测试MACD计算"""
    indicator = TechnicalIndicators()

    prices = [10.0 + i * 0.1 for i in range(50)]
    df = pd.DataFrame({"close": prices})

    result = indicator.calculate_macd(df)

    assert result is not None
    assert "macd_dif" in result.columns
    assert "macd_dea" in result.columns
    assert "macd" in result.columns


@pytest.mark.unit
def test_insufficient_data_ma():
    """测试数据不足情况"""
    indicator = TechnicalIndicators()

    prices = [10.0, 10.1, 10.2]
    df = pd.DataFrame({"close": prices})

    result = indicator.calculate_ma(df, periods=[5])

    assert result is not None
    assert "ma5" in result.columns


@pytest.mark.unit
def test_empty_data():
    """测试空数据情况"""
    indicator = TechnicalIndicators()

    df = pd.DataFrame({"close": []})

    result = indicator.calculate_ma(df, periods=[5])

    assert result is not None
