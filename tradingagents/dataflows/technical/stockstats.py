# -*- coding: utf-8 -*-
import pandas as pd
from stockstats import wrap
from typing import Annotated, Optional
import os
import logging

from tradingagents.config.config_manager import config_manager

logger = logging.getLogger(__name__)


def get_config():
    """兼容性包装函数"""
    return config_manager.load_settings()


def _is_china_stock(symbol: str) -> bool:
    """判断是否为A股股票"""
    if not symbol:
        return False
    # 纯数字且长度为6位，通常是A股
    clean_symbol = symbol.replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
    if clean_symbol.isdigit() and len(clean_symbol) == 6:
        return True
    # 带有中国交易所后缀
    if any(suffix in symbol.upper() for suffix in [".SH", ".SZ", ".BJ", ".SS"]):
        return True
    return False


def _get_china_stock_data(
    symbol: str, start_date: str, end_date: str
) -> Optional[pd.DataFrame]:
    """
    获取A股股票数据
    优先使用AKShare，失败则降级到BaoStock
    """
    clean_symbol = (
        symbol.replace(".SH", "")
        .replace(".SZ", "")
        .replace(".BJ", "")
        .replace(".SS", "")
        .zfill(6)
    )

    # 方法1: 尝试使用AKShare
    try:
        import akshare as ak

        logger.debug(f"📊 [技术指标] 使用AKShare获取A股数据: {clean_symbol}")

        # 格式化日期
        start_fmt = start_date.replace("-", "")
        end_fmt = end_date.replace("-", "")

        data = ak.stock_zh_a_hist(
            symbol=clean_symbol,
            period="daily",
            start_date=start_fmt,
            end_date=end_fmt,
            adjust="qfq",  # 前复权
        )

        if data is not None and not data.empty:
            # 标准化列名以适配stockstats
            data = data.rename(
                columns={
                    "日期": "Date",
                    "开盘": "Open",
                    "收盘": "Close",
                    "最高": "High",
                    "最低": "Low",
                    "成交量": "Volume",
                    "成交额": "Amount",
                }
            )
            data["Date"] = pd.to_datetime(data["Date"])
            logger.info(
                f"✅ [技术指标] AKShare数据获取成功: {clean_symbol}, {len(data)}条记录"
            )
            return data
    except Exception as e:
        logger.warning(f"⚠️ [技术指标] AKShare获取失败: {e}")

    # 方法2: 降级到BaoStock
    try:
        import baostock as bs

        logger.debug(f"📊 [技术指标] 降级使用BaoStock获取A股数据: {clean_symbol}")

        # 确定交易所前缀
        if clean_symbol.startswith(("6", "9")):
            bs_code = f"sh.{clean_symbol}"
        else:
            bs_code = f"sz.{clean_symbol}"

        lg = bs.login()
        if lg.error_code != "0":
            logger.error(f"❌ BaoStock登录失败: {lg.error_msg}")
            return None

        try:
            rs = bs.query_history_k_data_plus(
                code=bs_code,
                fields="date,open,high,low,close,volume,amount",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="2",  # 前复权
            )

            if rs.error_code != "0":
                logger.error(f"❌ BaoStock查询失败: {rs.error_msg}")
                return None

            data_list = []
            while (rs.error_code == "0") and rs.next():
                data_list.append(rs.get_row_data())

            if not data_list:
                return None

            data = pd.DataFrame(
                data_list,
                columns=["Date", "Open", "High", "Low", "Close", "Volume", "Amount"],
            )

            # 转换数据类型
            for col in ["Open", "High", "Low", "Close", "Volume", "Amount"]:
                data[col] = pd.to_numeric(data[col], errors="coerce")
            data["Date"] = pd.to_datetime(data["Date"])

            logger.info(
                f"✅ [技术指标] BaoStock数据获取成功: {clean_symbol}, {len(data)}条记录"
            )
            return data

        finally:
            bs.logout()

    except Exception as e:
        logger.warning(f"⚠️ [技术指标] BaoStock获取失败: {e}")

    return None


def _get_us_stock_data(
    symbol: str, start_date: str, end_date: str
) -> Optional[pd.DataFrame]:
    """获取美股数据"""
    try:
        import yfinance as yf

        logger.debug(f"📊 [技术指标] 使用yfinance获取美股数据: {symbol}")

        data = yf.download(
            symbol,
            start=start_date,
            end=end_date,
            multi_level_index=False,
            progress=False,
            auto_adjust=True,
        )

        if data is not None and not data.empty:
            data = data.reset_index()
            logger.info(
                f"✅ [技术指标] yfinance数据获取成功: {symbol}, {len(data)}条记录"
            )
            return data
    except Exception as e:
        logger.warning(f"⚠️ [技术指标] yfinance获取失败: {e}")

    return None


class StockstatsUtils:
    @staticmethod
    def get_stock_stats(
        symbol: Annotated[str, "ticker symbol for the company"],
        indicator: Annotated[
            str, "quantitative indicators based off of the stock data for the company"
        ],
        curr_date: Annotated[
            str, "curr date for retrieving stock price data, YYYY-mm-dd"
        ],
        data_dir: Annotated[
            str,
            "directory where the stock data is stored.",
        ],
        online: Annotated[
            bool,
            "whether to use online tools to fetch data or offline tools. If True, will use online tools.",
        ] = False,
    ):
        df = None
        data = None

        # 判断股票类型
        is_china = _is_china_stock(symbol)

        if not online:
            # 离线模式：尝试从本地文件读取
            try:
                # 尝试多种文件名格式
                possible_files = [
                    f"{symbol}-YFin-data-2015-01-01-2025-03-25.csv",
                    f"{symbol}-data.csv",
                    f"{symbol}.csv",
                ]

                data = None
                for filename in possible_files:
                    filepath = os.path.join(data_dir, filename)
                    if os.path.exists(filepath):
                        data = pd.read_csv(filepath)
                        logger.debug(f"📁 [技术指标] 从文件加载数据: {filepath}")
                        break

                if data is None:
                    # 如果是A股，尝试在线获取
                    if is_china:
                        logger.warning(
                            f"⚠️ [技术指标] 本地文件不存在，尝试在线获取A股数据: {symbol}"
                        )
                        online = True  # 强制切换到在线模式
                    else:
                        raise FileNotFoundError(f"找不到股票数据文件: {symbol}")
                else:
                    df = wrap(data)

            except FileNotFoundError as e:
                if is_china:
                    logger.warning(f"⚠️ [技术指标] {e}，尝试在线获取")
                    online = True
                else:
                    raise Exception(f"Stockstats fail: 股票数据文件不存在 - {symbol}")

        if online:
            # 在线模式：根据股票类型选择数据源
            today_date = pd.Timestamp.today()
            curr_date_dt = pd.to_datetime(curr_date)

            end_date = today_date
            start_date = today_date - pd.DateOffset(years=2)  # A股通常2年数据足够
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")

            # 获取配置并确保缓存目录存在
            config = get_config()
            cache_dir = config.get("data_cache_dir", "data/cache")
            os.makedirs(cache_dir, exist_ok=True)

            # 生成缓存文件名
            market_tag = "CN" if is_china else "US"
            data_file = os.path.join(
                cache_dir,
                f"{symbol}-{market_tag}-data-{start_date_str}-{end_date_str}.csv",
            )

            # 检查缓存
            if os.path.exists(data_file):
                try:
                    data = pd.read_csv(data_file)
                    data["Date"] = pd.to_datetime(data["Date"])
                    logger.debug(f"📁 [技术指标] 从缓存加载: {data_file}")
                except Exception as e:
                    logger.warning(f"⚠️ [技术指标] 缓存文件读取失败: {e}")
                    data = None

            # 如果缓存不存在或读取失败，从网络获取
            if data is None:
                if is_china:
                    data = _get_china_stock_data(symbol, start_date_str, end_date_str)
                else:
                    data = _get_us_stock_data(symbol, start_date_str, end_date_str)

                # 保存到缓存
                if data is not None and not data.empty:
                    try:
                        data.to_csv(data_file, index=False)
                        logger.debug(f"💾 [技术指标] 数据已缓存: {data_file}")
                    except Exception as e:
                        logger.warning(f"⚠️ [技术指标] 缓存保存失败: {e}")

            if data is None or data.empty:
                return f"N/A: 无法获取 {symbol} 的股票数据"

            df = wrap(data)
            df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
            curr_date = curr_date_dt.strftime("%Y-%m-%d")

        # 计算技术指标 - 确保 df 已被赋值
        assert df is not None, "df should be initialized at this point"

        try:
            _ = df[indicator]  # trigger stockstats to calculate the indicator
        except Exception as e:
            logger.error(f"❌ [技术指标] 计算失败 {indicator}: {e}")
            return f"N/A: 无法计算指标 {indicator}"

        # 查找匹配日期的数据
        matching_rows = df[df["Date"].str.startswith(curr_date)]

        if not matching_rows.empty:
            indicator_value = matching_rows[indicator].values[0]
            return indicator_value
        else:
            return "N/A: Not a trading day (weekend or holiday)"
