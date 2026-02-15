# -*- coding: utf-8 -*-
"""
数据验证工具

提供股票代码、日期、参数等的验证逻辑
"""
from typing import Optional, List
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """验证错误异常"""

    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


def validate_stock_code(symbol: str, allow_empty: bool = False) -> Optional[str]:
    """验证股票代码

    Args:
        symbol: 股票代码
        allow_empty: 是否允许为空

    Returns:
        验证通过的股票代码

    Raises:
        ValidationError: 验证失败时
    """
    if not symbol:
        if allow_empty:
            return None
        raise ValidationError("股票代码不能为空", field="symbol")

    symbol = symbol.strip()

    # A股代码：6位数字
    if len(symbol) == 6 and symbol.isdigit():
        return symbol

    # 港股代码：5位数字（通常以0-9开头）
    if len(symbol) == 5 and symbol.isdigit():
        return symbol

    # 美股代码：字母+数字（如AAPL, TSLA）
    if re.match(r'^[A-Z]{1,5}$', symbol):
        return symbol.upper()

    # 其他格式：原样返回
    return symbol


def validate_analysis_date(date: Optional[str]) -> Optional[str]:
    """验证分析日期

    Args:
        date: 日期字符串（YYYY-MM-DD格式）

    Returns:
        验证通过的日期字符串

    Raises:
        ValidationError: 验证失败时
    """
    if not date:
        return None

    date = date.strip()

    # 验证日期格式 YYYY-MM-DD
    try:
        datetime.strptime(date, "%Y-%m-%d")
        return date
    except ValueError:
        raise ValidationError(
            f"日期格式错误: {date}，应为 YYYY-MM-DD",
            field="analysis_date"
        )


def validate_research_depth(depth: str) -> str:
    """验证研究深度

    Args:
        depth: 研究深度（快速/基础/标准/深度/全面）

    Returns:
        验证通过的研究深度

    Raises:
        ValidationError: 验证失败时
    """
    valid_depths = ["快速", "基础", "标准", "深度", "全面"]
    depth = depth.strip()

    if depth not in valid_depths:
        raise ValidationError(
            f"研究深度错误: {depth}，应为: {'/'.join(valid_depths)}",
            field="research_depth"
        )

    return depth


def validate_symbols_list(
    symbols: List[str], max_count: int = 10
) -> List[str]:
    """验证股票代码列表

    Args:
        symbols: 股票代码列表
        max_count: 最大数量限制

    Returns:
        验证通过的股票代码列表

    Raises:
        ValidationError: 验证失败时
    """
    if not symbols:
        raise ValidationError("股票代码列表不能为空", field="symbols")

    if len(symbols) > max_count:
        raise ValidationError(
            f"股票代码数量超出限制: {len(symbols)} > {max_count}",
            field="symbols"
        )

    validated_symbols = []
    for symbol in symbols:
        try:
            validated = validate_stock_code(symbol)
            if validated:
                validated_symbols.append(validated)
        except ValidationError as e:
            logger.warning(f"跳过无效股票代码: {symbol}, 原因: {e}")

    if not validated_symbols:
        raise ValidationError(
            "股票代码列表中没有有效代码", field="symbols"
        )

    return validated_symbols


def validate_market_type(market_type: str) -> str:
    """验证市场类型

    Args:
        market_type: 市场类型（A股/H股/美股等）

    Returns:
        验证通过的市场类型
    """
    market_type = market_type.strip()

    valid_types = ["A股", "港股", "美股", "HK", "US", "A"]

    if market_type not in valid_types:
        logger.warning(f"市场类型可能无效: {market_type}")

    return market_type


def validate_analysis_request(request: dict) -> dict:
    """验证分析请求参数

    Args:
        request: 请求参数字典

    Returns:
        验证后的请求参数字典

    Raises:
        ValidationError: 验证失败时
    """
    validated = {}

    # 验证股票代码
    if "symbol" in request:
        validated["symbol"] = validate_stock_code(request["symbol"])

    if "stock_code" in request:
        validated["stock_code"] = validate_stock_code(
            request["stock_code"], allow_empty=True
        )

    # 验证日期
    if "analysis_date" in request:
        try:
            validated["analysis_date"] = validate_analysis_date(
                request.get("analysis_date")
            )
        except ValidationError:
            pass  # 日期可选，验证失败时跳过

    # 验证研究深度
    if "research_depth" in request:
        validated["research_depth"] = validate_research_depth(
            request["research_depth"]
        )

    # 验证市场类型
    if "market_type" in request:
        validated["market_type"] = validate_market_type(
            request["market_type"]
        )

    # 复制其他参数
    for key, value in request.items():
        if key not in validated:
            validated[key] = value

    return validated
