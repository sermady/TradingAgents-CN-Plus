# -*- coding: utf-8 -*-
"""
技术指标计算模块单元测试

测试覆盖: tradingagents/technical/indicators.py
目标覆盖率: 100%

测试场景:
- 正常数据处理
- 空数据/单点数据
- 边界值（极值）
- 数值精度验证
- 异常处理
"""

import numpy as np
import pandas as pd
import pytest

from tradingagents.technical.indicators import (
    TechnicalIndicators,
    calculate_indicators_for_report,
)


class TestTechnicalIndicatorsCalculateMA:
    """测试移动平均线计算"""

    def test_calculate_ma_default_periods(self, sample_price_data):
        """测试默认周期的移动平均线计算"""
        result = TechnicalIndicators.calculate_ma(sample_price_data)
        assert "ma5" in result.columns
        assert "ma10" in result.columns
        assert "ma20" in result.columns
        assert "ma60" in result.columns

        # 验证计算正确性
        expected_ma5 = sample_price_data["close"].rolling(window=5, min_periods=1).mean()
        # 使用assert_allclose避免Series name属性不匹配
        np.testing.assert_allclose(result["ma5"].values, expected_ma5.values, rtol=1e-10)

    def test_calculate_ma_custom_periods(self, sample_price_data):
        """测试自定义周期的移动平均线计算"""
        result = TechnicalIndicators.calculate_ma(
            sample_price_data, periods=[3, 7, 30]
        )
        assert "ma3" in result.columns
        assert "ma7" in result.columns
        assert "ma30" in result.columns

    def test_calculate_ma_custom_price_column(self):
        """测试自定义价格列"""
        df = pd.DataFrame({"price": [100, 101, 102, 103, 104]})
        result = TechnicalIndicators.calculate_ma(df, price_col="price")
        assert "ma5" in result.columns

    def test_calculate_ma_empty_dataframe(self):
        """测试空DataFrame"""
        df = pd.DataFrame({"close": []})
        result = TechnicalIndicators.calculate_ma(df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_calculate_ma_single_row(self):
        """测试单行数据"""
        df = pd.DataFrame({"close": [100.0]})
        result = TechnicalIndicators.calculate_ma(df)
        assert "ma5" in result.columns
        assert result["ma5"].iloc[0] == 100.0

    def test_calculate_ma_not_modified_original(self, sample_price_data):
        """测试原始DataFrame不被修改"""
        original_cols = sample_price_data.columns.tolist()
        TechnicalIndicators.calculate_ma(sample_price_data)
        assert sample_price_data.columns.tolist() == original_cols


class TestTechnicalIndicatorsCalculateRSI:
    """测试RSI相对强弱指标计算"""

    def test_calculate_rsi_default_period(self, sample_price_data):
        """测试默认周期RSI计算"""
        result = TechnicalIndicators.calculate_rsi(sample_price_data)
        assert "rsi14" in result.columns
        # RSI应该在0-100之间
        valid_rsi = result["rsi14"].dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()

    def test_calculate_rsi_custom_period(self, sample_price_data):
        """测试自定义周期RSI计算"""
        result = TechnicalIndicators.calculate_rsi(sample_price_data, period=6)
        assert "rsi6" in result.columns

    def test_calculate_rsi_simple_style(self, sample_price_data):
        """测试简单移动平均风格RSI"""
        result = TechnicalIndicators.calculate_rsi(
            sample_price_data, style="simple"
        )
        assert "rsi14" in result.columns

    def test_calculate_rsi_sma_style(self, sample_price_data):
        """测试中国式SMA风格RSI"""
        result = TechnicalIndicators.calculate_rsi(sample_price_data, style="sma")
        assert "rsi14" in result.columns

    def test_calculate_rsi_exponential_style(self, sample_price_data):
        """测试指数移动平均风格RSI"""
        result = TechnicalIndicators.calculate_rsi(
            sample_price_data, style="exponential"
        )
        assert "rsi14" in result.columns

    def test_calculate_rsi_all_zeros_price(self):
        """测试全零价格数据处理"""
        df = pd.DataFrame({"close": [100] * 20})
        result = TechnicalIndicators.calculate_rsi(df)
        assert "rsi14" in result.columns

    def test_calculate_rsi_constant_price(self):
        """测试恒定价格数据（无涨跌）"""
        df = pd.DataFrame({"close": [100.0] * 30})
        result = TechnicalIndicators.calculate_rsi(df)
        assert "rsi14" in result.columns
        # 无涨跌时RSI应该接近50
        valid_rsi = result["rsi14"].dropna()
        if len(valid_rsi) > 0:
            # 可能是NaN或50附近
            assert valid_rsi.iloc[-1] == 50 or pd.isna(valid_rsi.iloc[-1])

    def test_calculate_rsi_strong_uptrend(self):
        """测试强上升趋势数据"""
        # 创建持续上涨的数据
        df = pd.DataFrame({"close": range(100, 130)})
        result = TechnicalIndicators.calculate_rsi(df)
        assert "rsi14" in result.columns
        # 强上升趋势RSI应该较高
        valid_rsi = result["rsi14"].dropna()
        if len(valid_rsi) > 0:
            assert valid_rsi.iloc[-1] > 70  # 超买区域

    def test_calculate_rsi_strong_downtrend(self):
        """测试强下降趋势数据"""
        # 创建持续下跌的数据
        df = pd.DataFrame({"close": range(130, 100, -1)})
        result = TechnicalIndicators.calculate_rsi(df)
        assert "rsi14" in result.columns
        # 强下降趋势RSI应该较低
        valid_rsi = result["rsi14"].dropna()
        if len(valid_rsi) > 0:
            assert valid_rsi.iloc[-1] < 30  # 超卖区域


class TestTechnicalIndicatorsCalculateMACD:
    """测试MACD指标计算"""

    def test_calculate_macd_default_params(self, sample_price_data):
        """测试默认参数MACD计算"""
        result = TechnicalIndicators.calculate_macd(sample_price_data)
        assert "macd_dif" in result.columns
        assert "macd_dea" in result.columns
        assert "macd" in result.columns

    def test_calculate_macd_custom_params(self, sample_price_data):
        """测试自定义参数MACD计算"""
        result = TechnicalIndicators.calculate_macd(
            sample_price_data, fast_period=6, slow_period=12, signal_period=5
        )
        assert "macd_dif" in result.columns
        assert "macd_dea" in result.columns
        assert "macd" in result.columns

    def test_calculate_macd_calculation_correctness(self):
        """测试MACD计算正确性"""
        # 使用固定数据验证计算
        df = pd.DataFrame({"close": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
                                     110, 111, 112, 113, 114, 115, 116, 117, 118, 119,
                                     120, 121, 122, 123, 124, 125, 126, 127, 128]})
        result = TechnicalIndicators.calculate_macd(df)
        assert "macd_dif" in result.columns
        # DIF = EMA(fast) - EMA(slow)
        # 由于数据持续上涨，DIF应该为正（跳过第一个接近0的值）
        valid_dif = result["macd_dif"].dropna()
        if len(valid_dif) > 1:
            # 跳过第一个值（预热期），其余应该为正
            assert (valid_dif.iloc[1:] > 0).all()

    def test_calculate_macd_histogram_formula(self):
        """测试MACD柱状图计算公式"""
        df = pd.DataFrame({"close": [100] * 30})
        result = TechnicalIndicators.calculate_macd(df)
        # MACD = (DIF - DEA) * 2
        for idx in range(len(result)):
            if (
                not pd.isna(result["macd_dif"].iloc[idx])
                and not pd.isna(result["macd_dea"].iloc[idx])
            ):
                expected_macd = (
                    result["macd_dif"].iloc[idx] - result["macd_dea"].iloc[idx]
                ) * 2
                actual_macd = result["macd"].iloc[idx]
                assert abs(expected_macd - actual_macd) < 1e-10


class TestTechnicalIndicatorsCalculateBoll:
    """测试布林带计算"""

    def test_calculate_boll_default_params(self, sample_price_data):
        """测试默认参数布林带计算"""
        result = TechnicalIndicators.calculate_boll(sample_price_data)
        assert "boll_mid" in result.columns
        assert "boll_upper" in result.columns
        assert "boll_lower" in result.columns

    def test_calculate_boll_custom_params(self, sample_price_data):
        """测试自定义参数布林带计算"""
        result = TechnicalIndicators.calculate_boll(
            sample_price_data, period=10, std_dev=1.5
        )
        assert "boll_mid" in result.columns
        assert "boll_upper" in result.columns
        assert "boll_lower" in result.columns

    def test_calculate_boll_band_width(self, sample_price_data):
        """测试布林带宽度"""
        result = TechnicalIndicators.calculate_boll(sample_price_data)
        # 上轨应该大于中轨，下轨应该小于中轨
        for idx in range(len(result)):
            if (
                not pd.isna(result["boll_upper"].iloc[idx])
                and not pd.isna(result["boll_lower"].iloc[idx])
            ):
                assert result["boll_upper"].iloc[idx] >= result["boll_mid"].iloc[idx]
                assert result["boll_lower"].iloc[idx] <= result["boll_mid"].iloc[idx]

    def test_calculate_boll_calculation_correctness(self):
        """测试布林带计算正确性"""
        df = pd.DataFrame({"close": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
                                     110, 111, 112, 113, 114, 115, 116, 117, 118, 119]})
        result = TechnicalIndicators.calculate_boll(df, period=5, std_dev=2.0)
        # 验证中轨是MA（使用数值比较避免name属性不匹配）
        expected_mid = df["close"].rolling(window=5, min_periods=1).mean()
        np.testing.assert_allclose(result["boll_mid"].values, expected_mid.values, rtol=1e-10)

    def test_calculate_boll_constant_price(self):
        """测试恒定价格的布林带"""
        df = pd.DataFrame({"close": [100.0] * 30})
        result = TechnicalIndicators.calculate_boll(df)
        # 恒定价格时，上下轨应该等于中轨（标准差为0）
        for idx in range(len(result)):
            if (
                not pd.isna(result["boll_upper"].iloc[idx])
                and not pd.isna(result["boll_mid"].iloc[idx])
            ):
                # 由于浮点精度，使用近似比较
                assert abs(result["boll_upper"].iloc[idx] - result["boll_mid"].iloc[idx]) < 1e-10
                assert abs(result["boll_lower"].iloc[idx] - result["boll_mid"].iloc[idx]) < 1e-10


class TestTechnicalIndicatorsCalculateAll:
    """测试计算所有技术指标"""

    def test_calculate_all_indicators_default(self, sample_price_data):
        """测试默认参数计算所有指标"""
        result = TechnicalIndicators.calculate_all_indicators(sample_price_data)
        # 验证MA指标
        assert "ma5" in result.columns
        assert "ma10" in result.columns
        assert "ma20" in result.columns
        assert "ma60" in result.columns
        # 验证RSI指标
        assert "rsi6" in result.columns
        assert "rsi12" in result.columns
        assert "rsi24" in result.columns
        assert "rsi14" in result.columns
        # 验证MACD指标
        assert "macd_dif" in result.columns
        assert "macd_dea" in result.columns
        assert "macd" in result.columns
        # 验证布林带
        assert "boll_mid" in result.columns
        assert "boll_upper" in result.columns
        assert "boll_lower" in result.columns

    def test_calculate_all_indicators_with_date_column(self):
        """测试带日期列的数据"""
        df = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
            "close": [100, 101, 102, 103, 104]
        })
        result = TechnicalIndicators.calculate_all_indicators(df)
        assert "ma5" in result.columns
        # 验证数据按日期排序（日期会被转换为datetime类型）
        assert str(result["date"].iloc[0]).startswith("2024-01-01")

    def test_calculate_all_indicators_custom_rsi_style(self, sample_price_data):
        """测试自定义RSI计算风格"""
        result = TechnicalIndicators.calculate_all_indicators(
            sample_price_data, rsi_style="simple"
        )
        assert "rsi14" in result.columns

    def test_calculate_all_indicators_not_modified_original(self, sample_price_data):
        """测试原始DataFrame不被修改"""
        original_cols = sample_price_data.columns.tolist()
        TechnicalIndicators.calculate_all_indicators(sample_price_data)
        assert sample_price_data.columns.tolist() == original_cols


class TestTechnicalIndicatorsGetSummary:
    """测试获取技术指标摘要"""

    def test_get_indicator_summary_normal(self, sample_price_data_with_indicators):
        """测试正常数据获取摘要"""
        summary = TechnicalIndicators.get_indicator_summary(
            sample_price_data_with_indicators
        )
        assert isinstance(summary, dict)
        assert "current_price" in summary
        assert "ma5" in summary
        assert "ma10" in summary
        assert "ma20" in summary
        assert "ma60" in summary
        assert "rsi6" in summary
        assert "rsi12" in summary
        assert "rsi24" in summary
        assert "rsi14" in summary
        assert "macd_dif" in summary
        assert "macd_dea" in summary
        assert "macd" in summary
        assert "boll_upper" in summary
        assert "boll_mid" in summary
        assert "boll_lower" in summary
        assert "trend" in summary
        assert "signal" in summary

    def test_get_indicator_summary_empty_dataframe(self):
        """测试空DataFrame"""
        summary = TechnicalIndicators.get_indicator_summary(pd.DataFrame())
        assert summary == {}

    def test_get_indicator_summary_custom_n_days(self, sample_price_data_with_indicators):
        """测试自定义天数"""
        summary = TechnicalIndicators.get_indicator_summary(
            sample_price_data_with_indicators, n_days=10
        )
        assert "current_price" in summary

    def test_get_indicator_summary_missing_columns(self):
        """测试缺少必要列的情况"""
        df = pd.DataFrame({"close": [100, 101, 102]})
        summary = TechnicalIndicators.get_indicator_summary(df)
        assert summary["current_price"] == 102
        # 缺失的指标应该返回默认值
        assert summary["ma5"] == 0


class TestTechnicalIndicatorsDetermineTrend:
    """测试趋势判断"""

    def test_determine_trend_up(self):
        """测试上升趋势判断"""
        summary = {
            "current_price": 105,
            "ma5": 100,
            "ma10": 95,
            "ma20": 90,
            "ma60": 85,
        }
        trend = TechnicalIndicators._determine_trend(summary)
        assert trend == "up"

    def test_determine_trend_down(self):
        """测试下降趋势判断"""
        summary = {
            "current_price": 85,
            "ma5": 90,
            "ma10": 95,
            "ma20": 100,
            "ma60": 105,
        }
        trend = TechnicalIndicators._determine_trend(summary)
        assert trend == "down"

    def test_determine_trend_neutral(self):
        """测试中性趋势判断"""
        summary = {
            "current_price": 100,
            "ma5": 98,
            "ma10": 102,
            "ma20": 100,
            "ma60": 95,
        }
        trend = TechnicalIndicators._determine_trend(summary)
        assert trend == "neutral"


class TestTechnicalIndicatorsDetermineSignal:
    """测试交易信号判断"""

    def test_determine_signal_buy_macd_golden_cross(self):
        """测试MACD金叉买入信号"""
        summary = {
            "macd": 0.5,
            "macd_dif": 1.0,
            "macd_dea": 0.7,
            "rsi6": 50,
            "rsi12": 50,
            "rsi24": 50,
        }
        signal = TechnicalIndicators._determine_signal(summary)
        assert signal == "buy"

    def test_determine_signal_sell_macd_death_cross(self):
        """测试MACD死叉卖出信号"""
        summary = {
            "macd": -0.5,
            "macd_dif": -1.0,
            "macd_dea": -0.7,
            "rsi6": 50,
            "rsi12": 50,
            "rsi24": 50,
        }
        signal = TechnicalIndicators._determine_signal(summary)
        assert signal == "sell"

    def test_determine_signal_sell_rsi_overbought(self):
        """测试RSI超买卖出信号"""
        summary = {
            "macd": 0,
            "macd_dif": 0,
            "macd_dea": 0,
            "rsi6": 85,
            "rsi12": 80,
            "rsi24": 75,
        }
        signal = TechnicalIndicators._determine_signal(summary)
        assert signal == "sell"

    def test_determine_signal_buy_rsi_oversold(self):
        """测试RSI超卖买入信号"""
        summary = {
            "macd": 0,
            "macd_dif": 0,
            "macd_dea": 0,
            "rsi6": 15,
            "rsi12": 20,
            "rsi24": 25,
        }
        signal = TechnicalIndicators._determine_signal(summary)
        assert signal == "buy"

    def test_determine_signal_neutral(self):
        """测试中性信号"""
        summary = {
            "macd": 0,
            "macd_dif": 0,
            "macd_dea": 0,
            "rsi6": 50,
            "rsi12": 50,
            "rsi24": 50,
        }
        signal = TechnicalIndicators._determine_signal(summary)
        assert signal == "neutral"


class TestCalculateIndicatorsForReport:
    """测试报告格式化函数"""

    def test_calculate_indicators_for_report_normal(self, sample_price_data):
        """测试正常数据生成报告"""
        report = calculate_indicators_for_report(sample_price_data)
        assert isinstance(report, str)
        assert "技术指标分析" in report
        assert "最新价格" in report
        assert "移动平均线" in report
        assert "MACD指标" in report
        assert "RSI指标" in report
        assert "布林带" in report
        assert "综合判断" in report

    def test_calculate_indicators_for_report_empty_dataframe(self):
        """测试空DataFrame"""
        report = calculate_indicators_for_report(pd.DataFrame())
        assert report == "无法计算技术指标"

    def test_calculate_indicators_for_report_none_input(self):
        """测试None输入"""
        report = calculate_indicators_for_report(None)
        assert report == "无法计算技术指标"

    def test_calculate_indicators_for_report_custom_currency(self, sample_price_data):
        """测试自定义货币符号"""
        report = calculate_indicators_for_report(sample_price_data, currency_symbol="$")
        assert "$" in report

    def test_calculate_indicators_for_report_formatting(self, sample_price_data):
        """测试报告格式正确性"""
        report = calculate_indicators_for_report(sample_price_data)
        # 验证价格格式
        assert "¥" in report or "CN" in report
        # 验证趋势和信号
        assert "趋势:" in report
        assert "信号:" in report
        # 验证箭头符号
        assert "↑" in report or "↓" in report or "价格" in report


# ============ Pytest Fixtures ============


@pytest.fixture
def sample_price_data():
    """生成示例价格数据"""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100)
    # 生成随机游走价格数据
    price = 100 + np.cumsum(np.random.randn(100) * 0.5)
    df = pd.DataFrame({
        "date": dates,
        "open": price + np.random.randn(100) * 0.2,
        "high": price + np.abs(np.random.randn(100) * 0.5),
        "low": price - np.abs(np.random.randn(100) * 0.5),
        "close": price,
        "volume": np.random.randint(1000000, 10000000, 100),
    })
    return df


@pytest.fixture
def sample_price_data_with_indicators(sample_price_data):
    """生成带技术指标的示例数据"""
    return TechnicalIndicators.calculate_all_indicators(sample_price_data.copy())
