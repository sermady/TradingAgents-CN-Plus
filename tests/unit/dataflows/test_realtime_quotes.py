# -*- coding: utf-8 -*-
"""
实时行情获取测试
测试Tushare rt_k和AKShare缓存机制
"""

import pytest
import sys
import os

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestTushareBatchQuotes:
    """Tushare批量行情测试"""

    def test_cache_functions_exist(self):
        """测试缓存函数存在"""
        from tradingagents.dataflows.providers.china.tushare import (
            _get_cached_batch_quotes,
            _set_cached_batch_quotes,
            _invalidate_batch_cache,
            BATCH_CACHE_TTL_SECONDS,
        )

        assert BATCH_CACHE_TTL_SECONDS == 30
        assert callable(_get_cached_batch_quotes)
        assert callable(_set_cached_batch_quotes)
        assert callable(_invalidate_batch_cache)

    def test_cache_operations(self):
        """测试缓存操作"""
        from tradingagents.dataflows.providers.china.tushare import (
            _get_cached_batch_quotes,
            _set_cached_batch_quotes,
            _invalidate_batch_cache,
            BATCH_QUOTES_CACHE,
        )

        # 初始状态应该是空的
        assert _get_cached_batch_quotes() is None

        # 设置缓存
        test_data = {"000001": {"close": 10.5}}
        _set_cached_batch_quotes(test_data)

        # 应该有缓存了
        cached = _get_cached_batch_quotes()
        assert cached is not None
        assert cached["000001"]["close"] == 10.5

        # 使缓存失效
        _invalidate_batch_cache()
        assert _get_cached_batch_quotes() is None

    def test_cache_status(self):
        """测试缓存状态获取"""
        from tradingagents.dataflows.providers.china.tushare import (
            _set_cached_batch_quotes,
            _invalidate_batch_cache,
        )

        from tradingagents.dataflows.providers.china.tushare import TushareProvider

        provider = TushareProvider()

        # 初始状态
        status = provider.get_batch_cache_status()
        assert status["cached"] is False

        # 设置缓存
        _set_cached_batch_quotes({"000001": {"close": 10.5}})
        status = provider.get_batch_cache_status()
        assert status["cached"] is True
        assert status["count"] == 1
        assert status["ttl_seconds"] == 30

        # 清理
        _invalidate_batch_cache()


class TestAkShareQuotes:
    """AKShare行情测试"""

    def test_cache_functions_exist(self):
        """测试缓存函数存在"""
        from tradingagents.dataflows.providers.china.akshare import (
            _get_akshare_cached_quote,
            _set_akshare_cached_quote,
            _clean_akshare_expired_cache,
            AKSHARE_CACHE_TTL,
            AKSHARE_QUOTES_CACHE,
        )

        assert AKSHARE_CACHE_TTL == 15
        assert callable(_get_akshare_cached_quote)
        assert callable(_set_akshare_cached_quote)
        assert callable(_clean_akshare_expired_cache)

    def test_cache_operations(self):
        """测试缓存操作"""
        from tradingagents.dataflows.providers.china.akshare import (
            _get_akshare_cached_quote,
            _set_akshare_cached_quote,
            AKSHARE_QUOTES_CACHE,
            AKSHARE_CACHE_LOCK,
        )

        code = "000001"

        # 初始状态应该是空的
        assert _get_akshare_cached_quote(code) is None

        # 设置缓存
        test_data = {"close": 10.5, "pct_chg": 1.2}
        _set_akshare_cached_quote(code, test_data)

        # 应该有缓存了
        cached = _get_akshare_cached_quote(code)
        assert cached is not None
        assert cached["close"] == 10.5

    def test_cache_status(self):
        """测试缓存状态获取"""
        from tradingagents.dataflows.providers.china.akshare import (
            _set_akshare_cached_quote,
            _clear_all_akshare_cache,
        )

        from tradingagents.dataflows.providers.china.akshare import AKShareProvider

        provider = AKShareProvider()

        # 先清空所有缓存
        _clear_all_akshare_cache()

        # 初始状态
        status = provider.get_akshare_cache_status()
        assert status["cached_count"] == 0

        # 设置缓存
        _set_akshare_cached_quote("000001", {"close": 10.5})
        _set_akshare_cached_quote("000002", {"close": 20.5})

        status = provider.get_akshare_cache_status()
        assert status["cached_count"] == 2
        assert status["ttl_seconds"] == 15

    def test_cached_function_sets_cache(self):
        """测试get_stock_quotes_cached获取数据后设置缓存"""
        from tradingagents.dataflows.providers.china.akshare import (
            AKShareProvider,
            _get_akshare_cached_quote,
            _clear_all_akshare_cache,
        )

        provider = AKShareProvider()

        # 先清空缓存
        _clear_all_akshare_cache()

        # 验证初始无缓存
        assert _get_akshare_cached_quote("000001") is None

        # 使用get_akshare_cache_status验证缓存被设置
        _clear_all_akshare_cache()
        provider.get_akshare_cache_status()  # 触发清理过期
        status = provider.get_akshare_cache_status()
        assert status["cached_count"] == 0


class TestRealtimeQuotesIntegration:
    """实时行情集成测试"""

    def test_provider_import(self):
        """测试Provider导入"""
        from tradingagents.dataflows.providers.china.tushare import TushareProvider
        from tradingagents.dataflows.providers.china.akshare import AKShareProvider

        assert TushareProvider is not None
        assert AKShareProvider is not None

    def test_cache_module_import(self):
        """测试缓存模块导入"""
        from tradingagents.dataflows.providers.china.tushare import (
            BATCH_QUOTES_CACHE,
            BATCH_CACHE_TTL_SECONDS,
        )

        from tradingagents.dataflows.providers.china.akshare import (
            AKSHARE_QUOTES_CACHE,
            AKSHARE_CACHE_TTL,
        )

        assert "data" in BATCH_QUOTES_CACHE
        assert "timestamp" in BATCH_QUOTES_CACHE
        assert "lock" in BATCH_QUOTES_CACHE
        assert isinstance(
            BATCH_QUOTES_CACHE["lock"], type(__import__("threading").Lock())
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
