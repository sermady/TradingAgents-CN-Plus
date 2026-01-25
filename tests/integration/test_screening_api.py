# -*- coding: utf-8 -*-
"""
Screening API 集成测试
测试股票筛选相关的所有 API 端点
"""

import pytest
from httpx import AsyncClient

from tests.conftest import pytest


# 测试标记
pytestmark = pytest.mark.integration


class TestScreeningAPI:
    """筛选 API 测试"""

    @pytest.mark.asyncio
    async def test_basic_screening_success(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试基础筛选 - 成功场景"""
        response = await async_client.post(
            "/api/screening/screen",
            headers=test_user_headers,
            json={
                "market_type": "china",
                "criteria": {"pe_ratio": {"min": 0, "max": 30}},
                "sort_by": "pe_ratio",
                "sort_order": "asc",
                "page": 1,
                "page_size": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_advanced_screening_with_multiple_criteria(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试高级筛选 - 多条件"""
        response = await async_client.post(
            "/api/screening/screen",
            headers=test_user_headers,
            json={
                "market_type": "china",
                "criteria": {
                    "pe_ratio": {"min": 0, "max": 30},
                    "roe": {"min": 10},
                    "market_cap": {"min": 10000000000},  # 100亿以上
                },
                "sort_by": "roe",
                "sort_order": "desc",
                "page": 1,
                "page_size": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_screening_by_industry(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试按行业筛选"""
        response = await async_client.post(
            "/api/screening/screen",
            headers=test_user_headers,
            json={
                "market_type": "china",
                "criteria": {"industry": ["白酒", "医药"]},
                "page": 1,
                "page_size": 20,
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_screening_pagination(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试分页功能"""
        # 第一页
        response1 = await async_client.post(
            "/api/screening/screen",
            headers=test_user_headers,
            json={"market_type": "china", "page": 1, "page_size": 5},
        )

        assert response1.status_code == 200
        data1 = response1.json()

        # 第二页
        response2 = await async_client.post(
            "/api/screening/screen",
            headers=test_user_headers,
            json={"market_type": "china", "page": 2, "page_size": 5},
        )

        assert response2.status_code == 200
        data2 = response2.json()

        # 确保分页数据不同
        if data1["items"] and data2["items"]:
            assert data1["items"][0]["stock_code"] != data2["items"][0]["stock_code"]

    @pytest.mark.asyncio
    async def test_screening_sorting(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试排序功能"""
        # 升序
        response_asc = await async_client.post(
            "/api/screening/screen",
            headers=test_user_headers,
            json={
                "market_type": "china",
                "criteria": {"pe_ratio": {"min": 0, "max": 100}},
                "sort_by": "pe_ratio",
                "sort_order": "asc",
                "page": 1,
                "page_size": 5,
            },
        )

        assert response_asc.status_code == 200
        data_asc = response_asc.json()

        # 降序
        response_desc = await async_client.post(
            "/api/screening/screen",
            headers=test_user_headers,
            json={
                "market_type": "china",
                "criteria": {"pe_ratio": {"min": 0, "max": 100}},
                "sort_by": "pe_ratio",
                "sort_order": "desc",
                "page": 1,
                "page_size": 5,
            },
        )

        assert response_desc.status_code == 200
        data_desc = response_desc.json()

        # 验证排序结果相反
        if data_asc["items"] and data_desc["items"]:
            asc_first = data_asc["items"][0]["pe_ratio"]
            desc_first = data_desc["items"][0]["pe_ratio"]
            assert asc_first <= desc_first

    @pytest.mark.asyncio
    async def test_save_screening_preset(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试保存筛选预设"""
        response = await async_client.post(
            "/api/screening/presets",
            headers=test_user_headers,
            json={
                "name": "低估值优质股",
                "market_type": "china",
                "criteria": {
                    "pe_ratio": {"min": 0, "max": 15},
                    "roe": {"min": 15},
                    "debt_ratio": {"max": 60},
                },
                "sort_by": "pe_ratio",
                "sort_order": "asc",
            },
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data or "_id" in data
        assert data["name"] == "低估值优质股"

    @pytest.mark.asyncio
    async def test_get_screening_presets(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试获取筛选预设列表"""
        response = await async_client.get(
            "/api/screening/presets", headers=test_user_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_screening_preset_by_id(
        self,
        async_client: AsyncClient,
        test_user_headers: dict,
        test_screening_preset_id: str,
    ):
        """测试获取单个筛选预设"""
        response = await async_client.get(
            f"/api/screening/presets/{test_screening_preset_id}",
            headers=test_user_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert (
            data["id"] == test_screening_preset_id
            or data.get("_id") == test_screening_preset_id
        )

    @pytest.mark.asyncio
    async def test_update_screening_preset(
        self,
        async_client: AsyncClient,
        test_user_headers: dict,
        test_screening_preset_id: str,
    ):
        """测试更新筛选预设"""
        response = await async_client.put(
            f"/api/screening/presets/{test_screening_preset_id}",
            headers=test_user_headers,
            json={
                "name": "更新后的预设",
                "criteria": {"pe_ratio": {"min": 0, "max": 20}},
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_screening_preset(
        self,
        async_client: AsyncClient,
        test_user_headers: dict,
        test_screening_preset_id: str,
    ):
        """测试删除筛选预设"""
        response = await async_client.delete(
            f"/api/screening/presets/{test_screening_preset_id}",
            headers=test_user_headers,
        )

        assert response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_screening_with_preset(
        self,
        async_client: AsyncClient,
        test_user_headers: dict,
        test_screening_preset_id: str,
    ):
        """测试使用预设进行筛选"""
        response = await async_client.post(
            f"/api/screening/presets/{test_screening_preset_id}/screen",
            headers=test_user_headers,
            json={"page": 1, "page_size": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, async_client: AsyncClient):
        """测试未授权访问"""
        response = await async_client.post(
            "/api/screening/screen",
            json={"market_type": "china", "page": 1, "page_size": 10},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_market_type(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试无效市场类型"""
        response = await async_client.post(
            "/api/screening/screen",
            headers=test_user_headers,
            json={"market_type": "invalid_market", "page": 1, "page_size": 10},
        )

        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_invalid_criteria(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试无效筛选条件"""
        response = await async_client.post(
            "/api/screening/screen",
            headers=test_user_headers,
            json={
                "market_type": "china",
                "criteria": {"invalid_field": {"min": 0}},
                "page": 1,
                "page_size": 10,
            },
        )

        # API 应该忽略无效字段或返回 400
        assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_export_screening_results(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试导出筛选结果"""
        # 先执行筛选
        screen_response = await async_client.post(
            "/api/screening/screen",
            headers=test_user_headers,
            json={
                "market_type": "china",
                "criteria": {"pe_ratio": {"min": 0, "max": 30}},
                "page": 1,
                "page_size": 100,
            },
        )

        assert screen_response.status_code == 200

        # 导出结果
        export_response = await async_client.post(
            "/api/screening/export",
            headers=test_user_headers,
            json={
                "criteria": {"pe_ratio": {"min": 0, "max": 30}},
                "format": "xlsx",
                "market_type": "china",
            },
        )

        assert export_response.status_code in [200, 202]

    @pytest.mark.asyncio
    async def test_screening_statistics(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试筛选统计信息"""
        response = await async_client.post(
            "/api/screening/statistics",
            headers=test_user_headers,
            json={"market_type": "china"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_stocks" in data
        assert "market_distribution" in data
