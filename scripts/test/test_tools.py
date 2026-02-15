# -*- coding: utf-8 -*-
"""
工具模块测试脚本

验证 tradingagents/agents/utils/toolkit/tools 的所有工具函数
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)


async def test_tools():
    """测试所有工具模块"""
    print("=" * 50)
    print("[TEST] 开始测试 tools 模块...")

    basic_tests_passed = True

    # 测试数据工具导入
    try:
        from tradingagents.agents.utils.toolkit.tools.data_tools import (
            get_stock_comprehensive_financials,
            get_stock_fundamentals_unified
        )
        print("[OK] 成功导入 data_tools 模块")

        # 验证可调用
        assert callable(get_stock_comprehensive_financials)
        assert callable(get_stock_fundamentals_unified)

        print("   [OK] data_tools - 工具导入测试通过")
    except Exception as e:
        print(f"   [ERROR] data_tools - 工具导入测试失败: {e}")
        basic_tests_passed = False

    # 测试市场工具导入
    try:
        from tradingagents.agents.utils.toolkit.tools.market_tools import (
            get_stock_market_data_unified
        )
        print("[OK] 成功导入 market_tools 模块")

        # 验证可调用
        assert callable(get_stock_market_data_unified)

        print("   [OK] market_tools - 工具导入测试通过")
    except Exception as e:
        print(f"   [ERROR] market_tools - 工具导入测试失败: {e}")
        basic_tests_passed = False

    # 测试分析工具导入
    try:
        from tradingagents.agents.utils.toolkit.tools.analysis_tools import (
            get_stock_news_unified,
            get_stock_sentiment_unified
        )
        print("[OK] 成功导入 analysis_tools 模块")

        # 验证可调用
        assert callable(get_stock_news_unified)
        assert callable(get_stock_sentiment_unified)

        print("   [OK] analysis_tools - 工具导入测试通过")
    except Exception as e:
        print(f"   [ERROR] analysis_tools - 工具导入测试失败: {e}")
        basic_tests_passed = False

    # 测试统一工具导出
    try:
        from tradingagents.agents.utils.toolkit.unified_tools import (
            get_stock_comprehensive_financials,
            get_stock_fundamentals_unified,
            get_stock_market_data_unified,
            get_stock_news_unified,
            get_stock_sentiment_unified
        )

        print("[OK] 成功导入 unified_tools 模块")

        # 验证所有工具都从unified_tools正确导出
        assert callable(get_stock_comprehensive_financials)
        assert callable(get_stock_fundamentals_unified)
        assert callable(get_stock_market_data_unified)
        assert callable(get_stock_news_unified)
        assert callable(get_stock_sentiment_unified)

        print("   [OK] unified_tools - 统一导出测试通过")
    except Exception as e:
        print(f"   [ERROR] unified_tools - 统一导出测试失败: {e}")
        basic_tests_passed = False

    # 汇总结果
    print("=" * 50)
    if basic_tests_passed:
        print("[SUCCESS] 所有工具模块测试通过！")
    else:
        print("[WARNING] 部分工具模块测试失败，需要修复")

    return basic_tests_passed


if __name__ == "__main__":
    asyncio.run(test_tools())
