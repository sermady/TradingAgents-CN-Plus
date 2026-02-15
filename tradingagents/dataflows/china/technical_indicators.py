# -*- coding: utf-8 -*-
"""
技术指标计算模块
提供常用技术指标的计算功能
"""

from typing import List, Dict, Any, Optional, Tuple
import math


class TechnicalIndicators:
    """
    技术指标计算类

    提供常用的技术分析指标计算功能
    """

    @staticmethod
    def calculate_ma(prices: List[float], period: int) -> Optional[float]:
        """
        计算移动平均线 (MA)

        Args:
            prices: 价格列表
            period: 周期

        Returns:
            MA值或None
        """
        if len(prices) < period:
            return None

        return sum(prices[-period:]) / period

    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> Optional[float]:
        """
        计算指数移动平均线 (EMA)

        Args:
            prices: 价格列表
            period: 周期

        Returns:
            EMA值或None
        """
        if len(prices) < period:
            return None

        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period  # 初始值使用SMA

        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema

        return ema

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """
        计算相对强弱指标 (RSI)

        Args:
            prices: 价格列表
            period: 周期，默认14

        Returns:
            RSI值或None
        """
        if len(prices) < period + 1:
            return None

        gains = []
        losses = []

        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        if len(gains) < period:
            return None

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def calculate_macd(
        prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        计算MACD指标

        Args:
            prices: 价格列表
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期

        Returns:
            (MACD线, 信号线, 柱状图) 元组
        """
        if len(prices) < slow + signal:
            return None, None, None

        # 计算EMA
        ema_fast = TechnicalIndicators.calculate_ema(prices, fast)
        ema_slow = TechnicalIndicators.calculate_ema(prices, slow)

        if ema_fast is None or ema_slow is None:
            return None, None, None

        macd_line = ema_fast - ema_slow

        # 计算信号线 (MACD的EMA)
        macd_values = []
        for i in range(slow, len(prices) + 1):
            ema_f = TechnicalIndicators.calculate_ema(prices[:i], fast)
            ema_s = TechnicalIndicators.calculate_ema(prices[:i], slow)
            if ema_f is not None and ema_s is not None:
                macd_values.append(ema_f - ema_s)

        signal_line = (
            TechnicalIndicators.calculate_ema(macd_values, signal)
            if len(macd_values) >= signal
            else None
        )

        histogram = (
            macd_line - signal_line if signal_line is not None else None
        )

        return macd_line, signal_line, histogram

    @staticmethod
    def calculate_bollinger_bands(
        prices: List[float], period: int = 20, std_dev: float = 2.0
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        计算布林带 (Bollinger Bands)

        Args:
            prices: 价格列表
            period: 周期
            std_dev: 标准差倍数

        Returns:
            (上轨, 中轨, 下轨) 元组
        """
        if len(prices) < period:
            return None, None, None

        middle = TechnicalIndicators.calculate_ma(prices, period)
        if middle is None:
            return None, None, None

        # 计算标准差
        recent_prices = prices[-period:]
        variance = sum((p - middle) ** 2 for p in recent_prices) / period
        std = math.sqrt(variance)

        upper = middle + std_dev * std
        lower = middle - std_dev * std

        return upper, middle, lower

    @staticmethod
    def calculate_kdj(
        highs: List[float], lows: List[float], closes: List[float], period: int = 9
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        计算KDJ指标

        Args:
            highs: 最高价列表
            lows: 最低价列表
            closes: 收盘价列表
            period: 周期

        Returns:
            (K值, D值, J值) 元组
        """
        if len(closes) < period:
            return None, None, None

        # 计算RSV
        rsv_values = []
        for i in range(period - 1, len(closes)):
            highest_high = max(highs[i - period + 1 : i + 1])
            lowest_low = min(lows[i - period + 1 : i + 1])

            if highest_high == lowest_low:
                rsv = 50
            else:
                rsv = 100 * (closes[i] - lowest_low) / (highest_high - lowest_low)

            rsv_values.append(rsv)

        if len(rsv_values) < 2:
            return None, None, None

        # 计算K、D值
        k = 50
        d = 50

        for rsv in rsv_values[:-1]:
            k = 2 / 3 * k + 1 / 3 * rsv
            d = 2 / 3 * d + 1 / 3 * k

        # 最后一个RSV
        last_rsv = rsv_values[-1]
        k = 2 / 3 * k + 1 / 3 * last_rsv
        d = 2 / 3 * d + 1 / 3 * k
        j = 3 * k - 2 * d

        return k, d, j

    @staticmethod
    def calculate_volatility(prices: List[float], period: int = 20) -> Optional[float]:
        """
        计算价格波动率

        Args:
            prices: 价格列表
            period: 周期

        Returns:
            波动率值或None
        """
        if len(prices) < period:
            return None

        recent_prices = prices[-period:]
        returns = []

        for i in range(1, len(recent_prices)):
            if recent_prices[i - 1] != 0:
                daily_return = (
                    recent_prices[i] - recent_prices[i - 1]
                ) / recent_prices[i - 1]
                returns.append(daily_return)

        if len(returns) < 2:
            return None

        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = math.sqrt(variance) * math.sqrt(252)  # 年化波动率

        return volatility

    @staticmethod
    def calculate_atr(
        highs: List[float], lows: List[float], closes: List[float], period: int = 14
    ) -> Optional[float]:
        """
        计算平均真实波幅 (ATR)

        Args:
            highs: 最高价列表
            lows: 最低价列表
            closes: 收盘价列表
            period: 周期

        Returns:
            ATR值或None
        """
        if len(closes) < period + 1:
            return None

        true_ranges = []

        for i in range(1, len(closes)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i - 1])
            tr3 = abs(lows[i] - closes[i - 1])
            true_ranges.append(max(tr1, tr2, tr3))

        if len(true_ranges) < period:
            return None

        return sum(true_ranges[-period:]) / period

    @staticmethod
    def analyze_trend(prices: List[float]) -> Dict[str, Any]:
        """
        分析价格趋势

        Args:
            prices: 价格列表

        Returns:
            趋势分析结果字典
        """
        if len(prices) < 20:
            return {"trend": "unknown", "strength": 0}

        # 计算不同周期的MA
        ma5 = TechnicalIndicators.calculate_ma(prices, 5)
        ma10 = TechnicalIndicators.calculate_ma(prices, 10)
        ma20 = TechnicalIndicators.calculate_ma(prices, 20)

        if ma5 is None or ma10 is None or ma20 is None:
            return {"trend": "unknown", "strength": 0}

        # 判断趋势
        if ma5 > ma10 > ma20:
            trend = "bullish"
            strength = min((ma5 - ma20) / ma20 * 100, 10)
        elif ma5 < ma10 < ma20:
            trend = "bearish"
            strength = min((ma20 - ma5) / ma20 * 100, 10)
        else:
            trend = "neutral"
            strength = 0

        return {
            "trend": trend,
            "strength": strength,
            "ma5": ma5,
            "ma10": ma10,
            "ma20": ma20,
        }

    @staticmethod
    def calculate_support_resistance(
        prices: List[float], period: int = 20
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        计算支撑位和阻力位

        Args:
            prices: 价格列表
            period: 周期

        Returns:
            (支撑位, 阻力位) 元组
        """
        if len(prices) < period:
            return None, None

        recent_prices = prices[-period:]
        support = min(recent_prices)
        resistance = max(recent_prices)

        return support, resistance
