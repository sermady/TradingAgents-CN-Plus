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
            target_date = datetime.strptime(requested_date, '%Y-%m-%d')
        else:
            target_date = now

        # 回溯查找最近的有效交易日（排除周末）
        # 注意：这里只处理周末，不处理节假日（需要外部日历数据）
        while target_date.weekday() >= 5:  # 5=周六, 6=周日
            target_date = target_date - timedelta(days=1)

        latest_trading_date = target_date.strftime('%Y-%m-%d')

        # 更新缓存
        self._cached_date = latest_trading_date
        self._cached_until = now + timedelta(minutes=self._cache_ttl_minutes)

        logger.info(f"📅 [交易日管理器] 确定最新交易日: {latest_trading_date}")
        return latest_trading_date

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
