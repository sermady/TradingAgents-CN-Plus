# -*- coding: utf-8 -*-
"""
统一价格缓存模块
确保所有分析师使用同一价格的缓存机制，解决报告中的价格不一致问题
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class UnifiedPriceCache:
    """统一价格缓存类 (单例模式)"""
    
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(UnifiedPriceCache, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # 缓存结构: {ticker: {'price': float, 'currency': str, 'timestamp': datetime}}
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = 600  # 缓存有效期：10分钟 (延长以覆盖整个分析过程)
        self.cache_lock = threading.Lock()
        
        logger.info("✅ [UnifiedPriceCache] 统一价格缓存已初始化")

    def get_price(self, ticker: str) -> Optional[float]:
        """获取缓存的价格"""
        with self.cache_lock:
            if ticker in self.cache:
                entry = self.cache[ticker]
                if self._is_valid(entry):
                    return entry['price']
        return None

    def get_price_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取完整的价格信息"""
        with self.cache_lock:
            if ticker in self.cache:
                entry = self.cache[ticker]
                if self._is_valid(entry):
                    return entry.copy()
        return None

    def update(self, ticker: str, price: float, currency: str = "¥"):
        """
        更新缓存
        
        Args:
            ticker: 股票代码
            price: 价格数值
            currency: 货币符号
        """
        with self.cache_lock:
            # 如果缓存已存在且非常新（例如10秒内），则不更新，避免微小波动
            # 除非是强制更新（此处未实现强制参数）
            if ticker in self.cache:
                entry = self.cache[ticker]
                age = (datetime.now() - entry['timestamp']).total_seconds()
                if age < 10:  # 10秒内不重复更新
                    return

            self.cache[ticker] = {
                'price': price,
                'currency': currency,
                'timestamp': datetime.now()
            }
            expire_time = (datetime.now() + timedelta(seconds=self.ttl_seconds)).strftime('%H:%M:%S')
            logger.info(f"✅ [价格缓存] {ticker} 已更新: {currency}{price:.2f}, 过期: {expire_time}")

    def _is_valid(self, entry: Dict[str, Any]) -> bool:
        """检查条目是否有效"""
        if not entry or 'timestamp' not in entry:
            return False
        
        age = (datetime.now() - entry['timestamp']).total_seconds()
        return age < self.ttl_seconds

    def clear(self, ticker: str = None):
        """清除缓存"""
        with self.cache_lock:
            if ticker:
                if ticker in self.cache:
                    del self.cache[ticker]
                    logger.debug(f"🗑️ [价格缓存] {ticker} 已清除")
            else:
                self.cache.clear()
                logger.debug("🗑️ [价格缓存] 全部已清除")

# 全局单例获取函数
def get_price_cache() -> UnifiedPriceCache:
    return UnifiedPriceCache()
