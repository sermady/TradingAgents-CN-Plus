# -*- coding: utf-8 -*-
"""
Base classes and shared typing for data source adapters
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class DataSourceAdapter(ABC):
    """数据源适配器基类"""

    def __init__(self):
        self._priority: Optional[int] = None  # 动态优先级，从数据库加载

    @property
    @abstractmethod
    def name(self) -> str:
        """数据源名称"""
        raise NotImplementedError

    @property
    def priority(self) -> int:
        """数据源优先级（数字越小优先级越高）"""
        # 如果有动态设置的优先级，使用动态优先级；否则使用默认优先级
        if self._priority is not None:
            return self._priority
        return self._get_default_priority()

    @abstractmethod
    def _get_default_priority(self) -> int:
        """获取默认优先级（子类实现）"""
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """检查数据源是否可用"""
        raise NotImplementedError

    @abstractmethod
    def get_stock_list(self) -> Optional[pd.DataFrame]:
        """获取股票列表"""
        raise NotImplementedError

    @abstractmethod
    def get_daily_basic(self, trade_date: str) -> Optional[pd.DataFrame]:
        """获取每日基础财务数据"""
        raise NotImplementedError

    @abstractmethod
    def find_latest_trade_date(self) -> Optional[str]:
        """查找最新交易日期"""
        raise NotImplementedError

    # ==================== 通用工具方法 ====================

    @staticmethod
    def _validate_trade_date(trade_date: str) -> None:
        """
        验证交易日期格式 (YYYYMMDD)

        Args:
            trade_date: 交易日期字符串

        Raises:
            ValueError: 日期格式无效
        """
        if not trade_date or not isinstance(trade_date, str):
            raise ValueError(f"trade_date 必须是非空字符串，收到: {trade_date}")

        if len(trade_date) != 8 or not trade_date.isdigit():
            raise ValueError(f"trade_date 格式必须为 YYYYMMDD (8位数字)，收到: {trade_date}")

        # 验证日期有效性
        try:
            year = int(trade_date[:4])
            month = int(trade_date[4:6])
            day = int(trade_date[6:8])

            if not (1990 <= year <= 2100):
                raise ValueError(f"年份超出合理范围 (1990-2100): {year}")
            if not (1 <= month <= 12):
                raise ValueError(f"月份无效: {month}")
            if not (1 <= day <= 31):
                raise ValueError(f"日期无效: {day}")
        except ValueError as e:
            raise ValueError(f"trade_date 包含无效日期: {trade_date}, error: {e}")

    def _safe_float(self, value) -> Optional[float]:
        """安全地将值转换为 float，失败时返回 None

        Args:
            value: 任意值

        Returns:
            float 值或 None
        """
        try:
            if value is None or value == "" or value == "None":
                return None
            return float(value)
        except (ValueError, TypeError):
            return None

    def _check_import_available(self, module_name: str) -> bool:
        """检查指定模块是否可用

        Args:
            module_name: 模块名称

        Returns:
            True 如果模块可导入
        """
        try:
            __import__(module_name)
            return True
        except ImportError:
            return False

    def _get_yesterday_date(self) -> str:
        """获取昨天的日期（YYYYMMDD格式）

        Returns:
            昨天日期字符串
        """
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        logger.debug(f"Using yesterday as trade date: {yesterday}")
        return yesterday

    # 新增：全市场实时快照（近实时价格/涨跌幅/成交额），键为6位代码
    @abstractmethod
    def get_realtime_quotes(self) -> Optional[Dict[str, Dict[str, Optional[float]]]]:
        """返回 { '000001': {'close': 10.0, 'pct_chg': 1.2, 'amount': 1.2e8}, ... }"""
        raise NotImplementedError

    @abstractmethod
    def get_daily_quotes(self, trade_date: str) -> Optional[Dict[str, Dict[str, Optional[float]]]]:
        """获取指定日期的全市场行情快照

        Args:
            trade_date: 交易日期 (YYYYMMDD)

        Returns:
            Dict[code, quote_data] where quote_data includes:
            close, pct_chg, amount, volume, open, high, low, pre_close
        """
        raise NotImplementedError

    # 新增：K线与新闻抽象接口
    @abstractmethod
    def get_kline(
        self, code: str, period: str = "day", limit: int = 120, adj: Optional[str] = None
    ) -> Optional[list]:
        """获取K线，返回按时间正序的列表: [{time, open, high, low, close, volume, amount}]"""
        raise NotImplementedError

    @abstractmethod
    def get_news(
        self, code: str, days: int = 2, limit: int = 50, include_announcements: bool = True
    ) -> Optional[list]:
        """获取新闻/公告，返回 [{title, source, time, url, type}]，type in ['news','announcement']"""
        raise NotImplementedError
