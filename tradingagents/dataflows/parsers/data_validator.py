# -*- coding: utf-8 -*-
"""
数据验证工具模块
提供价格、成交量、财务数据等验证功能
"""

from typing import Optional, Dict, Any, List, Tuple


def validate_price(price: Any, min_val: float = 0.01, max_val: float = 10000.0) -> Tuple[bool, Optional[float]]:
    """
    验证价格数据

    Args:
        price: 价格值
        min_val: 最小有效值
        max_val: 最大有效值

    Returns:
        (是否有效, 有效值或None)
    """
    if price is None:
        return False, None

    try:
        price_val = float(price)
        if min_val <= price_val <= max_val:
            return True, price_val
        return False, None
    except (ValueError, TypeError):
        return False, None


def validate_volume(volume: Any, min_val: float = 0, max_val: float = 1e12) -> Tuple[bool, Optional[float]]:
    """
    验证成交量数据

    Args:
        volume: 成交量值
        min_val: 最小有效值
        max_val: 最大有效值

    Returns:
        (是否有效, 有效值或None)
    """
    if volume is None:
        return False, None

    try:
        vol_val = float(volume)
        if min_val <= vol_val <= max_val:
            return True, vol_val
        return False, None
    except (ValueError, TypeError):
        return False, None


def validate_financial_data(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
    """
    验证财务数据完整性

    Args:
        data: 财务数据字典
        required_fields: 必需字段列表

    Returns:
        验证结果字典
    """
    missing_fields = []
    invalid_fields = []

    for field in required_fields:
        value = data.get(field)
        if value is None:
            missing_fields.append(field)
        elif value in ["N/A", "nan", "--", "", "None"]:
            invalid_fields.append(field)

    total_fields = len(required_fields)
    valid_count = total_fields - len(missing_fields) - len(invalid_fields)
    completeness = valid_count / total_fields if total_fields > 0 else 0

    return {
        "is_valid": len(missing_fields) == 0 and len(invalid_fields) == 0,
        "completeness": completeness,
        "missing_fields": missing_fields,
        "invalid_fields": invalid_fields,
        "valid_count": valid_count,
        "total_count": total_fields,
    }


def validate_percentage(value: Any, min_val: float = -1000, max_val: float = 1000) -> Tuple[bool, Optional[float]]:
    """
    验证百分比数据

    Args:
        value: 百分比值
        min_val: 最小有效值
        max_val: 最大有效值

    Returns:
        (是否有效, 有效值或None)
    """
    if value is None:
        return False, None

    try:
        # 处理带%的字符串
        if isinstance(value, str):
            value = value.replace("%", "").strip()

        pct_val = float(value)
        if min_val <= pct_val <= max_val:
            return True, pct_val
        return False, None
    except (ValueError, TypeError):
        return False, None


def validate_ratio(value: Any, min_val: float = 0, max_val: float = 1000) -> Tuple[bool, Optional[float]]:
    """
    验证比率数据

    Args:
        value: 比率值
        min_val: 最小有效值
        max_val: 最大有效值

    Returns:
        (是否有效, 有效值或None)
    """
    if value is None:
        return False, None

    try:
        # 处理带"倍"的字符串
        if isinstance(value, str):
            value = value.replace("倍", "").strip()

        ratio_val = float(value)
        if min_val <= ratio_val <= max_val:
            return True, ratio_val
        return False, None
    except (ValueError, TypeError):
        return False, None


def check_data_quality(
    symbol: str,
    industry_info: Dict[str, Any],
    financial_estimates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    检查数据质量，识别缺失的关键字段

    Args:
        symbol: 股票代码
        industry_info: 行业信息字典
        financial_estimates: 财务指标字典

    Returns:
        包含缺失字段列表和质量评分的字典
    """
    missing_fields = []
    quality_issues = []

    # 检查行业信息
    if industry_info.get("industry") in ["未知", "", None]:
        missing_fields.append("所属行业")
        quality_issues.append("行业信息缺失，可能影响行业对比分析")

    # 检查成长性指标
    if financial_estimates.get("revenue_yoy_fmt") in ["N/A", None]:
        missing_fields.append("营收同比增速")
        quality_issues.append("营收同比增速数据缺失，无法评估营收增长情况")

    if financial_estimates.get("net_income_yoy_fmt") in ["N/A", None]:
        missing_fields.append("净利润同比增速")
        quality_issues.append("净利润同比增速数据缺失，无法评估盈利能力变化")

    # 检查核心财务指标
    if financial_estimates.get("total_revenue_fmt") in ["N/A", None]:
        missing_fields.append("营业收入")

    if financial_estimates.get("net_income_fmt") in ["N/A", None]:
        missing_fields.append("净利润")

    if financial_estimates.get("pe") in ["N/A", None]:
        missing_fields.append("市盈率(PE)")

    if financial_estimates.get("pb") in ["N/A", None]:
        missing_fields.append("市净率(PB)")

    # 计算质量评分 (满分100)
    total_critical_fields = 7  # 行业、营收增速、净利润增速、营收、净利润、PE、PB
    missing_count = len(
        [
            f
            for f in missing_fields
            if f in ["所属行业", "营收同比增速", "净利润同比增速"]
        ]
    )
    quality_score = max(0, 100 - (missing_count * 15))  # 每个关键字段缺失扣15分

    return {
        "missing_fields": missing_fields,
        "quality_issues": quality_issues,
        "quality_score": quality_score,
        "quality_level": (
            "优秀"
            if quality_score >= 90
            else "良好"
            if quality_score >= 70
            else "一般"
            if quality_score >= 50
            else "较差"
        ),
    }


def format_number_yi(value: Any, decimal_places: int = 2) -> str:
    """
    将数值格式化为亿元单位

    Args:
        value: 原始数值（元）
        decimal_places: 小数位数

    Returns:
        格式化后的字符串
    """
    if value is None or value == "N/A":
        return "N/A"

    try:
        val_yi = float(value) / 100000000.0
        return f"{val_yi:,.{decimal_places}f}"
    except (ValueError, TypeError):
        return str(value)


def format_number_wan(value: Any, decimal_places: int = 2) -> str:
    """
    将数值格式化为万元单位

    Args:
        value: 原始数值（元）
        decimal_places: 小数位数

    Returns:
        格式化后的字符串
    """
    if value is None or value == "N/A":
        return "N/A"

    try:
        val_wan = float(value) / 10000.0
        return f"{val_wan:,.{decimal_places}f}"
    except (ValueError, TypeError):
        return str(value)
