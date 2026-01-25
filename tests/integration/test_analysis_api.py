# -*- coding: utf-8 -*-
"""
Analysis API 集成测试
测试分析相关的所有 API 端点
"""

import pytest
import asyncio
from datetime import datetime
from httpx import AsyncClient

from tests.conftest import pytest


# 测试标记
pytestmark = pytest.mark.integration


class TestAnalysisAPI:
    """分析 API 测试"""

    @pytest.mark.asyncio
    async def test_single_stock_analysis_success(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试单股分析 - 成功场景"""
        response = await async_client.post(
            "/api/analysis/analyze",
            headers=test_user_headers,
            json={"stock_code": "600519", "market_type": "china", "analysis_depth": 2},
        )

        # 检查响应
        assert response.status_code == 202  # Accepted - 异步任务
        data = response.json()
        assert "task_id" in data
        assert data["status"] in ["pending", "running", "completed"]

    @pytest.mark.asyncio
    async def test_batch_analysis_success(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试批量分析 - 成功场景"""
        response = await async_client.post(
            "/api/analysis/batch",
            headers=test_user_headers,
            json={
                "stock_codes": ["600519", "000001", "600036"],
                "market_type": "china",
                "analysis_depth": 1,
            },
        )

        # 检查响应
        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert data["total_stocks"] == 3

    @pytest.mark.asyncio
    async def test_analysis_depth_validation(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试分析深度验证"""
        # 测试无效的深度
        response = await async_client.post(
            "/api/analysis/analyze",
            headers=test_user_headers,
            json={
                "stock_code": "600519",
                "market_type": "china",
                "analysis_depth": 10,  # 无效深度
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_analysis_result_not_found(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试获取分析结果 - 不存在"""
        response = await async_client.get(
            "/api/analysis/result/nonexistent_id", headers=test_user_headers
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_analysis_history(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试获取分析历史"""
        response = await async_client.get(
            "/api/analysis/history",
            headers=test_user_headers,
            params={"page": 1, "page_size": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_get_analysis_history_with_filters(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试获取分析历史 - 带筛选条件"""
        response = await async_client.get(
            "/api/analysis/history",
            headers=test_user_headers,
            params={
                "market_type": "china",
                "analysis_depth": 2,
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "page": 1,
                "page_size": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_cancel_analysis_task(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试取消分析任务"""
        # 先创建一个任务
        create_response = await async_client.post(
            "/api/analysis/analyze",
            headers=test_user_headers,
            json={
                "stock_code": "600519",
                "market_type": "china",
                "analysis_depth": 5,  # 深度分析，耗时较长
            },
        )
        assert create_response.status_code == 202
        task_id = create_response.json()["task_id"]

        # 取消任务
        cancel_response = await async_client.post(
            f"/api/analysis/cancel/{task_id}", headers=test_user_headers
        )

        # 检查取消结果
        assert cancel_response.status_code in [
            200,
            404,
        ]  # 404 if task already completed

    @pytest.mark.asyncio
    async def test_delete_analysis_result(
        self,
        async_client: AsyncClient,
        test_user_headers: dict,
        test_analysis_result_id: str,
    ):
        """测试删除分析结果"""
        response = await async_client.delete(
            f"/api/analysis/result/{test_analysis_result_id}", headers=test_user_headers
        )

        assert response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_export_analysis_result(
        self,
        async_client: AsyncClient,
        test_user_headers: dict,
        test_analysis_result_id: str,
    ):
        """测试导出分析结果"""
        response = await async_client.get(
            f"/api/analysis/result/{test_analysis_result_id}/export",
            headers=test_user_headers,
            params={"format": "pdf"},
        )

        # 可能返回 200 (已生成) 或 202 (正在生成)
        assert response.status_code in [200, 202]

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, async_client: AsyncClient):
        """测试未授权访问"""
        response = await async_client.post(
            "/api/analysis/analyze",
            json={"stock_code": "600519", "market_type": "china"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_stock_code(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试无效股票代码"""
        response = await async_client.post(
            "/api/analysis/analyze",
            headers=test_user_headers,
            json={"stock_code": "INVALID_CODE", "market_type": "china"},
        )

        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_invalid_market_type(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试无效市场类型"""
        response = await async_client.post(
            "/api/analysis/analyze",
            headers=test_user_headers,
            json={"stock_code": "600519", "market_type": "invalid_market"},
        )

        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_analysis_progress(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试分析进度查询"""
        # 先创建一个任务
        create_response = await async_client.post(
            "/api/analysis/analyze",
            headers=test_user_headers,
            json={"stock_code": "600519", "market_type": "china", "analysis_depth": 3},
        )
        assert create_response.status_code == 202
        task_id = create_response.json()["task_id"]

        # 查询进度
        progress_response = await async_client.get(
            f"/api/analysis/progress/{task_id}", headers=test_user_headers
        )

        assert progress_response.status_code == 200
        data = progress_response.json()
        assert "progress" in data
        assert "current_step" in data

    @pytest.mark.asyncio
    async def test_custom_analysis_parameters(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试自定义分析参数"""
        response = await async_client.post(
            "/api/analysis/analyze",
            headers=test_user_headers,
            json={
                "stock_code": "600519",
                "market_type": "china",
                "analysis_depth": 2,
                "enable_news_analysis": True,
                "enable_social_media_analysis": False,
                "enable_fundamentals_analysis": True,
                "custom_prompt": "重点关注白酒行业趋势",
            },
        )

        assert response.status_code == 202

    @pytest.mark.asyncio
    async def test_comparison_analysis(
        self, async_client: AsyncClient, test_user_headers: dict
    ):
        """测试对比分析"""
        response = await async_client.post(
            "/api/analysis/compare",
            headers=test_user_headers,
            json={
                "stock_codes": ["600519", "000858"],
                "market_type": "china",
                "analysis_depth": 1,
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
