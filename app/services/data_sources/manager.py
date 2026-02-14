# -*- coding: utf-8 -*-
"""
Data source manager that orchestrates multiple adapters with priority and optional consistency checks
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .akshare_adapter import AKShareAdapter
from .baostock_adapter import BaoStockAdapter
from .base import DataSourceAdapter
from .constants import NETWORK_ERROR_KEYWORDS
from .tushare_adapter import TushareAdapter

logger = logging.getLogger(__name__)


class DataSourceManager:
    """
    数据源管理器
    - 管理多个适配器，基于优先级排序
    - 提供 fallback 获取能力
    - 可选：一致性检查（若依赖存在）
    """

    def __init__(self):
        # 检查各数据源的启用状态
        import os

        tushare_enabled = os.getenv("TUSHARE_ENABLED", "true").lower() in ("true", "1", "yes", "on")
        akshare_enabled = os.getenv("AKSHARE_UNIFIED_ENABLED", "true").lower() in (
            "true",
            "1",
            "yes",
            "on",
        )
        baostock_enabled = os.getenv("BAOSTOCK_UNIFIED_ENABLED", "false").lower() in (
            "true",
            "1",
            "yes",
            "on",
        )

        adapters_list = []

        # 仅在启用时添加各数据源适配器
        if tushare_enabled:
            adapters_list.append(TushareAdapter())
            logger.info("[OK] Tushare 数据源已启用")
        else:
            logger.info("[SKIP] Tushare 数据源已禁用（通过 TUSHARE_ENABLED 配置）")

        if akshare_enabled:
            adapters_list.append(AKShareAdapter())
            logger.info("[OK] AKShare 数据源已启用")
        else:
            logger.info("[SKIP] AKShare 数据源已禁用（通过 AKSHARE_UNIFIED_ENABLED 配置）")

        if baostock_enabled:
            adapters_list.append(BaoStockAdapter())
            logger.info("[OK] BaoStock 数据源已启用")
        else:
            logger.info("[SKIP] BaoStock 数据源已禁用（通过 BAOSTOCK_UNIFIED_ENABLED 配置）")

        self.adapters: List[DataSourceAdapter] = adapters_list

        # 记录启用的数据源名称（用于数据库优先级查询过滤）
        self._enabled_adapter_names = {adapter.name for adapter in adapters_list}
        logger.info(f"[DATA] 启用的数据源: {self._enabled_adapter_names}")

        # 从数据库加载优先级配置
        self._load_priority_from_database()

        # 按优先级排序（数字越大优先级越高，所以降序排列）
        self.adapters.sort(key=lambda x: x.priority, reverse=True)

        try:
            from .data_consistency_checker import DataConsistencyChecker  # type: ignore

            self.consistency_checker = DataConsistencyChecker()
        except Exception:
            logger.warning("[WARN] 数据一致性检查器不可用")
            self.consistency_checker = None

    def _load_priority_from_database(self):
        """从数据库加载数据源优先级配置（从 datasource_groupings 集合读取 A股市场的优先级）

        优化：仅查询已启用的数据源配置，跳过禁用数据源的数据库查询
        优化：检查 CONFIG_SOURCE 参数，当设置为 env 时跳过数据库查询
        """
        # [HOT] 新增：检查 CONFIG_SOURCE 参数，跳过数据库配置查询
        try:
            from app.core.config import settings

            if settings.CONFIG_SOURCE == "env" or settings.SKIP_DATABASE_CONFIG:
                logger.info("[FAST] 跳过数据库优先级加载，使用默认优先级")
                # 使用默认优先级
                for adapter in self.adapters:
                    adapter._priority = adapter._get_default_priority()
                return
        except ImportError:
            # 配置模块不可用时继续正常流程
            pass

        try:
            from app.core.database import get_mongo_db_sync

            db = get_mongo_db_sync()
            groupings_collection = db.datasource_groupings

            # [HOT] 优化：构建查询条件，仅查询已启用的数据源
            # 这样可以跳过禁用数据源的数据库查询
            enabled_sources = list(self._enabled_adapter_names)
            query_conditions = {
                "market_category_id": "a_shares",
                "enabled": True,
                "data_source_name": {"$in": enabled_sources},  # [HOT] 仅查询已启用的数据源
            }

            logger.info(f"[DEBUG] [优先级加载] 查询已启用的数据源配置: {enabled_sources}")
            groupings = list(groupings_collection.find(query_conditions))

            if groupings:
                # 创建名称到优先级的映射（数据源名称需要转换为小写）
                priority_map = {}
                for grouping in groupings:
                    data_source_name = grouping.get("data_source_name", "").lower()
                    priority = grouping.get("priority")
                    if data_source_name and priority is not None:
                        priority_map[data_source_name] = priority
                        logger.info(
                            f"[DATA] 从数据库读取 {data_source_name} 在 A股市场的优先级: {priority}"
                        )

                # 更新各个 Adapter 的优先级
                for adapter in self.adapters:
                    if adapter.name in priority_map:
                        # 动态设置优先级
                        adapter._priority = priority_map[adapter.name]
                        logger.info(f"[OK] 设置 {adapter.name} 优先级: {adapter._priority}")
                    else:
                        # 使用默认优先级
                        adapter._priority = adapter._get_default_priority()
                        logger.info(
                            f"[WARN] 数据库中未找到 {adapter.name} 配置，使用默认优先级: {adapter._priority}"
                        )
            else:
                logger.info("[WARN] 数据库中未找到 A股市场的数据源配置，使用默认优先级")
                # 使用默认优先级
                for adapter in self.adapters:
                    adapter._priority = adapter._get_default_priority()
        except Exception as e:
            logger.warning(f"[WARN] 从数据库加载优先级失败: {e}，使用默认优先级")
            import traceback

            logger.warning(f"堆栈跟踪:\n{traceback.format_exc()}")
            # 使用默认优先级
            for adapter in self.adapters:
                adapter._priority = adapter._get_default_priority()

    def get_available_adapters(self) -> List[DataSourceAdapter]:
        available: List[DataSourceAdapter] = []
        for adapter in self.adapters:
            if adapter.is_available():
                available.append(adapter)
                logger.info(
                    f"Data source {adapter.name} is available (priority: {adapter.priority})"
                )
            else:
                logger.warning(f"Data source {adapter.name} is not available")
        return available

    def _reorder_adapters(
        self,
        available_adapters: List[DataSourceAdapter],
        preferred_sources: Optional[List[str]] = None,
    ) -> List[DataSourceAdapter]:
        """
        根据优先数据源重新排序适配器列表

        Args:
            available_adapters: 可用的适配器列表
            preferred_sources: 优先使用的数据源列表

        Returns:
            重新排序后的适配器列表
        """
        if not preferred_sources:
            return available_adapters

        logger.info(f"Using preferred data sources: {preferred_sources}")
        priority_map = {name: idx for idx, name in enumerate(preferred_sources)}
        preferred = [a for a in available_adapters if a.name in priority_map]
        others = [a for a in available_adapters if a.name not in priority_map]
        preferred.sort(key=lambda a: priority_map.get(a.name, 999))
        result = preferred + others
        logger.info(f"Reordered adapters: {[a.name for a in result]}")
        return result

    def _execute_with_fallback(
        self,
        fetch_func,
        log_message: str,
        preferred_sources: Optional[List[str]] = None,
    ) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        通用 fallback 执行方法

        Args:
            fetch_func: 接收 adapter 作为参数的获取函数，返回数据或 None
            log_message: 日志消息模板，例如 "stock list from {name}"
            preferred_sources: 优先使用的数据源列表

        Returns:
            (data, source_name) 或 (None, None)
        """
        available_adapters = self._reorder_adapters(
            self.get_available_adapters(), preferred_sources
        )

        for adapter in available_adapters:
            try:
                logger.info(f"Trying to fetch {log_message.format(name=adapter.name)}")
                result = fetch_func(adapter)
                if result is not None and (
                    not isinstance(result, pd.DataFrame) or not result.empty
                ):
                    return result, adapter.name
            except Exception as e:
                logger.error(f"Failed to fetch {log_message.format(name=adapter.name)}: {e}")
                continue
        return None, None

    def get_stock_list_with_fallback(
        self, preferred_sources: Optional[List[str]] = None
    ) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        获取股票列表，支持指定优先数据源

        Args:
            preferred_sources: 优先使用的数据源列表，例如 ['akshare', 'baostock']
                             如果为 None，则按照默认优先级顺序

        Returns:
            (DataFrame, source_name) 或 (None, None)
        """
        return self._execute_with_fallback(
            fetch_func=lambda adapter: adapter.get_stock_list(),
            log_message="stock list from {name}",
            preferred_sources=preferred_sources,
        )

    def get_daily_basic_with_fallback(
        self, trade_date: str, preferred_sources: Optional[List[str]] = None
    ) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        获取每日基础数据，支持指定优先数据源

        Args:
            trade_date: 交易日期
            preferred_sources: 优先使用的数据源列表

        Returns:
            (DataFrame, source_name) 或 (None, None)
        """
        return self._execute_with_fallback(
            fetch_func=lambda adapter: adapter.get_daily_basic(trade_date),
            log_message="daily basic data from {name}",
            preferred_sources=preferred_sources,
        )

    def find_latest_trade_date_with_fallback(
        self, preferred_sources: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        查找最新交易日期，支持指定优先数据源

        Args:
            preferred_sources: 优先使用的数据源列表

        Returns:
            交易日期字符串（YYYYMMDD格式）或 None
        """
        result, _ = self._execute_with_fallback(
            fetch_func=lambda adapter: adapter.find_latest_trade_date(),
            log_message="latest trade date from {name}",
            preferred_sources=preferred_sources,
        )
        return result if result else (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

    def _execute_items_with_fallback(
        self,
        fetch_func,
        log_message: str,
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """
        通用 fallback 执行方法（用于返回列表数据的方法）

        Args:
            fetch_func: 接收 adapter 作为参数的获取函数，返回列表数据或 None
            log_message: 日志消息模板

        Returns:
            (items_list, source_name) 或 (None, None)
        """
        available_adapters = self.get_available_adapters()
        for adapter in available_adapters:
            try:
                logger.info(f"Trying to fetch {log_message.format(name=adapter.name)}")
                result = fetch_func(adapter)
                if result:
                    return result, adapter.name
            except Exception as e:
                logger.error(f"Failed to fetch {log_message.format(name=adapter.name)}: {e}")
                continue
        return None, None

    def get_realtime_quotes_with_fallback(
        self,
    ) -> Tuple[Optional[Dict], Optional[str], Dict]:
        """
        获取全市场实时快照，按适配器优先级依次尝试，返回首个成功结果

        Returns:
            Tuple[quotes_dict, source_name, diagnostics]
            - quotes_dict: 行情数据，格式 { '000001': {'close': 10.0, 'pct_chg': 1.2, 'amount': 1.2e8}, ... }
            - source_name: 成功获取数据的数据源名称
            - diagnostics: 诊断信息，包含所有尝试的详细信息
        """
        import os
        import time

        diagnostics = {
            "attempts": [],
            "total_attempts": 0,
            "total_duration": 0.0,
            "fallback_used": False,
            "proxy_status": {
                "http_proxy": os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy") or "",
                "https_proxy": os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or "",
            },
        }

        available_adapters = self.get_available_adapters()
        start_time = time.time()

        for adapter in available_adapters:
            attempt_start = time.time()
            diagnostics["total_attempts"] += 1

            try:
                logger.info(f"尝试从 {adapter.name} 获取实时行情...")

                # [HOT] AKShare 支持多个数据源，eastmoney 失败时自动尝试 sina
                if adapter.name == "akshare":
                    # 先尝试 eastmoney
                    data = adapter.get_realtime_quotes(source="eastmoney")
                    if not data:
                        logger.info("东方财富接口失败，尝试新浪财经接口...")
                        diagnostics["total_attempts"] += 1
                        data = adapter.get_realtime_quotes(source="sina")
                else:
                    data = adapter.get_realtime_quotes()

                duration = time.time() - attempt_start

                if data:
                    diagnostics["attempts"].append(
                        {
                            "source": adapter.name,
                            "success": True,
                            "duration": round(duration, 3),
                            "record_count": len(data),
                            "error": None,
                        }
                    )
                    diagnostics["total_duration"] = time.time() - start_time
                    return data, adapter.name, diagnostics

                diagnostics["attempts"].append(
                    {
                        "source": adapter.name,
                        "success": False,
                        "duration": round(duration, 3),
                        "record_count": 0,
                        "error": "returned_empty_data",
                    }
                )

            except Exception as e:
                duration = time.time() - attempt_start
                error_type = type(e).__name__
                is_network_error = any(x in str(e).lower() for x in NETWORK_ERROR_KEYWORDS)

                diagnostics["attempts"].append(
                    {
                        "source": adapter.name,
                        "success": False,
                        "duration": round(duration, 3),
                        "record_count": 0,
                        "error_type": error_type,
                        "error": str(e)[:200],
                        "is_network_error": is_network_error,
                    }
                )
                diagnostics["fallback_used"] = True
                continue

        diagnostics["total_duration"] = time.time() - start_time
        logger.error(
            f"[ERROR] 所有数据源获取失败: "
            f"attempts={diagnostics['total_attempts']}, "
            f"duration={diagnostics['total_duration']:.2f}s"
        )
        return None, None, diagnostics

    def get_daily_quotes_with_fallback(
        self, trade_date: str
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        获取指定日期的全市场收盘行情，按优先级尝试
        主要用于补录历史收盘数据

        Returns:
            (quotes_dict, source_name)
        """
        available_adapters = self.get_available_adapters()
        for adapter in available_adapters:
            # 检查该 adapter 是否实现了 get_daily_quotes
            if not hasattr(adapter, "get_daily_quotes"):
                continue

            try:
                logger.info(f"尝试从 {adapter.name} 获取 {trade_date} 的日线行情...")
                data = adapter.get_daily_quotes(trade_date)
                if data:
                    return data, adapter.name
            except Exception as e:
                logger.error(f"从 {adapter.name} 获取日线行情失败: {e}")
                continue
        return None, None

    def get_snapshot_with_fallback(self) -> Tuple[Optional[Dict], Optional[str]]:
        """
        获取最新的行情快照（用于 backfill）。
        策略：
        1. 优先尝试 get_realtime_quotes_with_fallback (Tushare/AkShare 实时接口)
        2. 如果失败，尝试获取最新交易日的日线数据 get_daily_quotes_with_fallback (Tushare/Baostock)

        Returns:
            (quotes_dict, source_name)
        """
        # 1. 尝试实时接口
        logger.info("📡 [Backfill策略] 1. 尝试获取实时行情快照...")
        quotes, source, _ = self.get_realtime_quotes_with_fallback()
        if quotes:
            return quotes, source

        # 2. 尝试日线接口
        logger.info("📡 [Backfill策略] 2. 实时接口失败，尝试获取最新交易日收盘数据...")
        try:
            latest_date = self.find_latest_trade_date_with_fallback()
            if not latest_date:
                # 如果获取不到最新交易日，尝试用昨天
                latest_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

            logger.info(f"📅 目标交易日: {latest_date}")
            quotes, source = self.get_daily_quotes_with_fallback(latest_date)
            if quotes:
                logger.info(f"[OK] 成功从 {source} 获取到日线收盘数据作为快照")
                return quotes, f"{source}_daily"

        except Exception as e:
            logger.error(f"[ERROR] 获取日线兜底数据失败: {e}")

        logger.error("[ERROR] [Backfill策略] 所有途径均失败")
        return None, None

    def get_daily_basic_with_consistency_check(
        self, trade_date: str
    ) -> Tuple[Optional[pd.DataFrame], Optional[str], Optional[Dict]]:
        """
        使用一致性检查获取每日基础数据

        Returns:
            Tuple[DataFrame, source_name, consistency_report]
        """
        available_adapters = self.get_available_adapters()
        if len(available_adapters) < 2:
            df, source = self.get_daily_basic_with_fallback(trade_date)
            return df, source, None
        primary_adapter = available_adapters[0]
        secondary_adapter = available_adapters[1]
        try:
            logger.info(
                f"[DEBUG] 获取数据进行一致性检查: {primary_adapter.name} vs {secondary_adapter.name}"
            )
            primary_data = primary_adapter.get_daily_basic(trade_date)
            secondary_data = secondary_adapter.get_daily_basic(trade_date)
            if primary_data is None or primary_data.empty:
                logger.warning(f"[WARN] 主数据源{primary_adapter.name}失败，使用fallback")
                df, source = self.get_daily_basic_with_fallback(trade_date)
                return df, source, None
            if secondary_data is None or secondary_data.empty:
                logger.warning(f"[WARN] 次数据源{secondary_adapter.name}失败，使用主数据源")
                return primary_data, primary_adapter.name, None
            if self.consistency_checker:
                consistency_result = self.consistency_checker.check_daily_basic_consistency(
                    primary_data,
                    secondary_data,
                    primary_adapter.name,
                    secondary_adapter.name,
                )
                final_data, resolution_strategy = self.consistency_checker.resolve_data_conflicts(
                    primary_data, secondary_data, consistency_result
                )
                consistency_report = {
                    "is_consistent": consistency_result.is_consistent,
                    "confidence_score": consistency_result.confidence_score,
                    "recommended_action": consistency_result.recommended_action,
                    "resolution_strategy": resolution_strategy,
                    "differences": consistency_result.differences,
                    "primary_source": primary_adapter.name,
                    "secondary_source": secondary_adapter.name,
                }
                logger.info(
                    f"[DATA] 数据一致性检查完成: 置信度={consistency_result.confidence_score:.2f}, 策略={consistency_result.recommended_action}"
                )
                return final_data, primary_adapter.name, consistency_report
            else:
                logger.warning("[WARN] 一致性检查器不可用，使用主数据源")
                return primary_data, primary_adapter.name, None
        except Exception as e:
            logger.error(f"[ERROR] 一致性检查失败: {e}")
            df, source = self.get_daily_basic_with_fallback(trade_date)
            return df, source, None

    def get_kline_with_fallback(
        self,
        code: str,
        period: str = "day",
        limit: int = 120,
        adj: Optional[str] = None,
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """按优先级尝试获取K线，返回(items, source)"""
        return self._execute_items_with_fallback(
            fetch_func=lambda adapter: adapter.get_kline(
                code=code, period=period, limit=limit, adj=adj
            ),
            log_message="kline from {name}",
        )

    def get_news_with_fallback(
        self,
        code: str,
        days: int = 2,
        limit: int = 50,
        include_announcements: bool = True,
    ) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """按优先级尝试获取新闻与公告，返回(items, source)"""
        return self._execute_items_with_fallback(
            fetch_func=lambda adapter: adapter.get_news(
                code=code,
                days=days,
                limit=limit,
                include_announcements=include_announcements,
            ),
            log_message="news from {name}",
        )
