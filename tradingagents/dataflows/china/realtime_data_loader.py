# -*- coding: utf-8 -*-
"""
实时数据加载器
提供A股实时行情数据加载功能
"""

import asyncio
from typing import Optional, Dict, Any, List

from .base_data_loader import BaseDataLoader, logger


class RealtimeDataLoader(BaseDataLoader):
    """
    实时数据加载器

    负责加载A股实时行情数据，支持多数据源
    """

    def __init__(self):
        super().__init__()

    def load(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """
        加载实时数据

        Args:
            symbol: 股票代码
            **kwargs: 其他参数
                - fields: 需要的字段列表

        Returns:
            实时数据字典
        """
        fields = kwargs.get("fields", ["price", "change", "volume"])

        # 尝试从market_quotes获取
        data = self._try_market_quotes(symbol, fields)
        if data:
            return data

        # 尝试从Tushare获取
        data = self._try_tushare(symbol, fields)
        if data:
            return data

        # 尝试从AKShare获取
        data = self._try_akshare(symbol, fields)
        if data:
            return data

        logger.warning(f"⚠️ 无法获取{symbol}的实时数据")
        return self._generate_empty_data(symbol, fields)

    def _try_market_quotes(self, symbol: str, fields: List[str]) -> Optional[Dict[str, Any]]:
        """尝试从market_quotes获取实时数据"""
        try:
            from tradingagents.config.runtime_settings import use_app_cache_enabled
            from ..cache.app_adapter import get_market_quote_dataframe

            if not use_app_cache_enabled(False):
                return None

            df = get_market_quote_dataframe(symbol)
            if df is None or df.empty:
                return None

            row = df.iloc[-1]
            data = {"symbol": symbol, "source": "market_quotes"}

            if "price" in fields:
                data["price"] = row.get("close")
            if "change" in fields:
                data["change"] = row.get("change")
            if "change_pct" in fields:
                data["change_pct"] = row.get("pct_chg")
            if "volume" in fields:
                data["volume"] = row.get("volume")
                data["volume_unit"] = row.get("volume_unit", "lots")
            if "open" in fields:
                data["open"] = row.get("open")
            if "high" in fields:
                data["high"] = row.get("high")
            if "low" in fields:
                data["low"] = row.get("low")

            logger.debug(f"✅ 从market_quotes获取实时数据: {symbol}")
            return data

        except Exception as e:
            logger.debug(f"从market_quotes获取数据失败: {e}")
            return None

    def _try_tushare(self, symbol: str, fields: List[str]) -> Optional[Dict[str, Any]]:
        """尝试从Tushare获取实时数据"""
        try:
            from ..providers.china.tushare import get_tushare_provider

            provider = get_tushare_provider()
            if not provider or not provider.connected:
                return None

            # 使用异步方法获取
            async def fetch():
                return await provider.get_realtime_price_from_batch(symbol)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                price = loop.run_until_complete(fetch())
            finally:
                loop.close()

            if price:
                return {
                    "symbol": symbol,
                    "price": price,
                    "source": "tushare",
                }

        except Exception as e:
            logger.debug(f"从Tushare获取实时数据失败: {e}")

        return None

    def _try_akshare(self, symbol: str, fields: List[str]) -> Optional[Dict[str, Any]]:
        """尝试从AKShare获取实时数据"""
        try:
            from ..providers.china.akshare import get_akshare_provider

            provider = get_akshare_provider()
            if not provider or not provider.connected:
                return None

            # 使用异步方法获取
            async def fetch():
                return await provider.get_stock_quotes_cached(symbol)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                quotes = loop.run_until_complete(fetch())
            finally:
                loop.close()

            if quotes:
                data = {"symbol": symbol, "source": "akshare"}
                if "price" in fields:
                    data["price"] = quotes.get("price")
                if "change" in fields:
                    data["change"] = quotes.get("change")
                if "volume" in fields:
                    data["volume"] = quotes.get("volume")
                return data

        except Exception as e:
            logger.debug(f"从AKShare获取实时数据失败: {e}")

        return None

    def _generate_empty_data(self, symbol: str, fields: List[str]) -> Dict[str, Any]:
        """生成空数据"""
        data = {"symbol": symbol, "source": "none"}
        for field in fields:
            data[field] = None
        return data

    def get_realtime_price(self, symbol: str) -> Optional[float]:
        """
        获取实时价格

        Args:
            symbol: 股票代码

        Returns:
            实时价格或None
        """
        data = self.load(symbol, fields=["price"])
        return data.get("price")

    def get_realtime_quote(self, symbol: str) -> Dict[str, Any]:
        """
        获取完整实时报价

        Args:
            symbol: 股票代码

        Returns:
            实时报价字典
        """
        return self.load(
            symbol,
            fields=["price", "open", "high", "low", "change", "change_pct", "volume"]
        )


# 全局实例
_realtime_data_loader: Optional[RealtimeDataLoader] = None


def get_realtime_data_loader() -> RealtimeDataLoader:
    """获取全局实时数据加载器实例"""
    global _realtime_data_loader
    if _realtime_data_loader is None:
        _realtime_data_loader = RealtimeDataLoader()
    return _realtime_data_loader
