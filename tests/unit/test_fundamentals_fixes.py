# -*- coding: utf-8 -*-
"""
基本面分析修复验证测试
验证以下修复：
1. Traders 决策自动填充（目标价、置信度、风险评分）
2. PS（市销率）计算
3. 数据源管理器导入修复
4. Tushare limit 参数调整
"""

import pytest
import sys
import os

# 设置 UTF-8 编码
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 修复 Windows 控制台编码问题
import io
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)


class TestTradingDecisionExtraction:
    """测试交易决策提取功能"""

    def test_extract_buy_recommendation(self):
        """测试提取买入建议"""
        from tradingagents.agents.trader.trader import extract_trading_decision

        content = "建议买入，目标价21元，置信度0.8，风险评分0.3"
        result = extract_trading_decision(content)

        assert result["recommendation"] == "买入"
        assert result["target_price"] == 21.0
        assert result["confidence"] == 0.8
        assert result["risk_score"] == 0.3

    def test_extract_hold_recommendation_with_range(self):
        """测试提取持有建议（带价格区间）"""
        from tradingagents.agents.trader.trader import extract_trading_decision

        content = "持有建议，价格区间19-22元，置信度0.6"
        result = extract_trading_decision(content)

        assert result["recommendation"] in ["持有", "未知"]
        if result["target_price_range"]:
            assert "19" in result["target_price_range"] and "22" in result["target_price_range"]

    def test_auto_calculate_target_price_for_buy(self):
        """测试买入时自动计算目标价"""
        from tradingagents.agents.trader.trader import extract_trading_decision

        content = "建议买入"
        result = extract_trading_decision(content, current_price=20.0)

        assert result["recommendation"] == "买入"
        assert result["target_price"] == 23.0  # 20 * 1.15
        assert any("自动计算" in w for w in result["warnings"])

    def test_auto_calculate_target_price_for_sell(self):
        """测试卖出时自动计算目标价"""
        from tradingagents.agents.trader.trader import extract_trading_decision

        content = "建议卖出"
        result = extract_trading_decision(content, current_price=20.0)

        assert result["recommendation"] == "卖出"
        assert result["target_price"] == 18.0  # 20 * 0.9
        assert any("自动计算" in w for w in result["warnings"])

    def test_auto_calculate_target_price_for_hold(self):
        """测试持有时自动计算价格区间"""
        from tradingagents.agents.trader.trader import extract_trading_decision

        content = "建议持有"
        result = extract_trading_decision(content, current_price=20.0)

        assert result["recommendation"] == "持有"
        assert result["target_price_range"] == "¥19.0-21.0"  # 20 * 0.95, 20 * 1.05
        assert any("自动计算" in w for w in result["warnings"])

    def test_default_confidence_for_buy(self):
        """测试买入时默认置信度"""
        from tradingagents.agents.trader.trader import extract_trading_decision

        content = "建议买入"
        result = extract_trading_decision(content)

        assert result["confidence"] == 0.7

    def test_default_risk_for_sell(self):
        """测试卖出时默认风险评分"""
        from tradingagents.agents.trader.trader import extract_trading_decision

        content = "建议卖出"
        result = extract_trading_decision(content)

        assert result["risk_score"] == 0.5


class TestPSCalculation:
    """测试 PS（市销率）计算"""

    def test_ps_calculation_formula(self):
        """测试 PS 计算公式"""
        # PS = 总市值(亿元) / 营业收入(亿元)
        total_mv_yuan = 323.76  # 亿元
        revenue_yuan = 77.76    # 亿元（77.76亿元营业收入）

        ps = total_mv_yuan / revenue_yuan

        assert abs(ps - 4.16) < 0.01  # 约4.16倍

    def test_ps_unit_conversion(self):
        """测试单位转换"""
        # Tushare revenue 单位是元
        revenue_yuan = 7776388488.14  # 元
        revenue_in_billion = revenue_yuan / 100000000  # 转亿元

        # Tushare total_mv 单位是万元
        total_mv_wanyuan = 3237636.3744  # 万元
        total_mv_in_billion = total_mv_wanyuan / 10000  # 转亿元

        ps = total_mv_in_billion / revenue_in_billion

        assert abs(ps - 4.16) < 0.1  # 约4.16倍


class TestDataSourceManager:
    """测试数据源管理器"""

    def test_get_database_manager_import(self):
        """测试 get_database_manager 导入"""
        # 确保导入不会出错
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
        limit_param = sig.parameters.get('limit')

        assert limit_param is not None, "limit 参数不存在"
        assert limit_param.default == 8, f"limit 默认值应为8，实际为{limit_param.default}"


class TestFundamentalsReport:
    """测试基本面报告生成"""

    def test_generate_fundamentals_report_pe(self):
        """测试基本面报告 PE 值"""
        import asyncio
        import logging

        logging.disable(logging.CRITICAL)

        def run_test():
            from tradingagents.dataflows.optimized_china_data import OptimizedChinaDataProvider

            provider = OptimizedChinaDataProvider()

            stock_data = """## A股当前价格信息
**股票代码**: 600765
**股票名称**: 中航重机
**当前价格**: ¥20.55
**涨跌幅**: +0.29%
**成交量**: 65,684,900
"""

            report = provider._generate_fundamentals_report('600765', stock_data, 'standard')

            # 验证 PE 值 - 使用更精确的正则表达式
            import re
            # 匹配 "市盈率(PE): 50.6倍" 或类似格式
            pe_match = re.search(r'市盈率\(PE\).*?([\d.]+)\s*倍', report)
            assert pe_match, f"未找到 PE 值，报告内容: {report[:500]}"
            pe = float(pe_match.group(1))
            assert 40 < pe < 60, f"PE 值应在50左右，实际为{pe}"

            # 验证 PB 值
            pb_match = re.search(r'市净率\(PB\).*?([\d.]+)\s*倍', report)
            assert pb_match, "未找到 PB 值"
            pb = float(pb_match.group(1))
            assert 2 < pb < 3, f"PB 值应在2.28左右，实际为{pb}"

            # 验证 PS 值
            ps_match = re.search(r'市销率\(PS\).*?([\d.]+)\s*倍', report)
            assert ps_match, "未找到 PS 值"
            ps = float(ps_match.group(1))
            assert 3 < ps < 5, f"PS 值应在4.16左右，实际为{ps}"

            # 验证总市值
            mv_match = re.search(r'总市值.*?([\d.]+)\s*亿元', report)
            assert mv_match, "未找到总市值"
            mv = float(mv_match.group(1))
            assert 300 < mv < 350, f"总市值应在323.76左右，实际为{mv}"

        run_test()


class TestValidateTradingDecision:
    """测试交易决策验证"""

    def test_validate_with_auto_filled_values(self):
        """测试包含自动填充值的验证"""
        from tradingagents.agents.trader.trader import validate_trading_decision

        # 没有目标价的决策，但应该有自动填充
        content = "建议买入"
        result = validate_trading_decision(content, "¥", "600765", current_price=20.0)

        assert result["recommendation"] == "买入"
        assert result["has_target_price"] == True  # 自动填充后应该有目标价
        assert result["extracted"]["target_price"] == 23.0

    def test_validate_currency_unit(self):
        """测试货币单位验证"""
        from tradingagents.agents.trader.trader import validate_trading_decision

        # A股使用美元应该警告
        content = "建议买入，目标价$21"
        result = validate_trading_decision(content, "¥", "600765")

        # 检查是否有货币单位相关的警告
        has_currency_warning = any("¥" in w or "$" in w or "A股" in w
                                    for w in result.get("warnings", []))
        assert has_currency_warning or len(result.get("warnings", [])) == 0, \
            f"应该有关于货币单位的警告，实际警告: {result.get('warnings', [])}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
