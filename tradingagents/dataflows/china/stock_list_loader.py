# -*- coding: utf-8 -*-
"""
股票列表加载器
提供A股股票列表加载和查询功能
"""

from typing import List, Dict, Any, Optional
from .base_data_loader import BaseDataLoader, logger


class StockListLoader(BaseDataLoader):
    """
    股票列表加载器

    负责加载和管理A股股票列表信息
    """

    def __init__(self):
        super().__init__()
        self._stock_list_cache: Optional[List[Dict[str, Any]]] = None
        self._stock_dict_cache: Optional[Dict[str, Dict[str, Any]]] = None

    def load(self, symbol: str = "", **kwargs) -> List[Dict[str, Any]]:
        """
        加载股票列表

        Args:
            symbol: 可选，特定股票代码
            **kwargs: 其他参数
                - refresh: 是否强制刷新缓存
                - market: 市场筛选 (sh/sz/all)

        Returns:
            股票列表
        """
        refresh = kwargs.get("refresh", False)
        market = kwargs.get("market", "all")

        if self._stock_list_cache is None or refresh:
            self._load_stock_list(market)

        if symbol:
            # 返回特定股票信息
            stock_info = self.get_stock_info(symbol)
            return [stock_info] if stock_info else []

        return self._stock_list_cache or []

    def _load_stock_list(self, market: str = "all"):
        """
        从数据源加载股票列表

        Args:
            market: 市场筛选
        """
        try:
            # 尝试从Tushare获取
            from ..providers.china.tushare import get_tushare_provider

            provider = get_tushare_provider()
            if provider and provider.is_available():
                self._stock_list_cache = provider.get_stock_list(market)
                self._build_stock_dict()
                logger.info(f"✅ 从Tushare加载股票列表: {len(self._stock_list_cache)}只")
                return
        except Exception as e:
            logger.warning(f"⚠️ 从Tushare加载股票列表失败: {e}")

        try:
            # 降级到AKShare
            from ..providers.china.akshare import get_akshare_provider

            provider = get_akshare_provider()
            if provider and provider.connected:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    self._stock_list_cache = loop.run_until_complete(
                        provider.get_stock_list()
                    )
                finally:
                    loop.close()
                self._build_stock_dict()
                logger.info(f"✅ 从AKShare加载股票列表: {len(self._stock_list_cache)}只")
                return
        except Exception as e:
            logger.warning(f"⚠️ 从AKShare加载股票列表失败: {e}")

        # 使用空列表
        self._stock_list_cache = []
        self._stock_dict_cache = {}

    def _build_stock_dict(self):
        """构建股票代码到信息的映射字典"""
        self._stock_dict_cache = {}
        if self._stock_list_cache:
            for stock in self._stock_list_cache:
                code = stock.get("code") or stock.get("symbol", "")
                if code:
                    self._stock_dict_cache[code] = stock

    def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取特定股票信息

        Args:
            symbol: 股票代码

        Returns:
            股票信息字典或None
        """
        from ..parsers.symbol_parser import normalize_symbol

        code = normalize_symbol(symbol)

        if self._stock_dict_cache is None:
            self._load_stock_list()

        return self._stock_dict_cache.get(code)

    def search_stocks(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        搜索股票

        Args:
            keyword: 搜索关键词（代码或名称）
            limit: 返回结果数量限制

        Returns:
            匹配的股票列表
        """
        if self._stock_list_cache is None:
            self._load_stock_list()

        keyword = keyword.lower()
        results = []

        for stock in self._stock_list_cache or []:
            code = stock.get("code", "").lower()
            name = stock.get("name", "").lower()

            if keyword in code or keyword in name:
                results.append(stock)
                if len(results) >= limit:
                    break

        return results

    def get_stocks_by_industry(self, industry: str) -> List[Dict[str, Any]]:
        """
        按行业获取股票列表

        Args:
            industry: 行业名称

        Returns:
            该行业的股票列表
        """
        if self._stock_list_cache is None:
            self._load_stock_list()

        return [
            stock
            for stock in self._stock_list_cache or []
            if industry in (stock.get("industry") or "")
        ]

    def get_stocks_by_market(self, market: str) -> List[Dict[str, Any]]:
        """
        按市场获取股票列表

        Args:
            market: 市场类型 (主板/创业板/科创板)

        Returns:
            该市场的股票列表
        """
        if self._stock_list_cache is None:
            self._load_stock_list()

        return [
            stock
            for stock in self._stock_list_cache or []
            if market in (stock.get("market") or "")
        ]


# 全局实例
_stock_list_loader: Optional[StockListLoader] = None


def get_stock_list_loader() -> StockListLoader:
    """获取全局股票列表加载器实例"""
    global _stock_list_loader
    if _stock_list_loader is None:
        _stock_list_loader = StockListLoader()
    return _stock_list_loader
