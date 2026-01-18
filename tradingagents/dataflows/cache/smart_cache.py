# -*- coding: utf-8 -*-
"""
智能缓存系统 - 根据数据特点调整缓存策略
"""

import time
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from hashlib import md5

from tradingagents.utils.logging_init import get_logger

logger = get_logger("smart_cache")


class SmartCache:
    """智能缓存管理器 - 根据数据特点调整缓存策略"""

    # 不同类型数据的默认 TTL（秒）
    DEFAULT_TTLS = {
        "realtime_quote": 300,  # 实时行情：5分钟
        "daily_kline": 3600,  # 日K线：1小时
        "fundamental": 86400,  # 基本面数据：1天
        "news": 1800,  # 新闻数据：30分钟
        "sentiment": 3600,  # 情绪数据：1小时
        "company_info": 259200,  # 公司信息：3天
        "market_stats": 7200,  # 市场统计：2小时
        "trading_decision": 86400,  # 交易决策：1天
    }

    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.cache_hit_stats = {}
        self.cache_miss_stats = {}

    def _generate_cache_key(
        self, symbol: str, date: str, data_type: str, params: Optional[Dict] = None
    ) -> str:
        """
        生成缓存键

        Args:
            symbol: 股票代码
            date: 日期
            data_type: 数据类型
            params: 额外参数

        Returns:
            缓存键
        """

        # 基础数据
        key_data = f"{symbol}:{date}:{data_type}"

        # 添加额外参数
        if params:
            param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            key_data += f":{param_str}"

        # 使用 MD5 哈希（避免键太长）
        return md5(key_data.encode()).hexdigest()

    async def get(
        self,
        symbol: str,
        date: str,
        data_type: str,
        params: Optional[Dict] = None,
        ttl: Optional[int] = None,
    ) -> Optional[Any]:
        """获取缓存数据，记录命中率"""

        cache_key = self._generate_cache_key(symbol, date, data_type, params)

        # 自动 TTL
        if ttl is None:
            ttl = self.DEFAULT_TTLS.get(data_type, 3600)

        # 更新统计
        self.cache_miss_stats[data_type] = self.cache_miss_stats.get(data_type, 0) + 1

        # 获取缓存
        value = await self.cache_manager.get(cache_key)

        if value is not None:
            # 记录统计
            self.cache_hit_stats[data_type] = self.cache_hit_stats.get(data_type, 0) + 1
            logger.debug(f"[SmartCache] 缓存命中: {data_type} for {symbol}")
            return value

        return None

    async def set(
        self,
        symbol: str,
        date: str,
        data_type: str,
        value: Any,
        params: Optional[Dict] = None,
        ttl: Optional[int] = None,
        priority: int = 0,
    ) -> bool:
        """设置缓存数据"""

        cache_key = self._generate_cache_key(symbol, date, data_type, params)

        # 自动 TTL
        if ttl is None:
            ttl = self.DEFAULT_TTLS.get(data_type, 3600)

        return await self.cache_manager.set(cache_key, value, ttl)

    def get_cache_hit_rate(self, data_type: str) -> float:
        """获取缓存命中率"""

        hits = self.cache_hit_stats.get(data_type, 0)
        misses = self.cache_miss_stats.get(data_type, 0)
        total = hits + misses

        if total == 0:
            return 0.0

        return hits / total

    def get_cache_stats(self) -> Dict[str, Dict[str, any]]:
        """获取缓存统计信息"""

        stats = {}

        for data_type in self.DEFAULT_TTLS.keys():
            hits = self.cache_hit_stats.get(data_type, 0)
            misses = self.cache_miss_stats.get(data_type, 0)
            total = hits + misses

            if total > 0:
                stats[data_type] = {
                    "hits": hits,
                    "misses": misses,
                    "total": total,
                    "hit_rate": hits / total,
                }

        return stats

    def get_optimized_ttl(
        self, data_type: str, data_age_minutes: Optional[int] = None
    ) -> int:
        """
        根据数据年龄动态调整 TTL

        Args:
            data_type: 数据类型
            data_age_minutes: 数据年龄（分钟）

        Returns:
            优化后的 TTL（秒）
        """

        base_ttl = self.DEFAULT_TTLS.get(data_type, 3600)

        # 新闻数据：年龄越大，TTL 越长
        if data_type == "news" and data_age_minutes:
            if data_age_minutes < 60:
                return 300  # 30分钟内的新闻，缓存5分钟
            elif data_age_minutes < 1440:  # 24小时内
                return 1800  # 1天内的新闻，缓存30分钟
            else:
                return 7200  # 老新闻，缓存2小时

        # 基本面数据：更新频率低，可以缓存更久
        if data_type == "fundamental":
            return 259200  # 3天

        # 交易决策：使用场景固定，可以缓存更久
        if data_type == "trading_decision":
            return 259200  # 3天

        return base_ttl

    def get_cache_priority(self, data_type: str) -> int:
        """
        获取缓存优先级

        Returns:
            优先级（数字越大优先级越高）
        """

        priority_map = {
            "realtime_quote": 5,  # 最高优先级
            "daily_kline": 4,
            "news": 3,
            "sentiment": 2,
            "fundamental": 2,
            "company_info": 1,
            "market_stats": 1,
            "trading_decision": 3,
        }

        return priority_map.get(data_type, 0)


class CacheMonitor:
    """缓存监控器"""

    def __init__(self):
        self.stats = {
            "hits": 0,
            "misses": 0,
            "size": 0,
            "evictions": 0,
        }
        self.start_time = time.time()

    def record_hit(self):
        """记录缓存命中"""
        self.stats["hits"] += 1

    def record_miss(self):
        """记录缓存未命中"""
        self.stats["misses"] += 1

    def record_eviction(self):
        """记录缓存过期"""
        self.stats["evictions"] += 1

    def get_hit_rate(self) -> float:
        """获取缓存命中率"""
        total = self.stats["hits"] + self.stats["misses"]
        if total == 0:
            return 0.0
        return self.stats["hits"] / total

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""

        runtime = time.time() - self.start_time

        return {
            "hit_rate": self.get_hit_rate(),
            "total_requests": self.stats["hits"] + self.stats["misses"],
            "cache_size": self.stats["size"],
            "evictions": self.stats["evictions"],
            "runtime_seconds": runtime,
        }

    async def cleanup_expired_keys(self):
        """清理过期缓存键"""

        logger.info("开始清理过期缓存...")

        # 清理7天前的记录
        threshold = datetime.now() - timedelta(days=7)

        try:
            from app.core.database import get_mongo_db_sync

            db = get_mongo_db_sync()
            cache_collection = db.cache_collection

            # 删除过期记录
            result = await cache_collection.delete_many(
                {"created_at": {"$lt": threshold}}
            )

            logger.info(f"清理 {result.deleted_count} 条过期缓存记录")
            return result.deleted_count

        except Exception as e:
            logger.error(f"清理缓存失败: {e}")
            return 0

    async def log_cache_report(self):
        """输出缓存报告"""

        stats = self.get_stats()

        logger.info("=" * 60)
        logger.info("缓存报告")
        logger.info("=" * 60)
        logger.info(f"缓存命中率: {stats['hit_rate']:.2%}")
        logger.info(f"总请求次数: {stats['total_requests']}")
        logger.info(f"缓存大小: {stats['cache_size']}")
        logger.info(f"过期次数: {stats['evictions']}")
        logger.info(f"运行时间: {stats['runtime_seconds']:.2f}秒")
        logger.info("=" * 60)
