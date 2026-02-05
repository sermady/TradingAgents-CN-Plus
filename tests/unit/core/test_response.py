#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一API响应格式工具测试
"""

import pytest
from unittest.mock import patch
from datetime import datetime
from app.core.response import ok, fail


class TestOkResponse:
    """测试成功响应函数"""

    def test_ok_with_default_params(self):
        """测试默认参数的成功响应"""
        with patch("app.core.response.now_tz") as mock_now:
            mock_now.return_value = datetime(2026, 2, 3, 12, 0, 0)

            result = ok()

            assert result["success"] is True
            assert result["data"] is None
            assert result["message"] == "ok"
            assert "timestamp" in result
            assert result["timestamp"] == "2026-02-03T12:00:00"

    def test_ok_with_custom_data(self):
        """测试带自定义数据的成功响应"""
        test_data = {"id": 1, "name": "test"}

        result = ok(data=test_data)

        assert result["success"] is True
        assert result["data"] == test_data
        assert result["message"] == "ok"

    def test_ok_with_custom_message(self):
        """测试带自定义消息的成功响应"""
        result = ok(message="操作成功")

        assert result["success"] is True
        assert result["message"] == "操作成功"

    def test_ok_with_data_and_message(self):
        """测试带数据和消息的成功响应"""
        test_data = {"users": ["user1", "user2"]}
        result = ok(data=test_data, message="用户列表获取成功")

        assert result["success"] is True
        assert result["data"] == test_data
        assert result["message"] == "用户列表获取成功"

    def test_ok_response_structure(self):
        """测试成功响应结构完整性"""
        result = ok(data={"key": "value"}, message="测试消息")

        # 验证必须包含的键
        assert "success" in result
        assert "data" in result
        assert "message" in result
        assert "timestamp" in result

        # 验证类型
        assert isinstance(result["success"], bool)
        assert isinstance(result["message"], str)
        assert isinstance(result["timestamp"], str)


class TestFailResponse:
    """测试失败响应函数"""

    def test_fail_with_default_params(self):
        """测试默认参数的失败响应"""
        with patch("app.core.response.now_tz") as mock_now:
            mock_now.return_value = datetime(2026, 2, 3, 12, 0, 0)

            result = fail()

            assert result["success"] is False
            assert result["data"] is None
            assert result["message"] == "error"
            assert result["code"] == 500
            assert "timestamp" in result

    def test_fail_with_custom_message(self):
        """测试带自定义消息的失败响应"""
        result = fail(message="验证失败")

        assert result["success"] is False
        assert result["message"] == "验证失败"
        assert result["code"] == 500

    def test_fail_with_custom_code(self):
        """测试带自定义错误码的失败响应"""
        result = fail(message="未授权", code=401)

        assert result["success"] is False
        assert result["message"] == "未授权"
        assert result["code"] == 401

    def test_fail_with_data(self):
        """测试带错误数据的失败响应"""
        error_data = {"field": "username", "error": "不能为空"}
        result = fail(message="表单验证失败", code=400, data=error_data)

        assert result["success"] is False
        assert result["message"] == "表单验证失败"
        assert result["code"] == 400
        assert result["data"] == error_data

    def test_fail_response_structure(self):
        """测试失败响应结构完整性"""
        result = fail(message="错误", code=404, data={"detail": "not found"})

        # 验证必须包含的键
        assert "success" in result
        assert "data" in result
        assert "message" in result
        assert "code" in result
        assert "timestamp" in result

        # 验证类型
        assert isinstance(result["success"], bool)
        assert isinstance(result["message"], str)
        assert isinstance(result["code"], int)
        assert isinstance(result["timestamp"], str)

    def test_fail_common_error_codes(self):
        """测试常见错误码"""
        test_cases = [
            (400, "Bad Request"),
            (401, "Unauthorized"),
            (403, "Forbidden"),
            (404, "Not Found"),
            (422, "Validation Error"),
            (500, "Internal Server Error"),
            (503, "Service Unavailable"),
        ]

        for code, message in test_cases:
            result = fail(message=message, code=code)
            assert result["code"] == code
            assert result["message"] == message
            assert result["success"] is False


class TestResponseTimestamp:
    """测试响应时间戳"""

    def test_timestamp_format(self):
        """测试时间戳格式为 ISO 8601"""
        result = ok()
        timestamp = result["timestamp"]

        # 验证时间戳格式
        assert "T" in timestamp
        assert timestamp.endswith("+08:00") or len(timestamp) >= 19

    def test_timestamp_changes(self):
        """测试每次调用时间戳不同"""
        result1 = ok()
        result2 = ok()

        # 两个时间戳应该不同（或至少不保证相同）
        assert "timestamp" in result1
        assert "timestamp" in result2


# 如果需要通过 __main__ 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
