# -*- coding: utf-8 -*-
"""
数据质量过滤器测试

测试 DataQualityFilter 的各种功能
"""

import pytest
from tradingagents.utils.data_quality_filter import DataQualityFilter


class TestDataQualityFilter:
    """测试数据质量过滤器"""

    def test_check_pe_ttm_calculation_logic_error(self):
        """测试: 检测PE_TTM计算逻辑错误"""
        # 模拟报告中用静态利润验算PE_TTM的情况
        report = """
        PE_TTM报告值（125.8x）系严重错误
        经验算：¥305.17亿 ÷ ¥6.16亿归母净利润 = 49.5倍
        """
        issues = DataQualityFilter.check_financial_data_quality(report)

        # 应该检测到 warning 级别问题
        warning_issues = [i for i in issues if i.get("severity") == "warning"]
        calc_issues = [i for i in issues if i.get("category") == "calculation_logic"]
        assert len(warning_issues) > 0, "应该检测到 warning 级别问题"
        assert len(calc_issues) > 0, "应该检测到 calculation_logic 类别问题"
        # detail 应该包含 PE_TTM 和滚动利润的说明
        detail = calc_issues[0].get("detail", "")
        assert "PE_TTM" in detail, "detail 应该包含 PE_TTM"
        assert "滚动" in detail, "detail 应该包含 滚动利润 说明"

    def test_normal_pe_ttm_no_error(self):
        """测试: 正常的PE_TTM不被标记为错误"""
        # 正常报告
        report = """
        PE_TTM: 129.43倍，符合军工股估值特征
        该值反映了市场对公司未来增长的预期
        """
        issues = DataQualityFilter.check_financial_data_quality(report)

        # 应该没有计算逻辑错误
        calc_issues = [i for i in issues if i.get("category") == "calculation_logic"]
        assert len(calc_issues) == 0

    def test_check_missing_data(self):
        """测试: 检测数据缺失"""
        report = """
        营收增长率: N/A
        部分数据未提供
        """
        issues = DataQualityFilter.check_financial_data_quality(report)

        # 应该检测到 info 级别问题
        info_issues = [i for i in issues if i.get("severity") == "info"]
        assert len(info_issues) > 0

    def test_generate_quality_summary(self):
        """测试: 生成质量摘要"""
        issues = [
            {"severity": "warning", "description": "测试警告1"},
            {"severity": "info", "description": "测试提示1"},
        ]

        summary = DataQualityFilter.generate_quality_summary(issues)

        assert "数据质量说明" in summary
        assert "警告" in summary
        assert "提示" in summary

    def test_generate_quality_summary_empty(self):
        """测试: 无问题时返回空"""
        summary = DataQualityFilter.generate_quality_summary([])
        assert summary == ""

    def test_filter_and_mark_data(self):
        """测试: 过滤并标记数据"""
        financial_data = {"pe_ttm": 129.43}
        report_text = "PE_TTM: 129.43倍"

        filtered_data, quality_summary = DataQualityFilter.filter_and_mark_data(
            financial_data, report_text
        )

        # 数据应保持不变（只标记不过滤）
        assert filtered_data == financial_data
        # 无问题时摘要应为空
        assert quality_summary == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
