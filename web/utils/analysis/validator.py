#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析参数验证工具

负责验证股票分析输入参数的有效性
"""

import re
from datetime import datetime
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("web.validator")


def validate_analysis_params(
    stock_symbol, analysis_date, analysts, research_depth, market_type="美股"
):
    """验证分析参数

    Args:
        stock_symbol: 股票代码
        analysis_date: 分析日期
        analysts: 分析师列表
        research_depth: 研究深度
        market_type: 市场类型（A股/港股/美股）

    Returns:
        tuple: (is_valid, errors) - (是否有效, 错误列表)
    """
    errors = []

    # 验证股票代码
    if not stock_symbol or len(stock_symbol.strip()) == 0:
        errors.append("股票代码不能为空")
    elif len(stock_symbol.strip()) > 10:
        errors.append("股票代码长度不能超过10个字符")
    else:
        # 根据市场类型验证代码格式
        symbol = stock_symbol.strip()
        if market_type == "A股":
            # A股：6位数字
            if not re.match(r"^\d{6}$", symbol):
                errors.append("A股代码格式错误，应为6位数字（如：000001）")
        elif market_type == "港股":
            # 港股：4-5位数字.HK 或 纯4-5位数字
            symbol_upper = symbol.upper()
            # 检查是否为 XXXX.HK 或 XXXXX.HK 格式
            hk_format = re.match(r"^\d{4,5}\.HK$", symbol_upper)
            # 检查是否为纯4-5位数字格式
            digit_format = re.match(r"^\d{4,5}$", symbol)

            if not (hk_format or digit_format):
                errors.append(
                    "港股代码格式错误，应为4位数字.HK（如：0700.HK）或4位数字（如：0700）"
                )
        elif market_type == "美股":
            # 美股：1-5位字母
            if not re.match(r"^[A-Z]{1,5}$", symbol.upper()):
                errors.append("美股代码格式错误，应为1-5位字母（如：AAPL）")

    # 验证分析师列表
    if not analysts or len(analysts) == 0:
        errors.append("必须至少选择一个分析师")

    valid_analysts = ["market", "social", "news", "fundamentals"]
    invalid_analysts = [a for a in analysts if a not in valid_analysts]
    if invalid_analysts:
        errors.append(f"无效的分析师类型: {', '.join(invalid_analysts)}")

    # 验证研究深度
    if not isinstance(research_depth, int) or research_depth < 1 or research_depth > 5:
        errors.append("研究深度必须是1-5之间的整数")

    # 验证分析日期（允许None，表示使用今天）
    if analysis_date is not None:
        try:
            datetime.strptime(analysis_date, "%Y-%m-%d")
        except ValueError:
            errors.append("分析日期格式无效，应为YYYY-MM-DD格式")

    return len(errors) == 0, errors


def get_supported_stocks():
    """获取支持的股票列表

    Returns:
        list: 支持的股票列表，每个股票包含symbol、name、sector字段
    """
    # 常见的美股股票代码
    popular_stocks = [
        {"symbol": "AAPL", "name": "苹果公司", "sector": "科技"},
        {"symbol": "MSFT", "name": "微软", "sector": "科技"},
        {"symbol": "GOOGL", "name": "谷歌", "sector": "科技"},
        {"symbol": "AMZN", "name": "亚马逊", "sector": "消费"},
        {"symbol": "TSLA", "name": "特斯拉", "sector": "汽车"},
        {"symbol": "NVDA", "name": "英伟达", "sector": "科技"},
        {"symbol": "META", "name": "Meta", "sector": "科技"},
        {"symbol": "NFLX", "name": "奈飞", "sector": "媒体"},
        {"symbol": "AMD", "name": "AMD", "sector": "科技"},
        {"symbol": "INTC", "name": "英特尔", "sector": "科技"},
        {"symbol": "SPY", "name": "S&P 500 ETF", "sector": "ETF"},
        {"symbol": "QQQ", "name": "纳斯达克100 ETF", "sector": "ETF"},
    ]

    return popular_stocks
