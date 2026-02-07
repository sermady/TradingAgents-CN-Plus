# -*- coding: utf-8 -*-
"""
技术指标工具模块单元测试

测试覆盖: tradingagents/tools/analysis/indicators.py
目标覆盖率: 100%

测试场景:
- 正常数据处理
- 空数据/单点数据
- 边界值（极值）
- 数值精度验证
- 异常处理
- RSI三种计算方法对比
"""

import numpy as np
import pandas as pd
import pytest

from tradingagents.tools.analysis.indicators import (
    SUPPORTED,
    IndicatorSpec,
    add_all_indicators,
    atr,
    boll,
    compute_indicator,
    compute_many,
    ema,
    kdj,
    last_values,
    ma,
    macd,
    rsi,
)


class TestIndicatorSpec:
    """测试指标规格数据类"""

    def test_indicator_spec_creation(self):
        """测试IndicatorSpec创建"""
        spec = IndicatorSpec(name="ma", params={"n": 20})
        assert spec.name == "ma"
        assert spec.params == {"n": 20}

    def test_indicator_spec_no_params(self):
        """测试无参数的IndicatorSpec"""
        spec = IndicatorSpec(name="rsi")
        assert spec.name == "rsi"
        assert spec.params is None


class TestMA:
    """测试移动平均线函数"""

    def test_ma_basic_calculation(self):
        """测试基本MA计算"""
        close = pd.Series([100, 101, 102, 103, 104, 105])
        result = ma(close, 3)
        assert len(result) == 6
        # 验证第一个值（min_periods=1，所以第一行就有值）
        assert result.iloc[0] == 100
        # 验证第三行的3日均线
        assert abs(result.iloc[2] - 101) < 1e-10

    def test_ma_custom_min_periods(self):
        """测试自定义min_periods"""
        close = pd.Series([100, 101, 102, 103, 104, 105])
        result = ma(close, 3, min_periods=3)
        # 前两行应该是NaN
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        # 第三行开始有值
        assert not pd.isna(result.iloc[2])

    def test_ma_large_period(self):
        """测试大周期"""
        close = pd.Series(range(100))
        result = ma(close, 50)
        assert len(result) == 100
        # 最后一个值应该是前50个数的平均值
        expected = sum(range(50, 100)) / 50
        assert abs(result.iloc[-1] - expected) < 1e-10

    def test_ma_period_greater_than_length(self):
        """测试周期大于数据长度"""
        close = pd.Series([100, 101, 102])
        result = ma(close, 10)
        assert len(result) == 3
        # min_periods=1，所以第一行就有值
        assert not pd.isna(result.iloc[0])

    def test_ma_empty_series(self):
        """测试空Series"""
        close = pd.Series([], dtype=float)
        result = ma(close, 5)
        assert len(result) == 0

    def test_ma_constant_values(self):
        """测试恒定值"""
        close = pd.Series([100.0] * 10)
        result = ma(close, 5)
        assert abs(result.iloc[-1] - 100.0) < 1e-10


class TestEMA:
    """测试指数移动平均线函数"""

    def test_ema_basic_calculation(self):
        """测试基本EMA计算"""
        close = pd.Series([100, 101, 102, 103, 104, 105])
        result = ema(close, 3)
        assert len(result) == 6
        # EMA的第一个值等于第一个价格
        assert result.iloc[0] == 100

    def test_ema_vs_ma_comparison(self):
        """测试EMA比MA更快响应价格变化"""
        close = pd.Series([100, 110, 120, 130, 140, 150])
        ma_result = ma(close, 3)
        ema_result = ema(close, 3)
        # EMA应该比MA更快响应价格上涨
        assert ema_result.iloc[-1] > ma_result.iloc[-1]

    def test_ema_large_period(self):
        """测试大周期EMA"""
        close = pd.Series(range(100))
        result = ema(close, 50)
        assert len(result) == 100
        assert not pd.isna(result.iloc[-1])

    def test_ema_constant_values(self):
        """测试恒定值EMA"""
        close = pd.Series([100.0] * 10)
        result = ema(close, 5)
        assert abs(result.iloc[-1] - 100.0) < 1e-10


class TestMACD:
    """测试MACD指标函数"""

    def test_macd_basic_calculation(self):
        """测试基本MACD计算"""
        close = pd.Series(range(100, 130))
        result = macd(close)
        assert "dif" in result.columns
        assert "dea" in result.columns
        assert "macd_hist" in result.columns
        assert len(result) == 30

    def test_macd_custom_params(self):
        """测试自定义MACD参数"""
        close = pd.Series(range(100, 130))
        result = macd(close, fast=6, slow=12, signal=5)
        assert "dif" in result.columns
        assert "dea" in result.columns
        assert "macd_hist" in result.columns

    def test_macd_formula(self):
        """测试MACD计算公式"""
        close = pd.Series([100] * 30)
        result = macd(close)
        # 恒定价格时，DIF应该接近0
        assert abs(result["dif"].iloc[-1]) < 1e-10
        # DEA也应该接近0
        assert abs(result["dea"].iloc[-1]) < 1e-10

    def test_macd_uptrend(self):
        """测试上升趋势MACD"""
        close = pd.Series(range(100, 150))
        result = macd(close)
        # 上升趋势时DIF应该为正
        assert result["dif"].iloc[-1] > 0

    def test_macd_downtrend(self):
        """测试下降趋势MACD"""
        close = pd.Series(range(150, 100, -1))
        result = macd(close)
        # 下降趋势时DIF应该为负
        assert result["dif"].iloc[-1] < 0

    def test_macd_histogram_formula(self):
        """测试MACD柱状图公式"""
        close = pd.Series(range(100, 130))
        result = macd(close)
        # macd_hist = dif - dea
        for idx in range(len(result)):
            if not pd.isna(result["dif"].iloc[idx]) and not pd.isna(
                result["dea"].iloc[idx]
            ):
                expected = result["dif"].iloc[idx] - result["dea"].iloc[idx]
                actual = result["macd_hist"].iloc[idx]
                assert abs(expected - actual) < 1e-10


class TestRSI:
    """测试RSI指标函数"""

    def test_rsi_ema_method(self):
        """测试RSI-EMA方法"""
        close = pd.Series([100, 102, 104, 106, 108, 110, 112, 114, 116, 118,
                           120, 122, 124, 126, 128, 130, 132, 134, 136, 138])
        result = rsi(close, 14, method="ema")
        assert len(result) == 20  # 修正：数据实际是20个点
        # RSI应该在0-100之间
        valid_rsi = result.dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()

    def test_rsi_sma_method(self):
        """测试RSI-SMA方法"""
        close = pd.Series([100, 102, 104, 106, 108, 110, 112, 114, 116, 118,
                           120, 122, 124, 126, 128, 130, 132, 134, 136, 138])
        result = rsi(close, 14, method="sma")
        assert len(result) == 20  # 修正：数据实际是20个点
        valid_rsi = result.dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()

    def test_rsi_china_method(self):
        """测试RSI-中国式方法"""
        close = pd.Series([100, 102, 104, 106, 108, 110, 112, 114, 116, 118,
                           120, 122, 124, 126, 128, 130, 132, 134, 136, 138])
        result = rsi(close, 14, method="china")
        assert len(result) == 20  # 修正：数据实际是20个点
        valid_rsi = result.dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()

    def test_rsi_invalid_method(self):
        """测试无效的RSI方法"""
        close = pd.Series([100, 102, 104, 106, 108])
        with pytest.raises(ValueError, match="不支持的RSI计算方法"):
            rsi(close, 14, method="invalid")

    def test_rsi_constant_price(self):
        """测试恒定价格RSI"""
        close = pd.Series([100.0] * 30)
        result = rsi(close, 14, method="ema")
        # 无涨跌时RSI应该接近50或NaN
        last_rsi = result.iloc[-1]
        assert pd.isna(last_rsi) or abs(last_rsi - 50) < 1e-10

    def test_rsi_uptrend(self):
        """测试上升趋势RSI"""
        close = pd.Series(range(100, 150))
        result = rsi(close, 14, method="ema")
        # 强上升趋势RSI应该较高
        valid_rsi = result.dropna()
        if len(valid_rsi) > 0:
            assert valid_rsi.iloc[-1] > 70

    def test_rsi_downtrend(self):
        """测试下降趋势RSI"""
        close = pd.Series(range(150, 100, -1))
        result = rsi(close, 14, method="ema")
        # 强下降趋势RSI应该较低
        valid_rsi = result.dropna()
        if len(valid_rsi) > 0:
            assert valid_rsi.iloc[-1] < 30

    def test_rsi_custom_period(self):
        """测试自定义RSI周期"""
        close = pd.Series(range(100, 130))
        result = rsi(close, 6, method="ema")
        assert len(result) == 30


class TestBoll:
    """测试布林带函数"""

    def test_boll_basic_calculation(self):
        """测试基本布林带计算"""
        close = pd.Series(range(100, 130))
        result = boll(close)
        assert "boll_mid" in result.columns
        assert "boll_upper" in result.columns
        assert "boll_lower" in result.columns

    def test_boll_custom_params(self):
        """测试自定义布林带参数"""
        close = pd.Series(range(100, 130))
        result = boll(close, n=10, k=1.5)
        assert "boll_mid" in result.columns
        assert "boll_upper" in result.columns
        assert "boll_lower" in result.columns

    def test_boll_band_relationship(self):
        """测试布林带上下轨关系"""
        close = pd.Series(range(100, 130))
        result = boll(close)
        # 上轨应该大于等于中轨，下轨应该小于等于中轨
        for idx in range(len(result)):
            if (
                not pd.isna(result["boll_upper"].iloc[idx])
                and not pd.isna(result["boll_mid"].iloc[idx])
                and not pd.isna(result["boll_lower"].iloc[idx])
            ):
                assert result["boll_upper"].iloc[idx] >= result["boll_mid"].iloc[idx]
                assert result["boll_lower"].iloc[idx] <= result["boll_mid"].iloc[idx]

    def test_boll_constant_price(self):
        """测试恒定价格布林带"""
        close = pd.Series([100.0] * 30)
        result = boll(close)
        # 标准差为0时，上下轨应该等于中轨
        for idx in range(len(result)):
            if not pd.isna(result["boll_upper"].iloc[idx]):
                assert abs(result["boll_upper"].iloc[idx] - result["boll_mid"].iloc[idx]) < 1e-10
                assert abs(result["boll_lower"].iloc[idx] - result["boll_mid"].iloc[idx]) < 1e-10

    def test_boll_volatility_effect(self):
        """测试波动率对布林带的影响"""
        # 高波动数据
        high_vol = pd.Series([100, 110, 90, 120, 80, 130, 70, 140, 60, 150])
        # 低波动数据
        low_vol = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109])
        high_vol_result = boll(high_vol, n=5)
        low_vol_result = boll(low_vol, n=5)
        # 高波动数据的带宽应该更大
        high_vol_width = high_vol_result["boll_upper"].iloc[-1] - high_vol_result[
            "boll_lower"
        ].iloc[-1]
        low_vol_width = low_vol_result["boll_upper"].iloc[-1] - low_vol_result[
            "boll_lower"
        ].iloc[-1]
        assert high_vol_width > low_vol_width


class TestATR:
    """测试ATR指标函数"""

    def test_atr_basic_calculation(self):
        """测试基本ATR计算"""
        high = pd.Series([105, 110, 115, 120, 125, 130])
        low = pd.Series([95, 100, 105, 110, 115, 120])
        close = pd.Series([100, 108, 112, 118, 122, 128])
        result = atr(high, low, close, 3)
        assert len(result) == 6
        # ATR应该为正
        valid_atr = result.dropna()
        assert (valid_atr > 0).all()

    def test_atr_custom_period(self):
        """测试自定义ATR周期"""
        high = pd.Series([105, 110, 115, 120, 125, 130])
        low = pd.Series([95, 100, 105, 110, 115, 120])
        close = pd.Series([100, 108, 112, 118, 122, 128])
        result = atr(high, low, close, 5)
        assert len(result) == 6

    def test_atr_calculation_correctness(self):
        """测试ATR计算正确性"""
        # 创建已知结果的数据
        high = pd.Series([105, 108, 110])
        low = pd.Series([100, 103, 105])
        close = pd.Series([102, 106, 108])
        result = atr(high, low, close, 2)
        # ATR是真实波幅的移动平均
        # TR1 = max(105-100, |105-102|, |100-102|) = max(5, 3, 2) = 5
        # TR2 = max(108-103, |108-102|, |103-102|) = max(5, 6, 1) = 6
        # TR3 = max(110-105, |110-106|, |105-106|) = max(5, 4, 1) = 5
        # ATR[1] = (TR1 + TR2) / 2 = (5 + 6) / 2 = 5.5
        # ATR[2] = (TR2 + TR3) / 2 = (6 + 5) / 2 = 5.5
        assert abs(result.iloc[-1] - 5.5) < 1e-10


class TestKDJ:
    """测试KDJ指标函数"""

    def test_kdj_basic_calculation(self):
        """测试基本KDJ计算"""
        high = pd.Series(range(105, 135))
        low = pd.Series(range(95, 125))
        close = pd.Series(range(100, 130))
        result = kdj(high, low, close)
        assert "kdj_k" in result.columns
        assert "kdj_d" in result.columns
        assert "kdj_j" in result.columns

    def test_kdj_custom_params(self):
        """测试自定义KDJ参数"""
        high = pd.Series(range(105, 135))
        low = pd.Series(range(95, 125))
        close = pd.Series(range(100, 130))
        result = kdj(high, low, close, n=14, m1=3, m2=3)
        assert "kdj_k" in result.columns
        assert "kdj_d" in result.columns
        assert "kdj_j" in result.columns

    def test_kdj_range(self):
        """测试KDJ值范围"""
        high = pd.Series(range(105, 135))
        low = pd.Series(range(95, 125))
        close = pd.Series(range(100, 130))
        result = kdj(high, low, close)
        # KDJ应该在0-100之间
        valid_k = result["kdj_k"].dropna()
        valid_d = result["kdj_d"].dropna()
        if len(valid_k) > 0:
            assert (valid_k >= 0).all() and (valid_k <= 100).all()
        if len(valid_d) > 0:
            assert (valid_d >= 0).all() and (valid_d <= 100).all()

    def test_kdj_j_formula(self):
        """测试KDJ中的J值公式"""
        high = pd.Series(range(105, 135))
        low = pd.Series(range(95, 125))
        close = pd.Series(range(100, 130))
        result = kdj(high, low, close)
        # J = 3*K - 2*D
        for idx in range(len(result)):
            if (
                not pd.isna(result["kdj_k"].iloc[idx])
                and not pd.isna(result["kdj_d"].iloc[idx])
            ):
                expected_j = 3 * result["kdj_k"].iloc[idx] - 2 * result["kdj_d"].iloc[idx]
                actual_j = result["kdj_j"].iloc[idx]
                assert abs(expected_j - actual_j) < 1e-10

    def test_kdj_initialization(self):
        """测试KDJ初始值"""
        high = pd.Series([110, 115, 120, 125, 130, 135, 140, 145, 150, 155])
        low = pd.Series([100, 105, 110, 115, 120, 125, 130, 135, 140, 145])
        close = pd.Series([105, 110, 115, 120, 125, 130, 135, 140, 145, 150])
        result = kdj(high, low, close, n=5)
        # 第一条有效KDJ应该从初始值50附近开始
        valid_k = result["kdj_k"].dropna()
        if len(valid_k) > 0:
            # 验证K值在合理范围内
            assert 0 <= valid_k.iloc[0] <= 100


class TestComputeIndicator:
    """测试单个指标计算函数"""

    def test_compute_ma_indicator(self):
        """测试计算MA指标"""
        df = pd.DataFrame({"close": [100, 101, 102, 103, 104]})
        spec = IndicatorSpec(name="ma", params={"n": 3})
        result = compute_indicator(df, spec)
        assert "ma3" in result.columns

    def test_compute_ema_indicator(self):
        """测试计算EMA指标"""
        df = pd.DataFrame({"close": [100, 101, 102, 103, 104]})
        spec = IndicatorSpec(name="ema", params={"n": 3})
        result = compute_indicator(df, spec)
        assert "ema3" in result.columns

    def test_compute_macd_indicator(self):
        """测试计算MACD指标"""
        df = pd.DataFrame({"close": [100] * 30})
        spec = IndicatorSpec(name="macd")
        result = compute_indicator(df, spec)
        assert "dif" in result.columns
        assert "dea" in result.columns
        assert "macd_hist" in result.columns

    def test_compute_rsi_indicator(self):
        """测试计算RSI指标"""
        df = pd.DataFrame({"close": [100] * 30})
        spec = IndicatorSpec(name="rsi", params={"n": 14})
        result = compute_indicator(df, spec)
        assert "rsi14" in result.columns

    def test_compute_boll_indicator(self):
        """测试计算布林带指标"""
        df = pd.DataFrame({"close": [100] * 30})
        spec = IndicatorSpec(name="boll")
        result = compute_indicator(df, spec)
        assert "boll_mid" in result.columns
        assert "boll_upper" in result.columns
        assert "boll_lower" in result.columns

    def test_compute_atr_indicator(self):
        """测试计算ATR指标"""
        df = pd.DataFrame({
            "high": [105] * 30,
            "low": [95] * 30,
            "close": [100] * 30
        })
        spec = IndicatorSpec(name="atr")
        result = compute_indicator(df, spec)
        assert "atr14" in result.columns

    def test_compute_kdj_indicator(self):
        """测试计算KDJ指标"""
        df = pd.DataFrame({
            "high": [105] * 30,
            "low": [95] * 30,
            "close": [100] * 30
        })
        spec = IndicatorSpec(name="kdj")
        result = compute_indicator(df, spec)
        assert "kdj_k" in result.columns
        assert "kdj_d" in result.columns
        assert "kdj_j" in result.columns

    def test_compute_indicator_missing_column(self):
        """测试缺少必要列"""
        df = pd.DataFrame({"open": [100, 101, 102]})
        spec = IndicatorSpec(name="ma")
        with pytest.raises(ValueError, match="DataFrame缺少必要列"):
            compute_indicator(df, spec)

    def test_compute_indicator_unsupported(self):
        """测试不支持的指标"""
        df = pd.DataFrame({"close": [100, 101, 102]})
        spec = IndicatorSpec(name="unsupported")
        with pytest.raises(ValueError, match="不支持的指标"):
            compute_indicator(df, spec)


class TestComputeMany:
    """测试批量计算指标函数"""

    def test_compute_many_empty_list(self):
        """测试空指标列表"""
        df = pd.DataFrame({"close": [100, 101, 102]})
        result = compute_many(df, [])
        pd.testing.assert_frame_equal(result, df)

    def test_compute_many_single_indicator(self):
        """测试单个指标"""
        df = pd.DataFrame({"close": [100, 101, 102, 103, 104]})
        specs = [IndicatorSpec(name="ma", params={"n": 3})]
        result = compute_many(df, specs)
        assert "ma3" in result.columns

    def test_compute_many_multiple_indicators(self):
        """测试多个指标"""
        df = pd.DataFrame({"close": [100] * 30})
        specs = [
            IndicatorSpec(name="ma", params={"n": 5}),
            IndicatorSpec(name="rsi", params={"n": 14}),
        ]
        result = compute_many(df, specs)
        assert "ma5" in result.columns
        assert "rsi14" in result.columns

    def test_compute_many_deduplication(self):
        """测试指标去重"""
        df = pd.DataFrame({"close": [100] * 30})
        specs = [
            IndicatorSpec(name="ma", params={"n": 5}),
            IndicatorSpec(name="ma", params={"n": 5}),  # 重复
        ]
        result = compute_many(df, specs)
        # 应该只有一个ma5列
        assert result.columns.tolist().count("ma5") == 1


class TestLastValues:
    """测试获取最后值函数"""

    def test_last_values_normal(self):
        """测试正常数据"""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]})
        result = last_values(df, ["a", "b", "c"])
        assert result == {"a": 3, "b": 6, "c": 9}

    def test_last_values_empty_dataframe(self):
        """测试空DataFrame"""
        df = pd.DataFrame()
        result = last_values(df, ["a", "b"])
        assert result == {"a": None, "b": None}

    def test_last_values_missing_column(self):
        """测试缺少列"""
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = last_values(df, ["a", "b", "c"])
        assert result == {"a": 3, "b": None, "c": None}

    def test_last_values_nan_value(self):
        """测试NaN值"""
        df = pd.DataFrame({"a": [1, 2, np.nan], "b": [4, 5, 6]})
        result = last_values(df, ["a", "b"])
        assert result["a"] is None
        assert result["b"] == 6


class TestAddAllIndicators:
    """测试添加所有指标函数"""

    def test_add_all_indicators_international_style(self):
        """测试国际风格指标"""
        df = pd.DataFrame({"close": [100] * 100})
        result = add_all_indicators(df)
        # 验证MA指标
        assert "ma5" in result.columns
        assert "ma10" in result.columns
        assert "ma20" in result.columns
        assert "ma60" in result.columns
        # 验证RSI指标（国际标准只有rsi）
        assert "rsi" in result.columns
        # 验证MACD指标
        assert "macd_dif" in result.columns
        assert "macd_dea" in result.columns
        assert "macd" in result.columns
        # 验证布林带
        assert "boll_mid" in result.columns
        assert "boll_upper" in result.columns
        assert "boll_lower" in result.columns

    def test_add_all_indicators_china_style(self):
        """测试中国风格指标"""
        df = pd.DataFrame({"close": [100] * 100})
        result = add_all_indicators(df, rsi_style="china")
        # 验证中国风格RSI
        assert "rsi6" in result.columns
        assert "rsi12" in result.columns
        assert "rsi24" in result.columns
        assert "rsi14" in result.columns
        # rsi列应该指向rsi12
        assert result["rsi"].equals(result["rsi12"])

    def test_add_all_indicators_missing_close_column(self):
        """测试缺少收盘价列"""
        df = pd.DataFrame({"open": [100, 101, 102]})
        with pytest.raises(ValueError, match="DataFrame缺少收盘价列"):
            add_all_indicators(df)

    def test_add_all_indicators_custom_close_column(self):
        """测试自定义收盘价列名"""
        df = pd.DataFrame({"price": [100] * 100})
        result = add_all_indicators(df, close_col="price")
        assert "ma5" in result.columns

    def test_add_all_indicators_in_place_modification(self):
        """测试原地修改"""
        df = pd.DataFrame({"close": [100] * 100})
        original_id = id(df)
        result = add_all_indicators(df)
        # 应该返回同一个DataFrame对象
        assert id(result) == original_id

    def test_add_all_indicators_rsi_values_range(self):
        """测试RSI值范围"""
        df = pd.DataFrame({"close": [100] * 100})
        result = add_all_indicators(df)
        valid_rsi = result["rsi"].dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()


class TestSupportedIndicators:
    """测试支持的指标列表"""

    def test_supported_indicators_set(self):
        """测试SUPPORTED常量"""
        assert isinstance(SUPPORTED, set)
        assert "ma" in SUPPORTED
        assert "ema" in SUPPORTED
        assert "macd" in SUPPORTED
        assert "rsi" in SUPPORTED
        assert "boll" in SUPPORTED
        assert "atr" in SUPPORTED
        assert "kdj" in SUPPORTED
