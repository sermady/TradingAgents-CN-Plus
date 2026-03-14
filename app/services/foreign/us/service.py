# -*- coding: utf-8 -*-
"""美股数据服务

组合所有 Mixin 提供完整的美股数据服务。
"""

import asyncio
import logging
from collections import defaultdict
from typing import Dict, List

from tradingagents.dataflows.cache import get_cache
from ..base import ForeignStockBaseService
from .quote import QuoteMixin
from .info import InfoMixin
from .kline import KlineMixin
from .news import NewsMixin

logger = logging.getLogger(__name__)


class USStockService(QuoteMixin, InfoMixin, KlineMixin, NewsMixin, ForeignStockBaseService):
    """美股数据服务"""

    def __init__(self, db=None):
        """初始化美股服务

        Args:
            db: MongoDB 数据库连接
        """
        super().__init__(db)

        # 初始化美股数据提供器
        self.yfinance_provider = None  # 延迟初始化

        # 请求去重：为每个 (code, data_type) 创建独立的锁
        self._request_locks = defaultdict(asyncio.Lock)

        logger.info("✅ USStockService 初始化完成（已启用请求去重）")

    @property
    def market(self) -> str:
        """市场标识"""
        return "US"
