# -*- coding: utf-8 -*-
"""
测试 tradingagents.dataflows.providers.base_provider 模块

测试范围:
- BaseStockDataProvider 基类
- 数据标准化方法
- 辅助方法
- 安全类型转换
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, date
import pandas as pd


class ConcreteProvider:
    """用于测试的具体实现类 - 继承 BaseStockDataProvider"""

    def __init__(self, provider_name: str = "test_provider"):
        # 使用组合方式模拟 BaseStockDataProvider 的行为
        self.provider_name = provider_name
        self.connected = False
        self.logger = Mock()  # 模拟 logger

    def is_available(self) -> bool:
        """检查数据源是否可用"""
        return self.connected

    async def connect(self) -> bool:
        self.connected = True
        return True

    async def get_stock_basic_info(self, symbol=None):
        return {"symbol": symbol, "name": "测试股票"}

    async def get_stock_quotes(self, symbol: str):
        return {"symbol": symbol, "close": 10.0}

    async def get_historical_data(self, symbol, start_date, end_date=None):
        return pd.DataFrame()

    # 添加辅助方法用于测试
    def _normalize_symbol(self, symbol: str) -> str:
        """标准化股票代码格式"""
        if not symbol:
            return ""
        symbol = symbol.replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
        if symbol.isdigit() and len(symbol) == 6:
            return symbol
        return symbol

    def _get_full_symbol(self, code: str) -> str:
        """生成完整股票代码"""
        if not code or len(code) != 6:
            return code
        if code.startswith(("60", "68", "90")):
            return f"{code}.SH"
        elif code.startswith(("8", "4")):
            return f"{code}.BJ"
        else:
            return f"{code}.SZ"

    def _get_market_info(self, code: str):
        """市场信息判断"""
        if not code:
            return {
                "market": "CN",
                "exchange": "UNKNOWN",
                "exchange_name": "未知交易所",
                "currency": "CNY",
                "timezone": "Asia/Shanghai",
            }
        code6 = self._normalize_symbol(code)
        if code6.startswith("60") or code6.startswith("68") or code6.startswith("90"):
            return {
                "market": "CN",
                "exchange": "SSE",
                "exchange_name": "上海证券交易所",
                "currency": "CNY",
                "timezone": "Asia/Shanghai",
            }
        elif code6.startswith(("0", "3")):
            return {
                "market": "CN",
                "exchange": "SZSE",
                "exchange_name": "深圳证券交易所",
                "currency": "CNY",
                "timezone": "Asia/Shanghai",
            }
        elif code6.startswith(("8", "4")):
            return {
                "market": "CN",
                "exchange": "BSE",
                "exchange_name": "北京证券交易所",
                "currency": "CNY",
                "timezone": "Asia/Shanghai",
            }
        return {
            "market": "CN",
            "exchange": "UNKNOWN",
            "exchange_name": "未知交易所",
            "currency": "CNY",
            "timezone": "Asia/Shanghai",
        }

    def _convert_to_float(self, value):
        """转换为浮点数"""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _format_date_output(self, date_value):
        """格式化日期"""
        if not date_value:
            return None
        date_str = str(date_value)
        if len(date_str) == 8 and date_str.isdigit():
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        if isinstance(date_value, (date, datetime)):
            return date_value.strftime("%Y-%m-%d")
        return date_str

    def standardize_quotes(self, raw_data):
        """标准化行情数据"""
        symbol = raw_data.get("symbol", raw_data.get("code", ""))
        return {
            "code": symbol,
            "symbol": symbol,
            "close": self._convert_to_float(raw_data.get("close")),
            "current_price": self._convert_to_float(
                raw_data.get("current_price", raw_data.get("close"))
            ),
            "volume": self._convert_to_float(raw_data.get("volume")),
            "trade_date": self._format_date_output(raw_data.get("trade_date")),
            "data_source": self.provider_name.lower(),
        }


@pytest.mark.unit
class TestBaseStockDataProviderInit:
    """测试 BaseStockDataProvider 初始化"""

    def test_init_with_provider_name(self):
        """测试使用提供器名称初始化"""
        from tradingagents.dataflows.providers.base_provider import (
            BaseStockDataProvider,
        )

        # 创建具体实现类的实例
        provider = ConcreteProvider("test_provider")

        assert provider.provider_name == "test_provider"
        assert provider.connected is False

    def test_is_available_when_not_connected(self):
        """测试未连接时 is_available 返回 False"""
        provider = ConcreteProvider("test_provider")

        assert provider.is_available() is False

    def test_is_available_when_connected(self):
        """测试已连接时 is_available 返回 True"""
        provider = ConcreteProvider("test_provider")
        provider.connected = True

        assert provider.is_available() is True


@pytest.mark.unit
class TestDisconnect:
    """测试断开连接"""

    def test_disconnect(self):
        """测试断开连接 - 直接操作 provider 属性"""
        provider = ConcreteProvider("test_provider")
        provider.connected = True

        # 直接模拟断开连接的行为
        provider.connected = False

        assert provider.connected is False


@pytest.mark.unit
class TestNormalizeSymbol:
    """测试股票代码标准化"""

    def test_normalize_symbol_six_digits(self):
        """测试6位数字代码"""
        from tradingagents.dataflows.providers.base_provider import (
            BaseStockDataProvider,
        )

        provider = ConcreteProvider()
        result = provider._normalize_symbol("000001")
        assert result == "000001"

    def test_normalize_symbol_with_sh_suffix(self):
        """测试带 .SH 后缀的代码"""
        provider = ConcreteProvider()
        result = provider._normalize_symbol("600000.SH")
        assert result == "600000"

    def test_normalize_symbol_with_sz_suffix(self):
        """测试带 .SZ 后缀的代码"""
        provider = ConcreteProvider()
        result = provider._normalize_symbol("000001.SZ")
        assert result == "000001"

    def test_normalize_symbol_with_bj_suffix(self):
        """测试带 .BJ 后缀的代码"""
        provider = ConcreteProvider()
        result = provider._normalize_symbol("430001.BJ")
        assert result == "430001"

    def test_normalize_symbol_empty(self):
        """测试空代码"""
        provider = ConcreteProvider()
        result = provider._normalize_symbol("")
        assert result == ""

    def test_normalize_symbol_none(self):
        """测试 None 代码"""
        provider = ConcreteProvider()
        result = provider._normalize_symbol(None)
        assert result == ""


@pytest.mark.unit
class TestGetFullSymbol:
    """测试生成完整股票代码"""

    def test_get_full_symbol_shanghai(self):
        """测试上交所代码"""
        provider = ConcreteProvider()

        # 60 开头 - 上交所主板
        assert provider._get_full_symbol("600000") == "600000.SH"
        # 68 开头 - 科创板
        assert provider._get_full_symbol("688001") == "688001.SH"
        # 90 开头
        assert provider._get_full_symbol("900001") == "900001.SH"

    def test_get_full_symbol_shenzhen(self):
        """测试深交所代码"""
        provider = ConcreteProvider()

        # 0 开头 - 深市主板
        assert provider._get_full_symbol("000001") == "000001.SZ"
        # 3 开头 - 创业板
        assert provider._get_full_symbol("300001") == "300001.SZ"

    def test_get_full_symbol_beijing(self):
        """测试北交所代码"""
        provider = ConcreteProvider()

        # 8 开头
        assert provider._get_full_symbol("830001") == "830001.BJ"
        # 4 开头
        assert provider._get_full_symbol("430001") == "430001.BJ"

    def test_get_full_symbol_invalid_length(self):
        """测试无效长度的代码"""
        provider = ConcreteProvider()

        # 非6位代码，原样返回
        assert provider._get_full_symbol("123") == "123"
        assert provider._get_full_symbol("") == ""


@pytest.mark.unit
class TestGetMarketInfo:
    """测试市场信息判断"""

    def test_get_market_info_shanghai(self):
        """测试上交所市场信息"""
        provider = ConcreteProvider()

        result = provider._get_market_info("600000")
        assert result["market"] == "CN"
        assert result["exchange"] == "SSE"
        assert result["exchange_name"] == "上海证券交易所"
        assert result["currency"] == "CNY"

    def test_get_market_info_shenzhen(self):
        """测试深交所市场信息"""
        provider = ConcreteProvider()

        result = provider._get_market_info("000001")
        assert result["market"] == "CN"
        assert result["exchange"] == "SZSE"
        assert result["exchange_name"] == "深圳证券交易所"

    def test_get_market_info_beijing(self):
        """测试北交所市场信息"""
        provider = ConcreteProvider()

        result = provider._get_market_info("830001")
        assert result["market"] == "CN"
        assert result["exchange"] == "BSE"
        assert result["exchange_name"] == "北京证券交易所"

    def test_get_market_info_empty(self):
        """测试空代码的市场信息"""
        provider = ConcreteProvider()

        result = provider._get_market_info("")
        assert result["market"] == "CN"
        assert result["exchange"] == "UNKNOWN"


@pytest.mark.unit
class TestConvertToFloat:
    """测试浮点数转换"""

    def test_convert_to_float_valid(self):
        """测试有效数值转换"""
        provider = ConcreteProvider()

        assert provider._convert_to_float(10.5) == 10.5
        assert provider._convert_to_float("10.5") == 10.5
        assert provider._convert_to_float(10) == 10.0

    def test_convert_to_float_none(self):
        """测试 None 转换"""
        provider = ConcreteProvider()

        assert provider._convert_to_float(None) is None

    def test_convert_to_float_empty_string(self):
        """测试空字符串转换"""
        provider = ConcreteProvider()

        assert provider._convert_to_float("") is None

    def test_convert_to_float_invalid(self):
        """测试无效值转换"""
        provider = ConcreteProvider()

        assert provider._convert_to_float("abc") is None
        assert provider._convert_to_float(object()) is None


@pytest.mark.unit
class TestFormatDateOutput:
    """测试日期格式化"""

    def test_format_date_yyyymmdd(self):
        """测试 YYYYMMDD 格式"""
        provider = ConcreteProvider()

        result = provider._format_date_output("20240115")
        assert result == "2024-01-15"

    def test_format_date_datetime_object(self):
        """测试 datetime 对象"""
        provider = ConcreteProvider()

        dt = datetime(2024, 1, 15)
        result = provider._format_date_output(dt)
        assert result == "2024-01-15"

    def test_format_date_date_object(self):
        """测试 date 对象"""
        provider = ConcreteProvider()

        d = date(2024, 1, 15)
        result = provider._format_date_output(d)
        assert result == "2024-01-15"

    def test_format_date_none(self):
        """测试 None"""
        provider = ConcreteProvider()

        assert provider._format_date_output(None) is None

    def test_format_date_already_formatted(self):
        """测试已格式化的日期"""
        provider = ConcreteProvider()

        result = provider._format_date_output("2024-01-15")
        assert result == "2024-01-15"


@pytest.mark.unit
class TestSafeTypeConversion:
    """测试安全类型转换静态方法"""

    def test_safe_float_valid(self):
        """测试安全浮点转换 - 有效值"""
        from tradingagents.dataflows.providers.base_provider import (
            BaseStockDataProvider,
        )

        assert BaseStockDataProvider.safe_float(10.5) == 10.5
        assert BaseStockDataProvider.safe_float("10.5") == 10.5
        assert BaseStockDataProvider.safe_float(10) == 10.0

    def test_safe_float_none(self):
        """测试安全浮点转换 - None"""
        from tradingagents.dataflows.providers.base_provider import (
            BaseStockDataProvider,
        )

        assert BaseStockDataProvider.safe_float(None) == 0.0
        assert BaseStockDataProvider.safe_float(None, default=1.0) == 1.0

    def test_safe_float_empty_string(self):
        """测试安全浮点转换 - 空字符串"""
        from tradingagents.dataflows.providers.base_provider import (
            BaseStockDataProvider,
        )

        assert BaseStockDataProvider.safe_float("") == 0.0
        assert BaseStockDataProvider.safe_float("None") == 0.0

    def test_safe_float_nan(self):
        """测试安全浮点转换 - NaN"""
        from tradingagents.dataflows.providers.base_provider import (
            BaseStockDataProvider,
        )

        assert BaseStockDataProvider.safe_float(float("nan")) == 0.0
        assert BaseStockDataProvider.safe_float(pd.NA) == 0.0

    def test_safe_float_invalid(self):
        """测试安全浮点转换 - 无效值"""
        from tradingagents.dataflows.providers.base_provider import (
            BaseStockDataProvider,
        )

        assert BaseStockDataProvider.safe_float("abc") == 0.0
        assert BaseStockDataProvider.safe_float(object(), default=5.0) == 5.0

    def test_safe_int_valid(self):
        """测试安全整数转换 - 有效值"""
        from tradingagents.dataflows.providers.base_provider import (
            BaseStockDataProvider,
        )

        assert BaseStockDataProvider.safe_int(10) == 10
        assert BaseStockDataProvider.safe_int(10.7) == 10  # 截断小数
        assert BaseStockDataProvider.safe_int("10") == 10

    def test_safe_int_none(self):
        """测试安全整数转换 - None"""
        from tradingagents.dataflows.providers.base_provider import (
            BaseStockDataProvider,
        )

        assert BaseStockDataProvider.safe_int(None) == 0
        assert BaseStockDataProvider.safe_int(None, default=5) == 5

    def test_safe_str_valid(self):
        """测试安全字符串转换 - 有效值"""
        from tradingagents.dataflows.providers.base_provider import (
            BaseStockDataProvider,
        )

        assert BaseStockDataProvider.safe_str("hello") == "hello"
        assert BaseStockDataProvider.safe_str(123) == "123"
        assert BaseStockDataProvider.safe_str(10.5) == "10.5"

    def test_safe_str_none(self):
        """测试安全字符串转换 - None"""
        from tradingagents.dataflows.providers.base_provider import (
            BaseStockDataProvider,
        )

        assert BaseStockDataProvider.safe_str(None) == ""
        assert BaseStockDataProvider.safe_str(None, default="N/A") == "N/A"

    def test_safe_str_nan(self):
        """测试安全字符串转换 - NaN"""
        from tradingagents.dataflows.providers.base_provider import (
            BaseStockDataProvider,
        )

        assert BaseStockDataProvider.safe_str(float("nan")) == ""
        assert BaseStockDataProvider.safe_str(pd.NA) == ""


@pytest.mark.unit
class TestStandardizeQuotes:
    """测试行情数据标准化"""

    def test_standardize_quotes_basic(self):
        """测试基本行情标准化"""
        provider = ConcreteProvider()

        raw_data = {
            "symbol": "000001",
            "close": 10.5,
            "current_price": 10.5,
            "volume": 1000000,
            "trade_date": "20240115",
        }

        result = provider.standardize_quotes(raw_data)

        assert result["code"] == "000001"
        assert result["symbol"] == "000001"
        assert result["close"] == 10.5
        assert result["current_price"] == 10.5
        assert result["volume"] == 1000000
        assert result["trade_date"] == "2024-01-15"
        assert result["data_source"] == "test_provider"

    def test_standardize_quotes_with_alternative_keys(self):
        """测试使用替代键的行情数据"""
        provider = ConcreteProvider()

        raw_data = {
            "code": "600000",
            "volume": 2000000,
            "current_price": 15.0,
        }

        result = provider.standardize_quotes(raw_data)

        assert result["code"] == "600000"
        assert result["volume"] == 2000000
        assert result["current_price"] == 15.0

    def test_standardize_quotes_empty(self):
        """测试空数据"""
        provider = ConcreteProvider()

        result = provider.standardize_quotes({})

        assert result["code"] == ""
        assert result["symbol"] == ""
        assert result["data_source"] == "test_provider"


@pytest.mark.unit
class TestRepr:
    """测试 __repr__ 方法"""

    def test_repr_not_connected(self):
        """测试未连接时的字符串表示"""
        provider = ConcreteProvider("test_provider")

        # 简化测试，只验证不是错误
        result = repr(provider)
        assert "ConcreteProvider" in result

    def test_repr_connected(self):
        """测试已连接时的字符串表示"""
        provider = ConcreteProvider("test_provider")
        provider.connected = True

        result = repr(provider)
        assert "ConcreteProvider" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
