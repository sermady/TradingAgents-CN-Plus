# -*- coding: utf-8 -*-
"""
Data Coordinator
Preloads all necessary data before analysis starts, coordinates data requests from analysts
Supports hybrid cache strategy to reduce API calls
"""

import logging
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AnalysisDepth(Enum):
    """Analysis depth levels (Chinese localization)"""

    QUICK = "快速"
    BASIC = "基础"
    STANDARD = "标准"
    DEEP = "深度"
    COMPREHENSIVE = "全面"


@dataclass
class PreloadedData:
    """Preloaded data structure"""

    market_data: str = ""
    fundamentals_data: str = ""
    news_data: str = ""
    sentiment_data: str = ""
    price_info: Dict[str, Any] = field(default_factory=dict)
    ticker: str = ""
    trade_date: str = ""
    depth: str = ""
    loaded_at: datetime = field(default_factory=datetime.now)

    # ========== 数据质量风控字段 (Phase 1.1) ==========
    data_quality_score: float = 100.0  # 数据质量评分 (0-100)
    data_quality_grade: str = "A"  # 数据质量等级 (A/B/C/D/F)
    data_quality_issues: List[str] = field(default_factory=list)  # 数据质量问题列表


class DataCoordinator:
    """Data Coordinator (Singleton)

    Functions:
    1. Preload all necessary data before analysis starts (all preload strategy)
    2. Coordinate data requests from Market Analyst and Fundamentals Analyst
    3. Integrate with PriceCache, support hybrid cache strategy
    4. Provide unified data access interface
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DataCoordinator, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Preloaded data cache {ticker: {trade_date: PreloadedData}}
        self._preloaded_cache: Dict[str, Dict[str, PreloadedData]] = {}
        # 注意：DataCoordinator 主要在同步上下文使用，且操作快速（仅字典访问）
        # threading.Lock 在此处是合适的，不改为 asyncio.Lock 以避免破坏现有 API
        self._cache_lock = threading.Lock()

        # Price cache
        self._price_cache = None

        # Cache TTL: 10 minutes (基础配置)
        self._cache_ttl_seconds = 600

        # Lookback days config
        self._lookback_days = 365

        # 分级缓存TTL配置（支持财报发布日期感知）
        # L1: 实时估值指标 → 1小时
        # L2: 季度财报数据 → 7天（财报日1小时）
        # L3: 长期基本面 → 30天
        self._tiered_cache_config = {
            "valuation": 3600,  # L1: 估值指标
            "financial": 604800,  # L2: 财报数据
            "dividend": 2592000,  # L3: 分红数据
            "default": 600,  # 默认: 10分钟
        }

        logger.info("[DataCoordinator] Data Coordinator initialized")
        logger.info("[DataCoordinator] 分级缓存策略已启用")
        logger.info("  - L1(估值指标): 1小时缓存")
        logger.info("  - L2(财报数据): 7天缓存（财报日1小时）")
        logger.info("  - L3(分红数据): 30天缓存")

    def _get_price_cache(self):
        """Lazy load price cache"""
        if self._price_cache is None:
            from tradingagents.utils.price_cache import get_price_cache

            self._price_cache = get_price_cache()
        return self._price_cache

    def _load_config(self):
        """Load configuration"""
        try:
            from app.core.config import get_settings

            settings = get_settings()
            self._lookback_days = settings.MARKET_ANALYST_LOOKBACK_DAYS
            logger.debug(
                f"[DataCoordinator] Config loaded: lookback_days={self._lookback_days}"
            )
        except Exception as e:
            logger.warning(f"[DataCoordinator] Cannot load config, using defaults: {e}")

    def _get_depth_from_config(self) -> AnalysisDepth:
        """Get analysis depth from config"""
        try:
            from tradingagents.agents.utils.agent_utils import Toolkit

            depth_str = Toolkit._config.get("research_depth", "Standard")

            numeric_mapping = {
                1: AnalysisDepth.QUICK,
                2: AnalysisDepth.BASIC,
                3: AnalysisDepth.STANDARD,
                4: AnalysisDepth.DEEP,
                5: AnalysisDepth.COMPREHENSIVE,
            }

            if isinstance(depth_str, (int, float)):
                depth = numeric_mapping.get(int(depth_str), AnalysisDepth.STANDARD)
                logger.debug(
                    f"[DataCoordinator] Numeric level {depth_str} -> {depth.value}"
                )
                return depth
            elif isinstance(depth_str, str):
                if depth_str.isdigit():
                    depth = numeric_mapping.get(int(depth_str), AnalysisDepth.STANDARD)
                    logger.debug(
                        f"[DataCoordinator] String number '{depth_str}' -> {depth.value}"
                    )
                    return depth
                elif depth_str in [
                    "Quick",
                    "Basic",
                    "Standard",
                    "Deep",
                    "Comprehensive",
                ]:
                    mapping = {
                        "Quick": AnalysisDepth.QUICK,
                        "Basic": AnalysisDepth.BASIC,
                        "Standard": AnalysisDepth.STANDARD,
                        "Deep": AnalysisDepth.DEEP,
                        "Comprehensive": AnalysisDepth.COMPREHENSIVE,
                    }
                    return mapping.get(depth_str, AnalysisDepth.STANDARD)

            return AnalysisDepth.STANDARD
        except Exception as e:
            logger.warning(f"[DataCoordinator] Failed to get analysis depth: {e}")
            return AnalysisDepth.STANDARD

    def _get_cache_key(self, ticker: str, trade_date: str) -> str:
        """Generate cache key"""
        return f"{ticker}_{trade_date}"

    def _get_tiered_cache_ttl(self, data_category: str = "default") -> int:
        """
        获取分级缓存TTL（支持财报发布日期感知）

        Args:
            data_category: 数据类别（valuation/financial/dividend/default）

        Returns:
            int: 缓存TTL（秒）
        """
        from tradingagents.utils.financial_calendar import FinancialCalendar

        # 基础TTL
        base_ttl = self._tiered_cache_config.get(data_category, self._cache_ttl_seconds)

        # 财报数据需要考虑财报发布日期
        if data_category in ["financial", "fundamental"]:
            return FinancialCalendar.get_adjusted_ttl(
                data_category=data_category,
                base_ttl=base_ttl,
                sensitive_days=3,  # 财报发布前3天开始缩短缓存
            )

        return base_ttl

    def _is_cache_valid(
        self, data: PreloadedData, data_category: str = "default"
    ) -> bool:
        """
        Check if cache is valid

        Args:
            data: PreloadedData instance
            data_category: 数据类别，用于分级缓存TTL

        Returns:
            bool: 缓存是否有效
        """
        if not data:
            return False

        # 使用分级缓存TTL
        cache_ttl = self._get_tiered_cache_ttl(data_category)

        age = (datetime.now() - data.loaded_at).total_seconds()
        return age < cache_ttl

    def preload_analysis_data(
        self, ticker: str, trade_date: str, analysis_depth: str = None
    ) -> PreloadedData:
        """
        Preload all data needed for analysis (all preload strategy)

        Args:
            ticker: Stock ticker
            trade_date: Trade date
            analysis_depth: Analysis depth (optional, read from config)

        Returns:
            PreloadedData: All preloaded data
        """
        cache_key = self._get_cache_key(ticker, trade_date)

        # Try to get from cache
        with self._cache_lock:
            if ticker in self._preloaded_cache:
                if trade_date in self._preloaded_cache[ticker]:
                    cached_data = self._preloaded_cache[ticker][trade_date]
                    if self._is_cache_valid(cached_data):
                        logger.info(f"[DataCoordinator] Cache hit: {cache_key}")
                        return cached_data

        logger.info(f"[DataCoordinator] Start preloading data: {cache_key}")

        # Load config
        self._load_config()

        # Determine analysis depth
        if not analysis_depth:
            depth = self._get_depth_from_config()
        else:
            depth_mapping = {
                "Quick": AnalysisDepth.QUICK,
                "Basic": AnalysisDepth.BASIC,
                "Standard": AnalysisDepth.STANDARD,
                "Deep": AnalysisDepth.DEEP,
                "Comprehensive": AnalysisDepth.COMPREHENSIVE,
            }
            depth = depth_mapping.get(analysis_depth, AnalysisDepth.STANDARD)

        # Create preloaded data object
        preloaded = PreloadedData(
            ticker=ticker, trade_date=trade_date, depth=depth.value
        )

        try:
            # 1. Load config
            from tradingagents.utils.stock_utils import StockUtils
            from tradingagents.utils.trading_date_manager import (
                get_trading_date_manager,
            )

            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info["is_china"]
            is_hk = market_info["is_hk"]
            is_us = market_info["is_us"]

            date_mgr = get_trading_date_manager()
            aligned_date = date_mgr.get_latest_trading_date(trade_date)

            # 2. Preload market data (with independent error handling)
            logger.info(f"[DataCoordinator] Preload market data: {ticker}")
            try:
                if is_china:
                    from tradingagents.dataflows.interface import (
                        get_china_stock_data_unified,
                    )

                    market_data = get_china_stock_data_unified(
                        ticker, aligned_date, aligned_date
                    )
                    preloaded.market_data = f"## A-Share Market Data\n{market_data}"
                elif is_hk:
                    from tradingagents.dataflows.interface import (
                        get_hk_stock_data_unified,
                    )

                    market_data = get_hk_stock_data_unified(
                        ticker, aligned_date, aligned_date
                    )
                    preloaded.market_data = f"## HK Stock Market Data\n{market_data}"
                else:
                    from tradingagents.dataflows.providers.us.optimized import (
                        get_us_stock_data_cached,
                    )

                    market_data = get_us_stock_data_cached(
                        ticker, aligned_date, aligned_date
                    )
                    preloaded.market_data = f"## US Stock Market Data\n{market_data}"
                logger.info(f"[DataCoordinator] Market data loaded successfully")
            except Exception as e:
                logger.error(
                    f"[DataCoordinator] Market data load failed: {e}", exc_info=True
                )
                preloaded.market_data = (
                    f"## Market Data: (unavailable - {str(e)[:100]})"
                )

            # 3. Preload price info to cache (independent error handling)
            try:
                self._extract_and_cache_price_info(ticker, preloaded.market_data)
            except Exception as e:
                logger.warning(f"[DataCoordinator] Price cache failed: {e}")

            # 4. Preload fundamentals data (independent error handling)
            logger.info(f"[DataCoordinator] Preload fundamentals data: {ticker}")
            try:
                if is_china:
                    preloaded.fundamentals_data = self._load_china_fundamentals(
                        ticker, aligned_date
                    )
                elif is_hk:
                    preloaded.fundamentals_data = self._load_hk_fundamentals(ticker)
                else:
                    preloaded.fundamentals_data = self._load_us_fundamentals(
                        ticker, trade_date
                    )
                logger.info(f"[DataCoordinator] Fundamentals data loaded successfully")
            except Exception as e:
                logger.error(
                    f"[DataCoordinator] Fundamentals data load failed: {e}",
                    exc_info=True,
                )
                preloaded.fundamentals_data = (
                    f"## Fundamentals Data: (unavailable - {str(e)[:100]})"
                )

            # 5. Preload news data (independent error handling)
            logger.info(f"[DataCoordinator] Preload news data: {ticker}")
            try:
                preloaded.news_data = self._load_news_data(
                    ticker, trade_date, market_info
                )
            except Exception as e:
                logger.warning(f"[DataCoordinator] News data load failed: {e}")
                preloaded.news_data = f"## News Data: (unavailable - {str(e)[:100]})"

            # 6. Preload sentiment data (independent error handling)
            logger.info(f"[DataCoordinator] Preload sentiment data: {ticker}")
            try:
                preloaded.sentiment_data = self._load_sentiment_data(
                    ticker, trade_date, market_info
                )
            except Exception as e:
                logger.warning(f"[DataCoordinator] Sentiment data load failed: {e}")
                preloaded.sentiment_data = (
                    f"## Sentiment Data: (unavailable - {str(e)[:100]})"
                )

            # 7. 计算数据质量评分 (Phase 1.1)
            try:
                preloaded = self._calculate_data_quality(
                    ticker, preloaded, market_info
                )
                logger.info(
                    f"[DataCoordinator] 数据质量评分: {preloaded.data_quality_grade} "
                    f"({preloaded.data_quality_score:.1f}/100)"
                )
            except Exception as e:
                logger.warning(f"[DataCoordinator] 数据质量评分计算失败: {e}")
                # 使用默认值
                preloaded.data_quality_score = 100.0
                preloaded.data_quality_grade = "A"
                preloaded.data_quality_issues = []

            logger.info(f"[DataCoordinator] Data preload completed: {cache_key}")

        except Exception as e:
            logger.error(
                f"[DataCoordinator] Unexpected error during data preload: {e}",
                exc_info=True,
            )

        # Save to cache
        with self._cache_lock:
            if ticker not in self._preloaded_cache:
                self._preloaded_cache[ticker] = {}
            self._preloaded_cache[ticker][trade_date] = preloaded

        return preloaded

    def _extract_and_cache_price_info(self, ticker: str, market_data: str):
        """Extract price info from market data and cache"""
        try:
            price_cache = self._get_price_cache()

            import re

            price_patterns = [
                r"Current Price[.:]\s*([\d.]+)",
                r"Latest Price[.:]\s*([\d.]+)",
                r"Close[.:]\s*([\d.]+)",
                r"close[.:]\s*([\d.]+)",
            ]

            current_price = None
            for pattern in price_patterns:
                match = re.search(pattern, market_data, re.IGNORECASE)
                if match:
                    current_price = float(match.group(1))
                    break

            if current_price:
                price_cache.update(ticker, current_price, "CNY")
                logger.debug(
                    f"[DataCoordinator] Price cached: {ticker} = {current_price}"
                )
        except Exception as e:
            logger.warning(f"[DataCoordinator] Price cache failed: {e}")

    def _load_china_fundamentals(self, ticker: str, trade_date: str) -> str:
        """Load China stock fundamentals data using comprehensive financial tool"""
        try:
            from tradingagents.agents.utils.agent_utils import Toolkit
            from tradingagents.dataflows.interface import get_china_stock_data_unified
            from datetime import datetime, timedelta

            logger.info(
                f"[DataCoordinator] Loading comprehensive financial data for {ticker}"
            )

            # 🔥 使用新的完整财务数据工具获取标准化数据
            comprehensive_financials = (
                Toolkit.get_stock_comprehensive_financials.invoke(
                    {"ticker": ticker, "curr_date": trade_date}
                )
            )

            # 同时获取价格数据作为补充
            recent_end = trade_date
            recent_start = (
                datetime.strptime(trade_date, "%Y-%m-%d") - timedelta(days=5)
            ).strftime("%Y-%m-%d")
            price_data = get_china_stock_data_unified(ticker, recent_start, recent_end)

            # 组合输出
            return f"""## A-Share Comprehensive Financial Data

{comprehensive_financials}

## A-Share Price Data (Supplement)
{price_data}
"""
        except Exception as e:
            logger.error(f"[DataCoordinator] A-Share fundamentals load failed: {e}")
            # 降级到旧方法
            try:
                from tradingagents.dataflows.interface import (
                    get_china_stock_data_unified,
                )
                from tradingagents.dataflows.optimized_china_data import (
                    OptimizedChinaDataProvider,
                )

                price_data = get_china_stock_data_unified(
                    ticker, trade_date, trade_date
                )
                analyzer = OptimizedChinaDataProvider()
                fundamentals = analyzer._generate_fundamentals_report(
                    ticker, price_data, "standard"
                )
                return f"## A-Share Fundamentals Data (Fallback)\n{fundamentals}\n\n## Price Data\n{price_data}"
            except Exception as fallback_error:
                logger.error(
                    f"[DataCoordinator] Fallback also failed: {fallback_error}"
                )
                return f"Fundamentals data fetch failed: {e}"

    def _load_hk_fundamentals(self, ticker: str) -> str:
        """Load HK stock fundamentals data"""
        try:
            from tradingagents.dataflows.interface import get_hk_stock_data_unified
            from tradingagents.dataflows.interface import get_hk_stock_info_unified

            info = get_hk_stock_info_unified(ticker)
            info_text = f"""## HK Stock Basic Info

**Ticker**: {ticker}
**Name**: {info.get("name", f"HK Stock {ticker}")}
**Currency**: HKD
**Exchange**: Hong Kong Stock Exchange (HKG)
"""
            return info_text
        except Exception as e:
            logger.error(f"[DataCoordinator] HK stock fundamentals load failed: {e}")
            return f"Fundamentals data fetch failed: {e}"

    def _load_us_fundamentals(self, ticker: str, trade_date: str) -> str:
        """Load US stock fundamentals data"""
        try:
            from tradingagents.dataflows.interface import get_fundamentals_openai

            fundamentals = get_fundamentals_openai(ticker, trade_date)
            return f"## US Stock Fundamentals Data\n{fundamentals}"
        except Exception as e:
            logger.error(f"[DataCoordinator] US stock fundamentals load failed: {e}")
            return f"Fundamentals data fetch failed: {e}"

    def _load_news_data(self, ticker: str, trade_date: str, market_info: Dict) -> str:
        """Load news data"""
        try:
            from tradingagents.dataflows.interface import get_stock_news_unified

            return get_stock_news_unified(ticker, trade_date)
        except Exception as e:
            logger.warning(f"[DataCoordinator] News data load failed: {e}")
            return f"News data fetch failed: {e}"

    def _load_sentiment_data(
        self, ticker: str, trade_date: str, market_info: Dict
    ) -> str:
        """Load sentiment data"""
        try:
            from tradingagents.dataflows.interface import get_stock_sentiment_unified

            return get_stock_sentiment_unified(ticker, trade_date)
        except Exception as e:
            logger.warning(f"[DataCoordinator] Sentiment data load failed: {e}")
            return f"Sentiment data fetch failed: {e}"

    def get_market_data(self, ticker: str, start_date: str, end_date: str) -> str:
        """
        Get market data, prefer cache

        Args:
            ticker: Stock ticker
            start_date: Start date
            end_date: End date

        Returns:
            str: Market data
        """
        # Try to get from preload cache
        with self._cache_lock:
            if ticker in self._preloaded_cache:
                for trade_date, data in self._preloaded_cache[ticker].items():
                    if self._is_cache_valid(data) and data.market_data:
                        logger.debug(
                            f"[DataCoordinator] Get market data from preload cache: {ticker}"
                        )
                        return data.market_data

        # Cache miss, get from API
        logger.info(
            f"[DataCoordinator] Market data cache miss, fetch from API: {ticker}"
        )
        return self._fetch_market_data(ticker, start_date, end_date)

    def get_fundamentals_data(
        self, ticker: str, start_date: str = None, end_date: str = None
    ) -> str:
        """
        Get fundamentals data, prefer cache

        Args:
            ticker: Stock ticker
            start_date: Start date (optional)
            end_date: End date (optional)

        Returns:
            str: Fundamentals data
        """
        # Try to get from preload cache
        with self._cache_lock:
            if ticker in self._preloaded_cache:
                for trade_date, data in self._preloaded_cache[ticker].items():
                    if self._is_cache_valid(data) and data.fundamentals_data:
                        logger.debug(
                            f"[DataCoordinator] Get fundamentals from preload cache: {ticker}"
                        )
                        return data.fundamentals_data

        # Cache miss, get from API
        logger.info(
            f"[DataCoordinator] Fundamentals data cache miss, fetch from API: {ticker}"
        )
        return self._fetch_fundamentals_data(ticker, start_date, end_date)

    def _fetch_market_data(self, ticker: str, start_date: str, end_date: str) -> str:
        """Fetch market data from API"""
        try:
            from tradingagents.utils.stock_utils import StockUtils

            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info["is_china"]
            is_hk = market_info["is_hk"]

            if is_china:
                from tradingagents.dataflows.interface import (
                    get_china_stock_data_unified,
                )

                return f"## A-Share Market Data\n{get_china_stock_data_unified(ticker, start_date, end_date)}"
            elif is_hk:
                from tradingagents.dataflows.interface import get_hk_stock_data_unified

                return f"## HK Stock Market Data\n{get_hk_stock_data_unified(ticker, start_date, end_date)}"
            else:
                from tradingagents.dataflows.providers.us.optimized import (
                    get_us_stock_data_cached,
                )

                return f"## US Stock Market Data\n{get_us_stock_data_cached(ticker, start_date, end_date)}"
        except Exception as e:
            logger.error(f"[DataCoordinator] Market data API call failed: {e}")
            return f"Market data fetch failed: {e}"

    def _fetch_fundamentals_data(
        self, ticker: str, start_date: str = None, end_date: str = None
    ) -> str:
        """Fetch fundamentals data from API"""
        try:
            from tradingagents.utils.stock_utils import StockUtils
            from datetime import datetime, timedelta

            market_info = StockUtils.get_market_info(ticker)
            is_china = market_info["is_china"]
            is_hk = market_info["is_hk"]

            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (
                    datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=5)
                ).strftime("%Y-%m-%d")

            if is_china:
                return self._load_china_fundamentals(ticker, end_date)
            elif is_hk:
                return self._load_hk_fundamentals(ticker)
            else:
                return self._load_us_fundamentals(ticker, end_date)
        except Exception as e:
            logger.error(f"[DataCoordinator] Fundamentals data API call failed: {e}")
            return f"Fundamentals data fetch failed: {e}"

    def get_all_data(self, ticker: str, trade_date: str) -> Dict[str, str]:
        """
        Get all data needed by analysts

        Args:
            ticker: Stock ticker
            trade_date: Trade date

        Returns:
            Dict: All data dictionary
        """
        preloaded = self.preload_analysis_data(ticker, trade_date)

        return {
            "market_data": preloaded.market_data,
            "fundamentals_data": preloaded.fundamentals_data,
            "news_data": preloaded.news_data,
            "sentiment_data": preloaded.sentiment_data,
            "price_info": preloaded.price_info,
        }

    def get_price_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get price info"""
        price_cache = self._get_price_cache()
        return price_cache.get_price_info(ticker)

    def update_price(self, ticker: str, price: float, currency: str = "CNY"):
        """Update price cache"""
        price_cache = self._get_price_cache()
        price_cache.update(ticker, price, currency)

    def clear_cache(self, ticker: str = None):
        """Clear cache"""
        with self._cache_lock:
            if ticker:
                if ticker in self._preloaded_cache:
                    del self._preloaded_cache[ticker]
                    logger.debug(f"[DataCoordinator] Cache cleared: {ticker}")
            else:
                self._preloaded_cache.clear()
                logger.debug("[DataCoordinator] All cache cleared")

        price_cache = self._get_price_cache()
        price_cache.clear(ticker)

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._cache_lock:
            total_entries = sum(len(dates) for dates in self._preloaded_cache.values())

        price_cache = self._get_price_cache()
        price_stats = price_cache.get_cache_stats()

        return {
            "preloaded_stocks": len(self._preloaded_cache),
            "preloaded_entries": total_entries,
            "price_cache_stats": price_stats,
        }

    def _calculate_data_quality(
        self, ticker: str, preloaded: PreloadedData, market_info: Dict[str, Any]
    ) -> PreloadedData:
        """
        计算数据质量评分 (Phase 1.1)

        Args:
            ticker: 股票代码
            preloaded: 预加载的数据
            market_info: 市场信息

        Returns:
            PreloadedData: 更新后的预加载数据（包含质量评分）
        """
        try:
            from tradingagents.dataflows.data_source_manager import (
                DataSourceManager,
                ValidatedDataResult,
            )

            # 创建数据源管理器
            data_manager = DataSourceManager()

            # 从市场数据中提取关键指标
            extracted_data = self._extract_metrics_from_data(
                preloaded.market_data, preloaded.fundamentals_data
            )

            # 获取验证结果
            validated_result = data_manager.get_data_with_validation(
                ticker, extracted_data
            )

            # 更新预加载数据
            preloaded.data_quality_score = validated_result.quality_score
            preloaded.data_quality_grade = validated_result.quality_grade
            preloaded.data_quality_issues = validated_result.quality_issues

        except Exception as e:
            logger.warning(f"[_calculate_data_quality] 质量评分计算失败: {e}")
            # 使用默认值
            preloaded.data_quality_score = 100.0
            preloaded.data_quality_grade = "A"
            preloaded.data_quality_issues = []

        return preloaded

    def _extract_metrics_from_data(
        self, market_data: str, fundamentals_data: str
    ) -> Dict[str, Any]:
        """
        从文本数据中提取关键指标

        Args:
            market_data: 市场数据文本
            fundamentals_data: 基本面数据文本

        Returns:
            Dict[str, Any]: 提取的指标字典
        """
        import re

        metrics = {}

        # 从市场数据中提取价格信息
        price_patterns = {
            "current_price": r"(?:Current Price|Latest Price|Close|current_price)[.:]?\s*[\u00a5\uffe5$]?\s*([\d.]+)",
            "open": r"(?:Open|open)[.:]?\s*[\u00a5\uffe5$]?\s*([\d.]+)",
            "high": r"(?:High|high|Highest)[.:]?\s*[\u00a5\uffe5$]?\s*([\d.]+)",
            "low": r"(?:Low|low|Lowest)[.:]?\s*[\u00a5\uffe5$]?\s*([\d.]+)",
            "volume": r"(?:Volume|volume|成交量)[.:]?\s*([\d,]+)",
        }

        combined_text = f"{market_data}\n{fundamentals_data}"

        for key, pattern in price_patterns.items():
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            if matches:
                try:
                    # 取最后一个匹配值（通常是最新的）
                    value = matches[-1].replace(",", "")
                    metrics[key] = float(value)
                except (ValueError, IndexError):
                    pass

        # 从基本面数据中提取估值指标
        valuation_patterns = {
            "PE": r"(?:P/E|PE|市盈率)[.:]?\s*([\d.]+)",
            "PB": r"(?:P/B|PB|市净率)[.:]?\s*([\d.]+)",
            "PS": r"(?:P/S|PS|市销率)[.:]?\s*([\d.]+)",
            "ROE": r"(?:ROE|净资产收益率)[.:]?\s*([\d.]+)",
            "ROA": r"(?:ROA|总资产收益率)[.:]?\s*([\d.]+)",
            "market_cap": r"(?:Market Cap|市值|market_cap)[.:]?\s*[\u00a5\uffe5$]?\s*([\d.]+)",
        }

        for key, pattern in valuation_patterns.items():
            matches = re.findall(pattern, fundamentals_data, re.IGNORECASE)
            if matches:
                try:
                    value = matches[-1].replace(",", "")
                    # 处理可能的单位（亿/万）
                    if "\u4ebf" in fundamentals_data[: fundamentals_data.find(matches[-1]) + 100]:
                        value = float(value)
                    else:
                        value = float(value)
                    metrics[key] = value
                except (ValueError, IndexError):
                    pass

        # 提取移动平均线
        ma_patterns = {
            "MA5": r"MA5[.:]?\s*([\d.]+)",
            "MA10": r"MA10[.:]?\s*([\d.]+)",
            "MA20": r"MA20[.:]?\s*([\d.]+)",
            "MA60": r"MA60[.:]?\s*([\d.]+)",
        }

        for key, pattern in ma_patterns.items():
            matches = re.findall(pattern, market_data, re.IGNORECASE)
            if matches:
                try:
                    metrics[key] = float(matches[-1])
                except (ValueError, IndexError):
                    pass

        return metrics


# Global singleton getter
def get_data_coordinator() -> DataCoordinator:
    return DataCoordinator()
