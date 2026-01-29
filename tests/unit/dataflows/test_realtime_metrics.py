# -*- coding: utf-8 -*-
"""
测试实时PE/PB计算功能
"""

import pytest
from tradingagents.dataflows.realtime_metrics import (
    calculate_realtime_pe_pb,
    validate_pe_pb,
    get_pe_pb_with_fallback,
)


def test_validate_pe_pb():
    """测试PE/PB验证"""
    # 正常范围
    assert validate_pe_pb(20.5, 3.2) == True
    assert validate_pe_pb(50, 2.5) == True
    assert validate_pe_pb(-10, 1.5) == True  # 允许负PE（亏损企业）

    # PE异常
    assert validate_pe_pb(1500, 3.2) == False  # PE过大
    assert validate_pe_pb(-150, 3.2) == False  # PE过小

    # PB异常
    assert validate_pe_pb(20.5, 150) == False  # PB过大
    assert validate_pe_pb(20.5, 0.05) == False  # PB过小

    # None值
    assert validate_pe_pb(None, 3.2) == True
    assert validate_pe_pb(20.5, None) == True
    assert validate_pe_pb(None, None) == True


class MockCollection:
    """Mock MongoDB Collection，支持属性访问和字典访问"""

    def __init__(self, collection_name):
        self.collection_name = collection_name

    def find_one(self, query, sort=None):
        code = query.get("code")
        if code == "000001":
            if self.collection_name == "market_quotes":
                # 返回实时行情
                return {
                    "code": "000001",
                    "close": 10.5,
                    "pre_close": 10.0,  # 添加昨日收盘价用于计算
                    "updated_at": "2025-10-14T10:30:00",
                }
            elif self.collection_name == "stock_basic_info":
                # 返回基础信息（使用tushare数据源）
                return {
                    "code": "000001",
                    "source": "tushare",
                    "total_share": 100000,  # 10万万股 = 10亿股
                    "total_mv": 1000,  # 1000亿元（昨日市值）
                    "pe_ttm": 20.0,  # Tushare PE_TTM
                    "pe": 21.0,  # Tushare PE
                    "pb": 3.0,  # Tushare PB
                    "updated_at": "2025-10-13T16:00:00",  # 昨天更新的数据
                }
            elif self.collection_name == "stock_financial_data":
                # 返回财务数据（用于PB计算）
                return {
                    "code": "000001",
                    "total_equity": 200000000000,  # 2000亿元净资产
                    "report_period": "2025-06-30",
                }
        return None


class MockDB:
    """Mock MongoDB Database，支持属性访问和字典访问"""

    def __init__(self):
        self._collections = {}

    def __getitem__(self, name):
        if name not in self._collections:
            self._collections[name] = MockCollection(name)
        return self._collections[name]

    def __getattr__(self, name):
        # 支持属性访问，如 db.market_quotes
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in self._collections:
            self._collections[name] = MockCollection(name)
        return self._collections[name]


class MockClient:
    """Mock MongoDB Client，支持属性访问和字典访问"""

    def __init__(self):
        self._databases = {}

    def __getitem__(self, name):
        if name not in self._databases:
            self._databases[name] = MockDB()
        return self._databases[name]

    def __getattr__(self, name):
        # 支持属性访问，如 client.tradingagents
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in self._databases:
            self._databases[name] = MockDB()
        return self._databases[name]


def test_calculate_realtime_pe_pb_with_mock_data():
    """测试实时PE/PB计算（使用mock数据）"""

    # 执行测试
    result = calculate_realtime_pe_pb("000001", MockClient())

    # 验证结果
    assert result is not None
    assert result["price"] == 10.5
    assert result["is_realtime"] == True

    # 验证PE计算：基于实时股价和TTM净利润
    # 逻辑：使用 pre_close (10.0) 反推股本，再用 realtime_price (10.5) 计算动态PE
    assert result["pe"] is not None
    assert result["pe"] > 0  # PE应该是正数

    # 验证PB计算
    assert result["pb"] is not None
    assert result["pb"] > 0  # PB应该是正数


def test_calculate_realtime_pe_pb_missing_data():
    """测试缺少数据时的处理"""

    class EmptyMockCollection:
        def __init__(self, collection_name):
            pass

        def find_one(self, query, sort=None):
            return None

    class EmptyMockDB:
        def __getitem__(self, name):
            return EmptyMockCollection(name)

        def __getattr__(self, name):
            if name.startswith("_"):
                raise AttributeError(name)
            return EmptyMockCollection(name)

    class EmptyMockClient:
        def __getitem__(self, name):
            return EmptyMockDB()

        def __getattr__(self, name):
            if name.startswith("_"):
                raise AttributeError(name)
            return EmptyMockDB()

    # 执行测试
    result = calculate_realtime_pe_pb("999999", EmptyMockClient())

    # 验证结果
    assert result is None


def test_get_pe_pb_with_fallback_success():
    """测试带降级的获取函数（成功场景）"""
    import tradingagents.dataflows.realtime_metrics as metrics_module

    # Mock 实时计算成功
    mock_calculate = lambda symbol, db_client: {
        "pe": 22.5,
        "pb": 3.2,
        "pe_ttm": 23.1,
        "pb_mrq": 3.3,
        "source": "realtime_calculated",
        "is_realtime": True,
        "updated_at": "2025-10-14T10:30:00",
    }

    # 保存原始函数并替换
    original_calculate = metrics_module.calculate_realtime_pe_pb
    metrics_module.calculate_realtime_pe_pb = mock_calculate

    try:
        # 执行测试
        result = metrics_module.get_pe_pb_with_fallback("000001", MockClient())

        # 验证结果
        assert result["pe"] == 22.5
        assert result["pb"] == 3.2
        assert result["is_realtime"] == True
    finally:
        # 恢复原始函数
        metrics_module.calculate_realtime_pe_pb = original_calculate


def test_get_pe_pb_with_fallback_to_static():
    """测试降级到静态数据"""
    import tradingagents.dataflows.realtime_metrics as metrics_module

    # Mock 实时计算失败
    original_calculate = metrics_module.calculate_realtime_pe_pb
    metrics_module.calculate_realtime_pe_pb = lambda symbol, db_client: None

    try:
        # 执行测试
        result = metrics_module.get_pe_pb_with_fallback("000001", MockClient())

        # 验证结果
        assert result["pe"] == 21.0  # 使用 mock 中的 pe 值
        assert result["pb"] == 3.0  # 使用 mock 中的 pb 值
        assert result["is_realtime"] == False
        assert result["source"] == "daily_basic"
    finally:
        # 恢复原始函数
        metrics_module.calculate_realtime_pe_pb = original_calculate


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
