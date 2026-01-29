# -*- coding: utf-8 -*-
"""
基本面指标计算和报告单元测试
"""

import pytest
import re


class TestPSCalculation:
    """测试 PS（市销率）计算"""

    def test_ps_calculation_formula(self):
        """测试 PS 计算公式"""
        total_mv_yuan = 323.76
        revenue_yuan = 77.76

        ps = total_mv_yuan / revenue_yuan

        assert abs(ps - 4.16) < 0.01

    def test_ps_unit_conversion(self):
        """测试单位转换"""
        revenue_yuan = 7776388488.14
        revenue_in_billion = revenue_yuan / 100000000

        total_mv_wanyuan = 3237636.3744
        total_mv_in_billion = total_mv_wanyuan / 10000

        ps = total_mv_in_billion / revenue_in_billion

        assert abs(ps - 4.16) < 0.1


class TestDataSourceManager:
    """测试数据源管理器"""

    def test_get_database_manager_import(self):
        """测试 get_database_manager 导入"""
        try:
            from tradingagents.config.database_manager import get_database_manager

            assert callable(get_database_manager)
        except ImportError as e:
            pytest.fail(f"导入失败: {e}")


class TestTushareProvider:
    """测试 Tushare 数据提供者"""

    def test_get_financial_data_limit(self):
        """测试 get_financial_data 默认 limit 参数"""
        import inspect
        from tradingagents.dataflows.providers.china.tushare import TushareProvider

        sig = inspect.signature(TushareProvider.get_financial_data)
        limit_param = sig.parameters.get("limit")

        assert limit_param is not None, "limit 参数不存在"
        assert limit_param.default == 8, (
            f"limit 默认值应为8，实际为{limit_param.default}"
        )


class TestFundamentalsReport:
    """测试基本面报告生成"""

    def test_generate_fundamentals_report_pe(self):
        """测试基本面报告 PE 值"""
        import asyncio
        import logging

        logging.disable(logging.CRITICAL)

        def run_test():
            from tradingagents.dataflows.optimized_china_data import (
                OptimizedChinaDataProvider,
            )

            provider = OptimizedChinaDataProvider()

            stock_data = """## A股当前价格信息
**股票代码**: 600765
**股票名称**: 中航重机
**当前价格**: ¥20.55
**涨跌幅**: +0.29%
**成交量**: 65,684,900
"""

            report = provider._generate_fundamentals_report(
                "600765", stock_data, "standard"
            )

            pe_match = re.search(r"市盈率\(PE\).*?([\d.]+)\s*倍", report)
            assert pe_match, f"未找到 PE 值，报告内容: {report[:500]}"
            pe = float(pe_match.group(1))
            assert 40 < pe < 60, f"PE 值应在50左右，实际为{pe}"

            pb_match = re.search(r"市净率\(PB\).*?([\d.]+)\s*倍", report)
            assert pb_match, "未找到 PB 值"
            pb = float(pb_match.group(1))
            assert 2 < pb < 3, f"PB 值应在2.28左右，实际为{pb}"

            ps_match = re.search(r"市销率\(PS\).*?([\d.]+)\s*倍", report)
            assert ps_match, "未找到 PS 值"
            ps = float(ps_match.group(1))
            assert 3 < ps < 5, f"PS 值应在4.16左右，实际为{ps}"

            mv_match = re.search(r"总市值.*?([\d.]+)\s*亿元", report)
            assert mv_match, "未找到总市值"
            mv = float(mv_match.group(1))
            assert 300 < mv < 350, f"总市值应在323.76左右，实际为{mv}"

        run_test()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
