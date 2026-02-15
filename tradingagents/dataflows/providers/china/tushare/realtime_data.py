# -*- coding: utf-8 -*-
"""
实时行情数据模块

提供实时行情、批量行情等功能。
"""

from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

from .base_provider import BaseTushareProvider, ts, logger
from ...base_provider import BaseStockDataProvider
from .cache_manager import (
    _get_cached_batch_quotes,
    _set_cached_batch_quotes,
    _invalidate_batch_cache,
    BATCH_CACHE_TTL_SECONDS,
    BATCH_QUOTES_CACHE,
)


class RealtimeDataMixin(BaseTushareProvider):
    """实时行情数据功能混入类"""

    async def get_stock_quotes(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取单只股票实时行情

        策略：
        1. 优先尝试 ts.get_realtime_quotes (Sina/Web API) 获取秒级实时数据
        2. 失败则回退到 daily 接口 (T-1或收盘数据)
        """
        if not self.is_available():
            return None

        # 1. 尝试使用 ts.get_realtime_quotes (实时接口)
        try:
            # ts.get_realtime_quotes 是同步的，需放入线程池
            # 注意：ts.get_realtime_quotes 接受的是股票代码字符串 (如 '000001')
            # 不需要带后缀，或者它能处理
            # 这里的 symbol 可能是 '000001' 或 '000001.SZ'
            # ts.get_realtime_quotes 需要 6位代码
            code_6 = symbol.split(".")[0]

            df = await asyncio.to_thread(ts.get_realtime_quotes, code_6)

            if df is not None and not df.empty:
                row = df.iloc[0]

                # Sina 返回的数据
                # price: 当前价
                # volume: 成交量(股)
                # amount: 成交额(元)
                # date: 日期 (YYYY-MM-DD)
                # time: 时间 (HH:MM:SS)

                # 检查数据有效性 (有时返回空壳数据)
                if float(row["price"]) > 0:
                    trade_date = row["date"]

                    # 成交量单位转换：Sina实时接口返回的是"股"，转换为"手"（1手=100股）
                    volume_in_shares = float(row["volume"])
                    volume_in_lots = volume_in_shares / 100 if volume_in_shares else 0

                    return {
                        "ts_code": self._normalize_ts_code(symbol),
                        "symbol": symbol,
                        "trade_date": trade_date.replace("-", ""),  # YYYYMMDD
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["price"]),  # 当前价
                        "current_price": float(row["price"]),
                        "price": float(row["price"]),  # 兼容性字段
                        "pre_close": float(row["pre_close"]),
                        "change": float(row["price"]) - float(row["pre_close"]),
                        "pct_chg": (float(row["price"]) - float(row["pre_close"]))
                        / float(row["pre_close"])
                        * 100
                        if float(row["pre_close"]) > 0
                        else 0,
                        "volume": volume_in_lots,  # 单位：手（已转换）
                        "volume_unit": "lots",  # 明确标注单位为手
                        "amount": float(row["amount"]),  # 已经是元
                        "source": "sina_realtime",
                    }

        except Exception as e:
            self.logger.warning(f"⚠️ Tushare实时接口(Sina)获取失败，降级到daily: {e}")

        # 2. 回退到 daily 接口 (原有逻辑)
        try:
            ts_code = self._normalize_ts_code(symbol)

            # 使用 daily 接口获取最新一天的数据（更节省配额）
            from datetime import datetime, timedelta

            # 获取最近3天的数据（考虑周末和节假日）
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=3)).strftime("%Y%m%d")

            df = await asyncio.to_thread(
                self.api.daily,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )

            if df is not None and not df.empty:
                # 取最新一天的数据
                row = df.iloc[0]

                # 标准化字段
                quote_data = {
                    "ts_code": row.get("ts_code"),
                    "symbol": symbol,
                    "trade_date": row.get("trade_date"),
                    "open": row.get("open"),
                    "high": row.get("high"),
                    "low": row.get("low"),
                    "close": row.get("close"),  # 收盘价
                    "pre_close": row.get("pre_close"),
                    "change": row.get("change"),  # 涨跌额
                    "pct_chg": row.get("pct_chg"),  # 涨跌幅
                    "volume": row.get("vol"),  # 成交量（手）
                    "amount": row.get("amount"),  # 成交额（千元）
                }

                # 补充 price 字段
                standardized = self.standardize_quotes(quote_data)
                standardized["price"] = standardized.get("close", 0)
                return standardized

            return None

        except Exception as e:
            # 检查是否为限流错误
            if self._is_rate_limit_error(str(e)):
                self.logger.error(f"❌ 获取实时行情失败（限流） symbol={symbol}: {e}")
                raise  # 抛出限流错误，让上层处理

            self.logger.error(f"❌ 获取实时行情失败 symbol={symbol}: {e}")
            return None

    async def get_realtime_quotes_batch(
        self, force_refresh: bool = False
    ) -> Optional[Dict[str, Dict[str, Any]]]:
        """
        批量获取全市场实时行情
        使用 rt_k 接口的通配符功能，一次性获取所有A股实时行情

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            Dict[str, Dict]: {symbol: quote_data}
            例如: {'000001': {'close': 10.5, 'pct_chg': 1.2, ...}, ...}
        """
        if not self.is_available():
            return None

        if not force_refresh:
            cached = _get_cached_batch_quotes()
            if cached is not None:
                self.logger.debug(f"[Cache] 使用缓存的批量行情: {len(cached)} 只股票")
                return cached

        try:
            df = await asyncio.to_thread(
                self.api.rt_k, ts_code="3*.SZ,6*.SH,0*.SZ,9*.BJ"
            )

            if df is None or df.empty:
                self.logger.warning("rt_k 接口返回空数据")
                return None

            cn_tz = __import__("datetime").timezone(
                __import__("datetime").timedelta(hours=8)
            )
            now_cn = datetime.now(cn_tz)
            trade_date = now_cn.strftime("%Y%m%d")

            result = {}
            for _, row in df.iterrows():
                ts_code = row.get("ts_code")
                if not ts_code or "." not in ts_code:
                    continue

                symbol = ts_code.split(".")[0]

                close = row.get("close")
                pre_close = row.get("pre_close")

                pct_chg = None
                change_val = None
                if close and pre_close:
                    try:
                        close_f = float(close)
                        pre_close_f = float(pre_close)
                        if pre_close_f > 0:
                            pct_chg = round(
                                ((close_f - pre_close_f) / pre_close_f) * 100, 2
                            )
                            change_val = round(close_f - pre_close_f, 2)
                    except (ValueError, TypeError):
                        pass

                quote_data = {
                    "ts_code": ts_code,
                    "symbol": symbol,
                    "name": row.get("name"),
                    "open": row.get("open"),
                    "high": row.get("high"),
                    "low": row.get("low"),
                    "close": close,
                    "pre_close": pre_close,
                    "volume": row.get("vol"),
                    "amount": row.get("amount"),
                    "num": row.get("num"),
                    "trade_date": trade_date,
                    "pct_chg": pct_chg,
                    "change": change_val,
                }

                result[symbol] = quote_data

            await _set_cached_batch_quotes(result)
            self.logger.info(f"[RT-K] 获取到 {len(result)} 只股票的实时行情")

            return result

        except Exception as e:
            if self._is_rate_limit_error(str(e)):
                self.logger.error(f"批量获取实时行情失败（限流）: {e}")
                raise

            self.logger.error(f"批量获取实时行情失败: {e}")
            return None

    async def get_realtime_price_from_batch(self, symbol: str) -> Optional[float]:
        """
        从批量实时行情中获取单只股票价格
        使用缓存机制，避免重复调用 rt_k 接口

        Args:
            symbol: 股票代码（如 '000001.SZ' 或 '000001'）

        Returns:
            实时价格，失败返回 None
        """
        if not self.is_available():
            return None

        try:
            ts_code = self._normalize_ts_code(symbol)
            code6 = ts_code.split(".")[0]

            cached = _get_cached_batch_quotes()
            if cached is not None:
                if code6 in cached:
                    close = cached[code6].get("close")
                    return float(close) if close else None
                return None

            batch_quotes = await self.get_realtime_quotes_batch()
            if not batch_quotes:
                return None

            if code6 in batch_quotes:
                close = batch_quotes[code6].get("close")
                return float(close) if close else None

            return None

        except Exception as e:
            self.logger.warning(f"从批量行情获取 {symbol} 价格失败: {e}")
            return None

    def get_batch_cache_status(self) -> Dict[str, Any]:
        """获取批量行情缓存状态"""
        if (
            BATCH_QUOTES_CACHE["data"] is None
            or BATCH_QUOTES_CACHE["timestamp"] is None
        ):
            return {
                "cached": False,
                "count": 0,
                "age_seconds": None,
                "ttl_seconds": BATCH_CACHE_TTL_SECONDS,
            }

        age = (datetime.now() - BATCH_QUOTES_CACHE["timestamp"]).total_seconds()
        return {
            "cached": True,
            "count": len(BATCH_QUOTES_CACHE["data"]),
            "age_seconds": round(age, 1),
            "ttl_seconds": BATCH_CACHE_TTL_SECONDS,
            "is_valid": age < BATCH_CACHE_TTL_SECONDS,
        }

    async def invalidate_batch_cache(self) -> None:
        """使批量缓存失效"""
        await _invalidate_batch_cache()

    def _is_rate_limit_error(self, error_msg: str) -> bool:
        """检测是否为 API 限流错误"""
        rate_limit_keywords = [
            "每分钟最多访问",
            "每分钟最多",
            "rate limit",
            "too many requests",
            "访问频率",
            "请求过于频繁",
        ]
        error_msg_lower = error_msg.lower()
        return any(keyword in error_msg_lower for keyword in rate_limit_keywords)

    def standardize_quotes(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化实时行情数据"""
        ts_code = raw_data.get("ts_code", "")
        symbol = ts_code.split(".")[0] if "." in ts_code else ts_code

        # 统一处理 volume/vol 字段，支持多种数据源格式
        raw_volume = raw_data.get("volume") or raw_data.get("vol")

        return {
            # 基础字段
            "code": symbol,
            "symbol": symbol,
            "full_symbol": ts_code,
            "market": self._determine_market(ts_code),
            # 价格数据
            "close": self._convert_to_float(raw_data.get("close")),
            "current_price": self._convert_to_float(raw_data.get("close")),
            "open": self._convert_to_float(raw_data.get("open")),
            "high": self._convert_to_float(raw_data.get("high")),
            "low": self._convert_to_float(raw_data.get("low")),
            "pre_close": self._convert_to_float(raw_data.get("pre_close")),
            # 变动数据
            "change": self._convert_to_float(raw_data.get("change")),
            "pct_chg": self._convert_to_float(raw_data.get("pct_chg")),
            # 成交数据
            # 成交量单位：直接使用原始单位"手"（Tushare返回的是手）
            # 统一处理 volume/vol 字段，保持原始单位
            "volume": self._convert_to_float(raw_volume) if raw_volume else None,
            "volume_unit": "lots",  # 明确标注单位为手
            # 成交额单位转换：Tushare daily 接口返回的是千元，需要转换为元
            "amount": self._convert_to_float(raw_data.get("amount")) * 1000
            if raw_data.get("amount")
            else None,
            # 财务指标
            "total_mv": self._convert_to_float(raw_data.get("total_mv")),
            "circ_mv": self._convert_to_float(raw_data.get("circ_mv")),
            "pe": self._convert_to_float(raw_data.get("pe")),
            "pb": self._convert_to_float(raw_data.get("pb")),
            "turnover_rate": self._convert_to_float(raw_data.get("turnover_rate")),
            # 时间数据
            "trade_date": self._format_date_output(raw_data.get("trade_date")),
            "timestamp": datetime.utcnow(),
            # 元数据
            "data_source": "tushare",
            "data_version": 1,
            "updated_at": datetime.utcnow(),
        }

    def _normalize_ts_code(self, symbol: str) -> str:
        """标准化为Tushare的ts_code格式"""
        if "." in symbol:
            return symbol  # 已经是ts_code格式

        # 6位数字代码，需要添加后缀
        if symbol.isdigit() and len(symbol) == 6:
            if symbol.startswith(("60", "68", "90")):
                return f"{symbol}.SH"  # 上交所
            else:
                return f"{symbol}.SZ"  # 深交所

        return symbol

    def _determine_market(self, ts_code: str) -> str:
        """确定市场代码（调用基类通用方法）"""
        return self._get_market_info(ts_code).get("market", "CN")

    def _format_date_output(self, date_value) -> Optional[str]:
        """格式化日期输出"""
        if date_value is None:
            return None
        if isinstance(date_value, str):
            # 已经是字符串，检查格式
            if len(date_value) == 8:
                return f"{date_value[:4]}-{date_value[4:6]}-{date_value[6:]}"
            return date_value
        return str(date_value)

    def _convert_to_float(self, value) -> Optional[float]:
        """安全转换为浮点数"""
        if value is None:
            return None
        try:
            if isinstance(value, str):
                value = value.strip()
                if not value or value.lower() in ["nan", "null", "none", ""]:
                    return None
            return float(value)
        except (ValueError, TypeError):
            return None
