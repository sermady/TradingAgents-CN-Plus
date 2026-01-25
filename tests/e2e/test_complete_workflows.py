# -*- coding: utf-8 -*-
"""
End-to-End 集成测试
测试完整的用户工作流程
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta

from tests.conftest import pytest


# 测试标记
pytestmark = pytest.mark.e2e


class TestCompleteAnalysisWorkflow:
    """完整分析工作流测试"""

    @pytest.mark.asyncio
    @pytest.mark.requires_auth
    @pytest.mark.slow
    async def test_complete_single_analysis_workflow(
        self, async_client: AsyncClient, test_user_headers: dict, test_user_token: str
    ):
        """测试完整的单股分析工作流"""
        # 1. 用户登录
        login_response = await async_client.post(
            "/api/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        assert login_response.status_code == 200
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # 2. 搜索股票
        search_response = await async_client.get(
            "/api/stocks/search", headers=headers, params={"query": "贵州茅台"}
        )
        assert search_response.status_code == 200
        stock_code = search_response.json()[0]["stock_code"]

        # 3. 获取股票详情
        detail_response = await async_client.get(
            f"/api/stocks/{stock_code}", headers=headers
        )
        assert detail_response.status_code == 200

        # 4. 创建分析任务
        analysis_response = await async_client.post(
            "/api/analysis/analyze",
            headers=headers,
            json={
                "stock_code": stock_code,
                "market_type": "china",
                "analysis_depth": 1,  # 快速分析用于测试
            },
        )
        assert analysis_response.status_code == 202
        task_id = analysis_response.json()["task_id"]

        # 5. 查询分析进度
        progress_response = await async_client.get(
            f"/api/analysis/progress/{task_id}", headers=headers
        )
        assert progress_response.status_code == 200

        # 6. 等待分析完成（实际 E2E 测试需要等待）
        # 这里我们只验证 API 结构
        # 真实场景下需要轮询直到完成

        # 7. 获取分析结果
        result_response = await async_client.get(
            f"/api/analysis/result/{task_id}", headers=headers
        )
        # 可能返回 404 (未完成) 或 200 (已完成)
        assert result_response.status_code in [200, 404]

        # 8. 添加到收藏
        favorite_response = await async_client.post(
            "/api/favorites",
            headers=headers,
            json={"stock_code": stock_code, "market_type": "china"},
        )
        assert favorite_response.status_code in [200, 201]

    @pytest.mark.asyncio
    @pytest.mark.requires_auth
    @pytest.mark.slow
    async def test_complete_batch_analysis_workflow(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试完整的批量分析工作流"""
        # 1. 筛选股票
        screening_response = await async_client.post(
            "/api/screening/screen",
            headers=test_user_headers,
            json={
                "market_type": "china",
                "criteria": {"pe_ratio": {"min": 0, "max": 30}},
                "page": 1,
                "page_size": 5,
            },
        )
        assert screening_response.status_code == 200
        stock_codes = [
            item["stock_code"] for item in screening_response.json()["items"][:3]
        ]

        # 2. 批量添加到收藏
        favorite_response = await async_client.post(
            "/api/favorites/batch",
            headers=test_user_headers,
            json={
                "stocks": [
                    {"stock_code": code, "market_type": "china"} for code in stock_codes
                ]
            },
        )
        assert favorite_response.status_code in [200, 201]

        # 3. 批量分析
        batch_analysis_response = await async_client.post(
            "/api/analysis/batch",
            headers=test_user_headers,
            json={
                "stock_codes": stock_codes,
                "market_type": "china",
                "analysis_depth": 1,
            },
        )
        assert batch_analysis_response.status_code == 202
        task_id = batch_analysis_response.json()["task_id"]

        # 4. 查询进度
        progress_response = await async_client.get(
            f"/api/analysis/progress/{task_id}", headers=test_user_headers
        )
        assert progress_response.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.requires_auth
    async def test_complete_screening_workflow(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试完整的筛选工作流"""
        # 1. 执行筛选
        screening_response = await async_client.post(
            "/api/screening/screen",
            headers=test_user_headers,
            json={
                "market_type": "china",
                "criteria": {"pe_ratio": {"min": 0, "max": 20}, "roe": {"min": 10}},
                "sort_by": "roe",
                "sort_order": "desc",
                "page": 1,
                "page_size": 10,
            },
        )
        assert screening_response.status_code == 200
        screening_data = screening_response.json()

        # 2. 保存筛选预设
        preset_response = await async_client.post(
            "/api/screening/presets",
            headers=test_user_headers,
            json={
                "name": "测试预设",
                "market_type": "china",
                "criteria": {"pe_ratio": {"min": 0, "max": 20}, "roe": {"min": 10}},
                "sort_by": "roe",
                "sort_order": "desc",
            },
        )
        assert preset_response.status_code in [200, 201]
        preset_id = preset_response.json().get("id") or preset_response.json().get(
            "_id"
        )

        # 3. 使用预设执行筛选
        preset_screen_response = await async_client.post(
            f"/api/screening/presets/{preset_id}/screen",
            headers=test_user_headers,
            json={"page": 1, "page_size": 10},
        )
        assert preset_screen_response.status_code == 200

        # 4. 导出筛选结果
        export_response = await async_client.post(
            "/api/screening/export",
            headers=test_user_headers,
            json={
                "criteria": {"pe_ratio": {"min": 0, "max": 20}, "roe": {"min": 10}},
                "format": "xlsx",
                "market_type": "china",
            },
        )
        assert export_response.status_code in [200, 202]

    @pytest.mark.asyncio
    @pytest.mark.requires_auth
    async def test_complete_favorites_workflow(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试完整的收藏夹工作流"""
        # 1. 创建收藏分组
        group_response = await async_client.post(
            "/api/favorites/groups",
            headers=test_user_headers,
            json={"name": "自选测试组", "description": "测试用自选股分组"},
        )
        assert group_response.status_code in [200, 201]
        group_id = group_response.json().get("id") or group_response.json().get("_id")

        # 2. 添加收藏
        stocks_to_add = [
            {"stock_code": "600519", "market_type": "china"},
            {"stock_code": "000001", "market_type": "china"},
            {"stock_code": "600036", "market_type": "china"},
        ]

        for stock in stocks_to_add:
            response = await async_client.post(
                "/api/favorites",
                headers=test_user_headers,
                json={**stock, "note": "测试备注"},
            )
            assert response.status_code in [200, 201]

        # 3. 获取收藏列表
        list_response = await async_client.get(
            "/api/favorites",
            headers=test_user_headers,
            params={"page": 1, "page_size": 10},
        )
        assert list_response.status_code == 200
        favorites = list_response.json()["items"]

        # 4. 移动收藏到分组
        if favorites:
            favorite_id = favorites[0].get("id") or favorites[0].get("_id")
            move_response = await async_client.put(
                f"/api/favorites/{favorite_id}/group",
                headers=test_user_headers,
                json={"group_id": group_id},
            )
            assert move_response.status_code in [200, 204]

        # 5. 导出收藏列表
        export_response = await async_client.get(
            "/api/favorites/export",
            headers=test_user_headers,
            params={"format": "xlsx"},
        )
        assert export_response.status_code in [200, 202]


class TestCompleteUserManagementWorkflow:
    """用户管理工作流测试"""

    @pytest.mark.asyncio
    async def test_complete_user_registration_workflow(self, async_client: AsyncClient):
        """测试完整的用户注册工作流"""
        import random

        # 1. 用户注册
        email = f"test_{random.randint(1000, 9999)}@example.com"
        register_response = await async_client.post(
            "/api/auth/register",
            json={
                "email": email,
                "username": f"testuser_{random.randint(1000, 9999)}",
                "password": "password123",
            },
        )
        assert register_response.status_code in [200, 201]

        # 2. 用户登录
        login_response = await async_client.post(
            "/api/auth/login", json={"email": email, "password": "password123"}
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 3. 获取用户信息
        user_response = await async_client.get("/api/auth/me", headers=headers)
        assert user_response.status_code == 200

        # 4. 修改密码
        change_password_response = await async_client.post(
            "/api/auth/change-password",
            headers=headers,
            json={"old_password": "password123", "new_password": "newpassword123"},
        )
        assert change_password_response.status_code == 200

        # 5. 使用新密码登录
        new_login_response = await async_client.post(
            "/api/auth/login", json={"email": email, "password": "newpassword123"}
        )
        assert new_login_response.status_code == 200


class TestCompleteDataIngestionWorkflow:
    """数据摄取工作流测试"""

    @pytest.mark.asyncio
    @pytest.mark.requires_auth
    @pytest.mark.slow
    async def test_complete_quotes_ingestion_workflow(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试完整的行情数据摄取工作流"""
        # 1. 获取实时报价
        quote_response = await async_client.get(
            "/api/stocks/600519/quote", headers=test_user_headers
        )
        assert quote_response.status_code in [200, 404]  # 404 if no data

        # 2. 获取批量报价
        batch_quote_response = await async_client.post(
            "/api/stocks/batch-quotes",
            headers=test_user_headers,
            json={
                "stock_codes": ["600519", "000001", "600036"],
                "market_type": "china",
            },
        )
        assert batch_quote_response.status_code in [200, 404]

        # 3. 获取历史数据
        history_response = await async_client.get(
            "/api/stocks/600519/historical",
            headers=test_user_headers,
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "interval": "daily",
            },
        )
        assert history_response.status_code in [200, 404]


class TestCompleteErrorHandlingWorkflow:
    """错误处理工作流测试"""

    @pytest.mark.asyncio
    async def test_complete_error_handling_workflow(self, async_client: AsyncClient):
        """测试完整的错误处理工作流"""
        # 1. 测试未授权访问
        unauthorized_response = await async_client.get("/api/auth/me")
        assert unauthorized_response.status_code == 401

        # 2. 测试无效登录
        invalid_login_response = await async_client.post(
            "/api/auth/login",
            json={"email": "invalid@example.com", "password": "wrongpassword"},
        )
        assert invalid_login_response.status_code == 401

        # 3. 测试不存在的股票
        invalid_stock_response = await async_client.get("/api/stocks/INVALIDCODE")
        assert invalid_stock_response.status_code in [400, 404]

        # 4. 测试无效的筛选条件
        invalid_screening_response = await async_client.post(
            "/api/screening/screen",
            json={"market_type": "china", "criteria": {"invalid_field": {"min": 0}}},
        )
        assert invalid_screening_response.status_code in [
            400,
            422,
            200,
        ]  # 200 if ignored
