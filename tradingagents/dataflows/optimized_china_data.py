# -*- coding: utf-8 -*-
"""
优化的A股数据获取工具
集成缓存策略和多数据源接口，提高数据获取效率

本模块是重构后的主入口文件，协调各个子模块的工作。
具体实现已拆分到以下子模块：
- china/base_data_loader.py: 基础数据加载器基类
- china/stock_list_loader.py: 股票列表加载
- china/historical_data_loader.py: 历史数据加载
- china/realtime_data_loader.py: 实时数据加载
- china/fundamentals_loader.py: 基本面数据加载
- china/technical_indicators.py: 技术指标计算
- parsers/: 解析器工具模块
"""

import os
import time
import random
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, Dict, Any, List

from .cache import get_cache
from tradingagents.config.config_manager import config_manager
from tradingagents.config.runtime_settings import get_float, get_timezone_name

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("agents")

# 导入MongoDB缓存适配器
from .cache.mongodb_cache_adapter import (
    get_mongodb_cache_adapter,
    get_stock_data_with_fallback,
    get_financial_data_with_fallback,
)

# 导入新拆分的子模块
from .china import (
    BaseDataLoader,
    StockListLoader,
    get_stock_list_loader,
    HistoricalDataLoader,
    get_historical_data_loader,
    RealtimeDataLoader,
    get_realtime_data_loader,
    FundamentalsLoader,
    get_fundamentals_loader,
    TechnicalIndicators,
)

from .parsers import (
    normalize_symbol,
    get_market_type,
    get_market_type_by_code,
    parse_date,
    format_date,
    validate_price,
    validate_volume,
    check_data_quality,
    format_number_yi,
)


class OptimizedChinaDataProvider:
    """
    优化的A股数据提供器 - 集成缓存和多数据源接口

    这是主协调类，负责整合各个子加载器的功能，
    提供统一的A股数据获取接口。
    """

    def __init__(self):
        self.cache = get_cache()
        self.config = config_manager.load_settings()
        self.last_api_call = 0
        self.min_api_interval = get_float(
            "TA_CHINA_MIN_API_INTERVAL_SECONDS",
            "ta_china_min_api_interval_seconds",
            0.5,
        )

        # 初始化各子加载器
        self._stock_list_loader = get_stock_list_loader()
        self._historical_loader = get_historical_data_loader()
        self._realtime_loader = get_realtime_data_loader()
        self._fundamentals_loader = get_fundamentals_loader()

        logger.info(f"📊 优化A股数据提供器初始化完成")

    def _wait_for_rate_limit(self):
        """等待API限制"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call

        if time_since_last_call < self.min_api_interval:
            wait_time = self.min_api_interval - time_since_last_call
            time.sleep(wait_time)

        self.last_api_call = time.time()

    def get_stock_data(
        self, symbol: str, start_date: str, end_date: str, force_refresh: bool = False
    ) -> str:
        """
        获取A股历史数据 - 优先使用缓存

        Args:
            symbol: 股票代码（6位数字）
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            force_refresh: 是否强制刷新缓存

        Returns:
            格式化的股票数据字符串
        """
        return self._historical_loader.load(
            symbol, start_date, end_date, force_refresh=force_refresh
        )

    def get_fundamentals_data(self, symbol: str, force_refresh: bool = False) -> str:
        """
        获取A股基本面数据 - 优先使用缓存

        Args:
            symbol: 股票代码
            force_refresh: 是否强制刷新缓存

        Returns:
            格式化的基本面数据字符串
        """
        return self._fundamentals_loader.load(symbol, force_refresh=force_refresh)

    def get_realtime_data(self, symbol: str) -> Dict[str, Any]:
        """
        获取A股实时数据

        Args:
            symbol: 股票代码

        Returns:
            实时数据字典
        """
        return self._realtime_loader.load(symbol)

    def get_stock_list(
        self, market: str = "all", refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """
        获取股票列表

        Args:
            market: 市场筛选 (sh/sz/all)
            refresh: 是否强制刷新

        Returns:
            股票列表
        """
        return self._stock_list_loader.load(market=market, refresh=refresh)

    def search_stocks(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        搜索股票

        Args:
            keyword: 搜索关键词
            limit: 返回数量限制

        Returns:
            匹配的股票列表
        """
        return self._stock_list_loader.search_stocks(keyword, limit)

    def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取特定股票信息

        Args:
            symbol: 股票代码

        Returns:
            股票信息字典或None
        """
        return self._stock_list_loader.get_stock_info(symbol)

    def get_industry_info(self, symbol: str) -> Dict[str, Any]:
        """
        获取行业信息

        Args:
            symbol: 股票代码

        Returns:
            行业信息字典
        """
        return self._fundamentals_loader._get_industry_info(symbol)

    def _format_financial_data_to_fundamentals(
        self, financial_data: Dict[str, Any], symbol: str
    ) -> str:
        """
        将MongoDB财务数据转换为基本面分析格式

        保持向后兼容的方法
        """
        return self._fundamentals_loader._format_financial_data_to_fundamentals(
            financial_data, symbol
        )

    def _try_get_old_cache(
        self, symbol: str, start_date: str, end_date: str
    ) -> Optional[str]:
        """尝试获取过期的缓存数据作为备用"""
        return self._historical_loader._try_get_old_cache(symbol, "stock_data")

    def _generate_fallback_data(
        self, symbol: str, start_date: str, end_date: str, error_msg: str
    ) -> str:
        """生成备用数据"""
        return self._historical_loader._generate_fallback_data(
            symbol, start_date, end_date, error_msg
        )

    def _generate_fallback_fundamentals(self, symbol: str, error_msg: str) -> str:
        """生成备用基本面数据"""
        return self._fundamentals_loader._generate_fallback_fundamentals(
            symbol, error_msg
        )

    def _generate_fundamentals_report(
        self, symbol: str, analysis_modules: str = "standard"
    ) -> str:
        """
        生成基本面分析报告

        Args:
            symbol: 股票代码
            analysis_modules: 分析模块级别 (basic/standard/full)

        Returns:
            格式化的基本面分析报告
        """
        return self._fundamentals_loader._generate_fundamentals_report(
            symbol, analysis_modules
        )


# 全局实例
_china_data_provider = None


def get_optimized_china_data_provider() -> OptimizedChinaDataProvider:
    """获取全局A股数据提供器实例"""
    global _china_data_provider
    if _china_data_provider is None:
        _china_data_provider = OptimizedChinaDataProvider()
    return _china_data_provider


def get_china_stock_data_cached(
    symbol: str, start_date: str, end_date: str, force_refresh: bool = False
) -> str:
    """
    获取A股历史数据的便捷函数

    Args:
        symbol: 股票代码（6位数字）
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        force_refresh: 是否强制刷新缓存

    Returns:
        格式化的股票数据字符串
    """
    provider = get_optimized_china_data_provider()
    return provider.get_stock_data(symbol, start_date, end_date, force_refresh)


def get_china_fundamentals_cached(symbol: str, force_refresh: bool = False) -> str:
    """
    获取A股基本面数据的便捷函数

    Args:
        symbol: 股票代码（6位数字）
        force_refresh: 是否强制刷新缓存

    Returns:
        格式化的基本面数据字符串
    """
    provider = get_optimized_china_data_provider()
    return provider.get_fundamentals_data(symbol, force_refresh)


def get_china_realtime_data(symbol: str) -> Dict[str, Any]:
    """
    获取A股实时数据的便捷函数

    Args:
        symbol: 股票代码

    Returns:
        实时数据字典
    """
    provider = get_optimized_china_data_provider()
    return provider.get_realtime_data(symbol)


# 导出子模块中的类和函数，保持向后兼容
__all__ = [
    # 主类
    "OptimizedChinaDataProvider",
    "get_optimized_china_data_provider",
    # 便捷函数
    "get_china_stock_data_cached",
    "get_china_fundamentals_cached",
    "get_china_realtime_data",
    # 子模块类
    "BaseDataLoader",
    "StockListLoader",
    "HistoricalDataLoader",
    "RealtimeDataLoader",
    "FundamentalsLoader",
    "TechnicalIndicators",
    # 子模块获取函数
    "get_stock_list_loader",
    "get_historical_data_loader",
    "get_realtime_data_loader",
    "get_fundamentals_loader",
    # 解析器工具
    "normalize_symbol",
    "get_market_type",
    "get_market_type_by_code",
    "parse_date",
    "format_date",
    "validate_price",
    "validate_volume",
    "check_data_quality",
    "format_number_yi",
]
