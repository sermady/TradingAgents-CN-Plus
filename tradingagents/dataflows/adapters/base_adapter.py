# -*- coding: utf-8 -*-
"""
数据源适配器基类
定义统一的数据源适配器接口
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

import pandas as pd


class BaseDataAdapter(ABC):
    """
    数据源适配器基类

    所有数据源适配器必须继承此类并实现其抽象方法
    """

    def __init__(self, source_name: str):
        """
        初始化适配器

        Args:
            source_name: 数据源名称
        """
        self.source_name = source_name
        self._available = False

    @abstractmethod
    def is_available(self) -> bool:
        """
        检查数据源是否可用

        Returns:
            bool: 是否可用
        """
        pass

    @abstractmethod
    async def get_historical_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "daily",
    ) -> Optional[pd.DataFrame]:
        """
        获取历史数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期（daily/weekly/monthly）

        Returns:
            DataFrame: 历史数据
        """
        pass

    @abstractmethod
    async def get_stock_basic_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取股票基本信息

        Args:
            symbol: 股票代码

        Returns:
            Dict: 股票基本信息
        """
        pass

    @abstractmethod
    async def get_realtime_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取实时行情

        Args:
            symbol: 股票代码

        Returns:
            Dict: 实时行情数据
        """
        pass

    def normalize_symbol(self, symbol: str) -> str:
        """
        标准化股票代码

        Args:
            symbol: 原始股票代码

        Returns:
            str: 标准化后的股票代码
        """
        # 移除空格并转换为大写
        symbol = symbol.strip().upper()
        # 移除可能的后缀
        symbol = symbol.replace(".SH", "").replace(".SZ", "").replace(".BJ", "")
        return symbol

    def standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化 DataFrame 列名和格式

        Args:
            df: 原始 DataFrame

        Returns:
            pd.DataFrame: 标准化后的 DataFrame
        """
        if df is None or df.empty:
            return pd.DataFrame()

        out = df.copy()

        # 列名映射
        colmap = {
            # English
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "vol",
            "Amount": "amount",
            "symbol": "code",
            "Symbol": "code",
            # Already lower
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "vol": "vol",
            "volume": "vol",
            "amount": "amount",
            "code": "code",
            "date": "date",
            "trade_date": "date",
            # Chinese (AKShare common)
            "日期": "date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "vol",
            "成交额": "amount",
            "涨跌幅": "pct_change",
            "涨跌额": "change",
        }
        out = out.rename(columns={c: colmap.get(c, c) for c in out.columns})

        # 确保日期排序
        if "date" in out.columns:
            try:
                if not pd.api.types.is_datetime64_any_dtype(out["date"]):
                    out["date"] = pd.to_datetime(out["date"])
                out = out.sort_values("date")
            except Exception:
                pass

        # 计算涨跌幅（如果缺失）
        if "pct_change" not in out.columns and "close" in out.columns:
            out["pct_change"] = out["close"].pct_change() * 100.0

        return out
