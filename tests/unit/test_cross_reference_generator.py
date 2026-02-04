# -*- coding: utf-8 -*-
"""
报告交叉引用生成器测试

测试 CrossReferenceGenerator 的各种功能
"""

import pytest
from tradingagents.utils.cross_reference_generator import CrossReferenceGenerator


def test_generate_perspective_summary():
    """测试: 生成观点摘要"""
    reports = {
        "market_report": "技术分析显示上涨趋势，建议: 买入",
        "fundamentals_report": "基本面良好，建议: 买入",
        "news_report": "无重大新闻，建议: 观望"
    }

    summary = CrossReferenceGenerator.generate_perspective_summary(reports)

    assert "各分析师观点对比" in summary
    assert "技术分析师" in summary
    assert "基本面分析师" in summary
    assert "新闻分析师" in summary
    assert "共识与分歧" in summary


def test_agreement_detection_all_buy():
    """测试: 检测共识（全部看多）"""
    recs = ["买入", "买入", "买入"]
    analysis = CrossReferenceGenerator._analyze_agreement(recs)

    assert "共识" in analysis
    assert "看多" in analysis


def test_agreement_detection_all_sell():
    """测试: 检测共识（全部看空）"""
    recs = ["卖出", "卖出", "强烈卖出"]
    analysis = CrossReferenceGenerator._analyze_agreement(recs)

    assert "共识" in analysis
    assert "看空" in analysis


def test_agreement_detection_mixed():
    """测试: 检测分歧"""
    recs = ["买入", "卖出", "持有"]
    analysis = CrossReferenceGenerator._analyze_agreement(recs)

    assert "分歧" in analysis


def test_generate_consistency_report_with_issues():
    """测试: 生成一致性报告（有问题时）"""
    issues = [
        {"severity": "critical", "description": "投资建议严重不一致"},
        {"severity": "warning", "description": "价格数据不一致"},
    ]

    report = CrossReferenceGenerator.generate_consistency_report(issues)

    assert "报告一致性检查" in report
    assert "严重问题" in report
    assert "警告" in report


def test_generate_consistency_report_no_issues():
    """测试: 生成一致性报告（无问题时）"""
    report = CrossReferenceGenerator.generate_consistency_report([])

    assert report == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
