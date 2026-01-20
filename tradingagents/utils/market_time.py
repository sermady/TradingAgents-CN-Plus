#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
交易时间判断和实时行情相关工具函数
"""

from datetime import datetime, time
from typing import Dict, Optional, Tuple

import pytz

from tradingagents.utils.logging_manager import get_logger

logger = get_logger("market_time")


class MarketTimeUtils:
    """市场交易时间工具类"""

    # A股交易时间
    A_STOCK_MORNING_START = time(9, 30)  # 上午开盘
    A_STOCK_MORNING_END = time(11, 30)  # 上午收盘
    A_STOCK_AFTERNOON_START = time(13, 0)  # 下午开盘
    A_STOCK_AFTERNOON_END = time(15, 0)  # 下午收盘

    # 港股交易时间
    HK_STOCK_MORNING_START = time(9, 30)  # 上午开盘
    HK_STOCK_MORNING_END = time(12, 0)  # 上午收盘
    HK_STOCK_AFTERNOON_START = time(13, 0)  # 下午开盘
    HK_STOCK_AFTERNOON_END = time(16, 0)  # 下午收盘

    # 美股交易时间（东部时间）
    US_STOCK_REGULAR_START = time(9, 30)  # 常规交易开盘
    US_STOCK_REGULAR_END = time(16, 0)  # 常规交易收盘
    US_STOCK_PREMARKET_START = time(4, 0)  # 盘前交易开始
    US_STOCK_AFTERHOURS_END = time(20, 0)  # 盘后交易结束

    @staticmethod
    def is_a_stock_trading_time(
        check_time: Optional[datetime] = None,
    ) -> Tuple[bool, str]:
        """
        判断是否是A股交易时间

        Args:
            check_time: 要检查的时间，默认为当前时间

        Returns:
            Tuple[bool, str]: (是否交易时间, 交易状态描述)
        """
        if check_time is None:
            check_time = datetime.now(pytz.timezone("Asia/Shanghai"))
        elif check_time.tzinfo is None:
            # 如果没有时区信息，假设是上海时区
            check_time = pytz.timezone("Asia/Shanghai").localize(check_time)

        # 检查是否是工作日（周一到周五）
        if check_time.weekday() >= 5:  # 5=周六, 6=周日
            return False, "非交易日（周末）"

        current_time = check_time.time()

        # 上午交易时段
        if (
            MarketTimeUtils.A_STOCK_MORNING_START
            <= current_time
            < MarketTimeUtils.A_STOCK_MORNING_END
        ):
            return True, "盘中-上午交易时段"

        # 下午交易时段
        if (
            MarketTimeUtils.A_STOCK_AFTERNOON_START
            <= current_time
            < MarketTimeUtils.A_STOCK_AFTERNOON_END
        ):
            return True, "盘中-下午交易时段"

        # 盘前
        if current_time < MarketTimeUtils.A_STOCK_MORNING_START:
            return False, "盘前-未开盘"

        # 午间休息
        if (
            MarketTimeUtils.A_STOCK_MORNING_END
            <= current_time
            < MarketTimeUtils.A_STOCK_AFTERNOON_START
        ):
            return False, "午间休市"

        # 盘后
        if current_time >= MarketTimeUtils.A_STOCK_AFTERNOON_END:
            return False, "盘后-已收盘"

        return False, "其他时段"

    @staticmethod
    def is_hk_stock_trading_time(
        check_time: Optional[datetime] = None,
    ) -> Tuple[bool, str]:
        """
        判断是否是港股交易时间

        Args:
            check_time: 要检查的时间，默认为当前时间

        Returns:
            Tuple[bool, str]: (是否交易时间, 交易状态描述)
        """
        if check_time is None:
            check_time = datetime.now(pytz.timezone("Asia/Hong_Kong"))
        elif check_time.tzinfo is None:
            check_time = pytz.timezone("Asia/Hong_Kong").localize(check_time)

        # 检查是否是工作日
        if check_time.weekday() >= 5:
            return False, "非交易日（周末）"

        current_time = check_time.time()

        # 上午交易时段
        if (
            MarketTimeUtils.HK_STOCK_MORNING_START
            <= current_time
            < MarketTimeUtils.HK_STOCK_MORNING_END
        ):
            return True, "盘中-上午交易时段"

        # 下午交易时段
        if (
            MarketTimeUtils.HK_STOCK_AFTERNOON_START
            <= current_time
            < MarketTimeUtils.HK_STOCK_AFTERNOON_END
        ):
            return True, "盘中-下午交易时段"

        # 盘前
        if current_time < MarketTimeUtils.HK_STOCK_MORNING_START:
            return False, "盘前-未开盘"

        # 午间休息
        if (
            MarketTimeUtils.HK_STOCK_MORNING_END
            <= current_time
            < MarketTimeUtils.HK_STOCK_AFTERNOON_START
        ):
            return False, "午间休市"

        # 盘后
        if current_time >= MarketTimeUtils.HK_STOCK_AFTERNOON_END:
            return False, "盘后-已收盘"

        return False, "其他时段"

    @staticmethod
    def is_us_stock_trading_time(
        check_time: Optional[datetime] = None, include_extended: bool = False
    ) -> Tuple[bool, str]:
        """
        判断是否是美股交易时间

        Args:
            check_time: 要检查的时间，默认为当前时间
            include_extended: 是否包括盘前盘后交易

        Returns:
            Tuple[bool, str]: (是否交易时间, 交易状态描述)
        """
        if check_time is None:
            check_time = datetime.now(pytz.timezone("America/New_York"))
        elif check_time.tzinfo is None:
            check_time = pytz.timezone("America/New_York").localize(check_time)

        # 检查是否是工作日
        if check_time.weekday() >= 5:
            return False, "非交易日（周末）"

        current_time = check_time.time()

        # 常规交易时段
        if (
            MarketTimeUtils.US_STOCK_REGULAR_START
            <= current_time
            < MarketTimeUtils.US_STOCK_REGULAR_END
        ):
            return True, "盘中-常规交易时段"

        if include_extended:
            # 盘前交易
            if (
                MarketTimeUtils.US_STOCK_PREMARKET_START
                <= current_time
                < MarketTimeUtils.US_STOCK_REGULAR_START
            ):
                return True, "盘前交易时段"

            # 盘后交易
            if (
                MarketTimeUtils.US_STOCK_REGULAR_END
                <= current_time
                < MarketTimeUtils.US_STOCK_AFTERHOURS_END
            ):
                return True, "盘后交易时段"

        # 其他时段
        if current_time < MarketTimeUtils.US_STOCK_PREMARKET_START:
            return False, "未开盘"

        if current_time >= MarketTimeUtils.US_STOCK_AFTERHOURS_END:
            return False, "已收盘"

        return False, "其他时段"

    @staticmethod
    def should_use_realtime_quote(
        symbol: str, check_time: Optional[datetime] = None
    ) -> Tuple[bool, str]:
        """
        判断是否应该使用实时行情

        Args:
            symbol: 股票代码
            check_time: 要检查的时间，默认为当前时间

        Returns:
            Tuple[bool, str]: (是否使用实时行情, 原因说明)
        """
        from tradingagents.utils.stock_utils import StockMarket, StockUtils

        # 识别股票市场
        market = StockUtils.identify_stock_market(symbol)

        if market == StockMarket.CHINA_A:
            is_trading, status = MarketTimeUtils.is_a_stock_trading_time(check_time)
            if is_trading:
                return True, f"A股{status}，使用实时行情"
            else:
                return False, f"A股{status}，使用历史数据"

        elif market == StockMarket.HONG_KONG:
            is_trading, status = MarketTimeUtils.is_hk_stock_trading_time(check_time)
            if is_trading:
                return True, f"港股{status}，使用实时行情"
            else:
                return False, f"港股{status}，使用历史数据"

        elif market == StockMarket.US:
            is_trading, status = MarketTimeUtils.is_us_stock_trading_time(
                check_time, include_extended=True
            )
            if is_trading:
                return True, f"美股{status}，使用实时行情"
            else:
                return False, f"美股{status}，使用历史数据"

        else:
            return False, "未知市场，使用历史数据"

    @staticmethod
    def get_market_status(symbol: str, check_time: Optional[datetime] = None) -> Dict:
        """
        获取市场状态信息

        Args:
            symbol: 股票代码
            check_time: 要检查的时间，默认为当前时间

        Returns:
            Dict: 市场状态信息
        """
        from tradingagents.utils.stock_utils import StockMarket, StockUtils

        market = StockUtils.identify_stock_market(symbol)
        market_info = StockUtils.get_market_info(symbol)

        if market == StockMarket.CHINA_A:
            is_trading, status = MarketTimeUtils.is_a_stock_trading_time(check_time)
            timezone = "Asia/Shanghai"
        elif market == StockMarket.HONG_KONG:
            is_trading, status = MarketTimeUtils.is_hk_stock_trading_time(check_time)
            timezone = "Asia/Hong_Kong"
        elif market == StockMarket.US:
            is_trading, status = MarketTimeUtils.is_us_stock_trading_time(
                check_time, include_extended=True
            )
            timezone = "America/New_York"
        else:
            is_trading = False
            status = "未知市场"
            timezone = "UTC"

        # 获取当前时间
        if check_time is None:
            current_time = datetime.now(pytz.timezone(timezone))
        else:
            current_time = check_time

        should_use_rt, reason = MarketTimeUtils.should_use_realtime_quote(
            symbol, check_time
        )

        return {
            "symbol": symbol,
            "market": market_info["market_name"],
            "is_trading": is_trading,
            "status": status,
            "should_use_realtime": should_use_rt,
            "reason": reason,
            "timezone": timezone,
            "current_time": current_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        }


def is_trading_time(symbol: str, check_time: Optional[datetime] = None) -> bool:
    """
    简化的交易时间判断函数

    Args:
        symbol: 股票代码
        check_time: 要检查的时间，默认为当前时间

    Returns:
        bool: 是否是交易时间
    """
    should_use, _ = MarketTimeUtils.should_use_realtime_quote(symbol, check_time)
    return should_use


def get_realtime_cache_timeout(
    symbol: str, check_time: Optional[datetime] = None
) -> int:
    """
    根据市场状态获取实时数据缓存超时时间（秒）

    Args:
        symbol: 股票代码
        check_time: 要检查的时间，默认为当前时间

    Returns:
        int: 缓存超时时间（秒）
    """
    should_use_rt, _ = MarketTimeUtils.should_use_realtime_quote(symbol, check_time)

    if should_use_rt:
        # 盘中：缓存10秒
        return 10
    else:
        # 盘后：缓存1小时
        return 3600


if __name__ == "__main__":
    # 测试代码
    print("=" * 80)
    print("交易时间判断测试")
    print("=" * 80)

    test_symbols = ["600765", "00700.HK", "AAPL"]

    for symbol in test_symbols:
        print(f"\n📊 股票代码: {symbol}")
        status = MarketTimeUtils.get_market_status(symbol)
        print(f"   市场: {status['market']}")
        print(f"   当前时间: {status['current_time']}")
        print(f"   市场状态: {status['status']}")
        print(f"   是否交易中: {status['is_trading']}")
        print(f"   是否使用实时行情: {status['should_use_realtime']}")
        print(f"   原因: {status['reason']}")

    print("\n" + "=" * 80)
