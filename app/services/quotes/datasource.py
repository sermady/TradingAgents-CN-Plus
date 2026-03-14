# -*- coding: utf-8 -*-
"""行情数据源管理模块

提供数据源轮换、Tushare权限检测等功能。
"""

import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
from zoneinfo import ZoneInfo

from app.core.config import settings

logger = logging.getLogger(__name__)


class DataSourceMixin:
    """数据源管理混入类"""

    def __init__(self):
        self.tz = ZoneInfo(settings.TIMEZONE)

        # Tushare 权限检测相关属性
        self._tushare_permission_checked = False
        self._tushare_has_premium = False
        self._tushare_hourly_limit = settings.QUOTES_TUSHARE_HOURLY_LIMIT
        self._tushare_call_times = deque()

        # 接口轮换相关属性
        # 优先级：AKShare东方财富 > AKShare新浪 > Tushare
        self._rotation_sources = ["akshare_eastmoney", "akshare_sina", "tushare"]
        self._rotation_index = 0

    def _check_tushare_permission(self) -> bool:
        """
        检测 Tushare rt_k 接口权限

        Returns:
            True: 有付费权限（可高频调用）
            False: 免费用户（每小时最多2次）
        """
        if self._tushare_permission_checked:
            return self._tushare_has_premium or False

        try:
            from app.services.data_sources.tushare_adapter import TushareAdapter
            adapter = TushareAdapter()

            if not adapter.is_available():
                logger.info("Tushare unavailable, skipping permission check")
                self._tushare_has_premium = False
                self._tushare_permission_checked = True
                return False

            # 尝试调用 rt_k 接口测试权限
            try:
                df = adapter._provider.api.rt_k(ts_code='000001.SZ')
                if df is not None and not getattr(df, 'empty', True):
                    logger.info("Tushare rt_k permission detected (premium user)")
                    self._tushare_has_premium = True
                else:
                    logger.info("Tushare rt_k returned empty data (free user or limited)")
                    self._tushare_has_premium = False
            except Exception as e:
                error_msg = str(e).lower()
                if "permission" in error_msg or "access" in error_msg:
                    logger.info("Tushare rt_k no permission (free user)")
                    self._tushare_has_premium = False
                else:
                    logger.warning(f"Tushare rt_k test failed: {e}")
                    self._tushare_has_premium = False

            self._tushare_permission_checked = True
            return self._tushare_has_premium or False

        except Exception as e:
            logger.warning(f"Tushare permission check failed: {e}")
            self._tushare_has_premium = False
            self._tushare_permission_checked = True
            return False

    def _can_call_tushare(self) -> bool:
        """
        判断是否可以调用 Tushare rt_k 接口

        Returns:
            True: 可以调用
            False: 超过限制，不能调用
        """
        # 如果是付费用户，不限制调用次数
        if self._tushare_has_premium:
            return True

        # 免费用户：检查每小时调用次数
        now = datetime.now(self.tz)
        one_hour_ago = now - timedelta(hours=1)

        # 清理1小时前的记录
        while self._tushare_call_times and self._tushare_call_times[0] < one_hour_ago:
            self._tushare_call_times.popleft()

        # 检查是否超过限制
        if len(self._tushare_call_times) >= self._tushare_hourly_limit:
            logger.warning(
                f"Tushare rt_k hourly limit reached ({self._tushare_hourly_limit} calls), "
                "using AKShare backup"
            )
            return False

        return True

    def _record_tushare_call(self) -> None:
        """记录 Tushare 调用时间"""
        self._tushare_call_times.append(datetime.now(self.tz))

    def _get_next_source(self) -> Tuple[str, Optional[str]]:
        """
        获取下一个数据源（轮换机制）

        优先级顺序（已优化）：
        1. AKShare东方财富（限制宽松）
        2. AKShare新浪财经（限制宽松）
        3. Tushare（免费用户限制：每分钟1次）

        Returns:
            (source_type, akshare_api):
                - source_type: "tushare" | "akshare"
                - akshare_api: "eastmoney" | "sina"
        """
        if not settings.QUOTES_ROTATION_ENABLED:
            # 未启用轮换，使用默认优先级
            return "akshare", "eastmoney"

        # 轮换逻辑
        current_source = self._rotation_sources[self._rotation_index]
        self._rotation_index = (self._rotation_index + 1) % len(self._rotation_sources)

        if current_source == "tushare":
            return "tushare", None
        elif current_source == "akshare_eastmoney":
            return "akshare", "eastmoney"
        else:  # akshare_sina
            return "akshare", "sina"

    def _is_trading_time(self, now: Optional[datetime] = None) -> bool:
        """
        判断是否在交易时间或收盘后缓冲期

        交易时间：
        - 上午：9:30-11:30
        - 下午：13:00-15:00
        - 收盘后缓冲期：15:00-15:30（确保获取到收盘价）
        """
        from datetime import time as dtime

        now = now or datetime.now(self.tz)
        # 工作日 Mon-Fri
        if now.weekday() > 4:
            return False

        t = now.time()
        morning = dtime(9, 30)
        noon = dtime(11, 30)
        afternoon_start = dtime(13, 0)
        buffer_end = dtime(15, 30)

        return (morning <= t <= noon) or (afternoon_start <= t <= buffer_end)

    def _fetch_quotes_from_source(self, source_type: str, akshare_api: Optional[str] = None):
        """
        从指定数据源获取行情

        Args:
            source_type: "tushare" | "akshare"
            akshare_api: "eastmoney" | "sina" (仅当 source_type="akshare")

        Returns:
            (quotes_map, source_name)
        """
        try:
            if source_type == "tushare":
                return self._fetch_from_tushare()
            elif source_type == "akshare":
                return self._fetch_from_akshare(akshare_api)
            else:
                logger.error(f"Unknown source type: {source_type}")
                return None, None
        except Exception as e:
            logger.error(f"Failed to fetch from {source_type}: {e}")
            return None, None

    def _fetch_from_tushare(self):
        """从 Tushare 获取行情"""
        if not self._can_call_tushare():
            return None, None

        from app.services.data_sources.tushare_adapter import TushareAdapter
        adapter = TushareAdapter()

        if not adapter.is_available():
            logger.warning("Tushare unavailable")
            return None, None

        logger.info("Using Tushare rt_k API for real-time quotes")
        quotes_map = adapter.get_realtime_quotes()

        if quotes_map:
            self._record_tushare_call()
            return quotes_map, "tushare"
        else:
            logger.warning("Tushare rt_k returned empty data")
            return None, None

    def _fetch_from_akshare(self, akshare_api: Optional[str] = None):
        """从 AKShare 获取行情"""
        from app.services.data_sources.akshare_adapter import AKShareAdapter
        adapter = AKShareAdapter()

        if not adapter.is_available():
            logger.warning("AKShare unavailable")
            return None, None

        api_name = akshare_api or "eastmoney"
        logger.info(f"Using AKShare {api_name} API for real-time quotes")
        quotes_map = adapter.get_realtime_quotes(source=api_name)

        if quotes_map:
            return quotes_map, f"akshare_{api_name}"
        else:
            logger.warning(f"AKShare {api_name} returned empty data")
            return None, None
