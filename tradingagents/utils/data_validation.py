# -*- coding: utf-8 -*-
"""
统一数据验证工具

提供各种数据验证函数，用于检查分析师报告中的数据是否合理
"""

import logging
from typing import Dict, List, Optional, Union
import pandas as pd

logger = logging.getLogger(__name__)


def validate_technical_indicators(data: Union[dict, pd.DataFrame]) -> Dict:
    """
    验证技术指标数据是否合理

    Args:
        data: 技术指标数据，可以是字典或DataFrame

    Returns:
        包含验证结果的字典
    """
    issues = []

    # 转换DataFrame为字典以便统一处理
    if isinstance(data, pd.DataFrame):
        try:
            data_dict = data.to_dict("records")[0] if len(data) > 0 else {}
        except Exception as e:
            logger.error(f"DataFrame转字典失败: {e}")
            data_dict = {}
    else:
        data_dict = data

    # 验证 MA (移动平均线)
    ma_keys = ["MA5", "MA10", "MA20", "MA60"]
    for key in ma_keys:
        if key in data_dict:
            value = data_dict[key]
            try:
                ma_value = float(value)
                if not (0 < ma_value < 100000):  # 股价范围：0-10万
                    issues.append(f"{key}值异常: {ma_value}（应在 0-100000 之间）")
            except (ValueError, TypeError):
                issues.append(f"{key}值格式错误: {value}（应为数字）")

    # 验证 MACD
    macd_keys = ["DIF", "DEA", "MACD"]
    for key in macd_keys:
        if key in data_dict:
            value = data_dict[key]
            try:
                macd_value = float(value)
                # MACD值通常在-1000到1000之间
                if not (-1000 <= macd_value <= 1000):
                    issues.append(
                        f"{key}值异常: {macd_value}（应在 -1000 到 1000 之间）"
                    )
            except (ValueError, TypeError):
                issues.append(f"{key}值格式错误: {value}（应为数字）")

    # 验证 RSI
    if "RSI" in data_dict:
        rsi = data_dict["RSI"]
        try:
            rsi_value = float(rsi)
            if not (0 <= rsi_value <= 100):
                issues.append(f"RSI值异常: {rsi_value}（应在 0-100 之间）")
        except (ValueError, TypeError):
            issues.append(f"RSI值格式错误: {rsi}（应为数字）")

    # 验证布林带
    boll_keys = ["BOLL_UPPER", "BOLL_MIDDLE", "BOLL_LOWER"]
    for key in boll_keys:
        if key in data_dict:
            value = data_dict[key]
            try:
                boll_value = float(value)
                if not (0 < boll_value < 100000):
                    issues.append(f"{key}值异常: {boll_value}（应在 0-100000 之间）")
            except (ValueError, TypeError):
                issues.append(f"{key}值格式错误: {value}（应为数字）")

    # 验证价格和成交量
    if "close" in data_dict:
        close = data_dict["close"]
        try:
            close_value = float(close)
            if not (0 < close_value < 100000):
                issues.append(f"收盘价异常: {close_value}（应在 0-100000 之间）")
        except (ValueError, TypeError):
            issues.append(f"收盘价格式错误: {close}（应为数字）")

    if "volume" in data_dict:
        volume = data_dict["volume"]
        try:
            volume_value = float(volume)
            if volume_value < 0:
                issues.append(f"成交量异常: {volume_value}（不能为负数）")
        except (ValueError, TypeError):
            issues.append(f"成交量格式错误: {volume}（应为数字）")

    return {"valid": len(issues) == 0, "issues": issues}


def validate_fundamentals(data: Union[dict, pd.DataFrame]) -> Dict:
    """
    验证基本面数据是否合理

    Args:
        data: 基本面数据，可以是字典或DataFrame

    Returns:
        包含验证结果的字典
    """
    issues = []

    # 转换DataFrame为字典以便统一处理
    if isinstance(data, pd.DataFrame):
        try:
            data_dict = data.to_dict("records")[0] if len(data) > 0 else {}
        except Exception as e:
            logger.error(f"DataFrame转字典失败: {e}")
            data_dict = {}
    else:
        data_dict = data

    # 验证 PE (市盈率)
    if "PE" in data_dict:
        pe = data_dict["PE"]
        try:
            pe_value = float(pe)
            if not (-100 < pe_value < 1000):  # PE可以为负（亏损），但不应太极端
                issues.append(f"PE值异常: {pe_value}（通常在 -100 到 1000 之间）")
        except (ValueError, TypeError):
            issues.append(f"PE值格式错误: {pe}（应为数字）")

    # 验证 PB (市净率)
    if "PB" in data_dict:
        pb = data_dict["PB"]
        try:
            pb_value = float(pb)
            if not (-10 < pb_value < 100):
                issues.append(f"PB值异常: {pb_value}（通常在 -10 到 100 之间）")
        except (ValueError, TypeError):
            issues.append(f"PB值格式错误: {pb}（应为数字）")

    # 验证 ROE (净资产收益率)
    if "ROE" in data_dict:
        roe = data_dict["ROE"]
        try:
            roe_value = float(roe)
            if not (-100 <= roe_value <= 100):  # ROE可以为负，但不应太极端
                issues.append(f"ROE值异常: {roe_value}（通常在 -100% 到 100% 之间）")
        except (ValueError, TypeError):
            issues.append(f"ROE值格式错误: {roe}（应为数字）")

    # 验证 growth_rate (增长率)
    if "growth_rate" in data_dict:
        growth = data_dict["growth_rate"]
        try:
            growth_value = float(growth)
            if not (-50 <= growth_value <= 500):  # 增长率范围较宽
                issues.append(f"增长率异常: {growth_value}（通常在 -50% 到 500% 之间）")
        except (ValueError, TypeError):
            issues.append(f"增长率格式错误: {growth}（应为数字）")

    # 验证 revenue (营收)
    if "revenue" in data_dict:
        revenue = data_dict["revenue"]
        try:
            revenue_value = float(revenue)
            if revenue_value < 0:
                issues.append(f"营收异常: {revenue_value}（不能为负数）")
        except (ValueError, TypeError):
            issues.append(f"营收格式错误: {revenue}（应为数字）")

    # 验证 net_profit (净利润)
    if "net_profit" in data_dict:
        profit = data_dict["net_profit"]
        try:
            profit_value = float(profit)
            # 净利润可以为负，但不应太极端
            if not (-(10**12) < profit_value < 10**12):
                issues.append(f"净利润异常: {profit_value}（超出合理范围）")
        except (ValueError, TypeError):
            issues.append(f"净利润格式错误: {profit}（应为数字）")

    return {"valid": len(issues) == 0, "issues": issues}


def validate_sentiment(data: Union[dict, str, None]) -> Dict:
    """
    验证情绪数据是否合理

    Args:
        data: 情绪数据，可以是字典、字符串或None

    Returns:
        包含验证结果的字典
    """
    issues = []

    if data is None:
        return {"valid": False, "issues": ["情绪数据为空"]}

    # 如果是字符串，检查是否有足够的内容
    if isinstance(data, str):
        if len(data.strip()) < 50:
            issues.append(f"情绪数据过短: {len(data)}字符（至少需要50字符）")

    # 如果是字典，验证情绪指数
    if isinstance(data, dict):
        # 验证情绪指数评分 (1-10分)
        if "sentiment_score" in data:
            score = data["sentiment_score"]
            try:
                score_value = float(score)
                if not (1 <= score_value <= 10):
                    issues.append(f"情绪指数评分异常: {score_value}（应在 1-10 之间）")
            except (ValueError, TypeError):
                issues.append(f"情绪指数评分格式错误: {score}（应为数字）")

        # 验证情绪类别
        valid_sentiments = [
            "bullish",
            "bearish",
            "neutral",
            "strong_bullish",
            "strong_bearish",
        ]
        if "sentiment" in data:
            sentiment = data["sentiment"]
            if isinstance(sentiment, str) and sentiment.lower() not in valid_sentiments:
                issues.append(
                    f"情绪类别异常: {sentiment}（应为: {', '.join(valid_sentiments)}）"
                )

        # 验证波动幅度
        if "volatility" in data:
            volatility = data["volatility"]
            try:
                volatility_value = float(volatility)
                if volatility_value < 0:
                    issues.append(f"波动幅度异常: {volatility_value}（不能为负数）")
            except (ValueError, TypeError):
                issues.append(f"波动幅度格式错误: {volatility}（应为数字）")

    return {"valid": len(issues) == 0, "issues": issues}


def validate_price_data(data: Union[dict, float, int, None]) -> Dict:
    """
    验证价格数据是否合理

    Args:
        data: 价格数据，可以是字典、数字或None

    Returns:
        包含验证结果的字典
    """
    issues = []

    if data is None:
        return {"valid": False, "issues": ["价格数据为空"]}

    # 如果是数字，直接验证范围
    if isinstance(data, (int, float)):
        price_value = float(data)
        if not (0 < price_value < 100000):
            issues.append(f"价格异常: {price_value}（应在 0-100000 之间）")
    elif isinstance(data, dict):
        # 验证目标价格
        if "target_price" in data:
            target = data["target_price"]
            try:
                target_value = float(target)
                if not (0 < target_value < 100000):
                    issues.append(f"目标价格异常: {target_value}（应在 0-100000 之间）")
            except (ValueError, TypeError):
                issues.append(f"目标价格格式错误: {target}（应为数字）")

        # 验证止损价格
        if "stop_loss" in data:
            stop_loss = data["stop_loss"]
            try:
                stop_loss_value = float(stop_loss)
                if stop_loss_value < 0:
                    issues.append(f"止损价格异常: {stop_loss_value}（不能为负数）")
            except (ValueError, TypeError):
                issues.append(f"止损价格格式错误: {stop_loss}（应为数字）")

        # 验证支撑位
        if "support" in data:
            support = data["support"]
            try:
                support_value = float(support)
                if support_value < 0:
                    issues.append(f"支撑位异常: {support_value}（不能为负数）")
            except (ValueError, TypeError):
                issues.append(f"支撑位格式错误: {support}（应为数字）")

        # 验证压力位
        if "resistance" in data:
            resistance = data["resistance"]
            try:
                resistance_value = float(resistance)
                if resistance_value < 0:
                    issues.append(f"压力位异常: {resistance_value}（不能为负数）")
            except (ValueError, TypeError):
                issues.append(f"压力位格式错误: {resistance}（应为数字）")

    return {"valid": len(issues) == 0, "issues": issues}


def get_validation_summary(validation_results: List[Dict]) -> str:
    """
    生成验证结果摘要

    Args:
        validation_results: 验证结果列表

    Returns:
        验证摘要字符串
    """
    all_issues = []
    for result in validation_results:
        if "issues" in result and result["issues"]:
            all_issues.extend(result["issues"])

    if len(all_issues) == 0:
        return "✅ 所有数据验证通过，数据质量良好"

    summary = f"⚠️ 发现 {len(all_issues)} 个数据问题：\n\n"
    for i, issue in enumerate(all_issues[:20], 1):  # 最多显示20个问题
        summary += f"{i}. {issue}\n"

    if len(all_issues) > 20:
        summary += f"\n... 还有 {len(all_issues) - 20} 个问题未显示"

    return summary
