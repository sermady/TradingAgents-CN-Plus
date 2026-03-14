# -*- coding: utf-8 -*-
"""
回测数据加载器

直接对接项目数据源 Provider 和 MongoDB 缓存，
获取原始 DataFrame 数据（而非格式化字符串）。

数据源优先级：MongoDB缓存 → Tushare → AKShare → BaoStock
"""

import asyncio
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

import pandas as pd

from tradingagents.utils.logging_init import get_logger

logger = get_logger("backtest.data_loader")

# 标准列名（回测引擎使用）
STANDARD_COLUMNS = {
    "date", "open", "high", "low", "close", "pre_close",
    "volume", "amount", "change_pct", "turnover_rate",
}


class BacktestDataLoader:
    """
    回测数据加载器

    直接从 Provider 层获取 DataFrame，跳过 DataSourceManager
    的字符串格式化，为回测引擎提供干净的 OHLCV 数据。
    """

    def __init__(self):
        self._available_sources: List[str] = []
        self._detect_available_sources()

    def _detect_available_sources(self):
        """检测可用的数据源"""
        # MongoDB
        try:
            from tradingagents.config.runtime_settings import use_app_cache_enabled
            if use_app_cache_enabled(False):
                from tradingagents.dataflows.cache.mongodb_cache_adapter import (
                    get_mongodb_cache_adapter,
                )
                adapter = get_mongodb_cache_adapter()
                if adapter.use_app_cache and adapter.db is not None:
                    self._available_sources.append("mongodb")
        except Exception:
            pass

        # Tushare
        try:
            from tradingagents.dataflows.providers.china.tushare import get_tushare_provider
            provider = get_tushare_provider()
            if provider and provider.is_available():
                self._available_sources.append("tushare")
        except Exception:
            pass

        # AKShare
        try:
            import akshare  # noqa: F401
            self._available_sources.append("akshare")
        except ImportError:
            pass

        # BaoStock
        try:
            import baostock  # noqa: F401
            self._available_sources.append("baostock")
        except ImportError:
            pass

        logger.info(f"📥 回测数据加载器: 可用数据源={self._available_sources}")

    # ==================== 公共 API ====================

    def load_symbol(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> Optional[pd.DataFrame]:
        """
        加载单只股票的历史日线数据

        自动按优先级尝试：MongoDB → Tushare → AKShare → BaoStock

        Args:
            symbol: 6位纯数字代码，如 '000001'
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            标准化的 DataFrame，列名统一为:
            date, open, high, low, close, pre_close,
            volume(股), amount(元), change_pct(%), turnover_rate(%)
            按日期升序排列。失败返回 None。
        """
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        for source in self._available_sources:
            try:
                df = self._fetch_from_source(source, symbol, start_str, end_str)
                if df is not None and not df.empty:
                    df = self._standardize(df, symbol)
                    df = self._filter_date_range(df, start_date, end_date)
                    if not df.empty:
                        logger.info(
                            f"  ✅ {symbol}: {len(df)} 条记录 (来源: {source})"
                        )
                        return df
            except Exception as e:
                logger.debug(f"  ⚠️ {symbol} 从 {source} 获取失败: {e}")
                continue

        logger.warning(f"  ❌ {symbol}: 所有数据源均失败")
        return None

    def load_symbols(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
    ) -> Dict[str, pd.DataFrame]:
        """
        批量加载多只股票数据

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            {symbol: DataFrame} 字典，加载失败的股票不包含在内
        """
        logger.info(f"📥 开始加载 {len(symbols)} 只股票: {start_date} ~ {end_date}")
        result = {}

        for symbol in symbols:
            df = self.load_symbol(symbol, start_date, end_date)
            if df is not None:
                result[symbol] = df

        logger.info(f"✅ 加载完成: {len(result)}/{len(symbols)} 只股票成功")
        return result

    # ==================== 各数据源获取 ====================

    def _fetch_from_source(
        self, source: str, symbol: str, start_str: str, end_str: str
    ) -> Optional[pd.DataFrame]:
        """从指定数据源获取数据"""
        if source == "mongodb":
            return self._fetch_mongodb(symbol, start_str, end_str)
        elif source == "tushare":
            return self._fetch_tushare(symbol, start_str, end_str)
        elif source == "akshare":
            return self._fetch_akshare(symbol, start_str, end_str)
        elif source == "baostock":
            return self._fetch_baostock(symbol, start_str, end_str)
        return None

    def _fetch_mongodb(
        self, symbol: str, start_str: str, end_str: str
    ) -> Optional[pd.DataFrame]:
        """从 MongoDB 缓存获取"""
        from tradingagents.dataflows.cache.mongodb_cache_adapter import (
            get_mongodb_cache_adapter,
        )
        adapter = get_mongodb_cache_adapter()
        return adapter.get_historical_data(symbol, start_str, end_str, period="daily")

    def _fetch_tushare(
        self, symbol: str, start_str: str, end_str: str
    ) -> Optional[pd.DataFrame]:
        """从 Tushare 获取"""
        from tradingagents.dataflows.providers.china.tushare import get_tushare_provider
        provider = get_tushare_provider()
        if not provider or not provider.is_available():
            return None
        return self._run_async(
            provider.get_historical_data(symbol, start_str, end_str)
        )

    def _fetch_akshare(
        self, symbol: str, start_str: str, end_str: str
    ) -> Optional[pd.DataFrame]:
        """从 AKShare 获取"""
        from tradingagents.dataflows.providers.china.akshare import get_akshare_provider
        provider = get_akshare_provider()
        return self._run_async(
            provider.get_historical_data(symbol, start_str, end_str, "daily")
        )

    def _fetch_baostock(
        self, symbol: str, start_str: str, end_str: str
    ) -> Optional[pd.DataFrame]:
        """从 BaoStock 获取"""
        try:
            from tradingagents.dataflows.providers.china.baostock import get_baostock_provider
            provider = get_baostock_provider()
            return self._run_async(
                provider.get_historical_data(symbol, start_str, end_str, "daily")
            )
        except Exception:
            # BaoStock 可能不存在该模块，尝试直接调用
            return self._fetch_baostock_direct(symbol, start_str, end_str)

    def _fetch_baostock_direct(
        self, symbol: str, start_str: str, end_str: str
    ) -> Optional[pd.DataFrame]:
        """直接使用 baostock 库获取（兜底方案）"""
        import baostock as bs

        # 转换代码格式
        if symbol.startswith("6"):
            bs_code = f"sh.{symbol}"
        else:
            bs_code = f"sz.{symbol}"

        # 格式化日期
        s = f"{start_str[:4]}-{start_str[4:6]}-{start_str[6:8]}"
        e = f"{end_str[:4]}-{end_str[4:6]}-{end_str[6:8]}"

        lg = bs.login()
        try:
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,preclose,volume,amount,turn,pctChg",
                start_date=s,
                end_date=e,
                frequency="d",
                adjustflag="2",  # 前复权
            )

            rows = []
            while rs.error_code == "0" and rs.next():
                rows.append(rs.get_row_data())

            if not rows:
                return None

            df = pd.DataFrame(rows, columns=rs.fields)

            # 转换数值列
            for col in ["open", "high", "low", "close", "preclose", "volume", "amount", "turn", "pctChg"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            return df
        finally:
            bs.logout()

    # ==================== 标准化 ====================

    def _standardize(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        将各数据源返回的 DataFrame 标准化为统一格式

        标准列名:
          date, open, high, low, close, pre_close,
          volume(股), amount(元), change_pct(%), turnover_rate(%)
        """
        out = df.copy()

        # 列名映射（覆盖各数据源的常见命名）
        col_map = {
            # 日期
            "trade_date": "date",
            "日期": "date",
            # OHLC
            "Open": "open", "High": "high", "Low": "low", "Close": "close",
            "开盘": "open", "最高": "high", "最低": "low", "收盘": "close",
            # 昨收
            "pre_close": "pre_close", "preclose": "pre_close",
            "昨收": "pre_close",
            # 成交量
            "vol": "volume", "Volume": "volume", "成交量": "volume",
            # 成交额
            "Amount": "amount", "成交额": "amount",
            # 涨跌幅
            "pct_chg": "change_pct", "pctChg": "change_pct",
            "change_pct": "change_pct", "涨跌幅": "change_pct",
            # 换手率
            "turnover_rate": "turnover_rate", "turn": "turnover_rate",
            "换手率": "turnover_rate",
        }

        out = out.rename(columns={c: col_map.get(c, c) for c in out.columns})

        # 确保日期列存在且格式正确
        if "date" in out.columns:
            out["date"] = pd.to_datetime(out["date"], errors="coerce")
        elif isinstance(out.index, pd.DatetimeIndex):
            out["date"] = out.index
        else:
            logger.warning(f"⚠️ {symbol}: 缺少日期列")
            return pd.DataFrame()

        # 确保必要的数值列
        numeric_cols = ["open", "high", "low", "close", "pre_close",
                        "volume", "amount", "change_pct", "turnover_rate"]
        for col in numeric_cols:
            if col in out.columns:
                out[col] = pd.to_numeric(out[col], errors="coerce")
            else:
                out[col] = 0.0

        # 补充 pre_close（如果缺失）
        if out["pre_close"].isna().all() or (out["pre_close"] == 0).all():
            out["pre_close"] = out["close"].shift(1)
            out.loc[out.index[0], "pre_close"] = out["close"].iloc[0]

        # 补充 change_pct（如果缺失）
        if out["change_pct"].isna().all() or (out["change_pct"] == 0).all():
            out["change_pct"] = out["close"].pct_change() * 100.0
            out.loc[out.index[0], "change_pct"] = 0.0

        # 按日期升序
        out = out.sort_values("date").reset_index(drop=True)

        # 只保留标准列
        keep = [c for c in STANDARD_COLUMNS if c in out.columns]
        out = out[keep]

        # 移除全 NaN 行
        out = out.dropna(subset=["close"])

        return out

    def _filter_date_range(
        self, df: pd.DataFrame, start: date, end: date
    ) -> pd.DataFrame:
        """过滤日期范围"""
        if "date" not in df.columns:
            return df
        mask = (df["date"].dt.date >= start) & (df["date"].dt.date <= end)
        return df[mask].copy().reset_index(drop=True)

    # ==================== 工具方法 ====================

    @staticmethod
    def _run_async(coro):
        """安全运行异步协程"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
