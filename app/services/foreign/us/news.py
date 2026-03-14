# -*- coding: utf-8 -*-
"""美股新闻模块

提供美股新闻获取功能，支持多数据源。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List

logger = logging.getLogger(__name__)


class NewsMixin:
    """新闻 Mixin"""

    @property
    def news_source_handlers(self) -> Dict:
        """新闻数据源处理器映射"""
        return {
            "alpha_vantage": ("alpha_vantage", self._get_news_from_alpha_vantage),
            "yahoo_finance": ("yfinance", self._get_news_from_yfinance),
            "finnhub": ("finnhub", self._get_news_from_finnhub),
        }

    async def get_news(self, code: str, days: int = 2, limit: int = 50) -> Dict:
        """获取美股新闻（使用基类模板方法）"""
        return await self.get_news_template(code, days, limit)

    def _get_news_from_yfinance(self, code: str, days: int, limit: int) -> List[Dict]:
        """从yfinance获取美股新闻"""
        import yfinance as yf

        ticker = yf.Ticker(code)
        news = ticker.news

        if not news:
            raise Exception("无数据")

        news_list = []
        for article in news[:limit]:
            pub_time = datetime.fromtimestamp(article.get("providerPublishTime", 0))
            pub_time_str = pub_time.strftime("%Y-%m-%d %H:%M:%S")

            news_list.append({
                "title": article.get("title", ""),
                "summary": article.get("summary", ""),
                "url": article.get("link", ""),
                "source": article.get("publisher", ""),
                "publish_time": pub_time_str,
                "sentiment": None,
                "sentiment_score": None,
            })

        return news_list

    def _get_news_from_alpha_vantage(
        self, code: str, days: int, limit: int
    ) -> List[Dict]:
        """从Alpha Vantage获取美股新闻"""
        from tradingagents.dataflows.providers.us.alpha_vantage_common import (
            get_api_key,
            _make_api_request,
        )

        api_key = get_api_key()
        if not api_key:
            raise Exception("Alpha Vantage API Key 未配置")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

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

        news_list = []
        for article in data.get("feed", [])[:limit]:
            time_published = article.get("time_published", "")
            try:
                pub_time = datetime.strptime(time_published, "%Y%m%dT%H%M%S")
                pub_time_str = pub_time.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pub_time_str = time_published

            sentiment_score = None
            sentiment_label = article.get("overall_sentiment_label", "Neutral")

            ticker_sentiment = article.get("ticker_sentiment", [])
            for ts in ticker_sentiment:
                if ts.get("ticker", "").upper() == code.upper():
                    sentiment_score = ts.get("ticker_sentiment_score")
                    sentiment_label = ts.get("ticker_sentiment_label", sentiment_label)
                    break

            news_list.append({
                "title": article.get("title", ""),
                "summary": article.get("summary", ""),
                "url": article.get("url", ""),
                "source": article.get("source", ""),
                "publish_time": pub_time_str,
                "sentiment": sentiment_label,
                "sentiment_score": sentiment_score,
            })

        return news_list

    def _get_news_from_finnhub(self, code: str, days: int, limit: int) -> List[Dict]:
        """从Finnhub获取美股新闻"""
        import finnhub
        import os

        api_key = os.getenv("FINNHUB_API_KEY")
        if not api_key:
            raise Exception("Finnhub API Key 未配置")

        client = finnhub.Client(api_key=api_key)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        news = client.company_news(
            code.upper(),
            _from=start_date.strftime("%Y-%m-%d"),
            to=end_date.strftime("%Y-%m-%d"),
        )

        if not news:
            raise Exception("无数据")

        news_list = []
        for article in news[:limit]:
            timestamp = article.get("datetime", 0)
            pub_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

            news_list.append({
                "title": article.get("headline", ""),
                "summary": article.get("summary", ""),
                "url": article.get("url", ""),
                "source": article.get("source", ""),
                "publish_time": pub_time,
                "sentiment": None,
                "sentiment_score": None,
            })

        return news_list
