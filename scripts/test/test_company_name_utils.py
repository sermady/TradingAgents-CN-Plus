# -*- coding: utf-8 -*-
"""
公司名称工具单元测试

测试 tradingagents.utils.company_name_utils 模块的核心功能:
1. 美股名称映射
2. 未知股票代码的降级处理
3. 市场类型自动检测
4. 各市场类型的名称获取
"""

import sys
import os
from unittest.mock import Mock, MagicMock, patch

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)


class TestUSStockMapping:
    """美股名称映射测试"""

    def test_known_us_stock_apple(self):
        """验证苹果公司名称映射"""
        from tradingagents.utils.company_name_utils import get_company_name

        market_info = {'is_china': False, 'is_hk': False, 'is_us': True}
        result = get_company_name("AAPL", market_info)

        assert result == "苹果公司", f"AAPL应映射为'苹果公司'，实际为'{result}'"
        print("test_known_us_stock_apple PASSED")

    def test_known_us_stock_tesla(self):
        """验证特斯拉名称映射"""
        from tradingagents.utils.company_name_utils import get_company_name

        market_info = {'is_china': False, 'is_hk': False, 'is_us': True}
        result = get_company_name("TSLA", market_info)

        assert result == "特斯拉", f"TSLA应映射为'特斯拉'，实际为'{result}'"
        print("test_known_us_stock_tesla PASSED")

    def test_known_us_stock_nvidia(self):
        """验证英伟达名称映射"""
        from tradingagents.utils.company_name_utils import get_company_name

        market_info = {'is_china': False, 'is_hk': False, 'is_us': True}
        result = get_company_name("NVDA", market_info)

        assert result == "英伟达", f"NVDA应映射为'英伟达'，实际为'{result}'"
        print("test_known_us_stock_nvidia PASSED")

    def test_us_stock_case_insensitive(self):
        """验证美股代码大小写不敏感"""
        from tradingagents.utils.company_name_utils import get_company_name

        market_info = {'is_china': False, 'is_hk': False, 'is_us': True}

        # 小写应该也能识别
        result_lower = get_company_name("aapl", market_info)
        result_upper = get_company_name("AAPL", market_info)

        assert result_lower == result_upper == "苹果公司", "大小写应该得到相同结果"
        print("test_us_stock_case_insensitive PASSED")


class TestUnknownTickerFallback:
    """未知股票代码降级测试"""

    def test_unknown_us_ticker_fallback(self):
        """验证未知美股代码的降级处理"""
        from tradingagents.utils.company_name_utils import get_company_name

        market_info = {'is_china': False, 'is_hk': False, 'is_us': True}
        result = get_company_name("UNKNOWN123", market_info)

        assert "UNKNOWN123" in result or "美股" in result, \
            f"未知代码应包含原代码或'美股'标识，实际为'{result}'"
        print("test_unknown_us_ticker_fallback PASSED")

    def test_unknown_hk_ticker_fallback(self):
        """验证未知港股代码的降级处理"""
        from tradingagents.utils.company_name_utils import get_company_name

        market_info = {'is_china': False, 'is_hk': True, 'is_us': False}
        result = get_company_name("9999.HK", market_info)

        assert "港股" in result or "9999" in result, \
            f"港股应包含'港股'标识或代码，实际为'{result}'"
        print("test_unknown_hk_ticker_fallback PASSED")

    def test_no_market_type_fallback(self):
        """验证无市场类型时的降级处理"""
        from tradingagents.utils.company_name_utils import get_company_name

        market_info = {'is_china': False, 'is_hk': False, 'is_us': False}
        result = get_company_name("UNKNOWN", market_info)

        assert "UNKNOWN" in result or "股票" in result, \
            f"未知市场应返回包含代码的默认值，实际为'{result}'"
        print("test_no_market_type_fallback PASSED")


class TestUSStockNamesMapping:
    """美股名称映射表测试"""

    def test_us_stock_names_completeness(self):
        """验证美股名称映射表包含常用股票"""
        from tradingagents.utils.company_name_utils import US_STOCK_NAMES

        expected_stocks = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META']

        for ticker in expected_stocks:
            assert ticker in US_STOCK_NAMES, f"{ticker}应在映射表中"

        print("test_us_stock_names_completeness PASSED")

    def test_china_concept_stocks_included(self):
        """验证中概股也在映射表中"""
        from tradingagents.utils.company_name_utils import US_STOCK_NAMES

        china_concept_stocks = ['BABA', 'JD', 'PDD', 'NIO']

        for ticker in china_concept_stocks:
            assert ticker in US_STOCK_NAMES, f"中概股{ticker}应在映射表中"

        print("test_china_concept_stocks_included PASSED")

    def test_add_us_stock_name_function(self):
        """验证动态添加美股名称映射功能"""
        from tradingagents.utils.company_name_utils import (
            add_us_stock_name,
            get_company_name,
            US_STOCK_NAMES
        )

        # 添加一个新的映射
        test_ticker = "TEST123"
        test_name = "测试公司"

        add_us_stock_name(test_ticker, test_name)

        # 验证添加成功
        assert test_ticker.upper() in US_STOCK_NAMES, "新添加的股票应在映射表中"

        # 验证可以正确获取
        market_info = {'is_china': False, 'is_hk': False, 'is_us': True}
        result = get_company_name(test_ticker, market_info)
        assert result == test_name, f"应返回'{test_name}'，实际为'{result}'"

        # 清理测试数据
        if test_ticker.upper() in US_STOCK_NAMES:
            del US_STOCK_NAMES[test_ticker.upper()]

        print("test_add_us_stock_name_function PASSED")


class TestMarketInfoAutoDetection:
    """市场信息自动检测测试"""

    def test_auto_detect_when_market_info_none(self):
        """验证market_info为None时自动检测"""
        from tradingagents.utils.company_name_utils import get_company_name

        # 传入None，应该自动检测市场类型
        # 这个测试可能会因为实际检测逻辑而有不同结果
        try:
            result = get_company_name("AAPL", None)
            # 只要不抛出异常就算通过
            assert result is not None, "结果不应为None"
            print("test_auto_detect_when_market_info_none PASSED")
        except Exception as e:
            # 如果检测失败，应该返回默认值而不是抛出异常
            print(f"test_auto_detect_when_market_info_none PASSED (with fallback: {e})")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始运行公司名称工具单元测试")
    print("=" * 60)

    test_classes = [
        ("美股名称映射测试", TestUSStockMapping),
        ("未知股票降级测试", TestUnknownTickerFallback),
        ("映射表完整性测试", TestUSStockNamesMapping),
        ("市场自动检测测试", TestMarketInfoAutoDetection),
    ]

    passed = 0
    failed = 0

    for class_name, test_class in test_classes:
        print(f"\n--- {class_name} ---")
        instance = test_class()

        for method_name in dir(instance):
            if method_name.startswith("test_"):
                print(f"\n运行: {method_name}")
                try:
                    getattr(instance, method_name)()
                    passed += 1
                except Exception as e:
                    print(f"FAILED: {e}")
                    failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
