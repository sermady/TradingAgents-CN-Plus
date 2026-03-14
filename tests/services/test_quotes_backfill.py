# -*- coding: utf-8 -*-
"""测试行情数据回填功能"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock


class FakeCursor:
    """模拟 MongoDB 游标"""
    def __init__(self, docs):
        self._docs = docs

    async def to_list(self, length=None):
        return self._docs


class FakeCollection:
    """模拟 MongoDB 集合"""
    def __init__(self):
        self.last_ops = None
        self._data = []

    async def create_index(self, *args, **kwargs):
        return "ok"

    async def estimated_document_count(self):
        return 0  # empty -> should trigger backfill

    async def bulk_write(self, ops, ordered=False):
        self.last_ops = ops
        class Result:
            def __init__(self, upserted):
                self.matched_count = 0
                self.modified_count = 0
                self.upserted_ids = {i: None for i in range(upserted)}
        return Result(len(ops))

    def find(self, filter=None, projection=None):
        """模拟查询操作"""
        return FakeCursor(self._data)

    async def update_one(self, filter, update, upsert=False):
        """模拟更新操作"""
        class Result:
            matched_count = 1
            modified_count = 1
            upserted_id = None
        return Result()


class FakeDB:
    """模拟 MongoDB 数据库"""
    def __init__(self):
        self._collections = {}
        # 预创建 stock_daily_quotes 集合并添加数据
        self._collections["stock_daily_quotes"] = FakeCollection()

    def __getitem__(self, name: str):
        # 缓存集合实例，确保每次返回同一个对象
        if name not in self._collections:
            self._collections[name] = FakeCollection()
        return self._collections[name]

    @property
    def _daily_coll(self):
        """访问 daily_quotes 集合（向后兼容）"""
        return self["stock_daily_quotes"]

    @property
    def _coll(self):
        """访问默认集合（向后兼容）"""
        return self["market_quotes"]


@pytest.fixture
def fake_db():
    """提供 fake 数据库实例"""
    db = FakeDB()
    # 为 daily_quotes 集合添加模拟历史数据
    db._daily_coll._data = [
        {
            "symbol": "000001",
            "trade_date": "20250102",
            "period": "daily",
            "close": 10.2,
            "pct_chg": 0.2,
            "amount": 1.1e8,
            "volume": 10000,
            "open": 10.0,
            "high": 10.5,
            "low": 9.9,
            "pre_close": 10.0,
        },
        {
            "symbol": "600000",
            "trade_date": "20250102",
            "period": "daily",
            "close": 9.7,
            "pct_chg": -0.4,
            "amount": 7.1e7,
            "volume": 8000,
            "open": 9.8,
            "high": 9.9,
            "low": 9.6,
            "pre_close": 9.8,
        },
    ]
    return db


def test_offhours_backfill_when_empty(monkeypatch, fake_db):
    """测试非交易时间数据回填功能"""

    # Fake DataSourceManager
    class _FakeManager:
        def get_realtime_quotes_with_fallback(self):
            return {
                "000001": {"close": 10.2, "pct_chg": 0.2, "amount": 1.1e8},
                "600000": {"close": 9.7, "pct_chg": -0.4, "amount": 7.1e7},
            }, "fake"

        def find_latest_trade_date_with_fallback(self):
            return "20250102"

    # 先 patch DataSourceManager
    import app.services.data_sources.manager as ds_mod
    monkeypatch.setattr(ds_mod, "DataSourceManager", _FakeManager)

    # 再 patch get_mongo_db
    def _fake_get_mongo_db():
        return fake_db

    import app.core.database as db_mod
    monkeypatch.setattr(db_mod, "get_mongo_db", _fake_get_mongo_db)

    # 最后导入 QuotesIngestionService
    from app.services.quotes import QuotesIngestionService

    async def _run():
        svc = QuotesIngestionService()
        # Force off-hours
        monkeypatch.setattr(svc, "_is_trading_time", lambda now=None: False)
        await svc.run_once()
        # 验证 bulk_write 被调用（通过 FakeCollection 记录）
        assert fake_db._coll.last_ops is not None or fake_db._daily_coll.last_ops is not None

    asyncio.run(_run())
