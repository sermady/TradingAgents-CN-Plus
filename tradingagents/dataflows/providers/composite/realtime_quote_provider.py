# -*- coding: utf-8 -*-
"""
实时行情提供器 (Realtime Quote Provider)

从 DataSourceManager 中提取的组件，专门处理实时行情数据获取。
支持多数据源优先级配置和自动降级。

Created: 2026-01-31 (Phase 1 of DataSourceManager refactoring)
"""

import os
import time
import logging
from typing import Dict, Optional, Any, List, Tuple, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import numpy as np

from tradingagents.utils.logging_manager import get_logger

logger = get_logger("agents")


class RealtimeQuoteProvider:
    """
    实时行情数据提供器

    职责：
    1. 从多个数据源获取实时行情
    2. 支持优先级配置和自动降级
    3. 实现重试机制和错误处理
    4. 更新价格缓存

    支持的数据源：
    - AKShare (优先)
    - Tushare (备选)
    """

    def __init__(self):
        """初始化实时行情提供器"""
        self._config = self._load_config()
        self._executor = ThreadPoolExecutor(max_workers=4)
        logger.info("✅ RealtimeQuoteProvider initialized")

    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        return {
            "enabled": os.getenv("REALTIME_QUOTE_ENABLED", "true").lower() == "true",
            "tushare_enabled": os.getenv(
                "REALTIME_QUOTE_TUSHARE_ENABLED", "true"
            ).lower()
            == "true",
            "max_retries": int(os.getenv("REALTIME_QUOTE_MAX_RETRIES", "3")),
            "retry_delay": float(os.getenv("REALTIME_QUOTE_RETRY_DELAY", "1.0")),
            "retry_backoff": float(os.getenv("REALTIME_QUOTE_RETRY_BACKOFF", "2.0")),
            "akshare_priority": int(os.getenv("REALTIME_QUOTE_AKSHARE_PRIORITY", "1")),
            "tushare_priority": int(os.getenv("REALTIME_QUOTE_TUSHARE_PRIORITY", "2")),
            "timeout": float(os.getenv("REALTIME_QUOTE_TIMEOUT", "5.0")),
        }

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取实时行情（主要API）

        Args:
            symbol: 股票代码

        Returns:
            Dict with keys: price, change, change_pct, volume, turnover, open, high, low, prev_close
            None if all sources fail
        """
        if not self._config["enabled"]:
            logger.debug(f"[RealtimeQuote] Disabled, skipping {symbol}")
            return None

        logger.info(
            f"[RealtimeQuote] Fetching {symbol} (retries: {self._config['max_retries']})"
        )

        # 获取按优先级排序的数据源
        sources = self._get_sources_by_priority()

        # 依次尝试各数据源
        for source_name, source_func in sources:
            try:
                quote = self._fetch_with_retry(source_func, symbol)
                if quote:
                    logger.info(
                        f"[RealtimeQuote-{source_name.upper()}] Success for {symbol}"
                    )
                    self._update_price_cache(symbol, quote.get("price"))
                    return quote
            except Exception as e:
                logger.warning(f"[RealtimeQuote-{source_name.upper()}] Failed: {e}")
                continue

        logger.warning(f"[RealtimeQuote] All sources failed for {symbol}")
        return None

    def get_quotes_batch(
        self, symbols: List[str], max_workers: int = 4
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        批量获取实时行情

        Args:
            symbols: 股票代码列表
            max_workers: 并发线程数

        Returns:
            Dict mapping symbol to quote data (or None)
        """
        if not symbols:
            return {}

        results = {}

        # 使用线程池并发获取
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {
                executor.submit(self.get_quote, symbol): symbol for symbol in symbols
            }

            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    results[symbol] = future.result()
                except Exception as e:
                    logger.error(f"[RealtimeQuote-Batch] Error fetching {symbol}: {e}")
                    results[symbol] = None

        return results

    def _get_sources_by_priority(self) -> List[Tuple[str, Callable]]:
        """获取按优先级排序的数据源列表"""
        sources = []

        # AKShare
        if self._config["akshare_priority"] == 1:
            sources.append(("akshare", self._get_akshare_quote))

        # Tushare
        if self._config["tushare_enabled"] and self._config["tushare_priority"] == 1:
            sources.append(("tushare", self._get_tushare_quote))

        # AKShare (lower priority)
        if self._config["akshare_priority"] == 2:
            sources.append(("akshare", self._get_akshare_quote))

        # Tushare (lower priority)
        if self._config["tushare_enabled"] and self._config["tushare_priority"] == 2:
            sources.append(("tushare", self._get_tushare_quote))

        return sources

    def _fetch_with_retry(
        self, fetch_func: Callable, symbol: str
    ) -> Optional[Dict[str, Any]]:
        """带重试的获取"""
        max_retries = self._config["max_retries"]
        retry_delay = self._config["retry_delay"]
        backoff = self._config["retry_backoff"]

        for attempt in range(max_retries):
            try:
                result = fetch_func(symbol)
                if result:
                    return result
            except Exception as e:
                logger.warning(
                    f"[RealtimeQuote-Retry {attempt + 1}/{max_retries}] {symbol}: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= backoff

        return None

    def _get_akshare_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从AKShare获取实时行情"""
        try:
            import akshare as ak
            import asyncio

            # 标准化代码
            code_6 = symbol.split(".")[0] if "." in symbol else symbol
            code_6 = code_6.zfill(6)

            logger.debug(f"[AKShare-Realtime] Fetching {symbol} (code: {code_6})")

            # 判断市场
            if code_6.startswith("6"):
                # 上海
                full_code = f"sh{code_6}"
            elif code_6.startswith(("0", "3")):
                # 深圳
                full_code = f"sz{code_6}"
            elif code_6.startswith(("4", "8")):
                # 北交所/新三板
                full_code = f"bj{code_6}"
            else:
                full_code = f"sz{code_6}"  # 默认深圳

            # 使用AKShare获取实时行情
            try:
                # 尝试获取最新行情
                df = ak.stock_zh_a_spot_em()

                if df is None or df.empty:
                    return None

                # 查找对应股票
                code_col = "代码" if "代码" in df.columns else "股票代码"
                if code_col not in df.columns:
                    return None

                row = df[df[code_col] == code_6]
                if row.empty:
                    return None

                row = row.iloc[0]

                # 提取字段
                return self._extract_quote_from_akshare_row(row, symbol)

            except Exception as e:
                logger.warning(f"[AKShare-Realtime] Error: {e}")
                return None

        except ImportError:
            logger.warning("[AKShare-Realtime] akshare not installed")
            return None
        except Exception as e:
            logger.error(f"[AKShare-Realtime] Unexpected error: {e}")
            return None

    def _extract_quote_from_akshare_row(
        self, row: pd.Series, symbol: str
    ) -> Optional[Dict[str, Any]]:
        """从AKShare行数据提取行情"""
        try:
            # AKShare东方财富字段映射
            field_mapping = {
                "最新价": "price",
                "涨跌幅": "change_pct",
                "涨跌额": "change",
                "成交量": "volume",
                "成交额": "turnover",
                "今开": "open",
                "最高": "high",
                "最低": "low",
                "昨收": "prev_close",
            }

            quote = {
                "symbol": symbol,
                "source": "akshare",
                "timestamp": datetime.now().isoformat(),
            }

            for cn_field, en_field in field_mapping.items():
                if cn_field in row.index:
                    value = row[cn_field]
                    if pd.notna(value):
                        quote[en_field] = float(value)

            # 确保必要字段存在
            if "price" not in quote:
                return None

            # 标准化成交量单位（转为手）
            if "volume" in quote:
                # AKShare返回的是手，保持不变
                pass

            return quote

        except Exception as e:
            logger.error(f"[AKShare-Realtime] Extraction error: {e}")
            return None

    def _get_tushare_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从Tushare获取实时行情"""
        try:
            import asyncio
            import tushare as ts

            # 标准化代码
            code_6 = symbol.split(".")[0] if "." in symbol else symbol
            code_6 = code_6.zfill(6)

            logger.debug(f"[Tushare-Realtime] Fetching {symbol} (code: {code_6})")

            # 在线程池中执行同步调用
            # [改进] 使用 get_running_loop() 如果可用，否则获取/创建新loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # 没有运行中的loop，创建新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            future = loop.run_in_executor(
                None,  # 使用默认线程池
                lambda: ts.get_realtime_quotes(code_6),
            )

            # 等待执行完成并获取结果
            df = loop.run_until_complete(future)

            if df is None or df.empty:
                return None

            row = df.iloc[0]
            return self._extract_quote_from_tushare_row(row, symbol)

        except ImportError:
            logger.warning("[Tushare-Realtime] tushare not installed")
            return None
        except Exception as e:
            logger.error(f"[Tushare-Realtime] Error: {e}")
            return None

    def _extract_quote_from_tushare_row(
        self, row: pd.Series, symbol: str
    ) -> Optional[Dict[str, Any]]:
        """从Tushare行数据提取行情"""
        try:
            # Tushare实时行情字段映射
            quote = {
                "symbol": symbol,
                "source": "tushare",
                "timestamp": datetime.now().isoformat(),
            }

            # 价格字段
            if "price" in row:
                quote["price"] = float(row["price"])
            elif "pre_close" in row and "price" not in quote:
                # 如果没有price，使用pre_close作为fallback
                quote["price"] = float(row.get("pre_close", 0))

            # 其他字段
            if "open" in row:
                quote["open"] = float(row["open"])
            if "high" in row:
                quote["high"] = float(row["high"])
            if "low" in row:
                quote["low"] = float(row["low"])
            if "pre_close" in row:
                quote["prev_close"] = float(row["pre_close"])

            # 成交量（Tushare返回的是股数，转为手）
            if "volume" in row:
                volume = float(row["volume"])
                quote["volume"] = volume / 100  # 转为手

            # 成交额
            if "amount" in row:
                quote["turnover"] = float(row["amount"])

            # 涨跌幅计算
            if "price" in quote and "prev_close" in quote:
                prev = quote["prev_close"]
                curr = quote["price"]
                if prev > 0:
                    quote["change"] = curr - prev
                    quote["change_pct"] = (curr - prev) / prev * 100

            # 确保必要字段存在
            if "price" not in quote:
                return None

            return quote

        except Exception as e:
            logger.error(f"[Tushare-Realtime] Extraction error: {e}")
            return None

    def _update_price_cache(self, symbol: str, price: Optional[float]):
        """更新价格缓存"""
        if price is None:
            return
        try:
            from tradingagents.utils.price_cache import get_price_cache

            get_price_cache().update(symbol, price)
        except Exception as e:
            logger.debug(f"[RealtimeQuote] Price cache update failed: {e}")

    def reload_config(self):
        """重新加载配置（热更新）"""
        self._config = self._load_config()
        logger.info("✅ RealtimeQuoteProvider config reloaded")

    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return self._config.copy()


# 全局实例（单例模式）
_realtime_provider: Optional[RealtimeQuoteProvider] = None


def get_realtime_quote_provider() -> RealtimeQuoteProvider:
    """获取全局实时行情提供器实例"""
    global _realtime_provider
    if _realtime_provider is None:
        _realtime_provider = RealtimeQuoteProvider()
    return _realtime_provider


def reset_provider():
    """重置提供器（用于测试）"""
    global _realtime_provider
    _realtime_provider = None
