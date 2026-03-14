# -*- coding: utf-8 -*-
"""美股数据服务模块

提供美股数据获取功能，支持多数据源（yfinance, Alpha Vantage, Finnhub）。

导出:
    - USStockService: 美股数据服务主类

示例:
    from app.services.foreign.us import USStockService

    service = USStockService()
    quote = await service.get_quote("AAPL")
    info = await service.get_basic_info("AAPL")
    kline = await service.get_kline("AAPL", period="day", limit=30)
    news = await service.get_news("AAPL", days=7, limit=10)
"""

from .service import USStockService

__all__ = ["USStockService"]
