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


class TestFinancialMetricsExtraction:
    """测试财务指标提取（修复后的功能）"""

    def test_parse_financial_data_revenue_and_profit(self):
        """测试是否正确提取营收和净利润绝对值"""
        import logging

        logging.disable(logging.CRITICAL)

        from tradingagents.dataflows.optimized_china_data import (
            OptimizedChinaDataProvider,
        )

        provider = OptimizedChinaDataProvider()

        # 模拟 Tushare 返回的财务数据（扁平化结构）
        financial_data = {
            "revenue": 8073000000,  # 营业收入 80.73亿元（万元单位）
            "oper_rev": 8073000000,
            "n_income": 783000000,  # 净利润 7.83亿元
            "net_income": 783000000,
            "n_income_attr_p": 780000000,  # 归母净利润 7.8亿元
            "oper_profit": 850000000,  # 营业利润 8.5亿元
            "total_profit": 880000000,
            "total_assets": 15000000000,  # 总资产
            "total_liab": 5000000000,  # 总负债
            "total_hldr_eqy_exc_min_int": 10000000000,  # 股东权益
            "n_cashflow_act": 1200000000,  # 经营性现金流 12亿元
            "n_cashflow_inv_act": -500000000,  # 投资性现金流 -5亿元
            "n_cashflow_fin_act": -200000000,  # 筹资性现金流 -2亿元
            "roe": 7.5,
            "roa": 5.8,
        }

        stock_info = {
            "code": "605589",
            "name": "圣泉集团",
            "pe": 32.6,
            "pb": 2.48,
            "total_mv": 255.10,  # 亿元
        }

        price_value = 30.14

        metrics = provider._parse_financial_data(
            financial_data, stock_info, price_value
        )

        assert metrics is not None, "财务指标解析失败"

        # 验证营收指标
        assert "total_revenue" in metrics, "缺失 total_revenue 指标"
        assert "total_revenue_fmt" in metrics, "缺失 total_revenue_fmt 指标"
        assert metrics["total_revenue"] == 8073000000, "营业收入数值错误"
        assert "80.73" in metrics["total_revenue_fmt"], "营业收入格式化错误"

        # 验证净利润指标
        assert "net_income" in metrics, "缺失 net_income 指标"
        assert "net_income_fmt" in metrics, "缺失 net_income_fmt 指标"
        assert metrics["net_income"] == 783000000, "净利润数值错误"
        assert "7.83" in metrics["net_income_fmt"], "净利润格式化错误"

        # 验证归母净利润
        assert "net_profit_attr" in metrics, "缺失 net_profit_attr 指标"
        assert metrics["net_profit_attr"] == 780000000, "归母净利润数值错误"

        # 验证营业利润
        assert "operate_profit" in metrics, "缺失 operate_profit 指标"
        assert metrics["operate_profit"] == 850000000, "营业利润数值错误"

    def test_parse_financial_data_cashflow(self):
        """测试是否正确提取现金流指标"""
        import logging

        logging.disable(logging.CRITICAL)

        from tradingagents.dataflows.optimized_china_data import (
            OptimizedChinaDataProvider,
        )

        provider = OptimizedChinaDataProvider()

        financial_data = {
            "revenue": 5000000000,
            "n_income": 500000000,
            "total_assets": 10000000000,
            "total_liab": 4000000000,
            "total_hldr_eqy_exc_min_int": 6000000000,
            "n_cashflow_act": 800000000,  # 经营性现金流 8亿元
            "n_cashflow_inv_act": -300000000,  # 投资性现金流 -3亿元
            "n_cashflow_fin_act": -100000000,  # 筹资性现金流 -1亿元
        }

        stock_info = {"code": "000001", "pe": 10.0, "pb": 1.0, "total_mv": 100.0}
        price_value = 10.0

        metrics = provider._parse_financial_data(
            financial_data, stock_info, price_value
        )

        assert metrics is not None, "财务指标解析失败"

        # 验证经营性现金流
        assert "n_cashflow_act" in metrics, "缺失 n_cashflow_act 指标"
        assert "n_cashflow_act_fmt" in metrics, "缺失 n_cashflow_act_fmt 指标"
        assert metrics["n_cashflow_act"] == 800000000, "经营性现金流数值错误"
        assert "8.00" in metrics["n_cashflow_act_fmt"], "经营性现金流格式化错误"

        # 验证投资性现金流
        assert "n_cashflow_inv_act" in metrics, "缺失 n_cashflow_inv_act 指标"
        assert metrics["n_cashflow_inv_act"] == -300000000, "投资性现金流数值错误"

        # 验证筹资性现金流
        assert "n_cashflow_fin_act" in metrics, "缺失 n_cashflow_fin_act 指标"
        assert metrics["n_cashflow_fin_act"] == -100000000, "筹资性现金流数值错误"

    def test_yoy_calculation_with_sufficient_data(self):
        """测试有足够历史数据时的同比增速计算"""
        import logging

        logging.disable(logging.CRITICAL)

        from tradingagents.dataflows.optimized_china_data import (
            OptimizedChinaDataProvider,
        )

        provider = OptimizedChinaDataProvider()

        # 模拟包含4个季度历史数据的利润表
        financial_data = {
            "income_statement": [
                {
                    "end_date": "20241231",
                    "total_revenue": 9000000000,  # 2024Q4: 营收90亿元
                    "n_income": 900000000,  # 净利润9亿元
                },
                {
                    "end_date": "20240930",
                    "total_revenue": 6500000000,  # 2024Q3
                    "n_income": 650000000,
                },
                {
                    "end_date": "20240630",
                    "total_revenue": 4200000000,  # 2024Q2
                    "n_income": 420000000,
                },
                {
                    "end_date": "20231231",
                    "total_revenue": 8000000000,  # 2023Q4: 营收80亿元（去年同期）
                    "n_income": 800000000,  # 净利润8亿元
                },
            ],
            "balance_sheet": [
                {
                    "total_assets": 10000000000,
                    "total_liab": 4000000000,
                    "total_hldr_eqy_exc_min_int": 6000000000,
                }
            ],
            "cash_flow": [],
        }

        stock_info = {"code": "000001", "pe": 10.0, "pb": 1.0, "total_mv": 100.0}
        price_value = 10.0

        metrics = provider._parse_financial_data(
            financial_data, stock_info, price_value
        )

        assert metrics is not None, "财务指标解析失败"

        # 验证同比增速计算
        # 营收同比增速 = (90 - 80) / 80 * 100 = 12.5%
        assert "revenue_yoy" in metrics, "缺失 revenue_yoy 指标"
        assert "revenue_yoy_fmt" in metrics, "缺失 revenue_yoy_fmt 指标"
        assert metrics["revenue_yoy"] is not None, "营收同比增速为None"
        assert abs(metrics["revenue_yoy"] - 12.5) < 0.1, (
            f"营收同比增速计算错误: {metrics['revenue_yoy']}"
        )

        # 净利润同比增速 = (9 - 8) / 8 * 100 = 12.5%
        assert "net_income_yoy" in metrics, "缺失 net_income_yoy 指标"
        assert metrics["net_income_yoy"] is not None, "净利润同比增速为None"
        assert abs(metrics["net_income_yoy"] - 12.5) < 0.1, (
            f"净利润同比增速计算错误: {metrics['net_income_yoy']}"
        )

    def test_yoy_calculation_with_insufficient_data(self):
        """测试历史数据不足时同比增速应显示为N/A"""
        import logging

        logging.disable(logging.CRITICAL)

        from tradingagents.dataflows.optimized_china_data import (
            OptimizedChinaDataProvider,
        )

        provider = OptimizedChinaDataProvider()

        # 只有1个季度的数据，无法计算同比增速
        financial_data = {
            "revenue": 5000000000,
            "n_income": 500000000,
            "total_assets": 10000000000,
            "total_liab": 4000000000,
            "total_hldr_eqy_exc_min_int": 6000000000,
            "income_statement": [
                {
                    "end_date": "20241231",
                    "total_revenue": 5000000000,
                    "n_income": 500000000,
                }
            ],
        }

        stock_info = {"code": "000001", "pe": 10.0, "pb": 1.0, "total_mv": 100.0}
        price_value = 10.0

        metrics = provider._parse_financial_data(
            financial_data, stock_info, price_value
        )

        assert metrics is not None, "财务指标解析失败"

        # 历史数据不足，同比增速应该为 None 或 N/A
        assert "revenue_yoy_fmt" in metrics, "缺失 revenue_yoy_fmt 指标"
        assert metrics.get("revenue_yoy_fmt") == "N/A", (
            f"历史数据不足时营收同比增速应为N/A，实际为: {metrics.get('revenue_yoy_fmt')}"
        )

    def test_report_template_basic_mode(self):
        """测试基础模式报告模板包含新指标"""
        import logging

        logging.disable(logging.CRITICAL)

        from tradingagents.dataflows.optimized_china_data import (
            OptimizedChinaDataProvider,
        )

        provider = OptimizedChinaDataProvider()

        # 模拟财务指标数据
        financial_estimates = {
            "total_mv": "255.10亿元",
            "pe": "32.6倍",
            "pb": "2.48倍",
            "roe": "7.5%",
            "debt_ratio": "34.4%",
            "total_revenue_fmt": "80.73亿元",
            "net_income_fmt": "7.83亿元",
            "net_profit_attr_fmt": "7.80亿元",
            "n_cashflow_act_fmt": "12.00亿元",
            "revenue_yoy_fmt": "+12.5%",
            "net_income_yoy_fmt": "+15.2%",
            "fundamental_score": 7,
            "risk_level": "中",
        }

        industry_info = {
            "industry": "化工",
            "market": "沪市主板",
            "analysis": "化工行业分析",
        }

        symbol = "605589"
        company_name = "圣泉集团"
        current_price = "¥30.14"
        change_pct = "+1.2%"
        volume = "1,234,567"
        data_source_note = "\n✅ 数据说明: 财务指标基于Tushare真实财务数据计算"

        # 使用基础模式生成报告
        stock_data = f"""## A股当前价格信息
**股票代码**: {symbol}
**股票名称**: {company_name}
**当前价格**: {current_price}
**涨跌幅**: {change_pct}
**成交量**: {volume}
"""

        report = provider._generate_fundamentals_report(
            symbol=symbol,
            stock_data=stock_data,
            analysis_modules="basic",
        )

        # 验证报告包含新指标
        assert "营业收入" in report, "基础模式报告应包含营业收入"
        assert "净利润" in report, "基础模式报告应包含净利润"
        assert "归母净利润" in report, "基础模式报告应包含归母净利润"
        assert "经营性现金流" in report, "基础模式报告应包含经营性现金流"
        assert "营收同比增速" in report, "基础模式报告应包含营收同比增速"
        assert "净利润同比增速" in report, "基础模式报告应包含净利润同比增速"

        # 验证具体数值
        assert "80.73" in report, "报告应显示营收80.73亿元"
        assert "7.83" in report, "报告应显示净利润7.83亿元"

    def test_report_template_standard_mode(self):
        """测试标准模式报告模板包含核心财务指标部分"""
        import logging

        logging.disable(logging.CRITICAL)

        from tradingagents.dataflows.optimized_china_data import (
            OptimizedChinaDataProvider,
        )

        provider = OptimizedChinaDataProvider()

        # 生成标准模式报告
        stock_data = """## A股当前价格信息
**股票代码**: 605589
**股票名称**: 圣泉集团
**当前价格**: ¥30.14
**涨跌幅**: +1.2%
"""

        report = provider._generate_fundamentals_report(
            symbol="605589",
            stock_data=stock_data,
            analysis_modules="standard",
        )

        # 验证报告包含核心财务指标部分
        assert "### 核心财务指标（绝对值）" in report, (
            "标准模式报告应包含核心财务指标部分"
        )
        assert "### 成长性指标（同比增速）" in report, (
            "标准模式报告应包含成长性指标部分"
        )

        # 验证具体指标存在
        assert "营业收入:" in report, "标准模式报告应包含营业收入"
        assert "经营性现金流净额:" in report, "标准模式报告应包含经营性现金流净额"
        assert "营收同比增速:" in report, "标准模式报告应包含营收同比增速"


class TestFundamentalsReportIntegration:
    """基本面报告集成测试"""

    @pytest.mark.integration
    def test_generate_report_with_real_data_structure(self):
        """测试使用真实数据结构生成报告（需要Tushare连接）"""
        import logging

        logging.disable(logging.CRITICAL)

        from tradingagents.dataflows.optimized_china_data import (
            OptimizedChinaDataProvider,
        )

        provider = OptimizedChinaDataProvider()

        # 尝试生成报告（使用模拟数据，不依赖外部API）
        stock_data = """## A股当前价格信息
**股票代码**: 000001
**股票名称**: 平安银行
**当前价格**: ¥10.50
**涨跌幅**: +0.5%
**成交量**: 50,000,000
"""

        try:
            report = provider._generate_fundamentals_report(
                symbol="000001",  # 平安银行
                stock_data=stock_data,
                analysis_modules="basic",
            )

            # 验证报告生成成功
            assert report is not None, "报告生成失败"
            assert len(report) > 0, "报告内容为空"
            assert "000001" in report, "报告应包含股票代码"

            # 验证包含关键部分
            assert "股票基本信息" in report, "报告应包含股票基本信息部分"
            assert "核心财务指标" in report, "报告应包含核心财务指标部分"

        except Exception as e:
            pytest.fail(f"报告生成失败: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
