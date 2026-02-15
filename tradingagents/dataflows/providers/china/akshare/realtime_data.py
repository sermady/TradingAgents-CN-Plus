# -*- coding: utf-8 -*-
"""
AKShare实时数据模块

包含实时行情数据获取功能
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class RealtimeDataMixin:
    """实时数据功能混入类"""

    async def get_batch_stock_quotes(
        self, codes: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        批量获取股票实时行情（优化版：一次获取全市场快照）

        优先使用新浪财经接口（更稳定），失败时回退到东方财富接口
        支持指数退避重试和详细错误日志

        Args:
            codes: 股票代码列表

        Returns:
            股票代码到行情数据的映射字典
        """
        if not self.connected or self.ak is None:
            return {}

        max_retries = 3
        initial_delay = 1.0
        max_delay = 10.0
        backoff_multiplier = 2.0

        import os

        proxy_status = {
            "http_proxy": os.environ.get("HTTP_PROXY") or "",
            "https_proxy": os.environ.get("HTTPS_PROXY") or "",
        }
        proxy_enabled = any(v for v in proxy_status.values())

        last_exception = None

        for attempt in range(max_retries):
            attempt_start = (
                asyncio.get_event_loop().time()
                if hasattr(asyncio.get_event_loop(), "time")
                else 0
            )
            try:
                logger.debug(
                    f"📊 批量获取 {len(codes)} 只股票的实时行情... (尝试 {attempt + 1}/{max_retries})"
                )

                def fetch_spot_data_sina():
                    import time

                    time.sleep(0.3)
                    return self.ak.stock_zh_a_spot()

                def fetch_spot_data_em():
                    import time

                    time.sleep(0.5)
                    return self.ak.stock_zh_a_spot_em()

                spot_df = None
                data_source = None

                try:
                    spot_df = await asyncio.to_thread(fetch_spot_data_sina)
                    data_source = "sina"
                    logger.debug("✅ 使用新浪财经接口获取数据")
                except Exception as e:
                    logger.warning(f"⚠️ 新浪财经接口失败: {e}，尝试东方财富接口...")
                    try:
                        spot_df = await asyncio.to_thread(fetch_spot_data_em)
                        data_source = "eastmoney"
                        logger.debug("✅ 使用东方财富接口获取数据")
                    except Exception as e2:
                        raise ConnectionError(f"Sina failed: {e}, EM failed: {e2}")

                if spot_df is None or getattr(spot_df, "empty", True):
                    logger.warning("⚠️ 全市场快照为空")
                    if attempt < max_retries - 1:
                        delay = min(
                            initial_delay * (backoff_multiplier**attempt), max_delay
                        )
                        logger.debug(f"等待 {delay:.1f}秒后重试...")
                        await asyncio.sleep(delay)
                        continue
                    return {}

                quotes_map = {}
                codes_set = set(codes)

                code_mapping = {}
                for code in codes:
                    code_mapping[code] = code
                    for prefix in ["sh", "sz", "bj"]:
                        code_mapping[f"{prefix}{code}"] = code

                for _, row in spot_df.iterrows():
                    raw_code = str(row.get("代码", ""))

                    matched_code = None
                    if raw_code in code_mapping:
                        matched_code = code_mapping[raw_code]
                    elif raw_code in codes_set:
                        matched_code = raw_code

                    if matched_code:
                        quotes_data = {
                            "name": str(row.get("名称", f"股票{matched_code}")),
                            "price": self._safe_float(row.get("最新价", 0)),
                            "change": self._safe_float(row.get("涨跌额", 0)),
                            "change_percent": self._safe_float(row.get("涨跌幅", 0)),
                            "volume": self._safe_int(row.get("成交量", 0)),
                            "amount": self._safe_float(row.get("成交额", 0)),
                            "open": self._safe_float(row.get("今开", 0)),
                            "high": self._safe_float(row.get("最高", 0)),
                            "low": self._safe_float(row.get("最低", 0)),
                            "pre_close": self._safe_float(row.get("昨收", 0)),
                            # 新增：财务指标字段
                            "turnover_rate": self._safe_float(
                                row.get("换手率", None)
                            ),  # 换手率（%）
                            "volume_ratio": self._safe_float(
                                row.get("量比", None)
                            ),  # 量比
                            "pe": self._safe_float(
                                row.get("市盈率-动态", None)
                            ),  # 动态市盈率
                            "pb": self._safe_float(row.get("市净率", None)),  # 市净率
                            "total_mv": self._safe_float(
                                row.get("总市值", None)
                            ),  # 总市值（元）
                            "circ_mv": self._safe_float(
                                row.get("流通市值", None)
                            ),  # 流通市值（元）
                        }

                        # 转换为标准化字典（使用匹配后的代码）
                        quotes_map[matched_code] = {
                            "code": matched_code,
                            "symbol": matched_code,
                            "name": quotes_data.get("name", f"股票{matched_code}"),
                            "price": float(quotes_data.get("price", 0)),
                            "change": float(quotes_data.get("change", 0)),
                            "change_percent": float(
                                quotes_data.get("change_percent", 0)
                            ),
                            "volume": int(quotes_data.get("volume", 0)),
                            "amount": float(quotes_data.get("amount", 0)),
                            "open_price": float(quotes_data.get("open", 0)),
                            "high_price": float(quotes_data.get("high", 0)),
                            "low_price": float(quotes_data.get("low", 0)),
                            "pre_close": float(quotes_data.get("pre_close", 0)),
                            # 新增：财务指标字段
                            "turnover_rate": quotes_data.get(
                                "turnover_rate"
                            ),  # 换手率（%）
                            "volume_ratio": quotes_data.get("volume_ratio"),  # 量比
                            "pe": quotes_data.get("pe"),  # 动态市盈率
                            "pe_ttm": quotes_data.get(
                                "pe"
                            ),  # TTM市盈率（与动态市盈率相同）
                            "pb": quotes_data.get("pb"),  # 市净率
                            "total_mv": quotes_data.get("total_mv") / 1e8
                            if quotes_data.get("total_mv")
                            else None,  # 总市值（转换为亿元）
                            "circ_mv": quotes_data.get("circ_mv") / 1e8
                            if quotes_data.get("circ_mv")
                            else None,  # 流通市值（转换为亿元）
                            # 扩展字段
                            "full_symbol": self._get_full_symbol(matched_code),
                            "market_info": self._get_market_info(matched_code),
                            "data_source": "akshare",
                            "last_sync": datetime.now(timezone.utc),
                            "sync_status": "success",
                        }

                found_count = len(quotes_map)
                missing_count = len(codes) - found_count
                logger.debug(
                    f"✅ 批量获取完成: 找到 {found_count} 只, 未找到 {missing_count} 只"
                )

                # 记录未找到的股票
                if missing_count > 0:
                    missing_codes = codes_set - set(quotes_map.keys())
                    if missing_count <= 10:
                        logger.debug(f"⚠️ 未找到行情的股票: {list(missing_codes)}")
                    else:
                        logger.debug(
                            f"⚠️ 未找到行情的股票: {list(missing_codes)[:10]}... (共{missing_count}只)"
                        )

                return quotes_map

            except Exception as e:
                last_exception = e
                error_type = type(e).__name__
                is_network_error = any(
                    x in str(e).lower()
                    for x in [
                        "connection",
                        "remote",
                        "timeout",
                        "aborted",
                        "reset",
                        "closed",
                    ]
                )

                if attempt < max_retries - 1:
                    delay = min(
                        initial_delay * (backoff_multiplier**attempt), max_delay
                    )
                    logger.warning(
                        f"⚠️ 批量获取实时行情失败 ({attempt + 1}/{max_retries}): "
                        f"error_type={error_type}, network={is_network_error}, 等待{delay:.1f}秒后重试..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"❌ 批量获取实时行情失败，已达最大重试次数: "
                        f"proxy_enabled={proxy_enabled}, error_type={error_type}, error={str(e)[:200]}"
                    )
                    return {}

        # 如果循环结束仍未返回，返回空字典
        return {}

    async def get_stock_quotes(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取单个股票实时行情

        策略：使用 stock_bid_ask_em 接口获取单个股票的实时行情报价
        - 优点：只获取单个股票数据，速度快，不浪费资源
        - 适用场景：手动同步单个股票

        Args:
            code: 股票代码

        Returns:
            标准化的行情数据
        """
        if not self.connected or self.ak is None:
            return None

        try:
            logger.info(f"📈 使用 stock_bid_ask_em 接口获取 {code} 实时行情...")

            # 使用 stock_bid_ask_em 接口获取单个股票实时行情
            def fetch_bid_ask():
                return self.ak.stock_bid_ask_em(symbol=code)

            bid_ask_df = await asyncio.to_thread(fetch_bid_ask)

            # 打印原始返回数据
            logger.info(f"📊 stock_bid_ask_em 返回数据类型: {type(bid_ask_df)}")
            if bid_ask_df is not None:
                logger.info(f"📊 DataFrame shape: {bid_ask_df.shape}")
                logger.info(f"📊 DataFrame columns: {list(bid_ask_df.columns)}")
                logger.info(f"📊 DataFrame 完整数据:\n{bid_ask_df.to_string()}")

            if bid_ask_df is None or bid_ask_df.empty:
                logger.warning(f"⚠️ 未找到{code}的行情数据")
                return None

            # 将 DataFrame 转换为字典
            data_dict = dict(zip(bid_ask_df["item"], bid_ask_df["value"]))
            logger.info(f"📊 转换后的字典: {data_dict}")

            # 获取当前日期（UTC+8）
            cn_tz = timezone(timedelta(hours=8))
            now_cn = datetime.now(cn_tz)
            trade_date = now_cn.strftime("%Y-%m-%d")  # 格式：2025-11-05

            # 成交量单位：直接使用原始单位"手"（AKShare返回的是手）
            volume_in_lots = int(data_dict.get("总手", 0))  # 单位：手

            quotes = {
                "code": code,
                "symbol": code,
                "name": f"股票{code}",  # stock_bid_ask_em 不返回股票名称
                "price": float(data_dict.get("最新", 0)),
                "close": float(
                    data_dict.get("最新", 0)
                ),  # close 字段（与 price 相同）
                "current_price": float(
                    data_dict.get("最新", 0)
                ),  # current_price 字段（兼容旧数据）
                "change": float(data_dict.get("涨跌", 0)),
                "change_percent": float(data_dict.get("涨幅", 0)),
                "pct_chg": float(
                    data_dict.get("涨幅", 0)
                ),  # pct_chg 字段（兼容旧数据）
                "volume": volume_in_lots,  # 单位：手（直接使用原始单位）
                "volume_unit": "lots",  # 明确标注单位为手
                "amount": float(data_dict.get("金额", 0)),  # 单位：元
                "open": float(
                    data_dict.get("今开", 0)
                ),  # 使用 open 而不是 open_price
                "high": float(
                    data_dict.get("最高", 0)
                ),  # 使用 high 而不是 high_price
                "low": float(data_dict.get("最低", 0)),  # 使用 low 而不是 low_price
                "pre_close": float(data_dict.get("昨收", 0)),
                # 新增：财务指标字段
                "turnover_rate": float(data_dict.get("换手", 0)),  # 换手率（%）
                "volume_ratio": float(data_dict.get("量比", 0)),  # 量比
                "pe": None,  # stock_bid_ask_em 不返回市盈率
                "pe_ttm": None,
                "pb": None,  # stock_bid_ask_em 不返回市净率
                "total_mv": None,  # stock_bid_ask_em 不返回总市值
                "circ_mv": None,  # stock_bid_ask_em 不返回流通市值
                # 新增：交易日期和更新时间
                "trade_date": trade_date,  # 交易日期（格式：2025-11-05）
                "updated_at": now_cn.isoformat(),  # 更新时间（ISO格式，带时区）
                # 扩展字段
                "full_symbol": self._get_full_symbol(code),
                "market_info": self._get_market_info(code),
                "data_source": "akshare",
                "last_sync": datetime.now(timezone.utc),
                "sync_status": "success",
            }

            logger.info(
                f"✅ {code} 实时行情获取成功: 最新价={quotes['price']}, 涨跌幅={quotes['change_percent']}%, 成交量={quotes['volume']}, 成交额={quotes['amount']}"
            )

            from .cache_manager import _set_akshare_cached_quote_async

            await _set_akshare_cached_quote_async(code, quotes)
            return quotes

        except Exception as e:
            logger.error(f"❌ 获取{code}实时行情失败: {e}", exc_info=True)
            return None

    async def get_stock_quotes_cached(
        self, code: str, force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        获取单个股票实时行情（带缓存）

        Args:
            code: 股票代码
            force_refresh: 是否强制刷新缓存

        Returns:
            标准化的行情数据
        """
        if not force_refresh:
            from .cache_manager import _get_akshare_cached_quote_async

            cached = await _get_akshare_cached_quote_async(code)
            if cached is not None:
                logger.debug(f"[Cache] 使用AKShare缓存: {code}")
                return cached

        result = await self.get_stock_quotes(code)
        if result is not None:
            from .cache_manager import _set_akshare_cached_quote_async

            await _set_akshare_cached_quote_async(code, result)
        return result

    async def _get_realtime_quotes_data(self, code: str) -> Dict[str, Any]:
        """获取实时行情数据"""
        if self.ak is None:
            return {}

        try:
            # 方法1: 获取A股实时行情
            def fetch_spot_data():
                return self.ak.stock_zh_a_spot_em()

            try:
                spot_df = await asyncio.to_thread(fetch_spot_data)

                if spot_df is not None and not spot_df.empty:
                    # 查找对应股票
                    stock_data = spot_df[spot_df["代码"] == code]

                    if not stock_data.empty:
                        row = stock_data.iloc[0]

                        # 解析行情数据
                        return {
                            "name": str(row.get("名称", f"股票{code}")),
                            "price": self._safe_float(row.get("最新价", 0)),
                            "change": self._safe_float(row.get("涨跌额", 0)),
                            "change_percent": self._safe_float(row.get("涨跌幅", 0)),
                            "volume": self._safe_int(row.get("成交量", 0)),
                            "amount": self._safe_float(row.get("成交额", 0)),
                            "open": self._safe_float(row.get("今开", 0)),
                            "high": self._safe_float(row.get("最高", 0)),
                            "low": self._safe_float(row.get("最低", 0)),
                            "pre_close": self._safe_float(row.get("昨收", 0)),
                            # 新增：财务指标字段
                            "turnover_rate": self._safe_float(
                                row.get("换手率", None)
                            ),  # 换手率（%）
                            "volume_ratio": self._safe_float(
                                row.get("量比", None)
                            ),  # 量比
                            "pe": self._safe_float(
                                row.get("市盈率-动态", None)
                            ),  # 动态市盈率
                            "pb": self._safe_float(row.get("市净率", None)),  # 市净率
                            "total_mv": self._safe_float(
                                row.get("总市值", None)
                            ),  # 总市值（元）
                            "circ_mv": self._safe_float(
                                row.get("流通市值", None)
                            ),  # 流通市值（元）
                        }
            except Exception as e:
                logger.debug(f"获取{code}A股实时行情失败: {e}")

            # 方法2: 尝试获取单只股票实时数据
            def fetch_individual_spot():
                return self.ak.stock_zh_a_hist(
                    symbol=code, period="daily", adjust="qfq"
                )  # 前复权

            try:
                hist_df = await asyncio.to_thread(fetch_individual_spot)
                if hist_df is not None and not hist_df.empty:
                    # 取最新一天的数据作为当前行情
                    latest_row = hist_df.iloc[-1]
                    return {
                        "name": f"股票{code}",
                        "price": self._safe_float(latest_row.get("收盘", 0)),
                        "change": 0,  # 历史数据无法计算涨跌额
                        "change_percent": self._safe_float(latest_row.get("涨跌幅", 0)),
                        "volume": self._safe_int(latest_row.get("成交量", 0)),
                        "amount": self._safe_float(latest_row.get("成交额", 0)),
                        "open": self._safe_float(latest_row.get("开盘", 0)),
                        "high": self._safe_float(latest_row.get("最高", 0)),
                        "low": self._safe_float(latest_row.get("最低", 0)),
                        "pre_close": self._safe_float(latest_row.get("收盘", 0)),
                    }
            except Exception as e:
                logger.debug(f"获取{code}历史数据作为行情失败: {e}")

            return {}

        except Exception as e:
            logger.debug(f"获取{code}实时行情数据失败: {e}")
            return {}
