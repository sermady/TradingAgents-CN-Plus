# -*- coding: utf-8 -*-
"""
AKShare历史数据模块

包含历史行情数据获取功能
"""

import asyncio
import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class HistoricalDataMixin:
    """历史数据功能混入类"""

    async def get_historical_data(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "daily",
    ) -> Optional[pd.DataFrame]:
        """
        获取历史行情数据

        Args:
            code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            period: 周期 (daily, weekly, monthly)

        Returns:
            历史行情数据DataFrame
        """
        if not self.connected or self.ak is None:
            return None

        try:
            logger.debug(f"📊 获取{code}历史数据: {start_date} 到 {end_date}")

            # 转换周期格式
            period_map = {"daily": "daily", "weekly": "weekly", "monthly": "monthly"}
            ak_period = period_map.get(period, "daily")

            # 格式化日期
            start_date_formatted = start_date.replace("-", "")
            end_date_formatted = end_date.replace("-", "")

            # 获取历史数据（带重试机制）
            max_retries = 2
            last_error = None
            hist_df = None

            for attempt in range(max_retries):
                try:

                    def fetch_historical_data():
                        return self.ak.stock_zh_a_hist(
                            symbol=code,
                            period=ak_period,
                            start_date=start_date_formatted,
                            end_date=end_date_formatted,
                            adjust="qfq",  # 前复权
                        )

                    hist_df = await asyncio.to_thread(fetch_historical_data)

                    if hist_df is None:
                        raise ValueError("API返回None")

                    if hist_df.empty:
                        raise ValueError("API返回空DataFrame")

                    break  # 成功获取，跳出重试循环

                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        wait_time = 1.5 * (attempt + 1)
                        logger.warning(
                            f"⚠️ 获取{code}历史数据失败，{wait_time}秒后重试: {e}"
                        )
                        await asyncio.sleep(wait_time)
                    continue

            if hist_df is None or hist_df.empty:
                logger.warning(f"⚠️ {code}历史数据为空或获取失败 (尝试{max_retries}次)")
                return None

            # 标准化列名
            hist_df = self._standardize_historical_columns(hist_df, code)

            logger.debug(f"✅ {code}历史数据获取成功: {len(hist_df)}条记录")
            return hist_df

        except Exception as e:
            logger.error(f"❌ 获取{code}历史数据失败: {e}")
            return None

    def _standardize_historical_columns(
        self, df: pd.DataFrame, code: str
    ) -> pd.DataFrame:
        """标准化历史数据列名"""
        try:
            # 标准化列名映射
            column_mapping = {
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "成交额": "amount",
                "振幅": "amplitude",
                "涨跌幅": "change_percent",
                "涨跌额": "change",
                "换手率": "turnover",
            }

            # 重命名列
            df = df.rename(columns=column_mapping)

            # 添加标准字段
            df["code"] = code
            df["full_symbol"] = self._get_full_symbol(code)

            # 确保日期格式
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])

            # 数据类型转换
            numeric_columns = ["open", "close", "high", "low", "volume", "amount"]
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)  # type: ignore

            # 成交量单位：保持原始单位"手"（AKShare历史数据返回的是手）
            # 不再转换为股，直接使用原始单位

            return df

        except Exception as e:
            logger.error(f"标准化{code}历史数据列名失败: {e}")
            return df
