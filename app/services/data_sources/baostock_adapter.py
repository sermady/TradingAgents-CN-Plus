# -*- coding: utf-8 -*-
"""
BaoStock data source adapter
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

import pandas as pd

from .base import DataSourceAdapter

logger = logging.getLogger(__name__)


class BaoStockAdapter(DataSourceAdapter):
    """BaoStock data source adapter"""

    def __init__(self):
        super().__init__()  # 调用父类初始化

    @property
    def name(self) -> str:
        return "baostock"

    def _get_default_priority(self) -> int:
        return 1  # lowest priority (数字越大优先级越高)

    def is_available(self) -> bool:
        return self._check_import_available("baostock")

    def get_stock_list(self) -> Optional[pd.DataFrame]:
        if not self.is_available():
            return None
        try:
            import baostock as bs

            lg = bs.login()
            if lg.error_code != "0":
                logger.error(f"BaoStock: Login failed: {lg.error_msg}")
                return None
            try:
                logger.info("BaoStock: Querying stock basic info...")
                rs = bs.query_stock_basic()
                if rs.error_code != "0":
                    logger.error(f"BaoStock: Query failed: {rs.error_msg}")
                    return None
                data_list = []
                while (rs.error_code == "0") & rs.next():
                    data_list.append(rs.get_row_data())
                if not data_list:
                    return None
                df = pd.DataFrame(data_list, columns=rs.fields)
                df = df[df["type"] == "1"]
                df["symbol"] = df["code"].str.replace(r"^(sh|sz)\.", "", regex=True)
                df["ts_code"] = df["code"].str.replace("sh.", "").str.replace("sz.", "") + df[
                    "code"
                ].str.extract(r"^(sh|sz)\.").iloc[:, 0].str.upper().str.replace(
                    "SH", ".SH"
                ).str.replace(
                    "SZ", ".SZ"
                )
                df["name"] = df["code_name"]
                df["area"] = ""

                # 获取行业信息
                logger.info("BaoStock: Querying stock industry info...")
                industry_rs = bs.query_stock_industry()
                if industry_rs.error_code == "0":
                    industry_list = []
                    while (industry_rs.error_code == "0") & industry_rs.next():
                        industry_list.append(industry_rs.get_row_data())
                    if industry_list:
                        industry_df = pd.DataFrame(industry_list, columns=industry_rs.fields)

                        # 去掉行业编码前缀（如 "I65软件和信息技术服务业" -> "软件和信息技术服务业"）
                        def clean_industry_name(industry_str):
                            if not industry_str or pd.isna(industry_str):
                                return ""
                            # 使用正则表达式去掉前面的字母和数字编码（如 I65、C31 等）
                            import re

                            cleaned = re.sub(r"^[A-Z]\d+", "", str(industry_str))
                            return cleaned.strip()

                        industry_df["industry_clean"] = industry_df["industry"].apply(
                            clean_industry_name
                        )

                        # 创建行业映射字典 {code: industry_clean}
                        industry_map = dict(zip(industry_df["code"], industry_df["industry_clean"]))
                        # 将行业信息合并到主DataFrame
                        df["industry"] = df["code"].map(industry_map).fillna("")
                        logger.info(
                            f"BaoStock: Successfully mapped industry info for {len(industry_map)} stocks"
                        )
                    else:
                        df["industry"] = ""
                        logger.warning("BaoStock: No industry data returned")
                else:
                    df["industry"] = ""
                    logger.warning(
                        f"BaoStock: Failed to query industry info: {industry_rs.error_msg}"
                    )

                df["market"] = "主板"
                df["list_date"] = ""
                logger.info(f"BaoStock: Successfully fetched {len(df)} stocks")
                return df[["symbol", "name", "ts_code", "area", "industry", "market", "list_date"]]
            finally:
                bs.logout()
        except Exception as e:
            logger.error(f"BaoStock: Failed to fetch stock list: {e}")
            return None

    def get_daily_basic(self, trade_date: str, max_stocks: int = None) -> Optional[pd.DataFrame]:
        """
        获取每日基础数据（包含PE、PB、总市值等）

        Args:
            trade_date: 交易日期 (YYYYMMDD)
            max_stocks: 最大处理股票数量，None表示处理所有股票
        """
        self._validate_trade_date(trade_date)  # 验证日期格式
        if not self.is_available():
            return None
        try:
            import baostock as bs

            logger.info(f"BaoStock: Attempting to get valuation data for {trade_date}")
            lg = bs.login()
            if lg.error_code != "0":
                logger.error(f"BaoStock: Login failed: {lg.error_msg}")
                return None
            try:
                logger.info("BaoStock: Querying stock basic info...")
                rs = bs.query_stock_basic()
                if rs.error_code != "0":
                    logger.error(f"BaoStock: Query stock list failed: {rs.error_msg}")
                    return None
                stock_list = []
                while (rs.error_code == "0") & rs.next():
                    stock_list.append(rs.get_row_data())
                if not stock_list:
                    logger.warning("BaoStock: No stocks found")
                    return None

                total_stocks = len(
                    [s for s in stock_list if len(s) > 5 and s[4] == "1" and s[5] == "1"]
                )
                logger.info(
                    f"[DATA] BaoStock: 找到 {total_stocks} 只活跃股票，开始处理{'全部' if max_stocks is None else f'前 {max_stocks} 只'}..."
                )

                basic_data = []
                processed_count = 0
                failed_count = 0
                for stock in stock_list:
                    if max_stocks and processed_count >= max_stocks:
                        break
                    code = stock[0] if len(stock) > 0 else ""
                    name = stock[1] if len(stock) > 1 else ""
                    stock_type = stock[4] if len(stock) > 4 else "0"
                    status = stock[5] if len(stock) > 5 else "0"
                    if stock_type == "1" and status == "1":
                        try:
                            formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"
                            # [HOT] 获取估值数据和总股本
                            rs_valuation = bs.query_history_k_data_plus(
                                code,
                                "date,code,close,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST",
                                start_date=formatted_date,
                                end_date=formatted_date,
                                frequency="d",
                                adjustflag="3",
                            )
                            if rs_valuation.error_code == "0":
                                valuation_data = []
                                while (rs_valuation.error_code == "0") & rs_valuation.next():
                                    valuation_data.append(rs_valuation.get_row_data())
                                if valuation_data:
                                    row = valuation_data[0]
                                    symbol = code.replace("sh.", "").replace("sz.", "")
                                    ts_code = (
                                        f"{symbol}.SH" if code.startswith("sh.") else f"{symbol}.SZ"
                                    )
                                    pe_ttm = self._safe_float(row[3]) if len(row) > 3 else None
                                    pb_mrq = self._safe_float(row[4]) if len(row) > 4 else None
                                    ps_ttm = self._safe_float(row[5]) if len(row) > 5 else None
                                    pcf_ttm = self._safe_float(row[6]) if len(row) > 6 else None
                                    close_price = self._safe_float(row[2]) if len(row) > 2 else None

                                    # [HOT] BaoStock 不直接提供总市值和总股本
                                    # 为了避免同步超时，这里不调用额外的 API 获取总股本
                                    # total_mv 留空，后续可以通过其他数据源补充
                                    total_mv = None

                                    basic_data.append(
                                        {
                                            "ts_code": ts_code,
                                            "trade_date": trade_date,
                                            "name": name,
                                            "pe": pe_ttm,  # [HOT] 市盈率（TTM）
                                            "pb": pb_mrq,  # [HOT] 市净率（MRQ）
                                            "ps": ps_ttm,  # 市销率
                                            "pcf": pcf_ttm,  # 市现率
                                            "close": close_price,
                                            "total_mv": total_mv,  # [WARN] BaoStock 不提供，留空
                                            "turnover_rate": None,  # [WARN] BaoStock 不提供
                                        }
                                    )
                                    processed_count += 1

                                    # [HOT] 每处理50只股票输出一次进度日志
                                    if processed_count % 50 == 0:
                                        progress_pct = (processed_count / total_stocks) * 100
                                        logger.info(
                                            f"[CHART] BaoStock 同步进度: {processed_count}/{total_stocks} ({progress_pct:.1f}%) - 最新: {name}({ts_code})"
                                        )
                                else:
                                    failed_count += 1
                            else:
                                failed_count += 1
                        except Exception as e:
                            failed_count += 1
                            if failed_count % 50 == 0:
                                logger.warning(
                                    f"[WARN] BaoStock: 已有 {failed_count} 只股票获取失败"
                                )
                            logger.debug(f"BaoStock: Failed to get valuation for {code}: {e}")
                            continue
                if basic_data:
                    df = pd.DataFrame(basic_data)
                    logger.info(
                        f"[OK] BaoStock 同步完成: 成功 {len(df)} 只，失败 {failed_count} 只，日期 {trade_date}"
                    )
                    return df
                else:
                    logger.warning(
                        f"[WARN] BaoStock: 未获取到任何估值数据（失败 {failed_count} 只）"
                    )
                    return None
            finally:
                bs.logout()
        except Exception as e:
            logger.error(f"BaoStock: Failed to fetch valuation data for {trade_date}: {e}")
            return None

    def get_realtime_quotes(self):
        """Placeholder: BaoStock does not provide full-market realtime snapshot in our adapter.
        Return None to allow fallback to higher-priority sources.
        """
        if not self.is_available():
            return None
        return None

    def get_daily_quotes(self, trade_date: str) -> Optional[Dict[str, Dict[str, Optional[float]]]]:
        """获取指定日期的全市场行情快照
        注意：Baostock 需要逐个查询，速度较慢，仅作为最后的兜底
        """
        if not self.is_available():
            return None
        try:
            import baostock as bs

            lg = bs.login()
            if lg.error_code != "0":
                return None
            try:
                # 1. Get stock list first
                rs = bs.query_stock_basic()
                if rs.error_code != "0":
                    return None

                stock_list = []
                while (rs.error_code == "0") & rs.next():
                    stock_list.append(rs.get_row_data())

                # Filter active A-shares
                stocks = [s for s in stock_list if len(s) > 5 and s[4] == "1" and s[5] == "1"]
                if not stocks:
                    return None

                result = {}
                formatted_date = f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"

                # Batch processing log
                logger.info(
                    f"Baostock: Starting daily quotes backfill for {trade_date} (approx {len(stocks)} stocks)..."
                )

                count = 0
                for stock in stocks:
                    code = stock[0]
                    if not code:
                        continue

                    # query_history_k_data_plus
                    # fields: date,code,open,high,low,close,preclose,volume,amount,pctChg
                    rs_k = bs.query_history_k_data_plus(
                        code,
                        "code,open,high,low,close,preclose,volume,amount,pctChg",
                        start_date=formatted_date,
                        end_date=formatted_date,
                        frequency="d",
                        adjustflag="3",
                    )

                    if rs_k.error_code == "0" and rs_k.next():
                        row = rs_k.get_row_data()
                        # row indices correspond to fields string split by comma
                        # 0:code, 1:open, 2:high, 3:low, 4:close, 5:preclose, 6:volume, 7:amount, 8:pctChg

                        symbol = code.replace("sh.", "").replace("sz.", "")
                        code6 = symbol.zfill(6)

                        def sf(val):
                            try:
                                if val == "" or val is None:
                                    return None
                                return float(val)
                            except:
                                return None

                        # volume in Baostock is shares (already correct? wait, check log)
                        # Baostock docs: volume unit is shares.

                        result[code6] = {
                            "open": sf(row[1]),
                            "high": sf(row[2]),
                            "low": sf(row[3]),
                            "close": sf(row[4]),
                            "pre_close": sf(row[5]),
                            "volume": sf(row[6]),
                            "amount": sf(row[7]),
                            "pct_chg": sf(row[8]),
                        }
                        count += 1
                        if count % 500 == 0:
                            logger.info(f"Baostock: Processed {count} stocks...")

                logger.info(f"Baostock: Finished backfill. Got {len(result)} records.")
                return result
            finally:
                bs.logout()
        except Exception as e:
            logger.error(f"Baostock: Failed to get daily quotes: {e}")
            return None

    def get_kline(
        self, code: str, period: str = "day", limit: int = 120, adj: Optional[str] = None
    ):
        """BaoStock not used for K-line here; return None to allow fallback"""
        if not self.is_available():
            return None
        return None

    def get_news(
        self, code: str, days: int = 2, limit: int = 50, include_announcements: bool = True
    ):
        """BaoStock does not provide news in this adapter; return None"""
        if not self.is_available():
            return None
        return None

    def find_latest_trade_date(self) -> Optional[str]:
        return self._get_yesterday_date()
