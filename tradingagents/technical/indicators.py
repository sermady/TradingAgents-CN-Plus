# -*- coding: utf-8 -*-
"""
统一技术指标计算模块
提供统一的技术指标计算接口,减少代码重复
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


class TechnicalIndicators:
    """技术指标计算器"""

    @staticmethod
    def calculate_ma(
        data: pd.DataFrame, periods: list = [5, 10, 20, 60], price_col: str = "close"
    ) -> pd.DataFrame:
        """
        计算移动平均线

        Args:
            data: 股票数据DataFrame
            periods: 均线周期列表
            price_col: 价格列名

        Returns:
            添加了MA列的DataFrame
        """
        df = data.copy()

        for period in periods:
            df[f"ma{period}"] = (
                df[price_col].rolling(window=period, min_periods=1).mean()
            )

        return df

    @staticmethod
    def calculate_rsi(
        data: pd.DataFrame,
        period: int = 14,
        price_col: str = "close",
        style: str = "simple",  # simple 或 sma
    ) -> pd.DataFrame:
        """
        计算RSI相对强弱指标

        Args:
            data: 股票数据DataFrame
            period: 周期
            price_col: 价格列名
            style: 计算风格 (simple/SMA 或 exponential/EMA)

        Returns:
            添加了RSI列的DataFrame
        """
        df = data.copy()

        # 计算价格变化
        delta = df[price_col].diff()

        # 分离上涨和下跌
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        if style == "simple":
            # 简单移动平均
            avg_gain = gain.rolling(window=period, min_periods=1).mean()
            avg_loss = loss.rolling(window=period, min_periods=1).mean()
        elif style == "sma":
            # 指数平滑移动平均 (中国式SMA)
            # SMA with N-1 adjust factor, equivalent to ewm(com=N-1, adjust=True)
            avg_gain = gain.ewm(com=period - 1, adjust=True).mean()
            avg_loss = loss.ewm(com=period - 1, adjust=True).mean()
        else:  # exponential
            # 指数移动平均
            avg_gain = gain.ewm(span=period, adjust=False).mean()
            avg_loss = loss.ewm(span=period, adjust=False).mean()

        # 避免除以0
        avg_gain = avg_gain.replace(0, np.nan)
        avg_loss = avg_loss.replace(0, np.nan)

        # 计算RS
        rs = avg_gain / avg_loss

        df[f"rsi{period}"] = 100 - (100 / (1 + rs))

        return df

    @staticmethod
    def calculate_macd(
        data: pd.DataFrame,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        price_col: str = "close",
    ) -> pd.DataFrame:
        """
        计算MACD指标

        Args:
            data: 股票数据DataFrame
            fast_period: 快速EMA周期
            slow_period: 慢速EMA周期
            signal_period: 信号线EMA周期
            price_col: 价格列名

        Returns:
            添加了MACD列的DataFrame
        """
        df = data.copy()

        # 计算EMA
        ema_fast = df[price_col].ewm(span=fast_period, adjust=False).mean()
        ema_slow = df[price_col].ewm(span=slow_period, adjust=False).mean()

        # 计算DIF
        df["macd_dif"] = ema_fast - ema_slow

        # 计算DEA (DIF的EMA)
        df["macd_dea"] = df["macd_dif"].ewm(span=signal_period, adjust=False).mean()

        # 计算MACD柱状图
        df["macd"] = (df["macd_dif"] - df["macd_dea"]) * 2

        return df

    @staticmethod
    def calculate_boll(
        data: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0,
        price_col: str = "close",
    ) -> pd.DataFrame:
        """
        计算布林带

        Args:
            data: 股票数据DataFrame
            period: 周期
            std_dev: 标准差倍数
            price_col: 价格列名

        Returns:
            添加了BOLL列的DataFrame
        """
        df = data.copy()

        # 计算中轨(MA)
        df["boll_mid"] = df[price_col].rolling(window=period, min_periods=1).mean()

        # 计算标准差
        std = df[price_col].rolling(window=period, min_periods=1).std()

        # 计算上轨和下轨
        df["boll_upper"] = df["boll_mid"] + std_dev * std
        df["boll_lower"] = df["boll_mid"] - std_dev * std

        return df

    @staticmethod
    def calculate_all_indicators(
        data: pd.DataFrame,
        price_col: str = "close",
        rsi_style: str = "sma",
    ) -> pd.DataFrame:
        """
        计算所有技术指标

        Args:
            data: 股票数据DataFrame
            price_col: 价格列名
            rsi_style: RSI计算风格 (simple/sma/exponential)

        Returns:
            添加了所有技术指标的DataFrame
        """
        df = data.copy()

        # 确保数据按日期排序
        if "date" in df.columns:
            df = df.sort_values("date")

        # 计算所有指标
        df = TechnicalIndicators.calculate_ma(df, price_col=price_col)
        df = TechnicalIndicators.calculate_rsi(df, price_col=price_col, style=rsi_style)
        df = TechnicalIndicators.calculate_macd(df, price_col=price_col)
        df = TechnicalIndicators.calculate_boll(df, price_col=price_col)

        # 添加中国式RSI (6, 12, 24)
        df = TechnicalIndicators.calculate_rsi(
            df, period=6, price_col=price_col, style="sma"
        )
        df = TechnicalIndicators.calculate_rsi(
            df, period=12, price_col=price_col, style="sma"
        )
        df = TechnicalIndicators.calculate_rsi(
            df, period=24, price_col=price_col, style="sma"
        )

        return df

    @staticmethod
    def get_indicator_summary(
        data: pd.DataFrame,
        price_col: str = "close",
        n_days: int = 5,
    ) -> Dict[str, Any]:
        """
        获取技术指标摘要

        Args:
            data: 股票数据DataFrame
            price_col: 价格列名
            n_days: 最近n天数据

        Returns:
            技术指标摘要字典
        """
        if len(data) == 0:
            return {}

        # 获取最近n天数据
        recent_data = data.tail(n_days)

        latest = recent_data.iloc[-1]

        # 提取关键指标
        summary = {
            "current_price": latest[price_col] if price_col in latest else 0,
            "ma5": latest.get("ma5", 0),
            "ma10": latest.get("ma10", 0),
            "ma20": latest.get("ma20", 0),
            "ma60": latest.get("ma60", 0),
            "rsi6": latest.get("rsi6", 50),
            "rsi12": latest.get("rsi12", 50),
            "rsi24": latest.get("rsi24", 50),
            "rsi14": latest.get("rsi14", 50),
            "macd_dif": latest.get("macd_dif", 0),
            "macd_dea": latest.get("macd_dea", 0),
            "macd": latest.get("macd", 0),
            "boll_upper": latest.get("boll_upper", 0),
            "boll_mid": latest.get("boll_mid", 0),
            "boll_lower": latest.get("boll_lower", 0),
        }

        # 添加趋势判断
        summary["trend"] = TechnicalIndicators._determine_trend(summary)
        summary["signal"] = TechnicalIndicators._determine_signal(summary)

        return summary

    @staticmethod
    def _determine_trend(summary: Dict[str, Any]) -> str:
        """
        确定趋势

        Args:
            summary: 技术指标摘要

        Returns:
            趋势 (up/down/neutral)
        """
        price = summary["current_price"]
        ma5 = summary["ma5"]
        ma10 = summary["ma10"]
        ma20 = summary["ma20"]
        ma60 = summary["ma60"]

        if price > ma5 > ma10 > ma20:
            return "up"
        elif price < ma5 < ma10 < ma20:
            return "down"
        else:
            return "neutral"

    @staticmethod
    def _determine_signal(summary: Dict[str, Any]) -> str:
        """
        确定交易信号

        Args:
            summary: 技术指标摘要

        Returns:
            信号 (buy/sell/neutral)
        """
        macd = summary["macd"]
        macd_dif = summary["macd_dif"]
        macd_dea = summary["macd_dea"]

        rsi6 = summary["rsi6"]
        rsi12 = summary["rsi12"]
        rsi24 = summary["rsi24"]

        # MACD金叉/死叉
        if macd_dif > macd_dea and macd > 0:
            return "buy"
        elif macd_dif < macd_dea and macd < 0:
            return "sell"
        # RSI超买超卖
        elif rsi6 >= 80:
            return "sell"
        elif rsi6 <= 20:
            return "buy"
        else:
            return "neutral"


def calculate_indicators_for_report(
    data: pd.DataFrame,
    currency_symbol: str = "¥",
) -> str:
    """
    为报告格式化技术指标

    Args:
        data: 股票数据DataFrame
        currency_symbol: 货币符号

    Returns:
        格式化的技术指标字符串
    """
    if data is None or data.empty:
        return "无法计算技术指标"

    # 计算所有指标
    data = TechnicalIndicators.calculate_all_indicators(data)

    # 获取摘要
    summary = TechnicalIndicators.get_indicator_summary(data.tail(60))

    latest = data.iloc[-1]

    # 计算涨跌
    prev_close = data.iloc[-2]["close"] if len(data) > 1 else latest["close"]
    change = latest["close"] - prev_close
    change_pct = (change / prev_close * 100) if prev_close != 0 else 0

    # 格式化输出
    result = f"""
## 技术指标分析

### 最新价格
- 当前价格: {currency_symbol}{latest["close"]:.2f}
- 涨跌额: {currency_symbol}{change:+.2f} ({change_pct:+.2f}%)

### 移动平均线
- MA5: {currency_symbol}{summary["ma5"]:.2f} ({"价格上方 ↑" if latest["close"] > summary["ma5"] else "价格下方 ↓"})
- MA10: {currency_symbol}{summary["ma10"]:.2f} ({"价格上方 ↑" if latest["close"] > summary["ma10"] else "价格下方 ↓"})
- MA20: {currency_symbol}{summary["ma20"]:.2f} ({"价格上方 ↑" if latest["close"] > summary["ma20"] else "价格下方 ↓"})
- MA60: {currency_symbol}{summary["ma60"]:.2f}

### MACD指标
- DIF: {summary["macd_dif"]:.4f}
- DEA: {summary["macd_dea"]:.4f}
- MACD: {summary["macd"]:.4f} ({"多头 ↑" if summary["macd"] > 0 else "空头 ↓"})

### RSI指标
- RSI6: {summary["rsi6"]:.2f} ({"超买" if summary["rsi6"] >= 80 else "超卖" if summary["rsi6"] <= 20 else "正常"})
- RSI12: {summary["rsi12"]:.2f}
- RSI24: {summary["rsi24"]:.2f}
- RSI14 (国际标准): {summary["rsi14"]:.2f}

### 布林带
- 上轨: {currency_symbol}{summary["boll_upper"]:.2f}
- 中轨: {currency_symbol}{summary["boll_mid"]:.2f}
- 下轨: {currency_symbol}{summary["boll_lower"]:.2f}
- 价格位置: {((latest["close"] - summary["boll_lower"]) / (summary["boll_upper"] - summary["boll_lower"]) * 100):.1f}%

### 综合判断
- 趋势: {summary["trend"].upper()}
- 信号: {summary["signal"].upper()}
"""

    return result.strip()
