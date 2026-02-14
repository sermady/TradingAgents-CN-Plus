# -*- coding: utf-8 -*-
"""
港股数据服务
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import json
import asyncio
from collections import defaultdict

from tradingagents.dataflows.cache import get_cache
from tradingagents.dataflows.providers.hk.hk_stock import HKStockProvider
from .base import ForeignStockBaseService
from app.utils.error_handler import handle_errors_none

logger = logging.getLogger(__name__)


class HKStockService(ForeignStockBaseService):
    """港股数据服务"""

    def __init__(self, db=None):
        """初始化港股服务

        Args:
            db: MongoDB 数据库连接
        """
        super().__init__(db)

        # 初始化港股数据源提供者
        self.hk_provider = HKStockProvider()

        # 请求去重：为每个 (code, data_type) 创建独立的锁
        self._request_locks = defaultdict(asyncio.Lock)

        logger.info("✅ HKStockService 初始化完成（已启用请求去重）")

    @property
    def market(self) -> str:
        """市场标识"""
        return "HK"

    @property
    def quote_cache_key(self) -> str:
        """行情缓存key后缀"""
        return "hk_realtime_quote"

    @property
    def quote_source_handlers(self) -> Dict:
        """行情数据源处理器映射"""
        return {
            "yahoo_finance": ("yfinance", self._get_quote_from_yfinance),
            "akshare": ("akshare", self._get_quote_from_akshare),
        }

    @property
    def basic_info_cache_key(self) -> str:
        """基础信息缓存key后缀"""
        return "hk_basic_info"

    @property
    def basic_info_source_handlers(self) -> Dict:
        """基础信息数据源处理器映射"""
        return {
            "akshare": ("akshare", self._get_info_from_akshare),
            "yahoo_finance": ("yfinance", self._get_info_from_yfinance),
            "finnhub": ("finnhub", self._get_info_from_finnhub),
        }

    @property
    def kline_source_handlers(self) -> Dict:
        """K线数据源处理器映射"""
        return {
            "akshare": ("akshare", self._get_kline_from_akshare),
            "yahoo_finance": ("yfinance", self._get_kline_from_yfinance),
            "finnhub": ("finnhub", self._get_kline_from_finnhub),
        }

    @property
    def news_source_handlers(self) -> Dict:
        """新闻数据源处理器映射"""
        return {
            "akshare": ("akshare", self._get_news_from_akshare),
            "finnhub": ("finnhub", self._get_news_from_finnhub),
        }

    async def get_basic_info(self, code: str, force_refresh: bool = False) -> Dict:
        """获取港股基础信息（使用基类模板方法）"""
        return await self.get_basic_info_template(code, force_refresh)

    async def get_quote(self, code: str, force_refresh: bool = False) -> Dict:
        """获取港股实时行情（使用基类模板方法）"""
        return await self.get_quote_template(code, force_refresh)

    def _get_quote_from_yfinance(self, code: str) -> Dict:
        """从yfinance获取港股行情"""
        quote_data = self.hk_provider.get_real_time_price(code)
        if not quote_data:
            raise Exception("无数据")
        return quote_data

    def _get_quote_from_akshare(self, code: str) -> Dict:
        """从AKShare获取港股行情"""
        from tradingagents.dataflows.providers.hk.improved_hk import (
            get_hk_stock_info_akshare,
        )

        info = get_hk_stock_info_akshare(code)
        if not info or "error" in info:
            raise Exception("无数据")

        # 检查是否有价格数据
        if not info.get("price"):
            raise Exception("无价格数据")

        return info

    def _format_quote(self, data: Dict, code: str, source: str) -> Dict:
        """格式化港股行情数据"""
        return {
            "code": code,
            "name": data.get("name", f"港股{code}"),
            "market": "HK",
            "price": data.get("price") or data.get("close"),
            "open": data.get("open"),
            "high": data.get("high"),
            "low": data.get("low"),
            "volume": data.get("volume"),
            "currency": data.get("currency", "HKD"),
            "source": source,
            "trade_date": data.get("timestamp", datetime.now().strftime("%Y-%m-%d")),
            "updated_at": datetime.now().isoformat(),
        }

    @handle_errors_none(error_message="获取港股财务指标失败", log_level="warning")
    def _get_financial_indicators_safe(self, code: str) -> Optional[Dict]:
        """安全获取港股财务指标(失败返回None)"""
        from tradingagents.dataflows.providers.hk.improved_hk import (
            get_hk_financial_indicators,
        )

        return get_hk_financial_indicators(code)

    @property
    def format_basic_info(self):
        """格式化基础信息（基类模板需要的属性）"""

        def format_method(data: Dict, code: str, source: str) -> Dict:
            return self._format_info(data, code, source)

        return format_method

    def _get_info_from_akshare(self, code: str) -> Dict:
        """从AKShare获取港股基础信息和财务指标"""
        from tradingagents.dataflows.providers.hk.improved_hk import (
            get_hk_stock_info_akshare,
            get_hk_financial_indicators,
        )

        # 1. 获取基础信息（包含当前价格）
        info = get_hk_stock_info_akshare(code)
        if not info or "error" in info:
            raise Exception("无数据")

        # 2. 获取财务指标（EPS、BPS、ROE、负债率等）
        financial_indicators = self._get_financial_indicators_safe(code) or {}
        if financial_indicators:
            logger.info(
                f"✅ 获取港股{code}财务指标成功: {list(financial_indicators.keys())}"
            )

        # 3. 计算 PE、PB、PS（参考分析模块的计算方式）
        current_price = info.get("price")  # 当前价格
        pe_ratio = None
        pb_ratio = None
        ps_ratio = None

        if current_price and financial_indicators:
            # 计算 PE = 当前价 / EPS_TTM
            eps_ttm = financial_indicators.get("eps_ttm")
            if eps_ttm and eps_ttm > 0:
                pe_ratio = current_price / eps_ttm
                logger.info(f"📊 计算 PE: {current_price} / {eps_ttm} = {pe_ratio:.2f}")

            # 计算 PB = 当前价 / BPS
            bps = financial_indicators.get("bps")
            if bps and bps > 0:
                pb_ratio = current_price / bps
                logger.info(f"📊 计算 PB: {current_price} / {bps} = {pb_ratio:.2f}")

            # 计算 PS = 市值 / 营业收入（需要市值数据，暂时无法计算）
            # ps_ratio 暂时为 None

        # 4. 合并数据
        return {
            "name": info.get("name", f"港股{code}"),
            "market_cap": None,  # AKShare 基础信息不包含市值
            "industry": None,
            "sector": None,
            # 🔥 计算得到的估值指标
            "pe_ratio": pe_ratio,
            "pb_ratio": pb_ratio,
            "ps_ratio": ps_ratio,
            "dividend_yield": None,
            "currency": "HKD",
            # 🔥 从财务指标中获取
            "roe": financial_indicators.get("roe_avg"),  # 平均净资产收益率
            "debt_ratio": financial_indicators.get("debt_asset_ratio"),  # 资产负债率
        }

    def _get_info_from_yfinance(self, code: str) -> Dict:
        """从Yahoo Finance获取港股基础信息"""
        import yfinance as yf

        ticker = yf.Ticker(f"{code}.HK")
        info = ticker.info

        return {
            "name": info.get("longName") or info.get("shortName") or f"港股{code}",
            "market_cap": info.get("marketCap"),
            "industry": info.get("industry"),
            "sector": info.get("sector"),
            "pe_ratio": info.get("trailingPE"),
            "pb_ratio": info.get("priceToBook"),
            "dividend_yield": info.get("dividendYield"),
            "currency": info.get("currency", "HKD"),
            # Yahoo Finance 不提供 ROE 和负债率
            "roe": None,
            "debt_ratio": None,
        }

    def _get_info_from_finnhub(self, code: str) -> Dict:
        """从Finnhub获取港股基础信息"""
        import finnhub
        import os

        # 获取 API Key
        api_key = os.getenv("FINNHUB_API_KEY")
        if not api_key:
            raise Exception("Finnhub API Key 未配置")

        # 创建客户端
        client = finnhub.Client(api_key=api_key)

        # 港股代码需要添加 .HK 后缀
        hk_symbol = f"{code}.HK" if not code.endswith(".HK") else code

        # 获取公司基本信息
        profile = client.company_profile2(symbol=hk_symbol)

        if not profile:
            raise Exception("无数据")

        return {
            "name": profile.get("name", f"港股{code}"),
            "market_cap": profile.get("marketCapitalization") * 1e6
            if profile.get("marketCapitalization")
            else None,  # Finnhub返回的是百万单位
            "industry": profile.get("finnhubIndustry"),
            "sector": None,
            "pe_ratio": None,
            "pb_ratio": None,
            "dividend_yield": None,
            "currency": profile.get("currency", "HKD"),
            # Finnhub 不提供 ROE 和负债率
            "roe": None,
            "debt_ratio": None,
        }

    def _format_info(self, data: Dict, code: str, source: str) -> Dict:
        """格式化港股基础信息"""
        market_cap = data.get("market_cap")
        return {
            "code": code,
            "name": data.get("name", f"港股{code}"),
            "market": "HK",
            "industry": data.get("industry"),
            "sector": data.get("sector"),
            # 前端期望 total_mv（单位：亿元）
            "total_mv": market_cap / 1e8 if market_cap else None,
            # 前端期望 pe_ttm 或 pe
            "pe_ttm": data.get("pe_ratio"),
            "pe": data.get("pe_ratio"),
            # 前端期望 pb
            "pb": data.get("pb_ratio"),
            # 前端期望 ps
            "ps": data.get("ps_ratio"),
            "ps_ttm": data.get("ps_ratio"),
            # 🔥 从财务指标中获取 roe 和 debt_ratio
            "roe": data.get("roe"),
            "debt_ratio": data.get("debt_ratio"),
            "dividend_yield": data.get("dividend_yield"),
            "currency": data.get("currency", "HKD"),
            "source": source,
            "updated_at": datetime.now().isoformat(),
        }

    async def get_kline(
        self,
        code: str,
        period: str = "day",
        limit: int = 120,
        force_refresh: bool = False,
    ) -> List[Dict]:
        """获取港股K线数据（使用基类模板方法）"""
        return await self.get_kline_template(code, period, limit, force_refresh)

    def _get_kline_from_akshare(self, code: str, period: str, limit: int) -> List[Dict]:
        """从AKShare获取港股K线数据"""
        import akshare as ak
        from tradingagents.dataflows.providers.hk.improved_hk import (
            get_improved_hk_provider,
        )

        # 标准化代码
        provider = get_improved_hk_provider()
        normalized_code = provider._normalize_hk_symbol(code)

        # 直接使用 AKShare API
        df = ak.stock_hk_daily(symbol=normalized_code, adjust="qfq")

        if df is None or df.empty:
            raise Exception("无数据")

        # 过滤最近的数据
        df = df.tail(limit)

        # 格式化数据
        kline_data = []
        for _, row in df.iterrows():
            # AKShare 返回的列名：date, open, close, high, low, volume
            date_str = (
                row["date"].strftime("%Y-%m-%d")
                if hasattr(row["date"], "strftime")
                else str(row["date"])
            )
            kline_data.append(
                {
                    "date": date_str,
                    "trade_date": date_str,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"]) if "volume" in row else 0,
                }
            )

        return kline_data

    def _get_kline_from_yfinance(
        self, code: str, period: str, limit: int
    ) -> List[Dict]:
        """从Yahoo Finance获取港股K线数据"""
        import yfinance as yf

        ticker = yf.Ticker(f"{code}.HK")

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
                    "trade_date": date_str,
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                }
            )

        return kline_data[-limit:]  # 返回最后limit条

    def _get_kline_from_finnhub(self, code: str, period: str, limit: int) -> List[Dict]:
        """从Finnhub获取港股K线数据"""
        import finnhub
        import os

        # 获取 API Key
        api_key = os.getenv("FINNHUB_API_KEY")
        if not api_key:
            raise Exception("Finnhub API Key 未配置")

        # 创建客户端
        client = finnhub.Client(api_key=api_key)

        # 港股代码需要添加 .HK 后缀
        hk_symbol = f"{code}.HK" if not code.endswith(".HK") else code

        # 周期映射
        resolution_map = {
            "day": "D",
            "week": "W",
            "month": "M",
            "5m": "5",
            "15m": "15",
            "30m": "30",
            "60m": "60",
        }

        resolution = resolution_map.get(period, "D")

        # 计算时间范围
        end_time = int(datetime.now().timestamp())
        start_time = int((datetime.now() - timedelta(days=limit * 2)).timestamp())

        # 获取K线数据
        candles = client.stock_candles(hk_symbol, resolution, start_time, end_time)

        if not candles or candles.get("s") != "ok":
            raise Exception("无数据")

        # 格式化数据
        kline_data = []
        for i in range(len(candles["t"])):
            date_str = datetime.fromtimestamp(candles["t"][i]).strftime("%Y-%m-%d")
            kline_data.append(
                {
                    "date": date_str,
                    "trade_date": date_str,
                    "open": float(candles["o"][i]),
                    "high": float(candles["h"][i]),
                    "low": float(candles["l"][i]),
                    "close": float(candles["c"][i]),
                    "volume": int(candles["v"][i]),
                }
            )

        return kline_data[-limit:]  # 返回最后limit条

    async def get_news(self, code: str, days: int = 2, limit: int = 50) -> Dict:
        """获取港股新闻（使用基类模板方法）"""
        return await self.get_news_template(code, days, limit)

    def _get_news_from_akshare(self, code: str, days: int, limit: int) -> List[Dict]:
        """从AKShare获取港股新闻"""
        try:
            import akshare as ak

            # AKShare 的港股新闻接口
            # 注意：AKShare 可能没有专门的港股新闻接口，这里使用通用新闻接口
            # 如果没有合适的接口，抛出异常让系统尝试下一个数据源

            # 尝试获取港股新闻（使用东方财富港股新闻）
            try:
                df = ak.stock_news_em(symbol=code)
                if df is None or df.empty:
                    raise Exception("无数据")

                # 格式化新闻数据
                news_list = []
                for _, row in df.head(limit).iterrows():
                    pub_time = (
                        row["发布时间"]
                        if "发布时间" in row
                        else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                    news_list.append(
                        {
                            "title": row["新闻标题"] if "新闻标题" in row else "",
                            "summary": row["新闻内容"] if "新闻内容" in row else "",
                            "url": row["新闻链接"] if "新闻链接" in row else "",
                            "source": "AKShare-东方财富",
                            "publish_time": pub_time,
                            "sentiment": None,
                            "sentiment_score": None,
                        }
                    )

                return news_list
            except Exception as e:
                logger.debug(f"AKShare 东方财富接口失败: {e}")
                raise Exception("AKShare 暂不支持港股新闻")

        except Exception as e:
            logger.warning(f"⚠️ AKShare获取港股新闻失败: {e}")
            raise

    def _get_news_from_finnhub(self, code: str, days: int, limit: int) -> List[Dict]:
        """从Finnhub获取港股新闻"""
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

        # 港股代码需要添加 .HK 后缀
        hk_symbol = f"{code}.HK" if not code.endswith(".HK") else code

        # 获取公司新闻
        news = client.company_news(
            hk_symbol,
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
