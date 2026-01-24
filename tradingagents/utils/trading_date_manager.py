# -*- coding: utf-8 -*-
"""
交易日管理器 - 确保所有分析师使用同一交易日数据

解决技术分析和基本面分析报告价格不一致的问题
通过统一管理交易日和价格缓存，确保所有分析师使用相同的数据基准
"""

from datetime import datetime, timedelta
from typing import Optional
import logging
import threading

logger = logging.getLogger(__name__)


class TradingDateManager:
    """交易日管理器 - 单例模式

    功能：
    1. 确定最新的有效交易日（排除周末）
    2. 缓存交易日结果（避免重复计算）
    3. 线程安全
    """

    _instance = None
    _lock = None

    def __new__(cls):
        if cls._instance is None:
            cls._lock = threading.Lock()
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._cached_date = None
        self._cached_until = None
        self._cache_ttl_minutes = 60  # 缓存1小时
        self._initialized = True

    def get_latest_trading_date(self, requested_date: Optional[str] = None) -> str:
        """
        获取最新的有效交易日

        Args:
            requested_date: 请求的日期 (YYYY-MM-DD)，如果为None则使用今天

        Returns:
            最新的有效交易日 (YYYY-MM-DD)
        """
        now = datetime.now()

        # 检查缓存
        if self._cached_date and self._cached_until and now < self._cached_until:
            logger.debug(f"📅 [交易日管理器] 使用缓存的交易日: {self._cached_date}")
            return self._cached_date

        # 确定目标日期
        if requested_date:
            target_date = datetime.strptime(requested_date, "%Y-%m-%d")
        else:
            target_date = now

        # 回溯查找最近的有效交易日（排除周末）
        # 注意：这里只处理周末，不处理节假日（需要外部日历数据）
        while target_date.weekday() >= 5:  # 5=周六, 6=周日
            target_date = target_date - timedelta(days=1)

        latest_trading_date = target_date.strftime("%Y-%m-%d")

        # 更新缓存
        self._cached_date = latest_trading_date
        self._cached_until = now + timedelta(minutes=self._cache_ttl_minutes)

        logger.info(f"📅 [交易日管理器] 确定最新交易日: {latest_trading_date}")
        return latest_trading_date

    def get_trading_date_range(
        self, target_date=None, lookback_days: int = 10
    ) -> tuple:
        """
        获取用于查询交易数据的日期范围

        策略：获取最近N天的数据，以确保能获取到最后一个交易日的数据
        自动调整周末日期到最近的交易日，处理周末、节假日和数据延迟的情况

        使用统一的交易日管理器，确保所有分析师使用相同的日期基准

        Args:
            target_date: 目标日期（datetime对象或字符串YYYY-MM-DD），默认为今天
            lookback_days: 向前查找的天数，默认10天（可以覆盖周末+小长假）

        Returns:
            tuple: (start_date, end_date) 两个字符串，格式YYYY-MM-DD

        Example:
            >>> mgr.get_trading_date_range("2025-10-13", 10)
            ("2025-10-03", "2025-10-13")

            >>> mgr.get_trading_date_range("2025-10-12", 10)  # 周日
            ("2025-10-02", "2025-10-10")  # 自动调整到周五
        """
        from datetime import datetime as dt

        # 处理输入日期
        if target_date is None:
            target_date = dt.now()
        elif isinstance(target_date, str):
            target_date = dt.strptime(target_date, "%Y-%m-%d")

        # 如果是未来日期，使用今天
        today = dt.now()
        if target_date.date() > today.date():
            target_date = today

        # 🔧 调整：使用统一的交易日管理器处理周末
        # 调用 get_latest_trading_date 获取有效交易日（带缓存）
        if target_date.weekday() >= 5:  # 5=周六, 6=周日
            # 使用交易日管理器调整到最近的工作日
            adjusted_date_str = self.get_latest_trading_date(
                target_date.strftime("%Y-%m-%d")
            )
            target_date = dt.strptime(adjusted_date_str, "%Y-%m-%d")
            logger.info(
                f"📅 [交易日管理器] target_date={adjusted_date_str} (原始是周末，已调整为最近交易日)"
            )

        # 计算开始日期（向前推N天）
        start_date = target_date - timedelta(days=lookback_days)

        return start_date.strftime("%Y-%m-%d"), target_date.strftime("%Y-%m-%d")

    def clear_cache(self):
        """清除缓存"""
        self._cached_date = None
        self._cached_until = None
        logger.debug("🗑️ [交易日管理器] 缓存已清除")


# 全局访问函数
_trading_date_manager_instance = None


def get_trading_date_manager() -> TradingDateManager:
    """获取交易日管理器实例"""
    global _trading_date_manager_instance
    if _trading_date_manager_instance is None:
        _trading_date_manager_instance = TradingDateManager()
    return _trading_date_manager_instance
