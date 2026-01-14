# -*- coding: utf-8 -*-
"""
交易时段判断工具

用于判断当前时间是否在交易时段内，支持 A股、港股、美股 市场
"""

from datetime import datetime, time
from typing import Tuple, Optional
import pytz

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


class TradingHoursChecker:
    """交易时段检查器"""

    # A股交易时段（北京时间）
    A_SHARES_SESSIONS = [
        (time(9, 30), time(11, 30)),   # 上午盘
        (time(13, 0), time(15, 0)),    # 下午盘
    ]

    # 美股交易时段（纽约时间）
    US_STOCKS_SESSIONS = [
        (time(9, 30), time(16, 0)),    # 常规交易
    ]

    # 港股交易时段（香港时间）
    HK_STOCKS_SESSIONS = [
        (time(9, 30), time(12, 0)),    # 上午盘
        (time(13, 0), time(16, 0)),    # 下午盘
    ]

    # 时区映射
    TIMEZONE_MAP = {
        "A股": "Asia/Shanghai",
        "美股": "America/New_York",
        "港股": "Asia/Hong_Kong",
    }

    @classmethod
    def is_trading_hours(cls, market_type: str = "A股") -> bool:
        """
        判断当前是否在交易时段内

        Args:
            market_type: 市场类型 (A股/美股/港股)

        Returns:
            bool: 是否在交易时段
        """
        try:
            now = cls._get_market_time(market_type)
            sessions = cls._get_sessions(market_type)

            # 检查是否是交易日（周一到周五）
            if now.weekday() >= 5:  # 周六=5, 周日=6
                return False

            # 检查是否在交易时段内
            current_time = now.time()
            for start, end in sessions:
                if start <= current_time <= end:
                    return True

            return False
        except Exception as e:
            logger.warning(f"检查交易时段失败: {e}")
            return False

    @classmethod
    def get_market_status(cls, market_type: str = "A股") -> Tuple[str, str]:
        """
        获取市场状态

        Args:
            market_type: 市场类型

        Returns:
            Tuple[str, str]: (状态, 描述)
            状态: trading / pre_market / post_market / closed / lunch_break
        """
        try:
            now = cls._get_market_time(market_type)
            sessions = cls._get_sessions(market_type)

            # 周末
            if now.weekday() >= 5:
                return ("closed", "周末休市")

            current_time = now.time()

            # 检查是否在交易时段
            for i, (start, end) in enumerate(sessions):
                if start <= current_time <= end:
                    return ("trading", "交易中")

            # 检查是否在盘前
            first_session_start = sessions[0][0]
            if current_time < first_session_start:
                return ("pre_market", "盘前")

            # 检查是否在午间休市（A股和港股有午休）
            if len(sessions) > 1:
                morning_end = sessions[0][1]
                afternoon_start = sessions[1][0]
                if morning_end < current_time < afternoon_start:
                    return ("lunch_break", "午间休市")

            # 盘后
            last_session_end = sessions[-1][1]
            if current_time > last_session_end:
                return ("post_market", "盘后")

            return ("closed", "休市")
        except Exception as e:
            logger.warning(f"获取市场状态失败: {e}")
            return ("unknown", "状态未知")

    @classmethod
    def is_trading_day(cls, market_type: str = "A股", check_date: datetime = None) -> bool:
        """
        判断指定日期是否是交易日（仅检查周末，不检查节假日）

        Args:
            market_type: 市场类型
            check_date: 要检查的日期，默认今天

        Returns:
            bool: 是否是交易日
        """
        if check_date is None:
            check_date = cls._get_market_time(market_type)

        # 周末不是交易日
        return check_date.weekday() < 5

    @classmethod
    def get_next_trading_session(cls, market_type: str = "A股") -> Optional[Tuple[str, str]]:
        """
        获取下一个交易时段的开始和结束时间

        Args:
            market_type: 市场类型

        Returns:
            Tuple[str, str]: (开始时间, 结束时间) 或 None
        """
        try:
            now = cls._get_market_time(market_type)
            sessions = cls._get_sessions(market_type)
            current_time = now.time()

            for start, end in sessions:
                if current_time < start:
                    return (start.strftime("%H:%M"), end.strftime("%H:%M"))

            # 今日所有时段已过，返回明天第一个时段
            if sessions:
                start, end = sessions[0]
                return (start.strftime("%H:%M"), end.strftime("%H:%M"))

            return None
        except Exception as e:
            logger.warning(f"获取下一交易时段失败: {e}")
            return None

    @classmethod
    def _get_market_time(cls, market_type: str) -> datetime:
        """获取市场所在时区的当前时间"""
        tz_name = cls.TIMEZONE_MAP.get(market_type, "Asia/Shanghai")
        tz = pytz.timezone(tz_name)
        return datetime.now(tz)

    @classmethod
    def _get_sessions(cls, market_type: str) -> list:
        """获取市场交易时段"""
        sessions_map = {
            "A股": cls.A_SHARES_SESSIONS,
            "美股": cls.US_STOCKS_SESSIONS,
            "港股": cls.HK_STOCKS_SESSIONS,
        }
        return sessions_map.get(market_type, cls.A_SHARES_SESSIONS)


# 便捷函数
def is_trading_hours(market_type: str = "A股") -> bool:
    """便捷函数：判断是否在交易时段"""
    return TradingHoursChecker.is_trading_hours(market_type)


def get_market_status(market_type: str = "A股") -> Tuple[str, str]:
    """便捷函数：获取市场状态"""
    return TradingHoursChecker.get_market_status(market_type)


def is_trading_day(market_type: str = "A股", check_date: datetime = None) -> bool:
    """便捷函数：判断是否是交易日"""
    return TradingHoursChecker.is_trading_day(market_type, check_date)


def get_next_trading_session(market_type: str = "A股") -> Optional[Tuple[str, str]]:
    """便捷函数：获取下一个交易时段"""
    return TradingHoursChecker.get_next_trading_session(market_type)


if __name__ == "__main__":
    # 测试代码
    print("=" * 50)
    print("交易时段工具测试")
    print("=" * 50)

    for market in ["A股", "港股", "美股"]:
        print(f"\n--- {market} ---")
        print(f"  当前是否在交易时段: {is_trading_hours(market)}")
        status, desc = get_market_status(market)
        print(f"  市场状态: {status} ({desc})")
        print(f"  是否交易日: {is_trading_day(market)}")
        next_session = get_next_trading_session(market)
        if next_session:
            print(f"  下一交易时段: {next_session[0]} - {next_session[1]}")
