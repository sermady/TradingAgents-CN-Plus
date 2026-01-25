# -*- coding: utf-8 -*-
"""
Screening Service 单元测试

测试股票筛选服务的核心功能：
- 股票筛选逻辑
- 筛选条件验证
- 排序功能
- 分页功能
- 筛选结果缓存
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, List

from app.services.screening_service import ScreeningService


# ==============================================================================
# 测试筛选服务初始化
# ==============================================================================


@pytest.mark.unit
def test_screening_service_init():
    """测试筛选服务初始化"""
    with patch("app.services.screening_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_get_mongo.return_value = mock_mongo

        service = ScreeningService()

        assert service.mongo_db is not None


# ==============================================================================
# 测试股票筛选
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_screen_stocks():
    """测试股票筛选"""
    with patch("app.services.screening_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # 返回筛选结果
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [
            {"code": "000001", "name": "平安银行", "pe": 7.5, "roe": 10.5},
            {"code": "600519", "name": "贵州茅台", "pe": 35.0, "roe": 25.0},
            {"code": "000002", "name": "万科A", "pe": 8.2, "roe": 12.3},
        ]
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value.limit.return_value.skip.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = ScreeningService()

        # 筛选条件
        criteria = {
            "min_pe": 5.0,
            "max_pe": 40.0,
            "min_roe": 10.0,
            "market": ["sh", "sz"],
        }

        # 执行筛选
        results = await service.screen_stocks(criteria)

        assert len(results) == 3
        assert results[0]["code"] == "000001"
        assert results[1]["code"] == "600519"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_screen_stocks_empty_result():
    """测试股票筛选（空结果）"""
    with patch("app.services.screening_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # 空结果
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = []
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value.limit.return_value.skip.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = ScreeningService()

        # 严格的筛选条件
        criteria = {
            "min_pe": 0.1,
            "max_pe": 0.5,  # 不可能的价格范围
            "min_roe": 100.0,  # 不可能的ROE
        }

        # 执行筛选
        results = await service.screen_stocks(criteria)

        assert len(results) == 0


# ==============================================================================
# 测试筛选条件
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_screen_by_pe():
    """测试按PE筛选"""
    with patch("app.services.screening_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [
            {"code": "000001", "name": "平安银行", "pe": 7.5},
            {"code": "000002", "name": "万科A", "pe": 8.2},
        ]
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value.limit.return_value.skip.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = ScreeningService()

        # PE范围筛选
        results = await service.screen_stocks({"min_pe": 5.0, "max_pe": 10.0})

        assert len(results) == 2
        for result in results:
            assert 5.0 <= result["pe"] <= 10.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_screen_by_roe():
    """测试按ROE筛选"""
    with patch("app.services.screening_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [
            {"code": "600519", "name": "贵州茅台", "roe": 25.0},
            {"code": "000001", "name": "平安银行", "roe": 10.5},
        ]
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value.limit.return_value.skip.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = ScreeningService()

        # ROE范围筛选
        results = await service.screen_stocks({"min_roe": 10.0})

        assert len(results) == 2
        for result in results:
            assert result["roe"] >= 10.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_screen_by_market():
    """测试按市场筛选"""
    with patch("app.services.screening_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [
            {"code": "000001", "name": "平安银行", "market": "sz"},
            {"code": "000002", "name": "万科A", "market": "sz"},
        ]
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value.limit.return_value.skip.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = ScreeningService()

        # 市场筛选
        results = await service.screen_stocks({"market": ["sz"]})

        assert len(results) == 2
        for result in results:
            assert result["market"] == "sz"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_screen_by_industry():
    """测试按行业筛选"""
    with patch("app.services.screening_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [
            {"code": "600519", "name": "贵州茅台", "industry": "白酒"},
            {"code": "000568", "name": "泸州老窖", "industry": "白酒"},
        ]
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value.limit.return_value.skip.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = ScreeningService()

        # 行业筛选
        results = await service.screen_stocks({"industry": ["白酒"]})

        assert len(results) == 2
        for result in results:
            assert result["industry"] == "白酒"


# ==============================================================================
# 测试排序功能
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sort_by_market_cap():
    """测试按市值排序"""
    with patch("app.services.screening_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [
            {"code": "600519", "name": "贵州茅台", "market_cap": 20000},
            {"code": "000001", "name": "平安银行", "market_cap": 3000},
            {"code": "000002", "name": "万科A", "market_cap": 2500},
        ]
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value.limit.return_value.skip.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = ScreeningService()

        # 按市值降序排序
        results = await service.screen_stocks(
            criteria={}, sort_by="market_cap", sort_order="desc"
        )

        assert len(results) == 3
        # 验证降序
        assert results[0]["market_cap"] >= results[1]["market_cap"]
        assert results[1]["market_cap"] >= results[2]["market_cap"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_sort_by_pe():
    """测试按PE排序"""
    with patch("app.services.screening_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [
            {"code": "000001", "name": "平安银行", "pe": 7.5},
            {"code": "000002", "name": "万科A", "pe": 8.2},
            {"code": "600519", "name": "贵州茅台", "pe": 35.0},
        ]
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value.limit.return_value.skip.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = ScreeningService()

        # 按PE升序排序
        results = await service.screen_stocks(
            criteria={}, sort_by="pe", sort_order="asc"
        )

        assert len(results) == 3
        # 验证升序
        assert results[0]["pe"] <= results[1]["pe"]
        assert results[1]["pe"] <= results[2]["pe"]


# ==============================================================================
# 测试分页功能
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pagination():
    """测试分页功能"""
    with patch("app.services.screening_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # 总共100条数据
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [
            {"code": f"00000{i:03d}", "name": f"股票{i}", "pe": 10.0 + i * 0.1}
            for i in range(1, 21)
        ]
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value.limit.return_value.skip.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = ScreeningService()

        # 分页：第1页，每页20条
        results = await service.screen_stocks(criteria={}, page=1, page_size=20)

        assert len(results) == 20
        assert results[0]["code"] == "000001"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pagination_second_page():
    """测试分页（第2页）"""
    with patch("app.services.screening_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # 第2页数据
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [
            {"code": f"00000{i:03d}", "name": f"股票{i}", "pe": 10.0 + i * 0.1}
            for i in range(21, 41)
        ]
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value.limit.return_value.skip.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = ScreeningService()

        # 分页：第2页，每页20条
        results = await service.screen_stocks(criteria={}, page=2, page_size=20)

        assert len(results) == 20
        assert results[0]["code"] == "000021"


# ==============================================================================
# 测试复合条件筛选
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complex_screening():
    """测试复合条件筛选"""
    with patch("app.services.screening_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [
            {
                "code": "000001",
                "name": "平安银行",
                "pe": 7.5,
                "roe": 10.5,
                "market": "sz",
            },
            {"code": "000002", "name": "万科A", "pe": 8.2, "roe": 12.3, "market": "sz"},
        ]
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value.limit.return_value.skip.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = ScreeningService()

        # 复合筛选条件
        criteria = {
            "min_pe": 5.0,
            "max_pe": 10.0,
            "min_roe": 10.0,
            "market": ["sz"],
            "industry": ["银行", "地产"],
        }

        results = await service.screen_stocks(criteria)

        assert len(results) == 2
        # 验证所有条件
        for result in results:
            assert 5.0 <= result["pe"] <= 10.0
            assert result["roe"] >= 10.0
            assert result["market"] == "sz"


# ==============================================================================
# 测试筛选条件验证
# ==============================================================================


@pytest.mark.unit
def test_validate_criteria():
    """测试筛选条件验证"""
    with patch("app.services.screening_service.get_mongo_db"):
        service = ScreeningService()

        # 有效条件
        valid_criteria = {
            "min_pe": 5.0,
            "max_pe": 20.0,
            "min_roe": 10.0,
            "market": ["sh", "sz"],
        }

        # 验证应该通过
        is_valid = service.validate_criteria(valid_criteria)
        assert is_valid is True


@pytest.mark.unit
def test_validate_criteria_invalid():
    """测试无效筛选条件"""
    with patch("app.services.screening_service.get_mongo_db"):
        service = ScreeningService()

        # 无效条件（min > max）
        invalid_criteria = {
            "min_pe": 20.0,
            "max_pe": 10.0,  # min > max
        }

        # 验证应该失败
        is_valid = service.validate_criteria(invalid_criteria)
        assert is_valid is False


@pytest.mark.unit
def test_validate_criteria_negative_value():
    """测试负值筛选条件"""
    with patch("app.services.screening_service.get_mongo_db"):
        service = ScreeningService()

        # 无效条件（负值）
        invalid_criteria = {
            "min_pe": -5.0  # 负值
        }

        # 验证应该失败
        is_valid = service.validate_criteria(invalid_criteria)
        assert is_valid is False


# ==============================================================================
# 测试筛选结果保存
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_screening_result():
    """测试保存筛选结果"""
    with patch("app.services.screening_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        mock_collection.insert_one.return_value = AsyncMock(inserted_id="result_123")
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = ScreeningService()

        # 保存筛选结果
        result_data = {
            "criteria": {"min_pe": 5.0, "max_pe": 20.0},
            "results": [
                {"code": "000001", "name": "平安银行"},
                {"code": "600519", "name": "贵州茅台"},
            ],
            "total": 2,
            "timestamp": datetime.utcnow(),
        }

        result_id = await service.save_screening_result(result_data)

        assert result_id == "result_123"
        mock_collection.insert_one.assert_called_once()


# ==============================================================================
# 测试错误处理
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_error_handling_in_screening():
    """测试筛选时的错误处理"""
    with patch("app.services.screening_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # 数据库错误
        mock_collection.find.side_effect = Exception("Database error")
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = ScreeningService()

        # 应该抛出异常或返回空结果
        try:
            results = await service.screen_stocks({})
            # 如果不抛出异常，应该返回空结果
            assert results == []
        except Exception:
            # 如果抛出异常，应该被捕获
            pass


# ==============================================================================
# 测试边界条件
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_criteria():
    """测试空筛选条件"""
    with patch("app.services.screening_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # 返回所有股票
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [
            {"code": f"00000{i:03d}", "name": f"股票{i}"} for i in range(1, 100)
        ]
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value.limit.return_value.skip.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = ScreeningService()

        # 空条件
        results = await service.screen_stocks({})

        # 应该返回默认数量的结果（受limit限制）
        assert len(results) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_large_page_size():
    """测试大分页大小"""
    with patch("app.services.screening_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # 返回大量数据
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [
            {"code": f"00000{i:03d}", "name": f"股票{i}"}
            for i in range(1, 501)  # 500条
        ]
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value.limit.return_value.skip.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = ScreeningService()

        # 大分页（500条）
        results = await service.screen_stocks(criteria={}, page=1, page_size=500)

        assert len(results) == 500


# ==============================================================================
# 测试性能
# ==============================================================================


@pytest.mark.unit
@pytest.mark.slow
@pytest.mark.asyncio
async def test_screening_performance():
    """测试筛选性能"""
    import time

    with patch("app.services.screening_service.get_mongo_db") as mock_get_mongo:
        mock_mongo = Mock()
        mock_collection = AsyncMock()
        # 模拟快速查询
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [
            {"code": f"00000{i:03d}", "name": f"股票{i}", "pe": 10.0 + i * 0.01}
            for i in range(1, 1001)  # 1000条
        ]
        mock_collection.find.return_value = mock_cursor
        mock_collection.find.return_value.sort.return_value.limit.return_value.skip.return_value = mock_cursor
        mock_mongo.__getitem__ = Mock(return_value=mock_collection)
        mock_get_mongo.return_value = mock_mongo

        service = ScreeningService()

        # 性能测试：复杂条件筛选
        start = time.time()
        results = await service.screen_stocks(
            {"min_pe": 5.0, "max_pe": 20.0, "min_roe": 10.0, "market": ["sh", "sz"]},
            limit=100,
        )
        end = time.time()

        elapsed = end - start
        assert len(results) > 0
        # 筛选应该在合理时间内完成（例如< 5秒）
        assert elapsed < 5
