# -*- coding: utf-8 -*-
"""
股票历史数据 Schema
用于技术分析的历史日线数据统一格式
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class StockDailyData:
    """
    单日股票数据

    包含单日的所有交易数据
    """

    # 基础信息
    ts_code: str = ""  # Tushare格式代码
    trade_date: str = ""  # 交易日期 YYYY-MM-DD

    # OHLCV 数据
    open: Optional[float] = None  # 开盘价
    high: Optional[float] = None  # 最高价
    low: Optional[float] = None  # 最低价
    close: Optional[float] = None  # 收盘价
    volume: Optional[float] = None  # 成交量（股）
    amount: Optional[float] = None  # 成交额（元）

    # 涨跌数据
    change: Optional[float] = None  # 涨跌额
    pct_chg: Optional[float] = None  # 涨跌幅 %

    # 技术指标
    ma5: Optional[float] = None  # 5日均线
    ma10: Optional[float] = None  # 10日均线
    ma20: Optional[float] = None  # 20日均线
    ma60: Optional[float] = None  # 60日均线

    macd_dif: Optional[float] = None  # MACD DIF
    macd_dea: Optional[float] = None  # MACD DEA
    macd_hist: Optional[float] = None  # MACD 柱状图

    rsi6: Optional[float] = None  # RSI6
    rsi12: Optional[float] = None  # RSI12
    rsi24: Optional[float] = None  # RSI24

    boll_upper: Optional[float] = None  # 布林带上轨
    boll_middle: Optional[float] = None  # 布林带中轨
    boll_lower: Optional[float] = None  # 布林带下轨

    # 交易指标
    turnover_rate: Optional[float] = None  # 换手率 %
    volume_ratio: Optional[float] = None  # 量比

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StockDailyData":
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class StockHistoricalData:
    """
    股票历史数据（用于技术分析）

    包含多日的历史数据和技术指标
    """

    # 基础信息
    code: str = ""  # 股票代码
    name: str = ""  # 股票名称
    market: str = "CN"  # 市场类型
    currency: str = "CNY"  # 货币
    exchange: str = ""  # 交易所

    # 数据范围
    start_date: str = ""  # 开始日期
    end_date: str = ""  # 结束日期
    trading_days: int = 0  # 交易日数量

    # 最新数据快照
    latest_price: Optional[float] = None
    latest_change: Optional[float] = None
    latest_pct_chg: Optional[float] = None
    latest_volume: Optional[float] = None

    # 历史数据（按日期排序，最新的在最后）
    daily_data: List[StockDailyData] = None

    # 技术指标汇总
    latest_ma5: Optional[float] = None
    latest_ma10: Optional[float] = None
    latest_ma20: Optional[float] = None
    latest_ma60: Optional[float] = None

    latest_macd_dif: Optional[float] = None
    latest_macd_dea: Optional[float] = None
    latest_macd_hist: Optional[float] = None

    latest_rsi6: Optional[float] = None
    latest_rsi12: Optional[float] = None
    latest_rsi24: Optional[float] = None

    latest_boll_upper: Optional[float] = None
    latest_boll_middle: Optional[float] = None
    latest_boll_lower: Optional[float] = None

    # 数据来源
    data_source: str = ""
    last_updated: str = ""

    def __post_init__(self):
        if self.daily_data is None:
            self.daily_data = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result["daily_data"] = [d.to_dict() for d in self.daily_data]
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StockHistoricalData":
        """从字典创建"""
        daily_data = [StockDailyData.from_dict(d) for d in data.get("daily_data", [])]
        return cls(
            **{k: v for k, v in data.items() if k in cls.__dataclass_fields__},
            daily_data=daily_data,
        )

    def get_latest_daily(self) -> Optional[StockDailyData]:
        """获取最新一天的日线数据"""
        if self.daily_data:
            return self.daily_data[-1]
        return None

    def get_price_change_pct(self) -> float:
        """计算期间涨跌幅"""
        if len(self.daily_data) >= 2:
            first_close = self.daily_data[0].close
            last_close = self.daily_data[-1].close
            if first_close and last_close and first_close != 0:
                return ((last_close - first_close) / first_close) * 100
        return 0.0

    def get_volume_trend(self) -> str:
        """分析成交量趋势"""
        if len(self.daily_data) < 5:
            return "数据不足"

        recent_volumes = [d.volume for d in self.daily_data[-5:] if d.volume]
        if not recent_volumes:
            return "数据不足"

        avg_volume = sum(recent_volumes) / len(recent_volumes)
        latest_volume = recent_volumes[-1]

        if latest_volume > avg_volume * 1.5:
            return "放量"
        elif latest_volume < avg_volume * 0.5:
            return "缩量"
        else:
            return "持平"


# 统一的股票数据 Schema 导出
__all__ = [
    "StockDailyData",
    "StockHistoricalData",
]
