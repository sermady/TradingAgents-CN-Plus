# -*- coding: utf-8 -*-
"""
报告一致性检查器测试

测试 ReportConsistencyChecker 的各种检查功能
"""

import pytest
from tradingagents.utils.report_consistency_checker import (
    ReportConsistencyChecker,
    RecommendationLevel,
    ConsistencyIssue
)


def test_no_issues_when_consistent():
    """测试: 报告一致时不应有问题"""
    checker = ReportConsistencyChecker()

    reports = {
        "market_report": "当前价¥19.37，建议: 买入",
        "fundamentals_report": "当前价格19.37元，评级: 逢低买入",
        "trader_plan": "操作建议: 买入"
    }

    issues = checker.check_all_reports(reports)
    assert len(issues) == 0


def test_critical_recommendation_conflict():
    """测试: 检测严重的投资建议冲突"""
    checker = ReportConsistencyChecker()

    # 使用正确的报告类型名称 - investment_plan, trader, decision 才会被检查
    reports = {
        "investment_plan": "建议: 买入",
        "trader_investment_plan": "评级: 卖出（Strong Sell）"
    }

    issues = checker.check_all_reports(reports)

    # 应该检测到 critical 级别问题
    critical_issues = [i for i in issues if i.severity == "critical"]
    assert len(critical_issues) > 0


def test_price_data_inconsistency():
    """测试: 检测价格数据不一致"""
    checker = ReportConsistencyChecker()

    reports = {
        "market_report": "当前价¥19.37",
        "fundamentals_report": "当前价格¥22.50",  # 16%差异，超过5%阈值
    }

    issues = checker.check_all_reports(reports)

    # 应该检测到 warning 级别问题
    warning_issues = [i for i in issues if i.severity == "warning"]
    assert len(warning_issues) > 0
    assert "价格" in warning_issues[0].description


def test_missing_volume_data():
    """测试: 检测缺失的成交量数据"""
    checker = ReportConsistencyChecker()

    reports = {
        "market_report": "未提供单日成交量，仅给出5日均量"
    }

    issues = checker.check_all_reports(reports)

    # 应该检测到 info 级别问题
    info_issues = [i for i in issues if i.severity == "info"]
    assert len(info_issues) > 0
    assert "成交量" in info_issues[0].description


def test_financial_calculation_logic_error():
    """测试: 检测财务数据计算逻辑错误（用静态利润验算PE_TTM）"""
    checker = ReportConsistencyChecker()

    # 模拟报告内容：AI用归母净利润去验算PE_TTM并声称数据错误
    reports = {
        "fundamentals_report": """
        PE_TTM报告值（125.8x）系严重错误
        经验算：¥305.17亿 ÷ ¥6.16亿归母净利润 = 49.5倍
        正确值应为49.5倍
        """
    }

    issues = checker.check_all_reports(reports)

    # 应该检测到 warning 级别问题（计算逻辑错误）
    warning_issues = [i for i in issues if i.severity == "warning"]
    assert len(warning_issues) > 0
    assert "计算" in warning_issues[0].description or "验算" in warning_issues[0].description


def test_high_pe_ttm_not_flagged_as_error():
    """测试: 高PE_TTM本身不应被标记为错误"""
    checker = ReportConsistencyChecker()

    # PE_TTM = 129.43 倍，这是合理的军工股数据
    reports = {
        "fundamentals_report": "PE_TTM: 129.43倍，符合军工股估值特征"
    }

    issues = checker.check_all_reports(reports)

    # 不应该有任何问题
    assert len(issues) == 0


def test_consistency_summary_generation():
    """测试: 生成一致性摘要"""
    checker = ReportConsistencyChecker()

    # 创建一个有问题的情况 - 使用正确的报告类型
    reports = {
        "investment_plan": "建议: 买入",
        "trader_investment_plan": "评级: 强烈卖出"
    }

    checker.check_all_reports(reports)
    summary = checker.generate_consistency_summary()

    assert "⚠️" in summary
    assert "个一致性问题" in summary


def test_recommendation_level_mapping():
    """测试: 建议等级映射"""
    checker = ReportConsistencyChecker()

    # 测试各种建议的映射
    test_cases = [
        ("强烈买入", RecommendationLevel.STRONG_BUY),
        ("买入", RecommendationLevel.BUY),
        ("持有", RecommendationLevel.HOLD),
        ("卖出", RecommendationLevel.SELL),
        ("强烈卖出", RecommendationLevel.STRONG_SELL),
        ("谨慎看多", RecommendationLevel.BUY),
        ("坚决回避", RecommendationLevel.STRONG_SELL),
    ]

    for text, expected_level in test_cases:
        actual = checker.RECOMMENDATION_MAP.get(text)
        assert actual == expected_level, f"{text} 应该映射到 {expected_level}"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
