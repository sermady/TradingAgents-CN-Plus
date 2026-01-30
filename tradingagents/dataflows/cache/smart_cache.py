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
    """智能缓存管理器 - 根据数据特点调整缓存策略

    支持分级缓存策略：
    - L1（实时）: 估值指标，1小时缓存，存储于Redis
    - L2（季度）: 财报数据，7天缓存（财报日1小时），存储于MongoDB
    - L3（长期）: 分红/基本面，30天缓存，存储于MongoDB

    财报发布日期感知：
    - 财报发布前3天：缩短缓存至1小时
    - 财报发布日16:00后：强制刷新缓存
    """

    # 不同类型数据的默认 TTL（秒）- 分级缓存配置
    DEFAULT_TTLS = {
        # ===== L1: 实时估值指标（1小时）- Redis存储 =====
        "valuation": 3600,  # 估值指标（PE、PB、PS、总市值）
        "daily_basic": 3600,  # 每日指标
        "realtime_quote": 300,  # 实时行情：5分钟
        # ===== L2: 季度财报数据（7天，财报日调整为1小时）- MongoDB存储 =====
        "fundamental": 604800,  # 基本面数据（默认7天）
        "financial": 604800,  # 财报数据
        "financial_indicators": 604800,  # 财务指标（ROE、EPS等）
        "income_statement": 604800,  # 利润表
        "balance_sheet": 604800,  # 资产负债表
        "cashflow_statement": 604800,  # 现金流量表
        "daily_kline": 3600,  # 日K线：1小时
        # ===== L3: 长期基本面（30天）- MongoDB存储 =====
        "dividend": 2592000,  # 分红数据
        "company_info": 2592000,  # 公司信息
        "stock_basic": 2592000,  # 股票基础信息
        # ===== 其他数据 =====
        "news": 1800,  # 新闻数据：30分钟
        "sentiment": 3600,  # 情绪数据：1小时
        "market_stats": 7200,  # 市场统计：2小时
        "trading_decision": 86400,  # 交易决策：1天
    }

    # 数据类别到存储位置的映射
    STORAGE_MAPPING = {
        # L1: Redis存储（高频访问、实时性要求高）
        "valuation": "redis",
        "daily_basic": "redis",
        "realtime_quote": "redis",
        # L2/L3: MongoDB存储（持久化、容量大）
        "fundamental": "mongodb",
        "financial": "mongodb",
        "financial_indicators": "mongodb",
        "income_statement": "mongodb",
        "balance_sheet": "mongodb",
        "cashflow_statement": "mongodb",
        "dividend": "mongodb",
        "company_info": "mongodb",
        "stock_basic": "mongodb",
        "daily_kline": "mongodb",
        "news": "mongodb",
        "sentiment": "mongodb",
        "market_stats": "mongodb",
        "trading_decision": "mongodb",
    }

    # 受财报发布日期影响的数据类别
    REPORT_SENSITIVE_TYPES = {
        "fundamental",
        "financial",
        "financial_indicators",
        "income_statement",
        "balance_sheet",
        "cashflow_statement",
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
        use_calendar: bool = True,
    ) -> Optional[Any]:
        """获取缓存数据，记录命中率

        Args:
            symbol: 股票代码
            date: 日期
            data_type: 数据类型
            params: 额外参数
            ttl: 自定义TTL（秒）
            use_calendar: 是否使用财报日历调整TTL（默认True）
        """

        cache_key = self._generate_cache_key(symbol, date, data_type, params)

        # 自动 TTL（考虑财报日历）
        if ttl is None:
            if use_calendar and self.is_report_sensitive(data_type):
                ttl = self.get_ttl_with_calendar(data_type)
            else:
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
        use_calendar: bool = True,
    ) -> bool:
        """设置缓存数据

        Args:
            symbol: 股票代码
            date: 日期
            data_type: 数据类型
            value: 缓存值
            params: 额外参数
            ttl: 自定义TTL（秒）
            priority: 缓存优先级
            use_calendar: 是否使用财报日历调整TTL（默认True）
        """

        cache_key = self._generate_cache_key(symbol, date, data_type, params)

        # 自动 TTL（考虑财报日历）
        if ttl is None:
            if use_calendar and self.is_report_sensitive(data_type):
                ttl = self.get_ttl_with_calendar(data_type)
            else:
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

        # 交易决策：使用场景固定，可以缓存更久
        if data_type == "trading_decision":
            return 259200  # 3天

        return base_ttl

    def get_ttl_with_calendar(
        self, data_type: str, current_date: Optional[datetime] = None
    ) -> int:
        """
        根据财报发布日历获取优化的TTL

        对于财报敏感的数据类型，在财报发布前3天和发布日16:00后，
        使用短TTL（1小时）以确保及时获取新财报数据。

        Args:
            data_type: 数据类型
            current_date: 当前日期，默认为现在

        Returns:
            int: 优化后的TTL（秒）
        """
        from tradingagents.utils.financial_calendar import FinancialCalendar

        base_ttl = self.DEFAULT_TTLS.get(data_type, 3600)

        # 检查是否是财报敏感类型
        if data_type not in self.REPORT_SENSITIVE_TYPES:
            return base_ttl

        # 获取当前日期
        if current_date is None:
            current_date = FinancialCalendar.get_current_date()

        # 使用财务日历调整TTL
        return FinancialCalendar.get_adjusted_ttl(
            data_category=data_type,
            base_ttl=base_ttl,
            current_date=current_date,
            sensitive_days=3,  # 财报发布前3天开始缩短缓存
        )

    def get_storage_location(self, data_type: str) -> str:
        """
        获取数据类型的存储位置

        Args:
            data_type: 数据类型

        Returns:
            str: 存储位置（redis/mongodb）
        """
        return self.STORAGE_MAPPING.get(data_type, "mongodb")

    def is_report_sensitive(self, data_type: str) -> bool:
        """
        检查数据类型是否受财报发布日期影响

        Args:
            data_type: 数据类型

        Returns:
            bool: 是否受财报影响
        """
        return data_type in self.REPORT_SENSITIVE_TYPES

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

    def get_cache_info(self, data_type: str) -> Dict[str, Any]:
        """
        获取数据类型的缓存信息

        Args:
            data_type: 数据类型

        Returns:
            Dict: 包含TTL、存储位置、是否受财报影响等信息
        """
        from tradingagents.utils.financial_calendar import FinancialCalendar

        base_ttl = self.DEFAULT_TTLS.get(data_type, 3600)
        storage = self.get_storage_location(data_type)
        is_sensitive = self.is_report_sensitive(data_type)

        info = {
            "data_type": data_type,
            "base_ttl_seconds": base_ttl,
            "base_ttl_human": self._format_ttl(base_ttl),
            "storage_location": storage,
            "is_report_sensitive": is_sensitive,
        }

        # 如果是财报敏感类型，添加调整后TTL
        if is_sensitive:
            adjusted_ttl = self.get_ttl_with_calendar(data_type)
            info["adjusted_ttl_seconds"] = adjusted_ttl
            info["adjusted_ttl_human"] = self._format_ttl(adjusted_ttl)

            # 添加财报日历信息
            calendar_info = FinancialCalendar.get_report_info()
            info["financial_calendar"] = calendar_info

        return info

    @staticmethod
    def _format_ttl(seconds: int) -> str:
        """格式化TTL为可读字符串"""
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            return f"{seconds // 60}分钟"
        elif seconds < 86400:
            return f"{seconds // 3600}小时"
        else:
            return f"{seconds // 86400}天"


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
