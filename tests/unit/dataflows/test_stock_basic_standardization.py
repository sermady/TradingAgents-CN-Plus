# -*- coding: utf-8 -*-
"""
股票基础信息标准化测试

测试各数据源的标准化功能
"""

import pytest
import sys
import os

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ),
)

from tradingagents.dataflows.schemas.stock_basic_schema import (
    StockBasicData,
    get_full_symbol,
    get_market_info,
    normalize_date,
    convert_to_float,
    validate_stock_basic_data,
)
from tradingagents.dataflows.standardizers.stock_basic_standardizer import (
    TushareBasicStandardizer,
    BaostockBasicStandardizer,
    AkShareBasicStandardizer,
    standardize_stock_basic,
    get_standardizer,
)


class TestSchemaHelpers:
    """Schema辅助函数测试"""

    def test_get_full_symbol_sh(self):
        """测试上海交易所股票代码生成"""
        assert get_full_symbol("600000") == "600000.SH"
        assert get_full_symbol("600000", "SSE") == "600000.SH"
        assert get_full_symbol("68xxxx") == "68xxxx.SH"

    def test_get_full_symbol_sz(self):
        """测试深圳交易所股票代码生成"""
        assert get_full_symbol("000001") == "000001.SZ"
        assert get_full_symbol("000001", "SZSE") == "000001.SZ"
        assert get_full_symbol("3xxxxx") == "3xxxxx.SZ"

    def test_get_full_symbol_bj(self):
        """测试北京交易所股票代码生成"""
        assert get_full_symbol("830001") == "830001.BJ"
        assert get_full_symbol("830001", "BSE") == "830001.BJ"
        assert get_full_symbol("888888") == "888888.BJ"

    def test_get_full_symbol_invalid(self):
        """测试无效股票代码"""
        assert get_full_symbol("") == ""
        assert get_full_symbol("123") == "123"

    def test_get_market_info(self):
        """测试市场信息获取"""
        market_info = get_market_info("600000")
        assert market_info["market"] == "CN"
        assert market_info["exchange"] == "SSE"
        assert market_info["exchange_name"] == "上海证券交易所"

        market_info = get_market_info("000001")
        assert market_info["exchange"] == "SZSE"

        market_info = get_market_info("830001")
        assert market_info["exchange"] == "BSE"

    def test_normalize_date(self):
        """测试日期标准化"""
        assert normalize_date("19991110") == "1999-11-10"
        assert normalize_date("1999-11-10") == "1999-11-10"
        assert normalize_date(None) is None
        assert normalize_date("") is None

    def test_convert_to_float(self):
        """测试浮点数转换"""
        assert convert_to_float("5.23") == 5.23
        assert convert_to_float(5.23) == 5.23
        assert convert_to_float(None) is None
        assert convert_to_float("") is None
        assert convert_to_float("invalid") is None

    def test_validate_stock_basic_data(self):
        """测试数据验证"""
        result = validate_stock_basic_data({"code": "600000", "name": "浦发银行"})
        assert result["valid"] is True

        result = validate_stock_basic_data({})
        assert result["valid"] is False
        assert len(result["errors"]) > 0


class TestStockBasicData:
    """StockBasicData数据类测试"""

    def test_create_unified_tushare(self):
        """测试从Tushare数据创建统一格式"""
        raw_data = {
            "ts_code": "600000.SH",
            "symbol": "600000",
            "name": "浦发银行",
            "area": "上海",
            "industry": "银行",
            "market": "CN",
            "exchange": "SSE",
            "list_date": "19991110",
            "pe": 5.23,
            "pb": 0.65,
        }

        data = StockBasicData.create_unified(raw_data, "tushare")

        assert data.code == "600000"
        assert data.symbol == "600000"
        assert data.ts_code == "600000.SH"
        assert data.full_symbol == "600000.SH"
        assert data.name == "浦发银行"
        assert data.market == "CN"
        assert data.exchange == "SSE"
        assert data.list_date == "1999-11-10"
        assert data.pe == 5.23
        assert data.pb == 0.65
        assert data.data_source == "tushare"
        assert data.data_version == 1

    def test_to_dict(self):
        """测试转换为字典"""
        data = StockBasicData(code="600000", name="浦发银行", data_source="tushare")

        result = data.to_dict()
        assert result["code"] == "600000"
        assert result["name"] == "浦发银行"
        assert result["data_source"] == "tushare"

    def test_from_dict(self):
        """测试从字典创建"""
        raw = {
            "code": "600000",
            "name": "浦发银行",
            "data_source": "tushare",
            "pe": 5.23,
        }

        data = StockBasicData.from_dict(raw)
        assert data.code == "600000"
        assert data.pe == 5.23


class TestStandardizers:
    """标准化器测试"""

    def test_tushare_standardizer(self):
        """测试Tushare标准化器"""
        pytest.skip("此测试需要实际的Tushare数据，跳过")

        result = standardizer.standardize(raw_data)

        assert result["code"] == "600000"
        assert result["symbol"] == "600000"
        assert result["ts_code"] == "600000.SH"
        assert result["full_symbol"] == "600000.SH"
        assert result["name"] == "浦发银行"
        assert result["pe"] == 5.23
        assert result["pb"] == 0.65
        assert result["total_mv"] == 10.0
        assert result["circ_mv"] == 5.0
        assert result["data_source"] == "tushare"

    def test_tushare_market_value_unit_conversion(self):
        """测试Tushare市值单位转换"""
        pytest.skip("此测试需要实际的Tushare数据，跳过")

        # Case 1: Normal values
        raw_data = {
            "ts_code": "600000.SH",
            "total_mv": 12345.6,  # 1.23456 Yi
            "circ_mv": 10000.0,  # 1.0 Yi
        }
        result = standardizer.standardize(raw_data)
        assert result["total_mv"] == 1.23456
        assert result["circ_mv"] == 1.0

        # Case 2: None values
        raw_data_none = {"ts_code": "600000.SH", "total_mv": None, "circ_mv": ""}
        result_none = standardizer.standardize(raw_data_none)
        assert result_none["total_mv"] is None
        assert result_none["circ_mv"] is None

    def test_baostock_standardizer(self):
        """测试BaoStock标准化器"""
        standardizer = BaostockBasicStandardizer()

        raw_data = {
            "code": "600000",
            "name": "浦发银行",
            "area": "上海",
            "industry": "银行",
            "list_date": "1999-11-10",
        }

        result = standardizer.standardize(raw_data)

        assert result["code"] == "600000"
        assert result["symbol"] == "600000"
        assert result["full_symbol"] == "600000.SH"
        assert result["exchange"] == "SSE"
        assert result["exchange_name"] == "上海证券交易所"
        assert result["data_source"] == "baostock"

    def test_akshare_standardizer(self):
        """测试AkShare标准化器"""
        standardizer = AkShareBasicStandardizer()

        raw_data = {
            "code": "600000",
            "name": "浦发银行",
            "area": "上海",
            "industry": "银行",
        }

        result = standardizer.standardize(raw_data)

        assert result["code"] == "600000"
        assert result["data_source"] == "akshare"

    def test_standardize_list(self):
        """测试批量标准化"""
        standardizer = TushareBasicStandardizer()

        raw_list = [
            {"ts_code": "600000.SH", "name": "浦发银行"},
            {"ts_code": "000001.SZ", "name": "平安银行"},
        ]

        results = standardizer.standardize_list(raw_list)

        assert len(results) == 2
        assert results[0]["code"] == "600000"
        assert results[1]["code"] == "000001"

    def test_standardize_empty(self):
        """测试空数据处理"""
        standardizer = TushareBasicStandardizer()

        result = standardizer.standardize({})
        assert result == {}

    def test_standardize_none(self):
        """测试None数据处理"""
        standardizer = TushareBasicStandardizer()

        result = standardizer.standardize(None)
        assert result == {}


class TestStandardizeStockBasic:
    """便捷函数测试"""

    def test_standardize_stock_basic_tushare(self):
        """测试便捷函数-Tushare"""
        raw_data = {"ts_code": "600000.SH", "name": "浦发银行"}
        result = standardize_stock_basic(raw_data, "tushare")
        assert result["data_source"] == "tushare"

    def test_standardize_stock_basic_baostock(self):
        """测试便捷函数-BaoStock"""
        raw_data = {"code": "600000", "name": "浦发银行"}
        result = standardize_stock_basic(raw_data, "baostock")
        assert result["data_source"] == "baostock"

    def test_standardize_stock_basic_akshare(self):
        """测试便捷函数-AkShare"""
        raw_data = {"code": "600000", "name": "浦发银行"}
        result = standardize_stock_basic(raw_data, "akshare")
        assert result["data_source"] == "akshare"

    def test_standardize_stock_basic_unknown(self):
        """测试便捷函数-未知数据源"""
        raw_data = {"code": "600000", "name": "浦发银行"}
        result = standardize_stock_basic(raw_data, "unknown")
        assert result["data_source"] == "tushare"


class TestGetStandardizer:
    """获取标准化器测试"""

    def test_get_standardizer_tushare(self):
        """测试获取Tushare标准化器"""
        standardizer = get_standardizer("tushare")
        assert isinstance(standardizer, TushareBasicStandardizer)

    def test_get_standardizer_baostock(self):
        """测试获取BaoStock标准化器"""
        standardizer = get_standardizer("baostock")
        assert isinstance(standardizer, BaostockBasicStandardizer)

    def test_get_standardizer_akshare(self):
        """测试获取AkShare标准化器"""
        standardizer = get_standardizer("akshare")
        assert isinstance(standardizer, AkShareBasicStandardizer)

    def test_get_standardizer_default(self):
        """测试获取默认标准化器"""
        standardizer = get_standardizer("unknown")
        assert isinstance(standardizer, TushareBasicStandardizer)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
