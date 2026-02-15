# -*- coding: utf-8 -*-
"""
降级管理器
负责数据源降级策略和备用数据源管理
"""

import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import pandas as pd

from tradingagents.utils.logging_manager import get_logger

if TYPE_CHECKING:
    from tradingagents.dataflows.data_sources.enums import ChinaDataSource

logger = get_logger("agents")


class FallbackManager:
    """降级管理器 - 处理数据源降级和备用策略"""

    def __init__(self, available_sources: List[Any], current_source: Any):
        """
        初始化降级管理器

        Args:
            available_sources: 可用的数据源列表 (List[ChinaDataSource])
            current_source: 当前数据源 (ChinaDataSource)
        """
        self.available_sources = available_sources
        self.current_source = current_source

    def get_data_source_priority_order(
        self, symbol: Optional[str] = None
    ) -> List[Any]:
        """
        从环境变量获取数据源优先级顺序（用于降级）

        Args:
            symbol: 股票代码，用于识别市场类型

        Returns:
            按优先级排序的数据源列表 (List[ChinaDataSource])
        """
        # 延迟导入，避免循环导入
        from tradingagents.dataflows.data_sources.enums import ChinaDataSource

        # 从环境变量读取配置
        env_priority = os.getenv(
            "HISTORICAL_DATA_SOURCE_PRIORITY", "tushare,akshare,baostock"
        )

        # 解析环境变量配置
        source_mapping = {
            "tushare": ChinaDataSource.TUSHARE,
            "akshare": ChinaDataSource.AKSHARE,
            "baostock": ChinaDataSource.BAOSTOCK,
        }

        result = []
        for source_name in env_priority.split(","):
            source_name = source_name.strip().lower()
            if source_name in source_mapping:
                source = source_mapping[source_name]
                if source in self.available_sources:
                    result.append(source)

        if result:
            logger.info(f"✅ [数据源优先级] 从.env读取: {[s.value for s in result]}")
            return result

        # 回退到默认顺序
        default_order = [
            ChinaDataSource.TUSHARE,
            ChinaDataSource.AKSHARE,
            ChinaDataSource.BAOSTOCK,
        ]

        logger.warning(
            f"⚠️ [数据源优先级] .env配置无效，使用默认顺序"
        )

        # 只返回可用的数据源
        return [s for s in default_order if s in self.available_sources]

    def try_fallback_sources(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        realtime_quote: Dict[str, Any] = None,
        data_fetcher=None,
    ) -> Tuple[str, Optional[str]]:
        """
        尝试备用数据源 - 避免递归调用

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期
            realtime_quote: 实时行情数据
            data_fetcher: 数据获取函数字典 {source: callable}

        Returns:
            tuple[str, str | None]: (结果字符串, 实际使用的数据源名称)
        """
        logger.info(
            f"🔄 [{self.current_source.value}] 失败，尝试备用数据源获取{period}数据: {symbol}"
        )

        # 从数据库获取数据源优先级顺序
        fallback_order = self.get_data_source_priority_order(symbol)

        for source in fallback_order:
            if source != self.current_source and source in self.available_sources:
                try:
                    logger.info(
                        f"🔄 [备用数据源] 尝试 {source.value} 获取{period}数据: {symbol}"
                    )

                    # 调用对应的数据获取函数
                    if data_fetcher and source in data_fetcher:
                        result = data_fetcher[source](
                            symbol, start_date, end_date, period, realtime_quote
                        )
                    else:
                        logger.warning(f"⚠️ 未找到 {source.value} 的数据获取函数")
                        continue

                    if "❌" not in result:
                        logger.info(
                            f"✅ [备用数据源-{source.value}] 成功获取{period}数据: {symbol}"
                        )
                        return result, source.value
                    else:
                        logger.warning(
                            f"⚠️ [备用数据源-{source.value}] 返回错误结果: {symbol}"
                        )

                except Exception as e:
                    logger.error(
                        f"❌ [备用数据源-{source.value}] 获取失败: {symbol}, 错误: {e}"
                    )
                    continue

        # 所有在线数据源都失败，尝试使用 MongoDB 缓存作为兜底
        logger.warning(f"⚠️ [所有在线数据源失败] 尝试使用 MongoDB 缓存兜底: {symbol}")
        try:
            from tradingagents.dataflows.cache.mongodb_cache_adapter import (
                get_mongodb_cache_adapter,
            )

            adapter = get_mongodb_cache_adapter()
            # 不限制日期范围，获取任何可用的历史数据
            df = adapter.get_historical_data(
                symbol, start_date=None, end_date=None, period=period
            )

            if df is not None and not df.empty:
                # 检查数据时效性
                if "date" in df.columns or "trade_date" in df.columns:
                    date_col = "date" if "date" in df.columns else "trade_date"
                    latest_date = df[date_col].max()
                    from datetime import datetime

                    if isinstance(latest_date, str):
                        latest_date = datetime.strptime(latest_date, "%Y-%m-%d")
                    days_old = (datetime.now() - latest_date).days

                    logger.warning(
                        f"⚠️ [MongoDB兜底] 使用可能过期的数据: {symbol}, "
                        f"最新数据日期: {latest_date.strftime('%Y-%m-%d')}, "
                        f"已过期: {days_old} 天"
                    )

                # 获取股票名称
                stock_name = f"股票{symbol}"
                if "name" in df.columns and not df["name"].empty:
                    stock_name = df["name"].iloc[0]

                # 调用格式化方法（通过回调）
                if data_fetcher and "format_response" in data_fetcher:
                    result = data_fetcher["format_response"](
                        df, symbol, stock_name, start_date, end_date, realtime_quote
                    )
                else:
                    result = f"✅ 从MongoDB兜底获取到 {symbol} 的历史数据"

                logger.info(
                    f"✅ [MongoDB兜底] 成功获取过期数据: {symbol} ({len(df)}条记录)"
                )
                return result, "mongodb_fallback"
            else:
                logger.error(f"❌ [MongoDB兜底] 也没有缓存数据: {symbol}")
        except Exception as e:
            logger.error(f"❌ [MongoDB兜底] 获取缓存数据失败: {symbol}, 错误: {e}")

        logger.error(f"❌ [所有数据源失败] 无法获取{period}数据: {symbol}")
        return f"❌ 所有数据源都无法获取{symbol}的{period}数据", None

    def try_fallback_sources_with_save(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        realtime_quote: Optional[Dict[str, Any]] = None,
        data_fetcher=None,
    ) -> Tuple[str, Optional[str]]:
        """
        从在线数据源获取数据并保存到 MongoDB

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期
            realtime_quote: 实时行情数据
            data_fetcher: 数据获取函数字典

        Returns:
            tuple[str, str | None]: (结果字符串, 实际使用的数据源名称)
        """
        # 获取数据源优先级
        fallback_order = self.get_data_source_priority_order(symbol)

        logger.info(
            f"🔄 [跳过MongoDB缓存] 直接从在线数据源获取: {symbol}, 优先级: {[s.value for s in fallback_order]}"
        )

        result_data = None
        actual_source = None

        # 依次尝试各数据源
        for source in fallback_order:
            try:
                logger.info(
                    f"🔄 [在线数据源] 尝试 {source.value} 获取{period}数据: {symbol}"
                )

                # 调用对应的数据获取函数
                if data_fetcher and source in data_fetcher:
                    result_data = data_fetcher[source](
                        symbol, start_date, end_date, period, realtime_quote
                    )
                else:
                    logger.warning(f"⚠️ 未找到 {source.value} 的数据获取函数")
                    continue

                if result_data and "❌" not in result_data:
                    actual_source = source.value
                    logger.info(
                        f"✅ [在线数据源-{source.value}] 成功获取{period}数据: {symbol}"
                    )
                    break
                else:
                    logger.warning(
                        f"⚠️ [在线数据源-{source.value}] 返回错误结果: {symbol}"
                    )

            except Exception as e:
                logger.error(
                    f"❌ [在线数据源-{source.value}] 获取失败: {symbol}, 错误: {e}"
                )
                continue

        # 保存到 MongoDB（如果配置了 SAVE_TO_MONGODB_AFTER_QUERY=true）
        if result_data and "❌" not in result_data:
            save_to_mongodb = (
                os.getenv("SAVE_TO_MONGODB_AFTER_QUERY", "true").lower() == "true"
            )
            if save_to_mongodb and actual_source:
                try:
                    logger.info(
                        f"💾 [数据保存] 将 {symbol} 数据保存到 MongoDB (来源: {actual_source})"
                    )
                except Exception as e:
                    logger.warning(
                        f"⚠️ [数据保存] 保存到 MongoDB 失败: {symbol}, 错误: {e}"
                    )

            return result_data, actual_source

        # 所有在线数据源都失败，尝试 MongoDB 兜底
        logger.warning(f"⚠️ [所有在线数据源失败] 尝试使用 MongoDB 缓存兜底: {symbol}")
        if data_fetcher and "mongodb" in data_fetcher:
            return data_fetcher["mongodb"](symbol, start_date, end_date, period, realtime_quote)
        return f"❌ 所有数据源都无法获取{symbol}的{period}数据", None

    def should_degrade_source(
        self,
        source: str,
        cache_manager=None,
        metric: Optional[str] = None,
    ) -> bool:
        """
        判断是否应该降级数据源

        基于最近失败率判断是否需要自动降级

        降级条件:
        1. 可靠性评分 < 40
        2. 最近10次调用失败率 > 70%

        Args:
            source: 数据源名称
            cache_manager: 缓存管理器实例
            metric: 指标名称（可选）

        Returns:
            bool: True表示应该降级
        """
        # 检查总体可靠性评分
        if cache_manager:
            reliability_score = cache_manager.get_source_reliability_score(source)
            if reliability_score < 40:
                logger.warning(
                    f"⚠️ [数据源降级] {source} 可靠性评分过低 ({reliability_score:.1f}/100)"
                )
                return True

        return False

    def auto_degrade_source(
        self,
        failed_source: str,
        available_sources: List[Any],
        cache_manager=None,
        metric: Optional[str] = None,
    ) -> Optional[Any]:
        """
        自动降级到备用数据源

        根据可靠性评分自动选择最佳备用数据源

        Args:
            failed_source: 失败的数据源名称
            available_sources: 可用的数据源列表 (List[ChinaDataSource])
            cache_manager: 缓存管理器实例
            metric: 指标名称（可选）

        Returns:
            ChinaDataSource: 推荐的备用数据源，如果没有合适的则返回None
        """
        # 排除失败的数据源
        candidates = [
            s for s in available_sources if s.value.lower() != failed_source.lower()
        ]

        if not candidates:
            logger.warning("⚠️ [数据源降级] 没有可用的备用数据源")
            return None

        # 根据可靠性评分排序
        scored_candidates = []
        for source in candidates:
            if cache_manager:
                score = cache_manager.get_source_reliability_score(source.value)
            else:
                # 默认评分
                default_scores = {
                    "tushare": 90.0,
                    "akshare": 70.0,
                    "baostock": 75.0,
                }
                score = default_scores.get(source.value.lower(), 60.0)
            scored_candidates.append((score, source))

        # 按评分降序排序
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # 选择评分最高的
        best_score, best_source = scored_candidates[0]

        logger.info(
            f"🔄 [数据源降级] 从 {failed_source} 自动降级到 {best_source.value} "
            f"(可靠性评分: {best_score:.1f}/100)"
        )

        return best_source
