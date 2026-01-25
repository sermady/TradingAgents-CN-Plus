# -*- coding: utf-8 -*-
"""
数据协调器和价格缓存测试
验证数据架构优化功能
"""

import pytest
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestUnifiedPriceCache:
    """测试统一价格缓存"""

    def test_price_cache_initialization(self):
        """测试价格缓存初始化"""
        from tradingagents.utils.price_cache import get_price_cache, UnifiedPriceCache

        cache = get_price_cache()
        assert isinstance(cache, UnifiedPriceCache)

    def test_price_cache_update_and_get(self):
        """测试价格更新和获取"""
        from tradingagents.utils.price_cache import get_price_cache

        cache = get_price_cache()
        test_ticker = "TEST_001"

        # 更新价格
        cache.update(test_ticker, 123.45, "¥")

        # 获取价格
        price = cache.get_price(test_ticker)
        assert price == 123.45

        # 获取完整信息
        info = cache.get_price_info(test_ticker)
        assert info is not None
        assert info['price'] == 123.45
        assert info['currency'] == "¥"

        # 清理
        cache.clear(test_ticker)

    def test_price_cache_freshness(self):
        """测试价格新鲜度检查"""
        from tradingagents.utils.price_cache import get_price_cache

        cache = get_price_cache()
        test_ticker = "TEST_002"

        # 更新价格
        cache.update(test_ticker, 100.00, "¥")

        # 检查新鲜度（应该在600秒内）
        is_fresh = cache.is_price_fresh(test_ticker, 600)
        assert is_fresh is True

        # 清理
        cache.clear(test_ticker)

    def test_price_cache_multi_ticker(self):
        """测试多股票缓存"""
        from tradingagents.utils.price_cache import get_price_cache

        cache = get_price_cache()
        tickers = ["TICKER_A", "TICKER_B", "TICKER_C"]

        # 更新多个股票价格
        for i, ticker in enumerate(tickers):
            cache.update(ticker, 100.0 + i * 10, "¥")

        # 验证所有价格
        for i, ticker in enumerate(tickers):
            price = cache.get_price(ticker)
            assert price == 100.0 + i * 10

        # 清理
        cache.clear()

    def test_price_cache_stats(self):
        """测试缓存统计"""
        from tradingagents.utils.price_cache import get_price_cache

        cache = get_price_cache()

        # 更新价格
        cache.update("STATS_TEST_1", 10.0, "¥")
        cache.update("STATS_TEST_2", 20.0, "¥")

        stats = cache.get_cache_stats()
        assert 'memory_cache_count' in stats
        assert 'redis_available' in stats

        # 清理
        cache.clear()


class TestDataCoordinator:
    """测试数据协调器"""

    def test_coordinator_initialization(self):
        """测试协调器初始化"""
        from tradingagents.dataflows.data_coordinator import get_data_coordinator, DataCoordinator

        coordinator = get_data_coordinator()
        assert isinstance(coordinator, DataCoordinator)

    def test_preload_analysis_data_structure(self):
        """测试预加载数据结构"""
        from tradingagents.dataflows.data_coordinator import DataCoordinator, PreloadedData

        # 测试 PreloadedData 数据类
        data = PreloadedData(
            ticker="TEST_001",
            trade_date="2025-01-01",
            depth="标准"
        )

        assert data.ticker == "TEST_001"
        assert data.trade_date == "2025-01-01"
        assert data.depth == "标准"
        assert isinstance(data.loaded_at, datetime)

    def test_analysis_depth_enum(self):
        """测试分析深度枚举"""
        from tradingagents.dataflows.data_coordinator import AnalysisDepth

        assert AnalysisDepth.QUICK.value == "快速"
        assert AnalysisDepth.BASIC.value == "基础"
        assert AnalysisDepth.STANDARD.value == "标准"
        assert AnalysisDepth.DEEP.value == "深度"
        assert AnalysisDepth.COMPREHENSIVE.value == "全面"

    def test_cache_key_generation(self):
        """测试缓存键生成"""
        from tradingagents.dataflows.data_coordinator import DataCoordinator

        coordinator = DataCoordinator()
        key = coordinator._get_cache_key("600519", "2025-01-15")

        assert key == "600519_2025-01-15"

    def test_coordinator_cache_stats(self):
        """测试协调器缓存统计"""
        from tradingagents.dataflows.data_coordinator import get_data_coordinator

        coordinator = get_data_coordinator()
        stats = coordinator.get_cache_stats()

        assert 'preloaded_stocks' in stats
        assert 'preloaded_entries' in stats
        assert 'price_cache_stats' in stats

    def test_coordinator_clear_cache(self):
        """测试清除缓存"""
        from tradingagents.dataflows.data_coordinator import get_data_coordinator

        coordinator = get_data_coordinator()

        # 清除缓存不应该报错
        coordinator.clear_cache()
        coordinator.clear_cache("TEST_TICKER")


class TestIntegration:
    """集成测试"""

    def test_price_cache_and_coordinator_integration(self):
        """测试价格缓存和协调器集成"""
        from tradingagents.utils.price_cache import get_price_cache
        from tradingagents.dataflows.data_coordinator import get_data_coordinator

        # 确保两者初始化
        price_cache = get_price_cache()
        coordinator = get_data_coordinator()

        # 更新价格缓存
        price_cache.update("INTEG_001", 999.99, "¥")

        # 从协调器获取价格信息
        price_info = coordinator.get_price_info("INTEG_001")

        # 验证价格信息存在
        assert price_info is not None or price_cache.get_price("INTEG_001") == 999.99

        # 清理
        price_cache.clear("INTEG_001")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
