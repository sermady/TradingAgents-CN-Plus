# -*- coding: utf-8 -*-
"""
交易日管理器单元测试

测试交易日管理器的核心功能：
1. 周末回溯到最近交易日
2. 缓存机制
3. 线程安全
"""

import unittest
from datetime import datetime, timedelta
from tradingagents.utils.trading_date_manager import get_trading_date_manager, TradingDateManager


class TestTradingDateManager(unittest.TestCase):
    """交易日管理器测试类"""

    def setUp(self):
        """测试前准备：清除缓存"""
        mgr = get_trading_date_manager()
        mgr.clear_cache()

    def test_singleton_pattern(self):
        """测试单例模式"""
        mgr1 = get_trading_date_manager()
        mgr2 = get_trading_date_manager()
        self.assertIs(mgr1, mgr2, "应该返回同一个实例")

    def test_weekday_trading_date(self):
        """测试工作日（周一到周五）应保持不变"""
        mgr = get_trading_date_manager()

        # 测试周一到周五
        for weekday in range(5):  # 0=周一, 4=周五
            base_date = datetime(2025, 1, 6 + weekday)  # 2025-01-06 是周一
            test_date = base_date.strftime('%Y-%m-%d')
            result = mgr.get_latest_trading_date(test_date)
            self.assertEqual(result, test_date, f"工作日 {test_date} 应保持不变")

    def test_saturday_fallback(self):
        """测试周六应回溯到周五"""
        mgr = get_trading_date_manager()

        # 2025-01-11 是周六
        test_date = "2025-01-11"
        result = mgr.get_latest_trading_date(test_date)
        expected = "2025-01-10"  # 周五
        self.assertEqual(result, expected, f"周六 {test_date} 应回溯到周五 {expected}")

    def test_sunday_fallback(self):
        """测试周日应回溯到周五"""
        mgr = get_trading_date_manager()

        # 2025-01-12 是周日
        test_date = "2025-01-12"
        result = mgr.get_latest_trading_date(test_date)
        expected = "2025-01-10"  # 周五
        self.assertEqual(result, expected, f"周日 {test_date} 应回溯到周五 {expected}")

    def test_cache_mechanism(self):
        """测试缓存机制"""
        mgr = get_trading_date_manager()

        # 第一次调用
        test_date = "2025-01-15"
        result1 = mgr.get_latest_trading_date(test_date)

        # 清除缓存前的第二次调用应返回缓存值
        result2 = mgr.get_latest_trading_date(test_date)
        self.assertEqual(result1, result2, "缓存应返回相同值")

        # 清除缓存后再次调用
        mgr.clear_cache()
        result3 = mgr.get_latest_trading_date(test_date)
        self.assertEqual(result1, result3, "清除缓存后应返回相同值")

    def test_cache_expiry(self):
        """测试缓存过期（TTL = 60分钟）"""
        mgr = get_trading_date_manager()
        mgr._cache_ttl_minutes = 0  # 设置为0立即过期

        test_date = "2025-01-15"
        result1 = mgr.get_latest_trading_date(test_date)

        # 等待一小段时间确保缓存过期
        import time
        time.sleep(0.1)

        # 缓存应过期，但结果应相同
        result2 = mgr.get_latest_trading_date(test_date)
        self.assertEqual(result1, result2, "缓存过期后结果应一致")

    def test_none_date_uses_today(self):
        """测试传入None时应使用今天"""
        mgr = get_trading_date_manager()

        result = mgr.get_latest_trading_date(None)
        today = datetime.now()

        # 结果应该是今天或最近的交易日
        self.assertIsNotNone(result, "应返回有效日期")
        self.assertIn('-', result, "日期格式应包含连字符")


class TestPriceConsistencyIntegration(unittest.TestCase):
    """价格一致性集成测试"""

    def setUp(self):
        """测试前准备：清除缓存"""
        from tradingagents.utils.price_cache import get_price_cache
        mgr = get_trading_date_manager()
        mgr.clear_cache()
        cache = get_price_cache()
        cache.clear()

    def test_price_cache_and_trading_date_integration(self):
        """测试价格缓存和交易日管理器的集成"""
        from tradingagents.utils.price_cache import get_price_cache

        date_mgr = get_trading_date_manager()
        price_cache = get_price_cache()

        # 获取交易日
        trading_date = date_mgr.get_latest_trading_date("2025-01-11")  # 周六
        self.assertEqual(trading_date, "2025-01-10", "应回溯到周五")

        # 更新价格缓存
        price_cache.update("000001", 59.95, "¥")

        # 验证缓存价格
        price_info = price_cache.get_price_info("000001")
        self.assertIsNotNone(price_info, "应返回价格信息")
        self.assertEqual(price_info['price'], 59.95, "价格应匹配")
        self.assertEqual(price_info['currency'], "¥", "货币应匹配")

    def test_cross_analyst_price_consistency(self):
        """测试跨分析师价格一致性"""
        from tradingagents.utils.price_cache import get_price_cache

        # 模拟技术分析师更新缓存
        price_cache = get_price_cache()
        price_cache.update("002938", 58.29, "¥")

        # 模拟基本面分析师读取缓存
        price_info = price_cache.get_price_info("002938")
        self.assertIsNotNone(price_info, "基本面分析师应能读取缓存")
        self.assertEqual(price_info['price'], 58.29, "价格应一致")


if __name__ == '__main__':
    unittest.main()
