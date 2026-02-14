# -*- coding: utf-8 -*-
"""
美股数据服务
"""

from typing import Dict, List
from datetime import datetime, timedelta
import logging
import json
import asyncio
from collections import defaultdict

from tradingagents.dataflows.cache import get_cache
from .base import ForeignStockBaseService
from tradingagents.dataflows.providers.us.yfinance import YFinanceUtils

logger = logging.getLogger(__name__)


class USStockService(ForeignStockBaseService):
    """美股数据服务"""

    def __init__(self, db=None):
        """初始化美股服务

        Args:
            db: MongoDB 数据库连接
        """
        super().__init__(db)

        # 初始化美股数据提供器
        self.yfinance_provider = YFinanceUtils()

        # 请求去重：为每个 (code, data_type) 创建独立的锁
        self._request_locks = defaultdict(asyncio.Lock)

        logger.info("✅ USStockService 初始化完成（已启用请求去重）")

    @property
    def market(self) -> str:
        """市场标识"""
        return "US"

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

    @property
    def kline_source_handlers(self) -> Dict:
        """K线数据源处理器映射"""
        return {
            "alpha_vantage": ("alpha_vantage", self._get_kline_from_alpha_vantage),
            "yahoo_finance": ("yfinance", self._get_kline_from_yfinance),
            "finnhub": ("finnhub", self._get_kline_from_finnhub),
        }

    @property
    def news_source_handlers(self) -> Dict:
        """新闻数据源处理器映射"""
        return {
            "alpha_vantage": ("alpha_vantage", self._get_news_from_alpha_vantage),
            "yahoo_finance": ("yfinance", self._get_news_from_yfinance),
            "finnhub": ("finnhub", self._get_news_from_finnhub),
        }

    async def get_quote(self, code: str, force_refresh: bool = False) -> Dict:
        """获取美股实时行情（使用基类模板方法）"""
        return await self.get_quote_template(code, force_refresh)

    def _get_quote_from_yfinance(self, code: str) -> Dict:
        """从yfinance获取美股行情"""
        import yfinance as yf

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

            # 获取 API Key
            api_key = get_api_key()
            if not api_key:
                raise Exception("Alpha Vantage API Key 未配置")

            # 调用 GLOBAL_QUOTE API
            params = {
                "symbol": code.upper(),
            }

            data = _make_api_request("GLOBAL_QUOTE", params)

            if not data or "Global Quote" not in data:
                raise Exception("Alpha Vantage 返回数据为空")

            quote = data["Global Quote"]

            if not quote:
                raise Exception("无数据")

            # 解析数据
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

            # 获取 API Key
            api_key = os.getenv("FINNHUB_API_KEY")
            if not api_key:
                raise Exception("Finnhub API Key 未配置")

            # 创建客户端
            client = finnhub.Client(api_key=api_key)

            # 获取实时报价
            quote = client.quote(code.upper())

            if not quote or "c" not in quote:
                raise Exception("无数据")

            # 解析数据
            return {
                "symbol": code.upper(),
                "price": quote.get("c", 0),  # current price
                "open": quote.get("o", 0),  # open price
                "high": quote.get("h", 0),  # high price
                "low": quote.get("l", 0),  # low price
                "previous_close": quote.get("pc", 0),  # previous close
                "change": quote.get("d", 0),  # change
                "change_percent": quote.get("dp", 0),  # change percent
                "timestamp": quote.get("t", 0),  # timestamp
            }

        except Exception as e:
            logger.error(f"❌ Finnhub获取美股行情失败: {e}")
            raise

    async def get_basic_info(self, code: str, force_refresh: bool = False) -> Dict:
        """获取美股基础信息

        Args:
            code: 股票代码
            force_refresh: 是否强制刷新

        Returns:
            基础信息数据
        """
        # 1. 检查缓存（除非强制刷新）
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

        # 数据源名称映射
        source_handlers = {
            "alpha_vantage": ("alpha_vantage", self._get_info_from_alpha_vantage),
            "yahoo_finance": ("yfinance", self._get_info_from_yfinance),
            "finnhub": ("finnhub", self._get_info_from_finnhub),
        }

        valid_priority = self._get_valid_sources(source_priority, source_handlers, "US")

        if not valid_priority:
            logger.warning("⚠️ 数据库中没有配置有效的美股数据源，使用默认顺序")
            valid_priority = ["yahoo_finance", "alpha_vantage", "finnhub"]

        logger.info(f"📊 [US基础信息有效数据源] {valid_priority}")

        for source_name in valid_priority:
            source_key = source_name.lower()
            handler_name, handler_func = source_handlers[source_key]
            try:
                # 🔥 使用 asyncio.to_thread 避免阻塞事件循环
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

        # 4. 格式化数据（匹配前端期望的字段名）
        market_cap = info_data.get("market_cap")
        formatted_data = {
            "code": code,
            "name": info_data.get("name") or f"美股{code}",
            "market": "US",
            "industry": info_data.get("industry"),
            "sector": info_data.get("sector"),
            # 前端期望 total_mv（单位：亿元）
            "total_mv": market_cap / 1e8 if market_cap else None,
            # 前端期望 pe_ttm 或 pe
            "pe_ttm": info_data.get("pe_ratio"),
            "pe": info_data.get("pe_ratio"),
            # 前端期望 pb
            "pb": info_data.get("pb_ratio"),
            # 前端期望 ps（暂无数据）
            "ps": None,
            "ps_ttm": None,
            # 前端期望 roe 和 debt_ratio（暂无数据）
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
        import yfinance as yf

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

        # 获取 API Key
        api_key = get_api_key()
        if not api_key:
            raise Exception("Alpha Vantage API Key 未配置")

        # 调用 OVERVIEW API
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

        # 获取 API Key
        api_key = os.getenv("FINNHUB_API_KEY")
        if not api_key:
            raise Exception("Finnhub API Key 未配置")

        # 创建客户端
        client = finnhub.Client(api_key=api_key)

        # 获取公司信息
        profile = client.company_profile2(symbol=code.upper())

        if not profile:
            raise Exception("无数据")

        return {
            "name": profile.get("name"),
            "industry": profile.get("finnhubIndustry"),
            "sector": None,  # Finnhub 不提供 sector
            "market_cap": profile.get("marketCapitalization") * 1000000
            if profile.get("marketCapitalization")
            else None,  # 转换为美元
            "pe_ratio": None,  # Finnhub profile 不直接提供 PE
            "pb_ratio": None,  # Finnhub profile 不直接提供 PB
            "dividend_yield": None,  # Finnhub profile 不直接提供股息率
            "currency": profile.get("currency", "USD"),
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
        import yfinance as yf

        ticker = yf.Ticker(code)

        # 周期映射
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

        # 格式化数据
        kline_data = []
        for date, row in hist.iterrows():
            date_str = date.strftime("%Y-%m-%d")
            kline_data.append(
                {
                    "date": date_str,
                    "trade_date": date_str,  # 前端需要这个字段
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                }
            )

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

        # 获取 API Key
        api_key = get_api_key()
        if not api_key:
            raise Exception("Alpha Vantage API Key 未配置")

        # 根据周期选择API函数
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

        # 转换为 DataFrame
        df = pd.DataFrame.from_dict(time_series, orient="index")
        df.index = pd.to_datetime(df.index)
        df = df.sort_index(ascending=False)  # 最新的在前

        # 限制数量
        df = df.head(limit)

        # 格式化数据
        kline_data = []
        for date, row in df.iterrows():
            date_str = date.strftime("%Y-%m-%d")
            kline_data.append(
                {
                    "date": date_str,
                    "trade_date": date_str,  # 前端需要这个字段
                    "open": float(row["1. open"]),
                    "high": float(row["2. high"]),
                    "low": float(row["3. low"]),
                    "close": float(row["4. close"]),
                    "volume": int(row["5. volume"]),
                }
            )

        return kline_data

    def _get_kline_from_finnhub(self, code: str, period: str, limit: int) -> List[Dict]:
        """从Finnhub获取美股K线数据"""
        import finnhub
        import os

        # 获取 API Key
        api_key = os.getenv("FINNHUB_API_KEY")
        if not api_key:
            raise Exception("Finnhub API Key 未配置")

        # 创建客户端
        client = finnhub.Client(api_key=api_key)

        # 计算日期范围
        end_date = datetime.now()

        # 根据周期计算开始日期
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

        # 获取K线数据
        candles = client.stock_candles(
            code.upper(),
            resolution,
            int(start_date.timestamp()),
            int(end_date.timestamp()),
        )

        if not candles or candles.get("s") != "ok":
            raise Exception("无数据")

        # 格式化数据
        kline_data = []
        for i in range(len(candles["t"])):
            date_str = datetime.fromtimestamp(candles["t"][i]).strftime("%Y-%m-%d")
            kline_data.append(
                {
                    "date": date_str,
                    "trade_date": date_str,  # 前端需要这个字段
                    "open": float(candles["o"][i]),
                    "high": float(candles["h"][i]),
                    "low": float(candles["l"][i]),
                    "close": float(candles["c"][i]),
                    "volume": int(candles["v"][i]),
                }
            )

        return kline_data

    async def get_news(self, code: str, days: int = 2, limit: int = 50) -> Dict:
        """获取美股新闻（使用基类模板方法）"""
        return await self.get_news_template(code, days, limit)

        # 4. 构建返回数据
        result = {
            "code": code,
            "days": days,
            "limit": limit,
            "source": data_source,
            "items": news_data,
        }

        # 5. 缓存数据
        self.cache.save_stock_data(
            symbol=code,
            data=json.dumps(result, ensure_ascii=False),
            data_source=cache_key_str,
        )

        return result

    def _get_news_from_alpha_vantage(
        self, code: str, days: int, limit: int
    ) -> List[Dict]:
        """从Alpha Vantage获取美股新闻"""
        from tradingagents.dataflows.providers.us.alpha_vantage_common import (
            get_api_key,
            _make_api_request,
        )

        # 获取 API Key
        api_key = get_api_key()
        if not api_key:
            raise Exception("Alpha Vantage API Key 未配置")

        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 调用 NEWS_SENTIMENT API
        params = {
            "tickers": code.upper(),
            "time_from": start_date.strftime("%Y%m%dT%H%M"),
            "time_to": end_date.strftime("%Y%m%dT%H%M"),
            "sort": "LATEST",
            "limit": str(limit),
        }

        data = _make_api_request("NEWS_SENTIMENT", params)

        if not data or "feed" not in data:
            raise Exception("无数据")

        # 格式化新闻数据
        news_list = []
        for article in data.get("feed", [])[:limit]:
            # 解析时间
            time_published = article.get("time_published", "")
            try:
                # Alpha Vantage 时间格式: 20240101T120000
                pub_time = datetime.strptime(time_published, "%Y%m%dT%H%M%S")
                pub_time_str = pub_time.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pub_time_str = time_published

            # 提取相关股票的情感分数
            sentiment_score = None
            sentiment_label = article.get("overall_sentiment_label", "Neutral")

            ticker_sentiment = article.get("ticker_sentiment", [])
            for ts in ticker_sentiment:
                if ts.get("ticker", "").upper() == code.upper():
                    sentiment_score = ts.get("ticker_sentiment_score")
                    sentiment_label = ts.get("ticker_sentiment_label", sentiment_label)
                    break

            news_list.append(
                {
                    "title": article.get("title", ""),
                    "summary": article.get("summary", ""),
                    "url": article.get("url", ""),
                    "source": article.get("source", ""),
                    "publish_time": pub_time_str,
                    "sentiment": sentiment_label,
                    "sentiment_score": sentiment_score,
                }
            )

        return news_list

    def _get_news_from_finnhub(self, code: str, days: int, limit: int) -> List[Dict]:
        """从Finnhub获取美股新闻"""
        import finnhub
        import os

        # 获取 API Key
        api_key = os.getenv("FINNHUB_API_KEY")
        if not api_key:
            raise Exception("Finnhub API Key 未配置")

        # 创建客户端
        client = finnhub.Client(api_key=api_key)

        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 获取公司新闻
        news = client.company_news(
            code.upper(),
            _from=start_date.strftime("%Y-%m-%d"),
            to=end_date.strftime("%Y-%m-%d"),
        )

        if not news:
            raise Exception("无数据")

        # 格式化新闻数据
        news_list = []
        for article in news[:limit]:
            # 解析时间戳
            timestamp = article.get("datetime", 0)
            pub_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

            news_list.append(
                {
                    "title": article.get("headline", ""),
                    "summary": article.get("summary", ""),
                    "url": article.get("url", ""),
                    "source": article.get("source", ""),
                    "publish_time": pub_time,
                    "sentiment": None,  # Finnhub 不提供情感分析
                    "sentiment_score": None,
                }
            )

        return news_list
