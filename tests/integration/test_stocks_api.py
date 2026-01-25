# -*- coding: utf-8 -*-
"""
测试股票数据API

测试范围:
- GET /api/stocks/search - 股票搜索
- GET /api/stocks/{symbol} - 获取股票详情
- GET /api/stocks/{symbol}/quote - 获取实时行情
- GET /api/stocks/{symbol}/history - 获取历史数据
"""

import pytest
from httpx import AsyncClient
from typing import Dict


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_stocks(test_client: AsyncClient):
    """测试股票搜索"""
    # Act
    response = await test_client.get("/api/stocks/search?query=AAPL")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "data" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_stocks_china(test_client: AsyncClient):
    """测试中国股票搜索"""
    # Act
    response = await test_client.get("/api/stocks/search?query=000001")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "data" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_stocks_empty_query(test_client: AsyncClient):
    """测试空查询字符串"""
    # Act
    response = await test_client.get("/api/stocks/search?query=")

    # Assert
    # 空查询应该返回200，但可能为空结果
    assert response.status_code == 200
    data = response.json()
    assert "success" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_stock_details(test_client: AsyncClient):
    """测试获取股票详情"""
    # Act
    response = await test_client.get("/api/stocks/AAPL")

    # Assert
    # 可能成功或失败（取决于股票是否存在）
    assert response.status_code in [200, 404]

    if response.status_code == 200:
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert "symbol" in data["data"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_stock_details_china(test_client: AsyncClient):
    """测试获取中国股票详情"""
    # Act
    response = await test_client.get("/api/stocks/000001")

    # Assert
    assert response.status_code in [200, 404]

    if response.status_code == 200:
        data = response.json()
        assert "success" in data
        assert "data" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_realtime_quote(test_client: AsyncClient):
    """测试获取实时行情"""
    # Act
    response = await test_client.get("/api/stocks/AAPL/quote")

    # Assert
    # 可能成功或失败（取决于行情服务）
    assert response.status_code in [200, 404, 500]

    if response.status_code == 200:
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert "symbol" in data["data"] or "price" in data["data"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_historical_data(test_client: AsyncClient):
    """测试获取历史数据"""
    # Act
    response = await test_client.get("/api/stocks/AAPL/history?period=1M")

    # Assert
    # 可能成功或失败（取决于数据源）
    assert response.status_code in [200, 400, 404, 500]

    if response.status_code == 200:
        data = response.json()
        assert "success" in data
        assert "data" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_historical_data_with_dates(test_client: AsyncClient):
    """测试使用日期范围获取历史数据"""
    # Act
    response = await test_client.get(
        "/api/stocks/AAPL/history?start_date=2024-01-01&end_date=2024-12-31"
    )

    # Assert
    # 可能成功或失败
    assert response.status_code in [200, 400, 404, 500]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_historical_data_invalid_period(test_client: AsyncClient):
    """测试无效的时间周期"""
    # Act
    response = await test_client.get("/api/stocks/AAPL/history?period=invalid")

    # Assert
    # 应该返回400或422
    assert response.status_code in [400, 422]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_historical_data_china_stock(test_client: AsyncClient):
    """测试获取中国股票历史数据"""
    # Act
    response = await test_client.get("/api/stocks/000001/history?period=1M")

    # Assert
    # 可能成功或失败（取决于数据源）
    assert response.status_code in [200, 400, 404, 500]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_stock_search_pagination(test_client: AsyncClient):
    """测试股票搜索分页"""
    # Act
    response = await test_client.get("/api/stocks/search?query=A&page=1&limit=10")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "success" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_stock_search_by_market(test_client: AsyncClient):
    """测试按市场搜索股票"""
    # Act
    response = await test_client.get("/api/stocks/search?market=US")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "success" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_response_structure(test_client: AsyncClient):
    """测试API响应结构一致性"""
    # Arrange
    endpoints = [
        "/api/stocks/search?query=AAPL",
        "/api/stocks/AAPL",
        "/api/stocks/AAPL/quote",
        "/api/stocks/AAPL/history?period=1M",
        "/api/health",
    ]

    # Act & Assert
    for endpoint in endpoints:
        response = await test_client.get(endpoint)
        assert response.status_code in [200, 404, 500], (
            f"端点 {endpoint} 返回意外状态码: {response.status_code}"
        )

        data = response.json()
        # 验证所有响应都有success字段
        assert "success" in data, f"端点 {endpoint} 响应缺少success字段"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_stock_details_not_found(test_client: AsyncClient):
    """测试获取不存在的股票"""
    # Arrange
    invalid_symbol = "INVALID_SYMBOL_12345"

    # Act
    response = await test_client.get(f"/api/stocks/{invalid_symbol}")

    # Assert
    # 应该返回404或400
    assert response.status_code in [400, 404]
    data = response.json()
    assert data.get("success", True) is False
