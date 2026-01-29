# -*- coding: utf-8 -*-
"""
筛选功能 API 集成测试
"""

import pytest
import requests
import os
from dotenv import load_dotenv


load_dotenv()


def get_auth_headers():
    """获取认证请求头"""
    base_url = os.getenv("TEST_API_URL", "http://localhost:8000")

    try:
        login_response = requests.post(
            f"{base_url}/api/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=10,
        )

        if login_response.status_code == 200:
            token = login_response.json()["data"]["access_token"]
            return {"Authorization": f"Bearer {token}"}
    except Exception:
        pass
    return None


@pytest.fixture
def auth_headers():
    """获取认证请求头的 fixture"""
    headers = get_auth_headers()
    if headers is None:
        pytest.skip("认证失败，跳过API测试")
    return headers


@pytest.mark.integration
@pytest.mark.requires_auth
@pytest.mark.requires_db
class TestScreeningAPI:
    """筛选功能 API 集成测试"""

    def test_run_screening_basic(self, auth_headers):
        """测试基本筛选功能"""
        base_url = os.getenv("TEST_API_URL", "http://localhost:8000")

        screening_request = {
            "market": "CN",
            "conditions": {
                "logic": "AND",
                "children": [
                    {
                        "field": "market_cap",
                        "op": "between",
                        "value": [1000000, 50000000],
                    }
                ],
            },
            "order_by": [{"field": "market_cap", "direction": "desc"}],
            "limit": 10,
            "offset": 0,
        }

        response = requests.post(
            f"{base_url}/api/screening/run",
            json=screening_request,
            headers=auth_headers,
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert len(data["items"]) <= 10

    def test_run_screening_with_complex_conditions(self, auth_headers):
        """测试复杂筛选条件"""
        base_url = os.getenv("TEST_API_URL", "http://localhost:8000")

        complex_request = {
            "market": "CN",
            "conditions": {
                "logic": "AND",
                "children": [
                    {
                        "field": "market_cap",
                        "op": "between",
                        "value": [500000, 20000000],
                    }
                ],
            },
            "order_by": [{"field": "market_cap", "direction": "desc"}],
            "limit": 15,
            "offset": 0,
        }

        response = requests.post(
            f"{base_url}/api/screening/run",
            json=complex_request,
            headers=auth_headers,
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
