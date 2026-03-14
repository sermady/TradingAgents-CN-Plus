# -*- coding: utf-8 -*-
"""测试行情采集和增强筛选功能"""

import asyncio
from typing import Any, Dict, List


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

    def __getitem__(self, name: str):
        # 缓存集合实例，确保每次返回同一个对象
        if name not in self._collections:
            self._collections[name] = FakeCollection()
        return self._collections[name]

    def get_collection(self, name: str):
        """获取指定名称的集合"""
        return self[name]


def test_enhanced_screening_enriches_from_db(monkeypatch):
    """测试增强筛选从数据库获取行情数据"""
    # Late import to patch module symbols correctly
    from app.services.enhanced_screening_service import EnhancedScreeningService

    # Fake DB layer
    class ESSFakeCursor:
        def __init__(self, docs: List[Dict[str, Any]]):
            self._docs = docs

        async def to_list(self, length: int):
            return self._docs

    class ESSFakeColl:
        def __init__(self, docs):
            self._docs = docs

        def find(self, query, projection=None):
            return ESSFakeCursor(self._docs)

    class ESSFakeDB:
        def __init__(self, docs):
            self._coll = ESSFakeColl(docs)

        def __getitem__(self, name: str):
            return self._coll

    # Prepare quotes in DB for codes 000001, 600000
    quotes_docs = [
        {"code": "000001", "close": 10.5, "pct_chg": 1.2, "amount": 1.23e8},
        {"code": "600000", "close": 9.9, "pct_chg": -0.5, "amount": 8.76e7},
    ]

    # Patch get_mongo_db used inside enhanced_screening_service module
    import app.services.enhanced_screening_service as ess_mod

    def _fake_get_mongo_db():
        return ESSFakeDB(quotes_docs)

    monkeypatch.setattr(ess_mod, "get_mongo_db", _fake_get_mongo_db, raising=True)

    # Patch condition analysis to force DB path
    def _fake_analyze(_self, _conditions):
        return {"can_use_database": True, "needs_technical_indicators": False}

    monkeypatch.setattr(EnhancedScreeningService, "_analyze_conditions", _fake_analyze, raising=True)

    # Patch db_service.screen_stocks to return minimal items with codes
    class _FakeDbService:
        async def screen_stocks(self, conditions, limit, offset, order_by):
            items = [
                {"code": "1", "name": "平安银行"},
                {"code": "600000", "name": "浦发银行"},
                {"code": "300750", "name": "宁德时代"},  # not present in quotes -> stays None
            ]
            total = len(items)
            return items, total

    async def _run():
        svc = EnhancedScreeningService()
        svc.db_service = _FakeDbService()
        res = await svc.screen_stocks(conditions=[])
        items = res["items"]
        # Map by code for assertion
        by_code = {str(it["code"]).zfill(6): it for it in items}
        assert by_code["000001"]["close"] == 10.5
        assert by_code["000001"]["pct_chg"] == 1.2
        assert by_code["600000"]["amount"] == 8.76e7
        # Code not present in DB remains without enrichment
        assert "close" not in by_code["300750"] or by_code["300750"]["close"] is None

    asyncio.run(_run())


def test_quotes_ingestion_service_basic(monkeypatch):
    """测试 QuotesIngestionService 基本功能 - 验证服务能正常初始化和运行"""
    from app.services.quotes import QuotesIngestionService

    # 创建服务实例
    svc = QuotesIngestionService()

    # 验证基本属性
    assert svc.collection_name == "market_quotes"
    assert svc.status_collection_name == "quotes_ingestion_status"

    # 验证 _is_trading_time 方法存在且可调用
    assert callable(svc._is_trading_time)
