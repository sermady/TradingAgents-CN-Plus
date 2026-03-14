# -*- coding: utf-8 -*-
"""美股实时行情模块

提供美股实时行情获取功能，支持多数据源。
"""

import logging
from typing import Dict

import yfinance as yf

logger = logging.getLogger(__name__)


class QuoteMixin:
    """实时行情 Mixin"""

    @property
    def quote_cache_key(self) -> str:
        """行情缓存key后缀"""
        return "us_realtime_quote"

    @property
    def quote_source_handlers(self) -> Dict:
        """行情数据源处理器映射"""
        return {
            "alpha_vantage": ("alpha_vantage", self._get_quote_from_alpha_vantage),
            "yahoo_finance": ("yfinance", self._get_quote_from_yfinance),
            "finnhub": ("finnhub", self._get_quote_from_finnhub),
        }

    async def get_quote(self, code: str, force_refresh: bool = False) -> Dict:
        """获取美股实时行情（使用基类模板方法）"""
        return await self.get_quote_template(code, force_refresh)

    def _get_quote_from_yfinance(self, code: str) -> Dict:
        """从yfinance获取美股行情"""
        ticker = yf.Ticker(code)
        hist = ticker.history(period="1d")

        if hist.empty:
            raise Exception("无数据")

        latest = hist.iloc[-1]
        info = ticker.info

        return {
            "name": info.get("longName") or info.get("shortName"),
            "price": float(latest["Close"]),
            "open": float(latest["Open"]),
            "high": float(latest["High"]),
            "low": float(latest["Low"]),
            "volume": int(latest["Volume"]),
            "change_percent": round(
                ((latest["Close"] - latest["Open"]) / latest["Open"] * 100), 2
            ),
            "trade_date": hist.index[-1].strftime("%Y-%m-%d"),
            "currency": info.get("currency", "USD"),
        }

    def _get_quote_from_alpha_vantage(self, code: str) -> Dict:
        """从Alpha Vantage获取美股行情"""
        try:
            from tradingagents.dataflows.providers.us.alpha_vantage_common import (
                get_api_key,
                _make_api_request,
            )

            api_key = get_api_key()
            if not api_key:
                raise Exception("Alpha Vantage API Key 未配置")

            params = {"symbol": code.upper()}
            data = _make_api_request("GLOBAL_QUOTE", params)

            if not data or "Global Quote" not in data:
                raise Exception("Alpha Vantage 返回数据为空")

            quote = data["Global Quote"]
            if not quote:
                raise Exception("无数据")

            return {
                "symbol": quote.get("01. symbol", code),
                "price": float(quote.get("05. price", 0)),
                "open": float(quote.get("02. open", 0)),
                "high": float(quote.get("03. high", 0)),
                "low": float(quote.get("04. low", 0)),
                "volume": int(quote.get("06. volume", 0)),
                "latest_trading_day": quote.get("07. latest trading day", ""),
                "previous_close": float(quote.get("08. previous close", 0)),
                "change": float(quote.get("09. change", 0)),
                "change_percent": quote.get("10. change percent", "0%").rstrip("%"),
            }

        except Exception as e:
            logger.error(f"❌ Alpha Vantage获取美股行情失败: {e}")
            raise

    def _get_quote_from_finnhub(self, code: str) -> Dict:
        """从Finnhub获取美股行情"""
        try:
            import finnhub
            import os

            api_key = os.getenv("FINNHUB_API_KEY")
            if not api_key:
                raise Exception("Finnhub API Key 未配置")

            client = finnhub.Client(api_key=api_key)
            quote = client.quote(code.upper())

            if not quote or "c" not in quote:
                raise Exception("无数据")

            return {
                "symbol": code.upper(),
                "price": quote.get("c", 0),
                "open": quote.get("o", 0),
                "high": quote.get("h", 0),
                "low": quote.get("l", 0),
                "previous_close": quote.get("pc", 0),
                "change": quote.get("d", 0),
                "change_percent": quote.get("dp", 0),
                "timestamp": quote.get("t", 0),
            }

        except Exception as e:
            logger.error(f"❌ Finnhub获取美股行情失败: {e}")
            raise
