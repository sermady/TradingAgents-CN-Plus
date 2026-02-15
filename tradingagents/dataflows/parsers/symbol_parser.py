# -*- coding: utf-8 -*-
"""
股票代码解析工具模块
提供股票代码标准化、市场类型判断等功能
"""

from typing import Optional, Dict, Any


# 代码前缀到市场信息的映射
MARKET_MAP = {
    "000": {"market": "主板", "exchange": "深圳证券交易所", "type": "综合"},
    "001": {"market": "主板", "exchange": "深圳证券交易所", "type": "综合"},
    "002": {"market": "主板", "exchange": "深圳证券交易所", "type": "成长型"},
    "003": {"market": "创业板", "exchange": "深圳证券交易所", "type": "创新型"},
    "300": {"market": "创业板", "exchange": "深圳证券交易所", "type": "高科技"},
    "600": {"market": "主板", "exchange": "上海证券交易所", "type": "大盘蓝筹"},
    "601": {"market": "主板", "exchange": "上海证券交易所", "type": "大盘蓝筹"},
    "603": {"market": "主板", "exchange": "上海证券交易所", "type": "中小盘"},
    "605": {"market": "主板", "exchange": "上海证券交易所", "type": "中小盘"},
    "688": {"market": "科创板", "exchange": "上海证券交易所", "type": "科技创新"},
}


def normalize_symbol(symbol: str) -> str:
    """
    标准化股票代码为6位数字格式

    Args:
        symbol: 原始股票代码 (支持 000001, 000001.SZ, sz000001 等格式)

    Returns:
        标准化的6位数字代码
    """
    if not symbol:
        return ""

    # 移除空格和点号后的后缀
    symbol = symbol.strip().upper()
    symbol = symbol.replace(".SH", "").replace(".SZ", "")
    symbol = symbol.replace(".SS", "")

    # 移除前缀
    if symbol.startswith("SH") or symbol.startswith("SZ"):
        symbol = symbol[2:]

    # 补齐到6位
    return symbol.zfill(6)


def extract_code_prefix(symbol: str) -> str:
    """
    提取股票代码前缀（前3位）

    Args:
        symbol: 股票代码

    Returns:
        代码前缀
    """
    code = normalize_symbol(symbol)
    return code[:3] if len(code) >= 3 else code


def get_market_type(symbol: str) -> Dict[str, str]:
    """
    根据股票代码判断市场类型

    Args:
        symbol: 股票代码

    Returns:
        包含市场信息的字典
    """
    prefix = extract_code_prefix(symbol)
    return MARKET_MAP.get(
        prefix,
        {"market": "未知市场", "exchange": "未知交易所", "type": "综合"},
    )


def get_market_type_by_code(symbol: str) -> str:
    """
    根据股票代码判断市场类型描述

    Args:
        symbol: 股票代码

    Returns:
        市场类型描述
    """
    prefix = extract_code_prefix(symbol)
    type_map = {
        "000": "综合",
        "001": "综合",
        "002": "成长型",
        "003": "创新型",
        "300": "高科技",
        "600": "大盘蓝筹",
        "601": "大盘蓝筹",
        "603": "中小盘",
        "605": "中小盘",
        "688": "科技创新",
    }
    return type_map.get(prefix, "综合")


def is_shanghai_stock(symbol: str) -> bool:
    """
    判断是否为上海股票

    Args:
        symbol: 股票代码

    Returns:
        是否为上海股票
    """
    prefix = extract_code_prefix(symbol)
    return prefix in ("600", "601", "603", "605", "688")


def is_shenzhen_stock(symbol: str) -> bool:
    """
    判断是否为深圳股票

    Args:
        symbol: 股票代码

    Returns:
        是否为深圳股票
    """
    prefix = extract_code_prefix(symbol)
    return prefix in ("000", "001", "002", "003", "300")


def is_chinext_stock(symbol: str) -> bool:
    """
    判断是否为创业板股票

    Args:
        symbol: 股票代码

    Returns:
        是否为创业板股票
    """
    prefix = extract_code_prefix(symbol)
    return prefix in ("300", "003")


def is_star_market_stock(symbol: str) -> bool:
    """
    判断是否为科创板股票

    Args:
        symbol: 股票代码

    Returns:
        是否为科创板股票
    """
    prefix = extract_code_prefix(symbol)
    return prefix == "688"


def add_exchange_suffix(symbol: str) -> str:
    """
    为股票代码添加交易所后缀

    Args:
        symbol: 股票代码

    Returns:
        带后缀的股票代码 (如 000001.SZ)
    """
    code = normalize_symbol(symbol)

    if is_shanghai_stock(code):
        return f"{code}.SH"
    elif is_shenzhen_stock(code):
        return f"{code}.SZ"
    else:
        return code


def get_special_stocks() -> Dict[str, Dict[str, Any]]:
    """
    获取特殊股票的详细信息

    Returns:
        特殊股票信息字典
    """
    return {
        "000001": {
            "industry": "银行业",
            "analysis": "平安银行是中国领先的股份制商业银行，在零售银行业务方面具有显著优势。",
            "market_share": "股份制银行前列",
            "brand_value": "知名金融品牌",
            "tech_advantage": "金融科技创新领先",
        },
        "600036": {
            "industry": "银行业",
            "analysis": "招商银行是中国优质的股份制银行，零售银行业务和财富管理业务领先。",
            "market_share": "股份制银行龙头",
            "brand_value": "优质银行品牌",
            "tech_advantage": "数字化银行先锋",
        },
        "000002": {
            "industry": "房地产",
            "analysis": "万科A是中国房地产行业龙头企业，在住宅开发领域具有领先地位。",
            "market_share": "房地产行业前三",
            "brand_value": "知名地产品牌",
            "tech_advantage": "绿色建筑技术",
        },
        "002475": {
            "industry": "元器件",
            "analysis": "立讯精密是全球领先的精密制造服务商，主要从事连接器、声学、无线充电等产品的研发制造。",
            "market_share": "消费电子连接器龙头",
            "brand_value": "精密制造知名品牌",
            "tech_advantage": "精密制造技术领先",
        },
    }


def is_special_stock(symbol: str) -> bool:
    """
    判断是否为特殊股票（有预定义信息）

    Args:
        symbol: 股票代码

    Returns:
        是否为特殊股票
    """
    code = normalize_symbol(symbol)
    return code in get_special_stocks()


def get_special_stock_info(symbol: str) -> Optional[Dict[str, Any]]:
    """
    获取特殊股票信息

    Args:
        symbol: 股票代码

    Returns:
        特殊股票信息或None
    """
    code = normalize_symbol(symbol)
    return get_special_stocks().get(code)
