# -*- coding: utf-8 -*-
"""
统一价格缓存模块
确保所有分析师使用同一价格的缓存机制，解决报告中的价格不一致问题
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class UnifiedPriceCache:
    """统一价格缓存类"""

    def __init__(self):
        """初始化缓存"""
        self.price = None
        self.currency = None  # 货币符号，如 ¥, $, HK$
        self.timestamp = None
        self.ttl_seconds = 300  # 缓存有效期：5分钟（300秒）

    def is_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self.price or not self.timestamp:
            return False

        from datetime import datetime, timedelta

        cache_age = (datetime.now() - self.timestamp).total_seconds()
        return cache_age < self.ttl_seconds

    def is_expired(self) -> bool:
        """检查缓存是否过期"""
        return not self.is_valid()

    def update(self, price: float, currency: str = "¥"):
        """
        更新缓存

        Args:
            price: 价格数值
            currency: 货币符号（默认为人民币）
        """
        self.price = price
        self.currency = currency
        self.timestamp = datetime.now()
        logger.info(
            f"✅ [价格缓存] 已更新: {currency}{price:.2f}, "
            f"过期时间: {(self.timestamp + timedelta(seconds=self.ttl_seconds)).strftime('%H:%M:%S')}"
        )

    def get_price_str(self) -> Optional[str]:
        """获取格式化的价格字符串"""
        if not self.price or not self.currency:
            return None
        return f"{self.currency}{self.price:.2f}"

    def clear(self):
        """清除缓存"""
        self.price = None
        self.currency = None
        self.timestamp = None
        logger.debug("🗑️ [价格缓存] 缓存已清除")
