# -*- coding: utf-8 -*-
"""
统一股票基础信息Schema定义

定义所有数据源（tushare/baostock/akshare）的统一输出格式
确保数据一致性，简化上层业务逻辑
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime


STOCK_BASIC_SCHEMA = {
    "version": "1.0",
    "last_updated": "2026-01-25",
    "description": "统一股票基础信息Schema，所有数据源输出应符合此规范",
}


STOCK_BASIC_REQUIRED_FIELDS = {
    "code": {
        "type": "string",
        "description": "6位股票代码",
        "example": "600000",
        "validation": "6位数字",
    },
    "name": {
        "type": "string",
        "description": "股票名称",
        "example": "浦发银行",
        "validation": "非空字符串",
    },
    "data_source": {
        "type": "string",
        "description": "数据来源标识",
        "example": "tushare",
        "validation": "tushare|baostock|akshare",
    },
}


STOCK_BASIC_OPTIONAL_FIELDS = {
    "code": {
        "type": "string",
        "description": "6位股票代码（冗余，与symbol相同）",
        "example": "600000",
    },
    "symbol": {
        "type": "string",
        "description": "6位股票代码（同code）",
        "example": "600000",
    },
    "ts_code": {
        "type": "string",
        "description": "Tushare格式股票代码",
        "example": "600000.SH",
    },
    "full_symbol": {
        "type": "string",
        "description": "完整股票代码（含交易所后缀）",
        "example": "600000.SH",
    },
    "name": {"type": "string", "description": "股票名称", "example": "浦发银行"},
    "market": {
        "type": "string",
        "description": "市场代码",
        "example": "CN",
        "values": ["CN", "HK", "US"],
    },
    "exchange": {
        "type": "string",
        "description": "交易所代码",
        "example": "SSE",
        "values": ["SSE", "SZSE", "BSE", "HKEX", "NYSE", "NASDAQ"],
    },
    "exchange_name": {
        "type": "string",
        "description": "交易所名称",
        "example": "上海证券交易所",
    },
    "list_status": {
        "type": "string",
        "description": "上市状态",
        "example": "L",
        "values": ["L", "D", "P"],
        "meaning": {"L": "上市", "D": "退市", "P": "暂停上市"},
    },
    "area": {"type": "string", "description": "所在地区", "example": "上海"},
    "industry": {"type": "string", "description": "所属行业", "example": "银行"},
    "industry_sw": {"type": "string", "description": "申万一级行业", "example": "银行"},
    "industry_gn": {
        "type": "string",
        "description": "概念行业分类",
        "example": "沪股通",
    },
    "list_date": {
        "type": "string",
        "description": "上市日期",
        "example": "1999-11-10",
        "format": "YYYY-MM-DD",
    },
    "delist_date": {
        "type": "string",
        "description": "退市日期",
        "example": None,
        "format": "YYYY-MM-DD",
    },
    "is_hs": {
        "type": "string",
        "description": "是否沪深港通标的",
        "example": "H",
        "values": ["H", "S", "N"],
        "meaning": {"H": "沪股通", "S": "深股通", "N": "非标的"},
    },
    "act_name": {
        "type": "string",
        "description": "上市公司名称（英文）",
        "example": "Shanghai Pudong Development Bank",
    },
    "act_ent_type": {"type": "string", "description": "公司类型", "example": "1"},
    "pe": {
        "type": "number",
        "description": "市盈率（收盘价/每股收益）",
        "example": 5.23,
    },
    "pe_ttm": {
        "type": "number",
        "description": "市盈率TTM（基于近12个月净利润）",
        "example": 5.15,
    },
    "pb": {
        "type": "number",
        "description": "市净率（股价/每股净资产）",
        "example": 0.65,
    },
    "ps": {
        "type": "number",
        "description": "市销率（股价/每股销售额）",
        "example": 1.20,
    },
    "pcf": {
        "type": "number",
        "description": "市现率（股价/每股现金流）",
        "example": 4.5,
    },
    "total_mv": {"type": "number", "description": "总市值（亿元）", "example": 1500.5},
    "circ_mv": {"type": "number", "description": "流通市值（亿元）", "example": 1480.2},
    "turnover_rate": {"type": "number", "description": "换手率（%）", "example": 0.85},
    "volume_ratio": {"type": "number", "description": "量比", "example": 1.2},
    "last_sync": {
        "type": "string",
        "description": "最后同步时间",
        "example": "2026-01-25T10:30:00",
        "format": "ISO 8601",
    },
    "data_source": {
        "type": "string",
        "description": "数据来源标识",
        "example": "tushare",
    },
    "data_version": {"type": "integer", "description": "数据Schema版本", "example": 1},
}


EXCHANGE_MAPPING = {
    "SSE": "上海证券交易所",
    "SZSE": "深圳证券交易所",
    "BSE": "北京证券交易所",
    "HKEX": "香港联合交易所",
    "NYSE": "纽约证券交易所",
    "NASDAQ": "纳斯达克证券交易所",
}


def get_exchange_name(exchange_code: str) -> str:
    """获取交易所名称"""
    return EXCHANGE_MAPPING.get(exchange_code, "未知交易所")


def get_full_symbol(code: str, exchange: str = None) -> str:
    """
    生成完整股票代码

    Args:
        code: 6位股票代码
        exchange: 交易所代码

    Returns:
        完整股票代码（如 600000.SH）
    """
    if not code or len(code) != 6:
        return code

    code = code.strip()

    if exchange == "SSE" or code.startswith(("60", "68", "90")):
        return f"{code}.SH"
    elif exchange == "BSE" or code.startswith("8"):
        return f"{code}.BJ"
    elif exchange == "SZSE" or code.startswith(("0", "3")):
        return f"{code}.SZ"
    elif exchange == "HKEX" or len(code) == 5:
        return f"{code}.HK"

    return code


def get_market_info(code: str) -> Dict[str, Any]:
    """
    根据股票代码获取市场信息

    Args:
        code: 股票代码（支持6位或完整格式）

    Returns:
        市场信息字典
    """
    if not code:
        return {
            "market": "CN",
            "exchange": "UNKNOWN",
            "exchange_name": "未知交易所",
            "currency": "CNY",
            "timezone": "Asia/Shanghai",
        }

    code6 = code.split(".")[0] if "." in code else code

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


def normalize_date(date_value: Any) -> Optional[str]:
    """
    标准化日期格式

    Args:
        date_value: 原始日期值

    Returns:
        YYYY-MM-DD 格式字符串或None
    """
    if not date_value:
        return None

    date_str = str(date_value)

    if len(date_str) == 8 and date_str.isdigit():
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    return date_str


def convert_to_float(value: Any) -> Optional[float]:
    """转换为浮点数"""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def validate_stock_basic_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    验证并标准化股票基础数据

    Args:
        data: 原始数据字典

    Returns:
        验证后的数据字典，包含验证结果
    """
    result = {"valid": True, "data": data, "errors": [], "warnings": []}

    required_fields = ["code", "name"]
    for field in required_fields:
        if field not in data or not data.get(field):
            result["valid"] = False
            result["errors"].append(f"缺少必填字段: {field}")

    if not result["valid"]:
        return result

    if "code" in data and (
        len(str(data["code"])) != 6 or not str(data["code"]).isdigit()
    ):
        result["warnings"].append("code字段应为6位数字")

    return result


@dataclass
class StockBasicData:
    """
    股票基础信息数据类

    提供类型安全的数据结构和默认值
    """

    code: str = ""
    name: str = ""
    data_source: str = ""

    symbol: str = ""
    ts_code: str = ""
    full_symbol: str = ""

    market: str = "CN"
    exchange: str = ""
    exchange_name: str = ""
    list_status: str = "L"

    area: str = ""
    industry: str = ""
    industry_sw: str = ""
    industry_gn: str = ""

    list_date: str = ""
    delist_date: str = ""
    is_hs: str = "N"
    act_name: str = ""
    act_ent_type: str = ""

    pe: Optional[float] = None
    pe_ttm: Optional[float] = None
    pb: Optional[float] = None
    ps: Optional[float] = None
    pcf: Optional[float] = None
    total_mv: Optional[float] = None
    circ_mv: Optional[float] = None
    turnover_rate: Optional[float] = None
    volume_ratio: Optional[float] = None

    last_sync: str = ""
    data_version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StockBasicData":
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def create_unified(
        cls, raw_data: Dict[str, Any], data_source: str
    ) -> "StockBasicData":
        """
        从原始数据创建统一格式

        Args:
            raw_data: 原始数据字典
            data_source: 数据来源标识

        Returns:
            StockBasicData实例
        """
        market_info = get_market_info(raw_data.get("code", ""))
        code = raw_data.get("code", "") or raw_data.get("symbol", "")
        code6 = code.split(".")[0] if "." in code else code

        full_symbol = raw_data.get("full_symbol") or get_full_symbol(
            code6, market_info["exchange"]
        )

        ts_code = raw_data.get("ts_code") or full_symbol

        return cls(
            code=code6,
            symbol=code6,
            ts_code=ts_code,
            full_symbol=full_symbol,
            name=raw_data.get("name", f"股票{code6}"),
            market=raw_data.get("market") or market_info["market"],
            exchange=raw_data.get("exchange") or market_info["exchange"],
            exchange_name=raw_data.get("exchange_name") or market_info["exchange_name"],
            list_status=raw_data.get("list_status", "L"),
            area=raw_data.get("area", ""),
            industry=raw_data.get("industry", ""),
            industry_sw=raw_data.get("industry_sw", ""),
            industry_gn=raw_data.get("industry_gn", ""),
            list_date=normalize_date(raw_data.get("list_date")) or "",
            delist_date=normalize_date(raw_data.get("delist_date")),
            is_hs=raw_data.get("is_hs", "N"),
            act_name=raw_data.get("act_name", ""),
            act_ent_type=raw_data.get("act_ent_type", ""),
            pe=convert_to_float(raw_data.get("pe")),
            pe_ttm=convert_to_float(raw_data.get("pe_ttm")),
            pb=convert_to_float(raw_data.get("pb")),
            ps=convert_to_float(raw_data.get("ps")),
            pcf=convert_to_float(raw_data.get("pcf")),
            total_mv=convert_to_float(raw_data.get("total_mv")),
            circ_mv=convert_to_float(raw_data.get("circ_mv")),
            turnover_rate=convert_to_float(raw_data.get("turnover_rate")),
            volume_ratio=convert_to_float(raw_data.get("volume_ratio")),
            last_sync=datetime.now().isoformat(),
            data_source=data_source,
            data_version=1,
        )
