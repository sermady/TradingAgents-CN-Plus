# -*- coding: utf-8 -*-
"""
Data Consistency Checker Service Tests
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch


class TestDataConsistencyChecker:
    """DataConsistencyChecker 测试类"""

    def test_check_daily_basic_consistency_empty_data(self):
        """测试空数据的一致性检查"""
        with patch("app.services.data_consistency_checker.logger"):
            from app.services.data_consistency_checker import DataConsistencyChecker

            checker = DataConsistencyChecker()

            empty_df = pd.DataFrame()

            result = checker.check_daily_basic_consistency(
                primary_data=empty_df,
                secondary_data=pd.DataFrame({"code": ["000001"]}),
                primary_source="Tushare",
                secondary_source="Baostock",
            )

            assert result.is_consistent is False
            assert result.confidence_score == 0.0
            assert result.recommended_action == "use_primary_only"

    def test_check_daily_basic_consistency_no_common_stocks(self):
        """测试无共同股票的一致性检查"""
        with patch("app.services.data_consistency_checker.logger"):
            from app.services.data_consistency_checker import DataConsistencyChecker

            checker = DataConsistencyChecker()

            primary_df = pd.DataFrame({"ts_code": ["000001.SZ"], "pe": [15.0]})
            secondary_df = pd.DataFrame({"code": ["000002.SZ"], "pe": [16.0]})

            result = checker.check_daily_basic_consistency(
                primary_data=primary_df,
                secondary_data=secondary_df,
                primary_source="Tushare",
                secondary_source="Baostock",
            )

            assert result.is_consistent is False
            assert result.primary_source == "Tushare"
            assert result.secondary_source == "Baostock"

    def test_check_daily_basic_consistency_with_common_stocks(self):
        """测试有共同股票的一致性检查"""
        with patch("app.services.data_consistency_checker.logger"):
            from app.services.data_consistency_checker import DataConsistencyChecker

            checker = DataConsistencyChecker()

            primary_df = pd.DataFrame(
                {
                    "ts_code": ["000001.SZ", "000002.SZ"],
                    "pe": [15.0, 20.0],
                    "pb": [1.5, 2.0],
                }
            )
            secondary_df = pd.DataFrame(
                {
                    "code": ["000001.SZ", "000002.SZ"],
                    "pe": [15.5, 20.5],
                    "pb": [1.52, 2.02],
                }
            )

            result = checker.check_daily_basic_consistency(
                primary_data=primary_df,
                secondary_data=secondary_df,
                primary_source="Tushare",
                secondary_source="Baostock",
            )

            assert isinstance(result.is_consistent, bool)
            assert result.confidence_score >= 0.0
            assert result.confidence_score <= 1.0

    def test_find_common_stocks(self):
        """测试查找共同股票"""
        with patch("app.services.data_consistency_checker.logger"):
            from app.services.data_consistency_checker import DataConsistencyChecker

            checker = DataConsistencyChecker()

            primary_df = pd.DataFrame(
                {
                    "ts_code": ["000001.SZ", "000002.SZ", "000003.SZ"],
                    "pe": [15.0, 20.0, 25.0],
                }
            )
            secondary_df = pd.DataFrame(
                {
                    "code": ["000001.SZ", "000003.SZ", "000004.SZ"],
                    "pe": [15.5, 25.5, 30.0],
                }
            )

            common_stocks = checker._find_common_stocks(primary_df, secondary_df)

            assert "000001.SZ" in common_stocks
            assert "000003.SZ" in common_stocks
            assert "000002.SZ" not in common_stocks
            assert "000004.SZ" not in common_stocks

    def test_compare_metric_within_tolerance(self):
        """测试指标比较 - 在容差范围内"""
        with patch("app.services.data_consistency_checker.logger"):
            from app.services.data_consistency_checker import DataConsistencyChecker

            checker = DataConsistencyChecker()

            primary_df = pd.DataFrame({"ts_code": ["000001.SZ"], "pe": [15.0]})
            secondary_df = pd.DataFrame({"code": ["000001.SZ"], "pe": [15.5]})

            result = checker._compare_metric(
                df1=primary_df,
                df2=secondary_df,
                common_stocks=["000001.SZ"],
                metric="pe",
            )

            assert result is not None
            assert result.metric_name == "pe"
            assert result.primary_value == 15.0
            assert result.secondary_value == 15.5
            assert bool(result.is_significant) is False

    def test_compare_metric_outside_tolerance(self):
        """测试指标比较 - 超出容差范围"""
        with patch("app.services.data_consistency_checker.logger"):
            from app.services.data_consistency_checker import DataConsistencyChecker

            checker = DataConsistencyChecker()

            primary_df = pd.DataFrame({"ts_code": ["000001.SZ"], "pe": [15.0]})
            secondary_df = pd.DataFrame({"code": ["000001.SZ"], "pe": [20.0]})

            result = checker._compare_metric(
                df1=primary_df,
                df2=secondary_df,
                common_stocks=["000001.SZ"],
                metric="pe",
            )

            assert result is not None
            assert bool(result.is_significant) is True

    def test_calculate_overall_consistency(self):
        """测试整体一致性计算"""
        with patch("app.services.data_consistency_checker.logger"):
            from app.services.data_consistency_checker import (
                DataConsistencyChecker,
                FinancialMetricComparison,
            )

            checker = DataConsistencyChecker()

            comparisons = [
                FinancialMetricComparison(
                    metric_name="pe",
                    primary_value=15.0,
                    secondary_value=15.5,
                    difference_pct=0.033,
                    is_significant=False,
                    tolerance=0.05,
                ),
                FinancialMetricComparison(
                    metric_name="pb",
                    primary_value=1.5,
                    secondary_value=1.52,
                    difference_pct=0.013,
                    is_significant=False,
                    tolerance=0.05,
                ),
            ]

            result = checker._calculate_overall_consistency(
                comparisons=comparisons,
                primary_source="Tushare",
                secondary_source="Baostock",
            )

            assert result.primary_source == "Tushare"
            assert result.secondary_source == "Baostock"
            assert result.confidence_score >= 0.0

    def test_default_tolerance_thresholds(self):
        """测试默认容差阈值"""
        with patch("app.services.data_consistency_checker.logger"):
            from app.services.data_consistency_checker import DataConsistencyChecker

            checker = DataConsistencyChecker()

            assert "pe" in checker.tolerance_thresholds
            assert "pb" in checker.tolerance_thresholds
            assert "total_mv" in checker.tolerance_thresholds
            assert "price" in checker.tolerance_thresholds
            assert "volume" in checker.tolerance_thresholds
            assert "turnover_rate" in checker.tolerance_thresholds

            assert checker.tolerance_thresholds["pe"] == 0.05
            assert checker.tolerance_thresholds["price"] == 0.01

    def test_metric_weights_sum_to_one(self):
        """测试指标权重和为1"""
        with patch("app.services.data_consistency_checker.logger"):
            from app.services.data_consistency_checker import DataConsistencyChecker

            checker = DataConsistencyChecker()

            weights_sum = sum(checker.metric_weights.values())
            assert abs(weights_sum - 1.0) < 0.01


class TestDataConsistencyResult:
    """DataConsistencyResult 测试类"""

    def test_create_dataclass(self):
        """测试创建结果数据类"""
        from app.services.data_consistency_checker import DataConsistencyResult

        result = DataConsistencyResult(
            is_consistent=True,
            primary_source="Tushare",
            secondary_source="Baostock",
            differences={"pe": 0.02},
            confidence_score=0.95,
            recommended_action="use_primary",
            details={"note": "All metrics within tolerance"},
        )

        assert result.is_consistent is True
        assert result.primary_source == "Tushare"
        assert result.confidence_score == 0.95


class TestFinancialMetricComparison:
    """FinancialMetricComparison 测试类"""

    def test_create_dataclass(self):
        """测试创建财务指标比较结果"""
        from app.services.data_consistency_checker import FinancialMetricComparison

        comparison = FinancialMetricComparison(
            metric_name="pe",
            primary_value=15.0,
            secondary_value=15.5,
            difference_pct=0.0333,
            is_significant=False,
            tolerance=0.05,
        )

        assert comparison.metric_name == "pe"
        assert comparison.is_significant is False
