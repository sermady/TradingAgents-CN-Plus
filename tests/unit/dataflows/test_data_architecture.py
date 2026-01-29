# -*- coding: utf-8 -*-
"""
数据架构优化验证测试
独立测试，无外部依赖
"""

import sys
import os
import threading
import pytest
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List


class PriceCache:
    """价格缓存"""

    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.memory_ttl_seconds = 600
        self.redis_ttl_seconds = 1800
        self._redis_available = False

    def get_price(self, ticker: str) -> Optional[float]:
        if ticker in self.cache:
            entry = self.cache[ticker]
            age = (datetime.now() - entry["timestamp"]).total_seconds()
            if age < self.memory_ttl_seconds:
                return entry["price"]
        return None

    def update(
        self,
        ticker: str,
        price: float,
        currency: str = "CNY",
        data: Dict[str, Any] = None,
    ):
        entry = {
            "price": float(price),
            "currency": currency,
            "timestamp": datetime.now(),
            "data": data or {},
        }
        if ticker in self.cache:
            old_entry = self.cache[ticker]
            age = (datetime.now() - old_entry["timestamp"]).total_seconds()
            if age < 10:
                return
        self.cache[ticker] = entry

    def get_price_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        if ticker in self.cache:
            entry = self.cache[ticker]
            age = (datetime.now() - entry["timestamp"]).total_seconds()
            if age < self.memory_ttl_seconds:
                return entry.copy()
        return None

    def is_price_fresh(self, ticker: str, max_age_seconds: int = 600) -> bool:
        if ticker in self.cache:
            entry = self.cache[ticker]
            age = (datetime.now() - entry["timestamp"]).total_seconds()
            return age < max_age_seconds
        return False

    def get_cache_stats(self) -> Dict[str, Any]:
        valid_count = sum(
            1
            for entry in self.cache.values()
            if (datetime.now() - entry["timestamp"]).total_seconds()
            < self.memory_ttl_seconds
        )
        return {
            "memory_cache_count": len(self.cache),
            "valid_memory_cache": valid_count,
            "redis_available": self._redis_available,
            "memory_ttl_seconds": self.memory_ttl_seconds,
            "redis_ttl_seconds": self.redis_ttl_seconds,
        }

    def clear(self, ticker: str = None):
        if ticker:
            if ticker in self.cache:
                del self.cache[ticker]
        else:
            self.cache.clear()


class DataCoordinator:
    """数据协调器"""

    def __init__(self):
        self._preloaded_cache: Dict[str, Dict[str, Any]] = {}
        self._price_cache = PriceCache()
        self._cache_ttl_seconds = 600

    def _get_cache_key(self, ticker: str, trade_date: str) -> str:
        return f"{ticker}_{trade_date}"

    def get_price_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        return self._price_cache.get_price_info(ticker)

    def update_price(self, ticker: str, price: float, currency: str = "CNY"):
        self._price_cache.update(ticker, price, currency)

    def get_cache_stats(self) -> Dict[str, Any]:
        total_entries = sum(len(dates) for dates in self._preloaded_cache.values())
        return {
            "preloaded_stocks": len(self._preloaded_cache),
            "preloaded_entries": total_entries,
            "price_cache_stats": self._price_cache.get_cache_stats(),
        }

    def clear_cache(self, ticker: str = None):
        if ticker:
            if ticker in self._preloaded_cache:
                del self._preloaded_cache[ticker]
        else:
            self._preloaded_cache.clear()
        self._price_cache.clear(ticker)


@pytest.mark.unit
class TestPriceCache:
    """价格缓存测试"""

    def test_price_update_and_get(self):
        """测试价格更新和获取"""
        cache = PriceCache()
        cache.update("600519", 1800.50, "CNY")
        price = cache.get_price("600519")
        assert price == 1800.50

    def test_price_info_retrieval(self):
        """测试价格信息获取"""
        cache = PriceCache()
        cache.update("600519", 1800.50, "CNY")
        info = cache.get_price_info("600519")
        assert info is not None
        assert info["price"] == 1800.50
        assert info["currency"] == "CNY"

    def test_price_freshness(self):
        """测试价格新鲜度检查"""
        cache = PriceCache()
        cache.update("600519", 1800.50, "CNY")
        is_fresh = cache.is_price_fresh("600519", 600)
        assert is_fresh is True

    def test_multi_ticker_caching(self):
        """测试多股票缓存"""
        cache = PriceCache()
        cache.update("000001", 15.20, "CNY")
        cache.update("000002", 25.30, "CNY")
        assert cache.get_price("000001") == 15.20
        assert cache.get_price("000002") == 25.30

    def test_cache_stats(self):
        """测试缓存统计"""
        cache = PriceCache()
        cache.update("600519", 1800.50, "CNY")
        stats = cache.get_cache_stats()
        assert "memory_cache_count" in stats
        assert "redis_available" in stats
        assert stats["memory_cache_count"] == 1

    def test_cache_clear_single(self):
        """测试清除单个缓存"""
        cache = PriceCache()
        cache.update("600519", 1800.50, "CNY")
        cache.clear("600519")
        assert cache.get_price("600519") is None

    def test_cache_clear_all(self):
        """测试清除所有缓存"""
        cache = PriceCache()
        cache.update("600519", 1800.50, "CNY")
        cache.update("000001", 15.20, "CNY")
        cache.clear()
        assert cache.get_price("600519") is None
        assert cache.get_price("000001") is None


@pytest.mark.unit
class TestDataCoordinator:
    """数据协调器测试"""

    def test_price_update(self):
        """测试价格更新"""
        coordinator = DataCoordinator()
        coordinator.update_price("TEST_001", 100.50, "CNY")
        info = coordinator.get_price_info("TEST_001")
        assert info is not None
        assert info["price"] == 100.50

    def test_coordinator_stats(self):
        """测试协调器统计"""
        coordinator = DataCoordinator()
        stats = coordinator.get_cache_stats()
        assert "preloaded_stocks" in stats
        assert "price_cache_stats" in stats

    def test_coordinator_clear(self):
        """测试协调器清除"""
        coordinator = DataCoordinator()
        coordinator.update_price("TEST_001", 100.50, "CNY")
        coordinator.clear_cache("TEST_001")
        assert coordinator.get_price_info("TEST_001") is None


@pytest.mark.unit
class TestCacheIntegration:
    """缓存集成测试"""

    def test_batch_price_update(self):
        """测试批量价格更新"""
        coordinator = DataCoordinator()
        tickers = ["STOCK_A", "STOCK_B", "STOCK_C"]
        for ticker in tickers:
            coordinator.update_price(ticker, 100.0, "CNY")

        for ticker in tickers:
            price = coordinator.get_price_info(ticker)
            assert price is not None
            assert price["price"] == 100.0

    def test_batch_clear(self):
        """测试批量清除"""
        coordinator = DataCoordinator()
        tickers = ["STOCK_A", "STOCK_B", "STOCK_C"]
        for ticker in tickers:
            coordinator.update_price(ticker, 100.0, "CNY")

        coordinator.clear_cache()

        for ticker in tickers:
            assert coordinator.get_price_info(ticker) is None


@pytest.mark.unit
class TestCacheTTLBehavior:
    """缓存TTL行为测试"""

    def test_fresh_data_freshness(self):
        """测试新数据的新鲜度"""
        cache = PriceCache()
        cache.update("TTL_TEST", 50.00, "CNY")
        assert cache.is_price_fresh("TTL_TEST", 600) is True

    def test_expired_data_freshness(self):
        """测试过期数据的新鲜度"""
        cache = PriceCache()
        cache.update("TTL_TEST", 50.00, "CNY")
        cache.memory_ttl_seconds = 0
        assert cache.is_price_fresh("TTL_TEST", 0) is False

    def test_ttl_config(self):
        """测试TTL配置"""
        cache = PriceCache()
        assert cache.memory_ttl_seconds == 600
        assert cache.redis_ttl_seconds == 1800


@pytest.mark.unit
class TestConcurrentAccess:
    """并发访问测试"""

    def test_concurrent_update_no_errors(self):
        """测试并发更新无错误"""
        cache = PriceCache()
        errors = []

        def update_prices(ticker_prefix, count):
            try:
                for i in range(count):
                    ticker = f"{ticker_prefix}_{i}"
                    cache.update(ticker, 100.0 + i, "CNY")
            except Exception as e:
                errors.append(str(e))

        threads = []
        for i in range(5):
            t = threading.Thread(target=update_prices, args=(f"CONCURRENT_{i}", 10))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_all_records_cached(self):
        """测试所有记录正确缓存"""
        cache = PriceCache()

        def update_prices(ticker_prefix, count):
            for i in range(count):
                ticker = f"{ticker_prefix}_{i}"
                cache.update(ticker, 100.0 + i, "CNY")

        threads = []
        for i in range(5):
            t = threading.Thread(target=update_prices, args=(f"CONCURRENT_{i}", 10))
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        total_cached = len(cache.cache)
        assert total_cached == 50
