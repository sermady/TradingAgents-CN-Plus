# -*- coding: utf-8 -*-
"""美股基础信息模块

提供美股基础信息获取功能，支持多数据源。
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict

import yfinance as yf

logger = logging.getLogger(__name__)


class InfoMixin:
    """基础信息 Mixin"""

    @property
    def basic_info_cache_key(self) -> str:
        """基础信息缓存key后缀"""
        return "us_basic_info"

    @property
    def basic_info_source_handlers(self) -> Dict:
        """基础信息数据源处理器映射"""
        return {
            "alpha_vantage": ("alpha_vantage", self._get_info_from_alpha_vantage),
            "yahoo_finance": ("yfinance", self._get_info_from_yfinance),
            "finnhub": ("finnhub", self._get_info_from_finnhub),
        }

    async def get_basic_info(self, code: str, force_refresh: bool = False) -> Dict:
        """获取美股基础信息

        Args:
            code: 股票代码
            force_refresh: 是否强制刷新

        Returns:
            基础信息数据
        """
        # 1. 检查缓存
        if not force_refresh:
            cache_key = self.cache.find_cached_stock_data(
                symbol=code, data_source="us_basic_info"
            )
            if cache_key:
                cached_data = self.cache.load_stock_data(cache_key)
                if cached_data:
                    logger.info(f"⚡ 从缓存获取美股基础信息: {code}")
                    return self._parse_cached_data(cached_data, "US", code)

        # 2. 从数据库获取数据源优先级
        source_priority = await self._get_source_priority("US")

        # 3. 按优先级尝试各个数据源
        info_data = None
        data_source = None
        source_handlers = self.basic_info_source_handlers

        valid_priority = self._get_valid_sources(source_priority, source_handlers, "US")
        if not valid_priority:
            logger.warning("⚠️ 数据库中没有配置有效的美股数据源，使用默认顺序")
            valid_priority = ["yahoo_finance", "alpha_vantage", "finnhub"]

        logger.info(f"📊 [US基础信息有效数据源] {valid_priority}")

        for source_name in valid_priority:
            source_key = source_name.lower()
            handler_name, handler_func = source_handlers[source_key]
            try:
                info_data = await asyncio.to_thread(handler_func, code)
                data_source = handler_name
                if info_data:
                    logger.info(f"✅ {data_source}获取美股基础信息成功: {code}")
                    break
            except Exception as e:
                logger.warning(f"⚠️ {source_name}获取基础信息失败: {e}")
                continue

        if not info_data:
            raise Exception(f"无法获取美股{code}的基础信息：所有数据源均失败")

        # 4. 格式化数据
        market_cap = info_data.get("market_cap")
        formatted_data = {
            "code": code,
            "name": info_data.get("name") or f"美股{code}",
            "market": "US",
            "industry": info_data.get("industry"),
            "sector": info_data.get("sector"),
            "total_mv": market_cap / 1e8 if market_cap else None,
            "pe_ttm": info_data.get("pe_ratio"),
            "pe": info_data.get("pe_ratio"),
            "pb": info_data.get("pb_ratio"),
            "ps": None,
            "ps_ttm": None,
            "roe": None,
            "debt_ratio": None,
            "dividend_yield": info_data.get("dividend_yield"),
            "currency": info_data.get("currency", "USD"),
            "source": data_source,
            "updated_at": datetime.now().isoformat(),
        }

        # 5. 保存到缓存
        self.cache.save_stock_data(
            symbol=code,
            data=json.dumps(formatted_data, ensure_ascii=False),
            data_source="us_basic_info",
        )
        logger.info(f"💾 美股基础信息已缓存: {code}")

        return formatted_data

    def _get_info_from_yfinance(self, code: str) -> Dict:
        """从yfinance获取美股基础信息"""
        ticker = yf.Ticker(code)
        info = ticker.info

        if not info:
            raise Exception("无数据")

        return {
            "name": info.get("longName") or info.get("shortName"),
            "industry": info.get("industry"),
            "sector": info.get("sector"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "pb_ratio": info.get("priceToBook"),
            "dividend_yield": info.get("dividendYield"),
            "currency": info.get("currency", "USD"),
        }

    def _get_info_from_alpha_vantage(self, code: str) -> Dict:
        """从Alpha Vantage获取美股基础信息"""
        from tradingagents.dataflows.providers.us.alpha_vantage_common import (
            get_api_key,
            _make_api_request,
        )

        api_key = get_api_key()
        if not api_key:
            raise Exception("Alpha Vantage API Key 未配置")

        params = {"symbol": code.upper()}
        data = _make_api_request("OVERVIEW", params)

        if not data or not data.get("Symbol"):
            raise Exception("无数据")

        return {
            "name": data.get("Name"),
            "industry": data.get("Industry"),
            "sector": data.get("Sector"),
            "market_cap": self._safe_float(data.get("MarketCapitalization")),
            "pe_ratio": self._safe_float(data.get("TrailingPE")),
            "pb_ratio": self._safe_float(data.get("PriceToBookRatio")),
            "dividend_yield": self._safe_float(data.get("DividendYield")),
            "currency": "USD",
        }

    def _get_info_from_finnhub(self, code: str) -> Dict:
        """从Finnhub获取美股基础信息"""
        import finnhub
        import os

        api_key = os.getenv("FINNHUB_API_KEY")
        if not api_key:
            raise Exception("Finnhub API Key 未配置")

        client = finnhub.Client(api_key=api_key)
        profile = client.company_profile2(symbol=code.upper())

        if not profile:
            raise Exception("无数据")

        return {
            "name": profile.get("name"),
            "industry": profile.get("finnhubIndustry"),
            "sector": None,
            "market_cap": profile.get("marketCapitalization") * 1000000
            if profile.get("marketCapitalization")
            else None,
            "pe_ratio": None,
            "pb_ratio": None,
            "dividend_yield": None,
            "currency": profile.get("currency", "USD"),
        }

    def _safe_float(self, value, default=None):
        """安全转换为float"""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def _parse_cached_data(self, cached_data, market, code):
        """解析缓存数据（占位，实际应在基类中定义）"""
        if isinstance(cached_data, str):
            return json.loads(cached_data)
        return cached_data
