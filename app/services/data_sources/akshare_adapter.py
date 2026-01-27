# -*- coding: utf-8 -*-
"""
AKShare data source adapter
"""

from typing import Optional, Dict, Any
import logging
import os
import time
from datetime import datetime, timedelta
from functools import wraps
import pandas as pd

from .base import DataSourceAdapter

logger = logging.getLogger(__name__)

AKSHARE_RETRY_CONFIG = {
    "max_retries": 3,
    "initial_delay": 1.0,
    "max_delay": 10.0,
    "backoff_multiplier": 2.0,
    "jitter": 0.3,
}


def get_proxy_status() -> Dict[str, str]:
    """获取当前代理配置状态"""
    return {
        "http_proxy": os.environ.get("HTTP_PROXY")
        or os.environ.get("http_proxy")
        or "",
        "https_proxy": os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
        or "",
        "no_proxy": os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or "",
    }


def akshare_retry_with_backoff(func):
    """装饰器：为 AKShare 请求添加指数退避重试机制"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = AKSHARE_RETRY_CONFIG["max_retries"]
        initial_delay = AKSHARE_RETRY_CONFIG["initial_delay"]
        max_delay = AKSHARE_RETRY_CONFIG["max_delay"]
        backoff = AKSHARE_RETRY_CONFIG["backoff_multiplier"]
        jitter = AKSHARE_RETRY_CONFIG["jitter"]

        last_exception = None

        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                delay = min(initial_delay * (backoff**attempt), max_delay)
                if attempt < max_retries - 1:
                    delay += (time.time() % jitter) * delay
                    logger.warning(
                        f"⚠️ AKShare 请求失败，{delay:.1f}秒后重试 ({attempt + 1}/{max_retries}): "
                        f"{type(e).__name__}: {str(e)[:100]}"
                    )
                    time.sleep(delay)

        proxy_status = get_proxy_status()
        proxy_enabled = any(v for v in proxy_status.values())
        logger.error(
            f"❌ AKShare 请求失败，已达最大重试次数 ({max_retries}): "
            f"error_type={type(last_exception).__name__}, "
            f"proxy_enabled={proxy_enabled}, "
            f"error={str(last_exception)[:200]}"
        )
        return None

    return wrapper


class AKShareAdapter(DataSourceAdapter):
    """AKShare数据源适配器"""

    def __init__(self):
        super().__init__()  # 调用父类初始化

    @property
    def name(self) -> str:
        return "akshare"

    def _get_default_priority(self) -> int:
        return 2  # 数字越大优先级越高

    def _convert_volume(self, volume_value) -> Optional[float]:
        """
        成交量单位转换：AKShare 返回的是手，需要转换为股

        Args:
            volume_value: 成交量原始值

        Returns:
            转换后的成交量（股），如果输入无效则返回 None
        """
        if volume_value is None:
            return None
        try:
            vol = float(volume_value)
            if vol <= 0:
                return None
            # AKShare 返回的成交量单位是手，转换为股
            return vol * 100
        except (ValueError, TypeError):
            return None

    def is_available(self) -> bool:
        """检查AKShare是否可用"""
        try:
            import akshare as ak  # noqa: F401

            return True
        except ImportError:
            return False

    def get_stock_list(self) -> Optional[pd.DataFrame]:
        """获取股票列表（使用 AKShare 的 stock_info_a_code_name 接口获取真实股票名称）"""
        if not self.is_available():
            return None
        try:
            import akshare as ak

            logger.info(
                "AKShare: Fetching stock list with real names from stock_info_a_code_name()..."
            )

            # 使用 AKShare 的 stock_info_a_code_name 接口获取股票代码和名称
            df = ak.stock_info_a_code_name()

            if df is None or df.empty:
                logger.warning("AKShare: stock_info_a_code_name() returned empty data")
                return None

            # 标准化列名（AKShare 返回的列名可能是中文）
            # 通常返回的列：code（代码）、name（名称）
            df = df.rename(
                columns={
                    "code": "symbol",
                    "代码": "symbol",
                    "name": "name",
                    "名称": "name",
                }
            )

            # 确保有必需的列
            if "symbol" not in df.columns or "name" not in df.columns:
                logger.error(f"AKShare: Unexpected column names: {df.columns.tolist()}")
                return None

            # 生成 ts_code 和其他字段
            def generate_ts_code(code: str) -> str:
                """根据股票代码生成 ts_code"""
                if not code:
                    return ""
                code = str(code).zfill(6)
                if code.startswith(("60", "68", "90")):
                    return f"{code}.SH"
                elif code.startswith(("00", "30", "20")):
                    return f"{code}.SZ"
                elif code.startswith(("8", "4")):
                    return f"{code}.BJ"
                else:
                    return f"{code}.SZ"  # 默认深圳

            def get_market(code: str) -> str:
                """根据股票代码判断市场"""
                if not code:
                    return ""
                code = str(code).zfill(6)
                if code.startswith("000"):
                    return "主板"
                elif code.startswith("002"):
                    return "中小板"
                elif code.startswith("300"):
                    return "创业板"
                elif code.startswith("60"):
                    return "主板"
                elif code.startswith("688"):
                    return "科创板"
                elif code.startswith("8"):
                    return "北交所"
                elif code.startswith("4"):
                    return "新三板"
                else:
                    return "未知"

            # 添加 ts_code 和 market 字段
            df["ts_code"] = df["symbol"].apply(generate_ts_code)
            df["market"] = df["symbol"].apply(get_market)
            df["area"] = ""
            df["industry"] = ""
            df["list_date"] = ""

            logger.info(
                f"AKShare: Successfully fetched {len(df)} stocks with real names"
            )
            return df

        except Exception as e:
            logger.error(f"AKShare: Failed to fetch stock list: {e}")
            return None

    def get_daily_basic(self, trade_date: str) -> Optional[pd.DataFrame]:
        """获取每日基础财务数据（快速版）"""
        if not self.is_available():
            return None
        try:
            import akshare as ak  # noqa: F401

            logger.info(
                f"AKShare: Attempting to get basic financial data for {trade_date}"
            )

            stock_df = self.get_stock_list()
            if stock_df is None or stock_df.empty:
                logger.warning("AKShare: No stock list available")
                return None

            max_stocks = 10
            stock_list = stock_df.head(max_stocks)

            basic_data = []
            processed_count = 0
            import time

            start_time = time.time()
            timeout_seconds = 30

            for _, stock in stock_list.iterrows():
                if time.time() - start_time > timeout_seconds:
                    logger.warning(
                        f"AKShare: Timeout reached, processed {processed_count} stocks"
                    )
                    break
                try:
                    symbol = stock.get("symbol", "")
                    name = stock.get("name", "")
                    ts_code = stock.get("ts_code", "")
                    if not symbol:
                        continue
                    info_data = ak.stock_individual_info_em(symbol=symbol)
                    if info_data is not None and not info_data.empty:
                        info_dict = {}
                        for _, row in info_data.iterrows():
                            item = row.get("item", "")
                            value = row.get("value", "")
                            info_dict[item] = value
                        latest_price = self._safe_float(info_dict.get("最新", 0))
                        # 🔥 AKShare 的"总市值"单位是万元，需要转换为亿元（与 Tushare 一致）
                        total_mv_wan = self._safe_float(
                            info_dict.get("总市值", 0)
                        )  # 万元
                        total_mv_yi = (
                            total_mv_wan / 10000 if total_mv_wan else None
                        )  # 转换为亿元
                        basic_data.append(
                            {
                                "ts_code": ts_code,
                                "trade_date": trade_date,
                                "name": name,
                                "close": latest_price,
                                "total_mv": total_mv_yi,  # 亿元（与 Tushare 一致）
                                "turnover_rate": None,
                                "pe": None,
                                "pb": None,
                            }
                        )
                        processed_count += 1
                        if processed_count % 5 == 0:
                            logger.debug(
                                f"AKShare: Processed {processed_count} stocks in {time.time() - start_time:.1f}s"
                            )
                except Exception as e:
                    logger.debug(f"AKShare: Failed to get data for {symbol}: {e}")
                    continue

            if basic_data:
                df = pd.DataFrame(basic_data)
                logger.info(
                    f"AKShare: Successfully fetched basic data for {trade_date}, {len(df)} records"
                )
                return df
            else:
                logger.warning("AKShare: No basic data collected")
                return None
        except Exception as e:
            logger.error(f"AKShare: Failed to fetch basic data for {trade_date}: {e}")
            return None

    def _safe_float(self, value) -> Optional[float]:
        try:
            if value is None or value == "" or value == "None":
                return None
            return float(value)
        except (ValueError, TypeError):
            return None

    def get_realtime_quotes(self, source: str = "eastmoney"):
        """
        获取全市场实时快照，返回以6位代码为键的字典

        Args:
            source: 数据源选择，"eastmoney"（东方财富）或 "sina"（新浪财经）

        Returns:
            Dict[str, Dict]: {code: {close, pct_chg, amount, ...}}
        """
        if not self.is_available():
            return None

        max_retries = AKSHARE_RETRY_CONFIG["max_retries"]
        initial_delay = AKSHARE_RETRY_CONFIG["initial_delay"]
        max_delay = AKSHARE_RETRY_CONFIG["max_delay"]
        backoff = AKSHARE_RETRY_CONFIG["backoff_multiplier"]

        last_exception = None
        proxy_status = get_proxy_status()
        proxy_enabled = any(v for v in proxy_status.values())

        for attempt in range(max_retries):
            attempt_start = time.time()
            try:
                import akshare as ak  # type: ignore

                if source == "sina":
                    df = ak.stock_zh_a_spot()
                    logger.debug("使用 AKShare 新浪财经接口获取实时行情")
                else:
                    df = ak.stock_zh_a_spot_em()
                    logger.debug("使用 AKShare 东方财富接口获取实时行情")

                if df is None or getattr(df, "empty", True):
                    logger.warning(f"⚠️ AKShare {source} 返回空数据")
                    if attempt < max_retries - 1:
                        delay = min(initial_delay * (backoff**attempt), max_delay)
                        logger.debug(
                            f"等待 {delay:.1f}秒后重试 ({attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                        continue
                    return None

                code_col = next(
                    (
                        c
                        for c in ["代码", "code", "symbol", "股票代码"]
                        if c in df.columns
                    ),
                    None,
                )
                price_col = next(
                    (
                        c
                        for c in [
                            "最新价",
                            "现价",
                            "最新价(元)",
                            "price",
                            "最新",
                            "trade",
                        ]
                        if c in df.columns
                    ),
                    None,
                )
                pct_col = next(
                    (
                        c
                        for c in [
                            "涨跌幅",
                            "涨跌幅(%)",
                            "涨幅",
                            "pct_chg",
                            "changepercent",
                        ]
                        if c in df.columns
                    ),
                    None,
                )
                amount_col = next(
                    (
                        c
                        for c in [
                            "成交额",
                            "成交额(元)",
                            "amount",
                            "成交额(万元)",
                            "amount(万元)",
                        ]
                        if c in df.columns
                    ),
                    None,
                )
                open_col = next(
                    (
                        c
                        for c in ["今开", "开盘", "open", "今开(元)"]
                        if c in df.columns
                    ),
                    None,
                )
                high_col = next((c for c in ["最高", "high"] if c in df.columns), None)
                low_col = next((c for c in ["最低", "low"] if c in df.columns), None)
                pre_close_col = next(
                    (
                        c
                        for c in [
                            "昨收",
                            "昨收(元)",
                            "pre_close",
                            "昨收价",
                            "settlement",
                        ]
                        if c in df.columns
                    ),
                    None,
                )
                volume_col = next(
                    (
                        c
                        for c in ["成交量", "成交量(手)", "volume", "成交量(股)", "vol"]
                        if c in df.columns
                    ),
                    None,
                )

                if not code_col or not price_col:
                    logger.error(
                        f"AKShare {source} 缺少必要列: code={code_col}, price={price_col}"
                    )
                    return None

                result: Dict[str, Dict[str, Optional[float]]] = {}
                for _, row in df.iterrows():
                    code_raw = row.get(code_col)
                    if not code_raw:
                        continue
                    code_str = str(code_raw).strip()

                    if len(code_str) > 6:
                        code_str = "".join(filter(str.isdigit, code_str))

                    if code_str.isdigit():
                        code_clean = code_str.lstrip("0") or "0"
                        code = code_clean.zfill(6)
                    else:
                        code_digits = "".join(filter(str.isdigit, code_str))
                        if code_digits:
                            code = code_digits.zfill(6)
                        else:
                            continue

                    close = self._safe_float(row.get(price_col))
                    pct = self._safe_float(row.get(pct_col)) if pct_col else None
                    amt = self._safe_float(row.get(amount_col)) if amount_col else None
                    op = self._safe_float(row.get(open_col)) if open_col else None
                    hi = self._safe_float(row.get(high_col)) if high_col else None
                    lo = self._safe_float(row.get(low_col)) if low_col else None
                    pre = (
                        self._safe_float(row.get(pre_close_col))
                        if pre_close_col
                        else None
                    )
                    vol = self._safe_float(row.get(volume_col)) if volume_col else None

                    if vol is not None:
                        if volume_col and (
                            "手" in volume_col
                            or volume_col in ["成交量", "volume", "vol"]
                        ):
                            vol = vol * 100

                    if code in ["300750", "000001", "600000"]:
                        logger.debug(f"📊 [AKShare实时] {code} - vol={vol}, amt={amt}")

                    result[code] = {
                        "close": close,
                        "pct_chg": pct,
                        "amount": amt,
                        "volume": vol,
                        "open": op,
                        "high": hi,
                        "low": lo,
                        "pre_close": pre,
                    }

                duration = time.time() - attempt_start
                logger.info(
                    f"✅ AKShare {source} 获取到 {len(result)} 只股票 ({duration:.2f}s)"
                )
                return result

            except Exception as e:
                last_exception = e
                duration = time.time() - attempt_start

                error_type = type(e).__name__
                is_network_error = any(
                    x in str(e).lower()
                    for x in ["connection", "remote", "timeout", "aborted", "reset"]
                )

                logger.warning(
                    f"⚠️ AKShare {source} 请求失败 ({attempt + 1}/{max_retries}): "
                    f"error_type={error_type}, duration={duration:.2f}s, error={str(e)[:100]}"
                )

                if attempt < max_retries - 1:
                    delay = min(initial_delay * (backoff**attempt), max_delay)
                    logger.debug(f"等待 {delay:.1f}秒后重试...")
                    time.sleep(delay)

        logger.error(
            f"❌ AKShare {source} 获取失败，已达最大重试次数: "
            f"proxy_enabled={proxy_enabled}, error_type={type(last_exception).__name__}, "
            f"error={str(last_exception)[:200]}"
        )
        return None

    def get_daily_quotes(self, trade_date: str) -> Optional[Dict[str, Dict[str, Optional[float]]]]:
        """获取指定日期的全市场行情快照
        AKShare 获取指定日期全市场数据效率极低，暂不支持
        """
        logger.warning("AKShare does not efficiently support full-market daily quotes backfill")
        return None

    def get_kline(
        self,
        code: str,
        period: str = "day",
        limit: int = 120,
        adj: Optional[str] = None,
    ):
        """AKShare K-line as fallback. Try daily/week/month via stock_zh_a_hist; minutes via stock_zh_a_minute."""
        if not self.is_available():
            return None
        try:
            import akshare as ak

            code6 = str(code).zfill(6)
            items = []
            if period in ("day", "week", "month"):
                period_map = {"day": "daily", "week": "weekly", "month": "monthly"}
                adjust_map = {None: "", "qfq": "qfq", "hfq": "hfq"}
                df = ak.stock_zh_a_hist(
                    symbol=code6,
                    period=period_map[period],
                    adjust=adjust_map.get(adj, ""),
                )
                if df is None or getattr(df, "empty", True):
                    return None
                df = df.tail(limit)
                for _, row in df.iterrows():
                    items.append(
                        {
                            "time": str(row.get("日期") or row.get("date") or ""),
                            "open": self._safe_float(
                                row.get("开盘") or row.get("open")
                            ),
                            "high": self._safe_float(
                                row.get("最高") or row.get("high")
                            ),
                            "low": self._safe_float(row.get("最低") or row.get("low")),
                            "close": self._safe_float(
                                row.get("收盘") or row.get("close")
                            ),
                            # 🔥 成交量单位转换：AKShare 返回的是手，需要转换为股
                            "volume": self._convert_volume(
                                row.get("成交量") or row.get("volume")
                            ),
                            "amount": self._safe_float(
                                row.get("成交额") or row.get("amount")
                            ),
                        }
                    )
                return items
            else:
                # minutes
                per_map = {"5m": "5", "15m": "15", "30m": "30", "60m": "60"}
                if period not in per_map:
                    return None
                df = ak.stock_zh_a_minute(
                    symbol=code6,
                    period=per_map[period],
                    adjust=adj if adj in ("qfq", "hfq") else "",
                )
                if df is None or getattr(df, "empty", True):
                    return None
                df = df.tail(limit)
                for _, row in df.iterrows():
                    items.append(
                        {
                            "time": str(row.get("时间") or row.get("day") or ""),
                            "open": self._safe_float(
                                row.get("开盘") or row.get("open")
                            ),
                            "high": self._safe_float(
                                row.get("最高") or row.get("high")
                            ),
                            "low": self._safe_float(row.get("最低") or row.get("low")),
                            "close": self._safe_float(
                                row.get("收盘") or row.get("close")
                            ),
                            # 🔥 成交量单位转换：AKShare 返回的是手，需要转换为股
                            "volume": self._convert_volume(
                                row.get("成交量") or row.get("volume")
                            ),
                            "amount": self._safe_float(
                                row.get("成交额") or row.get("amount")
                            ),
                        }
                    )
                return items
        except Exception as e:
            logger.error(f"AKShare get_kline failed: {e}")
            return None

    def get_news(
        self,
        code: str,
        days: int = 2,
        limit: int = 50,
        include_announcements: bool = True,
    ):
        """AKShare-based news/announcements fallback"""
        if not self.is_available():
            return None
        try:
            import akshare as ak

            code6 = str(code).zfill(6)
            items = []
            # news
            try:
                dfn = ak.stock_news_em(symbol=code6)
                if dfn is not None and not dfn.empty:
                    for _, row in dfn.head(limit).iterrows():
                        items.append(
                            {
                                # AkShare 将字段标准化为中文列名：新闻标题 / 文章来源 / 发布时间 / 新闻链接
                                "title": str(
                                    row.get("新闻标题")
                                    or row.get("标题")
                                    or row.get("title")
                                    or ""
                                ),
                                "source": str(
                                    row.get("文章来源")
                                    or row.get("来源")
                                    or row.get("source")
                                    or "akshare"
                                ),
                                "time": str(
                                    row.get("发布时间") or row.get("time") or ""
                                ),
                                "url": str(row.get("新闻链接") or row.get("url") or ""),
                                "type": "news",
                            }
                        )
            except Exception:
                pass
            # announcements
            try:
                if include_announcements:
                    dfa = ak.stock_announcement_em(symbol=code6)
                    if dfa is not None and not dfa.empty:
                        for _, row in dfa.head(max(0, limit - len(items))).iterrows():
                            items.append(
                                {
                                    "title": str(
                                        row.get("公告标题") or row.get("title") or ""
                                    ),
                                    "source": "akshare",
                                    "time": str(
                                        row.get("公告时间") or row.get("time") or ""
                                    ),
                                    "url": str(
                                        row.get("公告链接") or row.get("url") or ""
                                    ),
                                    "type": "announcement",
                                }
                            )
            except Exception:
                pass
            return items if items else None
        except Exception as e:
            logger.error(f"AKShare get_news failed: {e}")
            return None

    def find_latest_trade_date(self) -> Optional[str]:
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        logger.info(f"AKShare: Using yesterday as trade date: {yesterday}")
        return yesterday
