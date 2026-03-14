# -*- coding: utf-8 -*-
"""
行情采集服务

定时从数据源适配层获取全市场近实时行情，入库到 MongoDB 集合 `market_quotes`。

核心特性：
- 调度频率：由 settings.QUOTES_INGEST_INTERVAL_SECONDS 控制（默认360秒=6分钟）
- 接口轮换：Tushare → AKShare东方财富 → AKShare新浪财经（避免单一接口被限流）
- 智能限流：Tushare免费用户每小时最多2次，付费用户自动切换到高频模式
- 休市时间：跳过任务，保持上次收盘数据；必要时执行一次性兜底补数
"""

from typing import Optional
from zoneinfo import ZoneInfo

from app.core.config import settings

from .utils import normalize_stock_code
from .datasource import DataSourceMixin
from .ingestion import IngestionMixin
from .backfill import BackfillMixin


class QuotesIngestionService(DataSourceMixin, IngestionMixin, BackfillMixin):
    """
    行情采集服务

    定时从数据源适配层获取全市场近实时行情，入库到 MongoDB 集合 `market_quotes`。
    """

    def __init__(self, collection_name: str = "market_quotes") -> None:
        DataSourceMixin.__init__(self)
        IngestionMixin.__init__(self)
        BackfillMixin.__init__(self)

        self.collection_name = collection_name
        self.status_collection_name = "quotes_ingestion_status"
        self.tz = ZoneInfo(settings.TIMEZONE)

    # 工具方法暴露
    normalize_stock_code = staticmethod(normalize_stock_code)


# 全局服务实例
_service_instance: Optional[QuotesIngestionService] = None


def get_quotes_ingestion_service() -> QuotesIngestionService:
    """获取行情采集服务实例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = QuotesIngestionService()
    return _service_instance
