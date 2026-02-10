# -*- coding: utf-8 -*-
"""
测试营收/净利润同比增速字段完整性

验证从原始数据获取到最终展示的完整数据流
"""

import pytest
from dataclasses import fields
from tradingagents.dataflows.schemas.stock_basic_schema import StockBasicData

# 标记所有测试为unit类型
pytestmark = [
    pytest.mark.unit,
    pytest.mark.dataflow,
]


class TestYoyFieldsExistence:
    """测试同比增速字段是否存在于 StockBasicData 中"""

    def test_or_yoy_field_exists(self):
        """测试营业收入同比增长率字段存在"""
        field_names = [f.name for f in fields(StockBasicData)]
        assert "or_yoy" in field_names, "StockBasicData 缺少 or_yoy 字段"

    def test_q_profit_yoy_field_exists(self):
        """测试净利润同比增长率字段存在"""
        field_names = [f.name for f in fields(StockBasicData)]
        assert "q_profit_yoy" in field_names, "StockBasicData 缺少 q_profit_yoy 字段"

    def test_eps_yoy_field_exists(self):
        """测试每股收益同比增长率字段存在"""
        field_names = [f.name for f in fields(StockBasicData)]
        assert "eps_yoy" in field_names, "StockBasicData 缺少 eps_yoy 字段"

    def test_roe_yoy_field_exists(self):
        """测试净资产收益率同比增长率字段存在"""
        field_names = [f.name for f in fields(StockBasicData)]
        assert "roe_yoy" in field_names, "StockBasicData 缺少 roe_yoy 字段"


class TestYoyDataFlow:
    """测试同比增速数据流完整性"""

    def test_create_unified_preserves_yoy_fields(self):
        """测试 create_unified 方法保留同比增速字段"""
        raw_data = {
            "code": "600000",
            "name": "浦发银行",
            "or_yoy": 15.5,  # 营业收入同比增长率
            "q_profit_yoy": 20.3,  # 净利润同比增长率
            "eps_yoy": 10.2,  # 每股收益同比增长率
            "roe_yoy": 5.8,  # 净资产收益率同比增长率
        }

        result = StockBasicData.create_unified(raw_data, "tushare")

        assert result.or_yoy == 15.5, f"or_yoy 字段值错误: {result.or_yoy}"
        assert result.q_profit_yoy == 20.3, f"q_profit_yoy 字段值错误: {result.q_profit_yoy}"
        assert result.eps_yoy == 10.2, f"eps_yoy 字段值错误: {result.eps_yoy}"
        assert result.roe_yoy == 5.8, f"roe_yoy 字段值错误: {result.roe_yoy}"

    def test_create_unified_handles_none_values(self):
        """测试 create_unified 方法正确处理 None 值"""
        raw_data = {
            "code": "600000",
            "name": "浦发银行",
            "or_yoy": None,
            "q_profit_yoy": None,
        }

        result = StockBasicData.create_unified(raw_data, "tushare")

        assert result.or_yoy is None
        assert result.q_profit_yoy is None

    def test_create_unified_handles_missing_fields(self):
        """测试 create_unified 方法正确处理缺失字段"""
        raw_data = {
            "code": "600000",
            "name": "浦发银行",
            # 不提供任何增速字段
        }

        result = StockBasicData.create_unified(raw_data, "tushare")

        assert result.or_yoy is None
        assert result.q_profit_yoy is None
        assert result.eps_yoy is None
        assert result.roe_yoy is None

    def test_create_unified_converts_string_to_float(self):
        """测试 create_unified 方法将字符串转换为浮点数"""
        raw_data = {
            "code": "600000",
            "name": "浦发银行",
            "or_yoy": "15.5",
            "q_profit_yoy": "20.3",
        }

        result = StockBasicData.create_unified(raw_data, "tushare")

        assert result.or_yoy == 15.5
        assert result.q_profit_yoy == 20.3

    def test_to_dict_includes_yoy_fields(self):
        """测试 to_dict 方法包含增速字段"""
        data = StockBasicData(
            code="600000",
            name="浦发银行",
            or_yoy=15.5,
            q_profit_yoy=20.3,
            eps_yoy=10.2,
            roe_yoy=5.8,
        )

        result = data.to_dict()

        assert "or_yoy" in result
        assert "q_profit_yoy" in result
        assert "eps_yoy" in result
        assert "roe_yoy" in result
        assert result["or_yoy"] == 15.5
        assert result["q_profit_yoy"] == 20.3
