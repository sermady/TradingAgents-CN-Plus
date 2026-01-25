# -*- coding: utf-8 -*-
"""
Favorites API 集成测试
测试收藏夹相关的所有 API 端点
"""

import pytest
from httpx import AsyncClient

from tests.conftest import pytest


# 测试标记
pytestmark = pytest.mark.integration


class TestFavoritesAPI:
    """收藏夹 API 测试"""

    @pytest.mark.asyncio
    async def test_add_favorite_success(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试添加收藏 - 成功场景"""
        response = await async_client.post(
            "/api/favorites",
            headers=test_user_headers,
            json={
                "stock_code": "600519",
                "market_type": "china",
                "note": "贵州茅台，白酒龙头",
            },
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data or "_id" in data
        assert data["stock_code"] == "600519"

    @pytest.mark.asyncio
    async def test_get_favorites_list(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试获取收藏列表"""
        response = await async_client.get(
            "/api/favorites",
            headers=test_user_headers,
            params={"page": 1, "page_size": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_get_favorite_by_id(
        self, async_client: AsyncClient, test_user_headers: dict, test_favorite_id: str
    ):
        """测试获取单个收藏"""
        response = await async_client.get(
            f"/api/favorites/{test_favorite_id}", headers=test_user_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_favorite_id or data.get("_id") == test_favorite_id

    @pytest.mark.asyncio
    async def test_update_favorite_note(
        self, async_client: AsyncClient, test_user_headers: dict, test_favorite_id: str
    ):
        """测试更新收藏备注"""
        response = await async_client.put(
            f"/api/favorites/{test_favorite_id}",
            headers=test_user_headers,
            json={"note": "更新后的备注信息"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["note"] == "更新后的备注信息"

    @pytest.mark.asyncio
    async def test_remove_favorite(
        self, async_client: AsyncClient, test_user_headers: dict, test_favorite_id: str
    ):
        """测试删除收藏"""
        response = await async_client.delete(
            f"/api/favorites/{test_favorite_id}", headers=test_user_headers
        )

        assert response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_check_is_favorite(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试检查是否收藏"""
        # 先添加收藏
        await async_client.post(
            "/api/favorites",
            headers=test_user_headers,
            json={"stock_code": "600519", "market_type": "china"},
        )

        # 检查是否收藏
        response = await async_client.get(
            "/api/favorites/check",
            headers=test_user_headers,
            params={"stock_code": "600519", "market_type": "china"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "is_favorite" in data
        assert data["is_favorite"] is True

    @pytest.mark.asyncio
    async def test_create_favorite_group(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试创建收藏分组"""
        response = await async_client.post(
            "/api/favorites/groups",
            headers=test_user_headers,
            json={"name": "核心持仓", "description": "重点关注的优质股票"},
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data or "_id" in data
        assert data["name"] == "核心持仓"

    @pytest.mark.asyncio
    async def test_get_favorite_groups(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试获取收藏分组列表"""
        response = await async_client.get(
            "/api/favorites/groups", headers=test_user_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_update_favorite_group(
        self,
        async_client: AsyncClient,
        test_user_headers: dict,
        test_favorite_group_id: str,
    ):
        """测试更新收藏分组"""
        response = await async_client.put(
            f"/api/favorites/groups/{test_favorite_group_id}",
            headers=test_user_headers,
            json={"name": "更新的分组名称", "description": "更新的描述"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_favorite_group(
        self,
        async_client: AsyncClient,
        test_user_headers: dict,
        test_favorite_group_id: str,
    ):
        """测试删除收藏分组"""
        response = await async_client.delete(
            f"/api/favorites/groups/{test_favorite_group_id}", headers=test_user_headers
        )

        assert response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_move_favorite_to_group(
        self,
        async_client: AsyncClient,
        test_user_headers: dict,
        test_favorite_id: str,
        test_favorite_group_id: str,
    ):
        """测试移动收藏到分组"""
        response = await async_client.put(
            f"/api/favorites/{test_favorite_id}/group",
            headers=test_user_headers,
            json={"group_id": test_favorite_group_id},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_favorites_by_group(
        self,
        async_client: AsyncClient,
        test_user_headers: dict,
        test_favorite_group_id: str,
    ):
        """测试获取分组的收藏列表"""
        response = await async_client.get(
            f"/api/favorites/groups/{test_favorite_group_id}/favorites",
            headers=test_user_headers,
            params={"page": 1, "page_size": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_batch_add_favorites(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试批量添加收藏"""
        response = await async_client.post(
            "/api/favorites/batch",
            headers=test_user_headers,
            json={
                "stocks": [
                    {"stock_code": "600519", "market_type": "china"},
                    {"stock_code": "000001", "market_type": "china"},
                    {"stock_code": "600036", "market_type": "china"},
                ]
            },
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert "added_count" in data
        assert data["added_count"] == 3

    @pytest.mark.asyncio
    async def test_batch_remove_favorites(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试批量删除收藏"""
        # 先添加收藏
        add_response = await async_client.post(
            "/api/favorites/batch",
            headers=test_user_headers,
            json={
                "stocks": [
                    {"stock_code": "600519", "market_type": "china"},
                    {"stock_code": "000001", "market_type": "china"},
                ]
            },
        )

        # 批量删除
        response = await async_client.post(
            "/api/favorites/batch/delete",
            headers=test_user_headers,
            json={
                "stocks": [
                    {"stock_code": "600519", "market_type": "china"},
                    {"stock_code": "000001", "market_type": "china"},
                ]
            },
        )

        assert response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_sort_favorites(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试收藏排序"""
        response = await async_client.put(
            "/api/favorites/sort",
            headers=test_user_headers,
            json={"sort_by": "added_at", "sort_order": "desc"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_favorites_with_stock_data(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试获取收藏列表（包含股票数据）"""
        response = await async_client.get(
            "/api/favorites",
            headers=test_user_headers,
            params={"include_stock_data": True, "page": 1, "page_size": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, async_client: AsyncClient):
        """测试未授权访问"""
        response = await async_client.post(
            "/api/favorites", json={"stock_code": "600519", "market_type": "china"}
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_duplicate_favorite(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试重复添加收藏"""
        # 第一次添加
        await async_client.post(
            "/api/favorites",
            headers=test_user_headers,
            json={"stock_code": "600519", "market_type": "china"},
        )

        # 第二次添加（应该失败或返回已存在）
        response = await async_client.post(
            "/api/favorites",
            headers=test_user_headers,
            json={"stock_code": "600519", "market_type": "china"},
        )

        assert response.status_code in [200, 201, 400, 409]

    @pytest.mark.asyncio
    async def test_favorite_not_found(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试获取不存在的收藏"""
        response = await async_client.get(
            "/api/favorites/nonexistent_id", headers=test_user_headers
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_export_favorites(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试导出收藏列表"""
        response = await async_client.get(
            "/api/favorites/export",
            headers=test_user_headers,
            params={"format": "xlsx"},
        )

        assert response.status_code in [200, 202]
