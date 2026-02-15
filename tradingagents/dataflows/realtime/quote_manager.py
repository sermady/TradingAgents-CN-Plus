# -*- coding: utf-8 -*-
"""
实时行情管理器
负责实时行情数据的获取和管理
"""

import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import requests

from tradingagents.utils.logging_manager import get_logger

logger = get_logger("agents")


class RealtimeQuoteManager:
    """实时行情管理器 - 处理实时行情获取"""

    def __init__(self):
        """初始化实时行情管理器"""
        self._config = self._get_realtime_quote_config()

    def _get_realtime_quote_config(self) -> Dict:
        """获取实时行情配置"""
        return {
            "enabled": os.getenv("REALTIME_QUOTE_ENABLED", "true").lower() == "true",
            "tushare_enabled": os.getenv(
                "REALTIME_QUOTE_TUSHARE_ENABLED", "true"
            ).lower()
            == "true",
            "max_retries": int(os.getenv("REALTIME_QUOTE_MAX_RETRIES", "3")),
            "retry_delay": float(os.getenv("REALTIME_QUOTE_RETRY_DELAY", "1.0")),
            "retry_backoff": float(os.getenv("REALTIME_QUOTE_RETRY_BACKOFF", "2.0")),
            "akshare_priority": int(os.getenv("REALTIME_QUOTE_AKSHARE_PRIORITY", "1")),
            "tushare_priority": int(os.getenv("REALTIME_QUOTE_TUSHARE_PRIORITY", "2")),
        }

    def get_realtime_quote(self, symbol: str) -> Optional[Dict]:
        """
        获取实时行情数据 - 只使用外部API，不使用MongoDB缓存

        Args:
            symbol: 股票代码

        Returns:
            Dict: 实时行情数据，包含price, change, change_pct, volume等
        """
        config = self._get_realtime_quote_config()

        if not config["enabled"]:
            logger.info(f"📊 [实时行情] 实时行情获取已禁用，跳过: {symbol}")
            return None

        logger.info(
            f"📊 [实时行情] 获取实时行情: {symbol} (重试次数: {config['max_retries']})"
        )

        try:
            # 根据优先级排序数据源
            sources = []
            if config["akshare_priority"] == 1:
                sources.append(("akshare", self._get_akshare_realtime_quote_with_retry))
            if config["tushare_enabled"] and config["tushare_priority"] == 1:
                sources.append(("tushare", self._get_tushare_realtime_quote_with_retry))
            if config["akshare_priority"] == 2:
                sources.append(("akshare", self._get_akshare_realtime_quote_with_retry))
            if config["tushare_enabled"] and config["tushare_priority"] == 2:
                sources.append(("tushare", self._get_tushare_realtime_quote_with_retry))

            # 依次尝试各个数据源
            for source_name, source_func in sources:
                try:
                    quote = source_func(symbol, config)
                    if quote:
                        logger.info(
                            f"✅ [实时行情-{source_name.upper()}] 成功获取 {symbol} 实时行情"
                        )
                        self._update_price_cache(symbol, quote.get("price"))
                        return quote
                except Exception as e:
                    logger.warning(f"⚠️ [实时行情-{source_name.upper()}] 获取失败: {e}")
                    continue

            # 所有数据源都失败
            logger.warning(
                f"⚠️ [实时行情] 无法获取 {symbol} 的实时行情（所有外部API失败）"
            )
            return None

        except Exception as e:
            logger.error(f"❌ 获取实时行情失败: {e}", exc_info=True)
            return None

    def _get_akshare_realtime_quote_with_retry(
        self, symbol: str, config: Dict
    ) -> Optional[Dict]:
        """带重试的AKShare实时行情获取"""
        max_retries = config["max_retries"]
        retry_delay = config["retry_delay"]
        backoff = config["retry_backoff"]

        for attempt in range(max_retries):
            try:
                quote = self._get_akshare_realtime_quote(symbol)
                if quote:
                    return quote
            except Exception as e:
                logger.warning(
                    f"⚠️ [AKShare-重试{attempt + 1}/{max_retries}] {symbol}: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= backoff

        return None

    def _get_tushare_realtime_quote_with_retry(
        self, symbol: str, config: Dict
    ) -> Optional[Dict]:
        """带重试的Tushare实时行情获取"""
        max_retries = config["max_retries"]
        retry_delay = config["retry_delay"]
        backoff = config["retry_backoff"]

        for attempt in range(max_retries):
            try:
                quote = self._get_tushare_realtime_quote(symbol)
                if quote:
                    return quote
            except Exception as e:
                logger.warning(
                    f"⚠️ [Tushare-重试{attempt + 1}/{max_retries}] {symbol}: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= backoff

        return None

    def _get_tushare_realtime_quote(self, symbol: str) -> Optional[Dict]:
        """
        使用Tushare获取实时行情

        使用 ts.get_realtime_quotes 接口获取秒级实时数据
        该接口基于新浪财经数据，无需高级权限
        """
        try:
            import asyncio

            import tushare as ts

            # 获取6位股票代码
            code_6 = symbol.split(".")[0] if "." in symbol else symbol
            code_6 = code_6.zfill(6)

            logger.debug(f"📊 [Tushare实时行情] 尝试获取 {symbol} (代码: {code_6})")

            # 创建事件循环
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # 在线程池中执行同步的 tushare 调用
            df = loop.run_until_complete(
                asyncio.to_thread(ts.get_realtime_quotes, code_6)
            )

            if df is not None and not df.empty:
                row = df.iloc[0]

                # 检查数据有效性
                price = float(row.get("price", 0))
                if price > 0:
                    pre_close = float(row.get("pre_close", 0))
                    change = price - pre_close if pre_close > 0 else 0
                    change_pct = (change / pre_close * 100) if pre_close > 0 else 0

                    quote = {
                        "symbol": symbol,
                        "price": price,
                        "open": float(row.get("open", 0)),
                        "high": float(row.get("high", 0)),
                        "low": float(row.get("low", 0)),
                        "volume": int(float(row.get("volume", 0))),
                        "amount": float(row.get("amount", 0)),
                        "change": change,
                        "change_pct": change_pct,
                        "pre_close": pre_close,
                        "date": row.get("date", datetime.now().strftime("%Y-%m-%d")),
                        "time": row.get("time", datetime.now().strftime("%H:%M:%S")),
                        "source": "tushare_sina_realtime",
                        "is_realtime": True,
                    }

                    logger.info(
                        f"✅ [实时行情-Tushare-Sina] {symbol} 价格={quote['price']:.2f}, "
                        f"涨跌={quote['change']:.2f}({quote['change_pct']:.2f}%)"
                    )
                    return quote
                else:
                    logger.warning(f"⚠️ [实时行情-Tushare] {symbol} 价格数据无效")
            else:
                logger.debug(f"📊 [实时行情-Tushare] {symbol} 无实时数据返回")

            return None

        except Exception as e:
            logger.error(f"❌ Tushare实时行情获取失败: {e}")
            return None

    def _get_akshare_realtime_quote(self, symbol: str) -> Optional[Dict]:
        """使用AKShare获取实时行情"""
        max_retries = 2
        last_error = None

        for attempt in range(max_retries):
            try:
                import akshare as ak

                # 转换股票代码格式为新浪格式
                if symbol.startswith("6"):
                    sina_symbol = f"sh{symbol}"
                elif symbol.startswith(("0", "3", "2")):
                    sina_symbol = f"sz{symbol}"
                elif symbol.startswith(("8", "4")):
                    sina_symbol = f"bj{symbol}"
                else:
                    sina_symbol = symbol

                # 优先尝试新浪实时接口
                try:
                    url = f"http://hq.sinajs.cn/list={sina_symbol}"
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    }

                    response = requests.get(url, headers=headers, timeout=10)
                    response.encoding = "gbk"

                    if response.status_code == 200:
                        data_str = response.text.strip()
                        if "var hq_str_" in data_str:
                            # 解析新浪数据
                            start_idx = data_str.index('"') + 1
                            end_idx = data_str.rindex('"')
                            data_str = data_str[start_idx:end_idx]

                            data = data_str.split(",")
                            if len(data) >= 33:
                                price = float(data[3])
                                open_price = float(data[1])
                                high_price = float(data[4])
                                low_price = float(data[5])
                                volume = int(float(data[8]))

                                quote = {
                                    "symbol": symbol,
                                    "price": price,
                                    "open": open_price,
                                    "high": high_price,
                                    "low": low_price,
                                    "volume": volume,
                                    "amount": 0.0,
                                    "change": float(data[2]),
                                    "change_pct": float(data[2]) / float(data[1]) * 100
                                    if float(data[1]) > 0
                                    else 0.0,
                                    "date": datetime.now().strftime("%Y-%m-%d"),
                                    "time": datetime.now().strftime("%H:%M:%S"),
                                    "source": "sina_realtime",
                                    "is_realtime": True,
                                }
                                logger.info(
                                    f"✅ [实时行情-新浪] {symbol} 价格={quote['price']:.2f}, 成交量={volume:,.0f}手"
                                )
                                return quote
                except Exception as e:
                    logger.debug(f"新浪接口失败，尝试东方财富: {e}")
                    last_error = e

                # 备用：东方财富单股票接口
                logger.info(
                    f"🔄 [AKShare] 尝试获取 {symbol} 单股票实时行情 (第{attempt + 1}次)"
                )
                df = ak.stock_bid_ask_em(symbol=symbol)

                if df is not None and not df.empty:
                    # 将 DataFrame 转换为字典
                    data_dict = dict(zip(df["item"], df["value"]))

                    # 成交量单位：手
                    volume_in_lots = int(data_dict.get("总手", 0))

                    quote = {
                        "symbol": symbol,
                        "price": float(data_dict.get("最新", 0)),
                        "open": float(data_dict.get("今开", 0)),
                        "high": float(data_dict.get("最高", 0)),
                        "low": float(data_dict.get("最低", 0)),
                        "volume": volume_in_lots,
                        "amount": float(data_dict.get("金额", 0)),
                        "change": float(data_dict.get("涨跌", 0)),
                        "change_pct": float(data_dict.get("涨幅", 0)),
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "source": "eastmoney_realtime",
                        "is_realtime": True,
                    }
                    logger.info(
                        f"✅ [实时行情-东方财富单股票] {symbol} 价格={quote['price']:.2f}, 成交量={volume_in_lots:,.0f}手"
                    )
                    return quote
                else:
                    logger.warning(f"⚠️ AKShare未找到{symbol}的实时行情")
                    if attempt < max_retries - 1:
                        time.sleep(2)

            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ [AKShare] 获取失败 (第{attempt + 1}次): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)

        logger.error(f"❌ AKShare实时行情获取失败: {last_error}")
        return None

    def _update_price_cache(self, symbol: str, price: float):
        """更新价格缓存"""
        if price is None:
            return
        try:
            from tradingagents.utils.price_cache import get_price_cache

            get_price_cache().update(symbol, price)
        except Exception as e:
            logger.warning(f"⚠️ [实时行情] 缓存更新失败: {e}")

    def is_realtime_capable(self, source: str) -> Dict[str, bool]:
        """
        判断数据源是否支持实时行情

        Args:
            source: 数据源名称

        Returns:
            Dict[str, bool]: 各项实时能力的字典
        """
        capabilities = {
            "mongodb": {
                "realtime_quote": False,
                "tick_data": False,
                "level2": False,
                "delay_seconds": 0,
                "description": "缓存数据,来自其他数据源的历史快照",
            },
            "tushare": {
                "realtime_quote": True,
                "tick_data": True,
                "level2": False,
                "delay_seconds": 900,
                "description": "官方数据,但实时行情有15分钟延迟",
            },
            "akshare": {
                "realtime_quote": True,
                "tick_data": True,
                "level2": True,
                "delay_seconds": 1,
                "description": "最佳实时数据源,来自东方财富/腾讯",
            },
            "baostock": {
                "realtime_quote": False,
                "tick_data": False,
                "level2": False,
                "delay_seconds": 86400,
                "description": "仅提供历史数据,不支持实时行情",
            },
        }

        return capabilities.get(
            source.lower(),
            {
                "realtime_quote": False,
                "tick_data": False,
                "level2": False,
                "delay_seconds": 999999,
                "description": "未知数据源",
            },
        )
