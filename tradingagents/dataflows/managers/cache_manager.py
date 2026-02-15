# -*- coding: utf-8 -*-
"""
缓存管理器
负责数据缓存的获取、保存和TTL管理
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from tradingagents.utils.logging_manager import get_logger

logger = get_logger("agents")


class CacheManager:
    """缓存管理器 - 处理数据缓存相关操作"""

    def __init__(self, cache_manager=None, cache_enabled: bool = False):
        """
        初始化缓存管理器

        Args:
            cache_manager: 底层缓存管理器实例
            cache_enabled: 是否启用缓存
        """
        self.cache_manager = cache_manager
        self.cache_enabled = cache_enabled

    def get_cached_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_age_hours: int = 24,
    ) -> Optional[pd.DataFrame]:
        """
        从缓存获取数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            max_age_hours: 最大缓存时间（小时）

        Returns:
            DataFrame: 缓存的数据，如果没有则返回None
        """
        if not self.cache_enabled or not self.cache_manager:
            return None

        try:
            cache_key = self.cache_manager.find_cached_stock_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                max_age_hours=max_age_hours,
            )

            if cache_key:
                cached_data = self.cache_manager.load_stock_data(cache_key)
                if (
                    cached_data is not None
                    and hasattr(cached_data, "empty")
                    and not cached_data.empty
                ):
                    logger.debug(f"📦 从缓存获取{symbol}数据: {len(cached_data)}条")
                    return cached_data
        except Exception as e:
            logger.warning(f"⚠️ 从缓存读取数据失败: {e}")

        return None

    def save_to_cache(
        self,
        symbol: str,
        data: pd.DataFrame,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        """
        保存数据到缓存

        Args:
            symbol: 股票代码
            data: 数据
            start_date: 开始日期
            end_date: 结束日期
        """
        if not self.cache_enabled or not self.cache_manager:
            return

        try:
            if data is not None and hasattr(data, "empty") and not data.empty:
                self.cache_manager.save_stock_data(symbol, data, start_date, end_date)
                logger.debug(f"💾 保存{symbol}数据到缓存: {len(data)}条")
        except Exception as e:
            logger.warning(f"⚠️ 保存数据到缓存失败: {e}")

    def get_smart_ttl(self, data_category: str) -> int:
        """
        获取分级缓存TTL（支持财报发布日期感知）

        使用 SmartCache 的分级缓存策略：
        - L1（实时）: 估值指标，1小时缓存
        - L2（季度）: 财报数据，7天缓存（财报日1小时）
        - L3（长期）: 分红/基本面，30天缓存

        Args:
            data_category: 数据类别（valuation/financial/dividend等）

        Returns:
            int: 缓存TTL（秒）
        """
        from tradingagents.dataflows.cache.smart_cache import SmartCache

        cache = SmartCache(self.cache_manager)
        return cache.get_ttl_with_calendar(data_category)

    def get_storage_location(self, data_category: str) -> str:
        """
        获取数据类型的存储位置

        Args:
            data_category: 数据类别

        Returns:
            str: 存储位置（redis/mongodb）
        """
        from tradingagents.dataflows.cache.smart_cache import SmartCache

        cache = SmartCache(self.cache_manager)
        return cache.get_storage_location(data_category)

    def record_source_reliability(
        self,
        source: str,
        success: bool,
        metric: str,
        error: Optional[str] = None,
    ) -> None:
        """
        记录数据源可靠性

        将数据源的成功/失败记录到 Redis，用于后续自动降级决策

        Args:
            source: 数据源名称 (tushare/akshare/baostock)
            success: 是否成功
            metric: 指标名称 (current_price/volume/MA5等)
            error: 错误信息（如果失败）
        """
        if not self.cache_enabled or not self.cache_manager:
            return

        try:
            import time

            # 获取 Redis 客户端
            redis_client = None
            if hasattr(self.cache_manager, "db_manager"):
                redis_client = self.cache_manager.db_manager.get_redis_client()
            elif hasattr(self.cache_manager, "redis_client"):
                redis_client = self.cache_manager.redis_client

            if not redis_client:
                return

            # 使用 Redis 记录可靠性
            redis_key = f"source_reliability:{source}:{metric}"
            timestamp = int(time.time())

            # 记录最近100次调用
            record = {
                "timestamp": timestamp,
                "success": success,
                "error_type": type(error).__name__ if error else None,
            }

            # 使用 Redis List 存储历史记录
            redis_client.lpush(redis_key, str(record))
            redis_client.ltrim(redis_key, 0, 99)

            # 设置过期时间（7天）
            redis_client.expire(redis_key, 7 * 24 * 3600)

            # 记录总体统计
            stats_key = f"source_stats:{source}"
            if success:
                redis_client.hincrby(stats_key, "success_count", 1)
            else:
                redis_client.hincrby(stats_key, "failure_count", 1)

            redis_client.expire(stats_key, 30 * 24 * 3600)  # 30天

        except Exception:
            logger.debug("记录数据源可靠性失败 (已抑制)")

    def get_source_reliability_score(self, source: str) -> float:
        """
        获取数据源可靠性评分

        基于历史成功率计算动态可靠性评分 (0-100)

        Args:
            source: 数据源名称

        Returns:
            float: 可靠性评分 (0-100)
        """
        # 默认静态评分
        default_scores = {
            "tushare": 90.0,
            "akshare": 70.0,
            "baostock": 75.0,
        }

        if not self.cache_enabled or not self.cache_manager:
            return default_scores.get(source.lower(), 60.0)

        try:
            # 获取 Redis 客户端
            redis_client = None
            if hasattr(self.cache_manager, "db_manager"):
                redis_client = self.cache_manager.db_manager.get_redis_client()
            elif hasattr(self.cache_manager, "redis_client"):
                redis_client = self.cache_manager.redis_client

            if not redis_client:
                return default_scores.get(source.lower(), 60.0)

            stats_key = f"source_stats:{source}"
            stats = redis_client.hgetall(stats_key)

            if not stats:
                return default_scores.get(source.lower(), 60.0)

            success_count = int(stats.get(b"success_count", 0))
            failure_count = int(stats.get(b"failure_count", 0))
            total = success_count + failure_count

            if total == 0:
                return default_scores.get(source.lower(), 60.0)

            success_rate = success_count / total

            # 转换为0-100评分
            if success_rate >= 0.5:
                score = 40 + (success_rate - 0.5) * 120
            else:
                score = success_rate * 80

            return min(max(score, 0), 100)

        except Exception as e:
            logger.debug(f"获取数据源可靠性评分失败: {e}")
            return default_scores.get(source.lower(), 60.0)
