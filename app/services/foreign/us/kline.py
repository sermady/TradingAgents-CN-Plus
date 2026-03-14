# -*- coding: utf-8 -*-
"""美股K线数据模块

提供美股K线数据获取功能，支持多数据源。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List

import yfinance as yf

logger = logging.getLogger(__name__)


class KlineMixin:
    """K线数据 Mixin"""

    @property
    def kline_source_handlers(self) -> Dict:
        """K线数据源处理器映射"""
        return {
            "alpha_vantage": ("alpha_vantage", self._get_kline_from_alpha_vantage),
            "yahoo_finance": ("yfinance", self._get_kline_from_yfinance),
            "finnhub": ("finnhub", self._get_kline_from_finnhub),
        }

    async def get_kline(
        self,
        code: str,
        period: str = "day",
        limit: int = 120,
        force_refresh: bool = False,
    ) -> List[Dict]:
        """获取美股K线数据（使用基类模板方法）"""
        return await self.get_kline_template(code, period, limit, force_refresh)

    def _get_kline_from_yfinance(
        self, code: str, period: str, limit: int
    ) -> List[Dict]:
        """从yfinance获取美股K线数据"""
        ticker = yf.Ticker(code)

        period_map = {
            "day": "1d",
            "week": "1wk",
            "month": "1mo",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "60m": "60m",
        }

        interval = period_map.get(period, "1d")
        hist = ticker.history(period=f"{limit}d", interval=interval)

        if hist.empty:
            raise Exception("无数据")

        kline_data = []
        for date, row in hist.iterrows():
            date_str = date.strftime("%Y-%m-%d")
            kline_data.append({
                "date": date_str,
                "trade_date": date_str,
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
            })

        return kline_data

    def _get_kline_from_alpha_vantage(
        self, code: str, period: str, limit: int
    ) -> List[Dict]:
        """从Alpha Vantage获取美股K线数据"""
        from tradingagents.dataflows.providers.us.alpha_vantage_common import (
            get_api_key,
            _make_api_request,
        )
        import pandas as pd

        api_key = get_api_key()
        if not api_key:
            raise Exception("Alpha Vantage API Key 未配置")

        if period in ["5m", "15m", "30m", "60m"]:
            function = "TIME_SERIES_INTRADAY"
            params = {"symbol": code.upper(), "interval": period, "outputsize": "full"}
            time_series_key = f"Time Series ({period})"
        else:
            function = "TIME_SERIES_DAILY"
            params = {"symbol": code.upper(), "outputsize": "full"}
            time_series_key = "Time Series (Daily)"

        data = _make_api_request(function, params)

        if not data or time_series_key not in data:
            raise Exception("无数据")

        time_series = data[time_series_key]
        df = pd.DataFrame.from_dict(time_series, orient="index")
        df.index = pd.to_datetime(df.index)
        df = df.sort_index(ascending=False)
        df = df.head(limit)

        kline_data = []
        for date, row in df.iterrows():
            date_str = date.strftime("%Y-%m-%d")
            kline_data.append({
                "date": date_str,
                "trade_date": date_str,
                "open": float(row["1. open"]),
                "high": float(row["2. high"]),
                "low": float(row["3. low"]),
                "close": float(row["4. close"]),
                "volume": int(row["5. volume"]),
            })

        return kline_data

    def _get_kline_from_finnhub(self, code: str, period: str, limit: int) -> List[Dict]:
        """从Finnhub获取美股K线数据"""
        import finnhub
        import os

        api_key = os.getenv("FINNHUB_API_KEY")
        if not api_key:
            raise Exception("Finnhub API Key 未配置")

        client = finnhub.Client(api_key=api_key)
        end_date = datetime.now()

        if period == "day":
            start_date = end_date - timedelta(days=limit)
            resolution = "D"
        elif period == "week":
            start_date = end_date - timedelta(weeks=limit)
            resolution = "W"
        elif period == "month":
            start_date = end_date - timedelta(days=limit * 30)
            resolution = "M"
        elif period == "5m":
            start_date = end_date - timedelta(days=limit)
            resolution = "5"
        elif period == "15m":
            start_date = end_date - timedelta(days=limit)
            resolution = "15"
        elif period == "30m":
            start_date = end_date - timedelta(days=limit)
            resolution = "30"
        elif period == "60m":
            start_date = end_date - timedelta(days=limit)
            resolution = "60"
        else:
            start_date = end_date - timedelta(days=limit)
            resolution = "D"

        candles = client.stock_candles(
            code.upper(),
            resolution,
            int(start_date.timestamp()),
            int(end_date.timestamp()),
        )

        if not candles or candles.get("s") != "ok":
            raise Exception("无数据")

        kline_data = []
        for i in range(len(candles["t"])):
            date_str = datetime.fromtimestamp(candles["t"][i]).strftime("%Y-%m-%d")
            kline_data.append({
                "date": date_str,
                "trade_date": date_str,
                "open": float(candles["o"][i]),
                "high": float(candles["h"][i]),
                "low": float(candles["l"][i]),
                "close": float(candles["c"][i]),
                "volume": int(candles["v"][i]),
            })

        return kline_data
