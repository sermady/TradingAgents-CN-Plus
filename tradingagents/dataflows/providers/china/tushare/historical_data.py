# -*- coding: utf-8 -*-
"""
历史行情数据模块

提供历史K线数据、每日基础数据等功能。
"""

from typing import Optional, Union
from datetime import datetime, date, timedelta
import asyncio
import pandas as pd

from .base_provider import BaseTushareProvider, ts


class HistoricalDataMixin(BaseTushareProvider):
    """历史行情数据功能混入类"""

    async def get_historical_data(
        self,
        symbol: str,
        start_date: Optional[Union[str, date]] = None,
        end_date: Optional[Union[str, date]] = None,
        period: str = "daily",
    ) -> Optional[pd.DataFrame]:
        """
        获取历史数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期 (daily/weekly/monthly)
        """
        if not self.is_available():
            return None

        try:
            ts_code = self._normalize_ts_code(symbol)

            # 格式化日期
            start_str = self._format_date(start_date)
            end_str = (
                self._format_date(end_date)
                if end_date
                else datetime.now().strftime("%Y%m%d")
            )

            # 使用 pro_bar 接口获取前复权数据（与同花顺一致）
            # 注意：Tushare 的 daily/weekly/monthly 接口不支持复权
            # 必须使用 ts.pro_bar() 函数并指定 adj='qfq' 参数

            # 周期映射
            freq_map = {"daily": "D", "weekly": "W", "monthly": "M"}
            freq = freq_map.get(period, "D")

            # 使用 ts.pro_bar() 函数获取前复权数据
            # 注意：pro_bar 是 tushare 模块的函数，不是 api 对象的方法
            # FIX: 添加异常处理，如果 pro_bar 失败也尝试备用方案
            df = None
            try:
                df = await asyncio.to_thread(
                    ts.pro_bar,
                    ts_code=ts_code,
                    api=self.api,  # 传入 api 对象
                    start_date=start_str,
                    end_date=end_str,
                    freq=freq,
                    adj="qfq",  # 前复权（与同花顺一致）
                )
            except Exception as pro_bar_e:
                self.logger.warning(
                    f"⚠️ Tushare pro_bar 调用异常: {pro_bar_e} "
                    f"symbol={symbol}, ts_code={ts_code}"
                )

            if df is None or df.empty:
                if df is None:
                    self.logger.warning(
                        f"⚠️ Tushare pro_bar 调用失败或返回 None: "
                        f"symbol={symbol}, ts_code={ts_code}, "
                        f"period={period}, start={start_str}, end={end_str}"
                    )
                else:
                    self.logger.warning(
                        f"⚠️ Tushare pro_bar 返回空数据: symbol={symbol}, ts_code={ts_code}, "
                        f"period={period}, start={start_str}, end={end_str}"
                    )

                # FIX: 尝试使用 api.daily 作为备用方案（5210积分可用）
                try:
                    self.logger.info(
                        f"🔄 [备用方案] 尝试使用 api.daily 获取数据: {ts_code}"
                    )
                    df = await asyncio.to_thread(
                        self.api.daily,
                        ts_code=ts_code,
                        start_date=start_str,
                        end_date=end_str,
                    )

                    if df is not None and not df.empty:
                        self.logger.info(
                            f"✅ [备用方案成功] api.daily 返回 {len(df)} 条记录"
                        )
                        # 注意：api.daily 返回的是非复权数据
                    else:
                        self.logger.warning(f"⚠️ [备用方案失败] api.daily 也返回空数据")
                        self.logger.warning(
                            f"💡 可能原因: "
                            f"1) 该股票在此期间无交易数据 "
                            f"2) 日期范围不正确 (当前: {start_str} 至 {end_str}) "
                            f"3) 股票代码格式错误 (当前: {ts_code}) "
                            f"4) Tushare API 限制或积分不足"
                        )
                        return None
                except Exception as daily_e:
                    self.logger.warning(
                        f"⚠️ [备用方案异常] api.daily 调用失败: {daily_e}"
                    )
                    return None

            # 数据标准化
            df = self._standardize_historical_data(df)

            self.logger.info(
                f"✅ 获取{period}历史数据: {symbol} {len(df)}条记录 (前复权 qfq)"
            )
            return df

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            self.logger.error(
                f"❌ 获取历史数据失败 symbol={symbol}, period={period}\n"
                f"   参数: ts_code={ts_code if 'ts_code' in locals() else 'N/A'}, "
                f"start={start_str if 'start_str' in locals() else 'N/A'}, "
                f"end={end_str if 'end_str' in locals() else 'N/A'}\n"
                f"   错误类型: {type(e).__name__}\n"
                f"   错误信息: {str(e)}\n"
                f"   堆栈跟踪:\n{error_details}"
            )
            return None

    async def get_daily_basic(self, trade_date: str) -> Optional[pd.DataFrame]:
        """获取每日基础财务数据"""
        if not self.is_available():
            return None

        try:
            date_str = trade_date.replace("-", "")
            df = await asyncio.to_thread(
                self.api.daily_basic,
                trade_date=date_str,
                fields="ts_code,total_mv,circ_mv,pe,pb,ps,turnover_rate,volume_ratio,pe_ttm,pb_mrq,ps_ttm,"
                "dv_ratio,dv_ttm,total_share,float_share",
            )

            if df is not None and not df.empty:
                self.logger.info(f"✅ 获取每日基础数据: {trade_date} {len(df)}条记录")
                return df

            return None

        except Exception as e:
            self.logger.error(f"❌ 获取每日基础数据失败 trade_date={trade_date}: {e}")
            return None

    async def find_latest_trade_date(self) -> Optional[str]:
        """查找最新交易日期"""
        if not self.is_available():
            return None

        try:
            today = datetime.now()
            for delta in range(0, 10):  # 最多回溯10天
                check_date = (today - timedelta(days=delta)).strftime("%Y%m%d")

                try:
                    df = await asyncio.to_thread(
                        self.api.daily_basic,
                        trade_date=check_date,
                        fields="ts_code",
                        limit=1,
                    )

                    if df is not None and not df.empty:
                        formatted_date = (
                            f"{check_date[:4]}-{check_date[4:6]}-{check_date[6:8]}"
                        )
                        self.logger.info(f"✅ 找到最新交易日期: {formatted_date}")
                        return formatted_date

                except Exception:
                    continue

            return None

        except Exception as e:
            self.logger.error(f"❌ 查找最新交易日期失败: {e}")
            return None

    def _format_date(self, date_value: Union[str, date]) -> str:
        """格式化日期为Tushare格式 (YYYYMMDD)"""
        if isinstance(date_value, str):
            return date_value.replace("-", "")
        elif isinstance(date_value, date):
            return date_value.strftime("%Y%m%d")
        else:
            return str(date_value).replace("-", "")

    def _standardize_historical_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化历史数据"""
        # 统一列名映射，与 AKShare 保持一致
        column_mapping = {
            "trade_date": "date",
            "vol": "volume",
            "open": "open",
            "close": "close",
            "high": "high",
            "low": "low",
            "amount": "amount",
            "pre_close": "pre_close",
            "change": "change",
            "pct_chg": "pct_chg",
            "turnover_rate": "turnover_rate",
        }
        df = df.rename(columns=column_mapping)

        # 格式化日期
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
            df.set_index("date", inplace=True)

        # 按日期排序
        df = df.sort_index()

        return df

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
