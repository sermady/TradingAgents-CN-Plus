# -*- coding: utf-8 -*-
"""
通用测试数据Fixtures
"""

import pytest
from typing import Dict, Any, List
from datetime import datetime, timedelta
import random
import string


@pytest.fixture
def random_string():
    """
    生成随机字符串
    """

    def _generate(length: int = 10) -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    return _generate


@pytest.fixture
def random_email(random_string):
    """
    生成随机邮箱地址
    """

    def _generate() -> str:
        return f"{random_string(8)}@example.com"

    return _generate


@pytest.fixture
def current_timestamp():
    """
    当前时间戳
    """
    return datetime.utcnow().isoformat() + "Z"


@pytest.fixture
def future_timestamp():
    """
    未来时间戳
    """

    def _generate(days: int = 7) -> str:
        future = datetime.utcnow() + timedelta(days=days)
        return future.isoformat() + "Z"

    return _generate


@pytest.fixture
def past_timestamp():
    """
    过去时间戳
    """

    def _generate(days: int = 7) -> str:
        past = datetime.utcnow() - timedelta(days=days)
        return past.isoformat() + "Z"

    return _generate


@pytest.fixture
def sample_user_data(random_string, random_email):
    """
    样本用户数据
    """
    return {
        "username": f"test_{random_string(6)}",
        "email": random_email(),
        "password": "Test123!",
        "full_name": "测试用户",
    }


@pytest.fixture
def sample_notification():
    """
    样本通知数据
    """
    return {
        "title": "测试通知",
        "message": "这是一条测试通知",
        "type": "info",
        "is_read": False,
    }


@pytest.fixture
def sample_operation_log():
    """
    样本操作日志
    """
    return {
        "action": "test_action",
        "resource_type": "stock",
        "resource_id": "000001",
        "details": {"test": "data"},
        "ip_address": "127.0.0.1",
        "user_agent": "test-agent",
    }


@pytest.fixture
def sample_config():
    """
    样本配置数据
    """
    return {
        "key": "test_config",
        "value": {"test": "value"},
        "description": "测试配置",
        "category": "test",
    }


@pytest.fixture
def sample_tag():
    """
    样本标签数据
    """
    return {"name": "测试标签", "color": "#FF0000", "description": "这是一个测试标签"}


@pytest.fixture
def sample_screening_criteria():
    """
    样本筛选条件
    """
    return {
        "name": "测试筛选",
        "criteria": {
            "market": ["sh", "sz"],
            "industry": ["银行", "科技"],
            "min_pe": 5.0,
            "max_pe": 20.0,
            "min_roe": 10.0,
            "min_price": 10.0,
            "max_price": 100.0,
        },
        "sort_by": "market_cap",
        "sort_order": "desc",
        "limit": 10,
    }


@pytest.fixture
def sample_batch_analysis_request():
    """
    样本批量分析请求
    """
    return {
        "stock_codes": ["000001", "600519", "000002"],
        "analysis_type": "comprehensive",
        "depth_level": 3,
        "enable_parallel": True,
    }


@pytest.fixture
def pagination_params():
    """
    分页参数fixture
    """

    def _generate_params(page: int = 1, page_size: int = 20):
        return {
            "page": page,
            "page_size": page_size,
            "offset": (page - 1) * page_size,
            "limit": page_size,
        }

    return _generate_params


@pytest.fixture
def mock_response_data():
    """
    Mock响应数据生成器
    """

    class MockResponseGenerator:
        @staticmethod
        def success(data: Any, message: str = "Success"):
            return {"success": True, "data": data, "message": message}

        @staticmethod
        def error(error_code: str, message: str, details: Any = None):
            return {
                "success": False,
                "error": {"code": error_code, "message": message, "details": details},
            }

        @staticmethod
        def paginated(items: List[Any], total: int, page: int = 1, page_size: int = 20):
            return {
                "success": True,
                "data": {
                    "items": items,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size,
                },
            }

    return MockResponseGenerator()
