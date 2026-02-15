# -*- coding: utf-8 -*-
"""
Tushare同步服务模块
提供Tushare数据同步的统一接口
"""

from typing import Union
from .base import TushareSyncBase, get_utc8_now
from .daily import TushareDailySync
from .realtime import TushareRealtimeSync
from .financial import TushareFinancialSync
from .news import TushareNewsSync

__all__ = [
    "TushareSyncService",
    "get_tushare_sync_service",
    "TushareSyncBase",
    "TushareDailySync",
    "TushareRealtimeSync",
    "TushareFinancialSync",
    "TushareNewsSync",
    "get_utc8_now",
]

# 全局同步服务实例
_tushare_sync_service = None


class TushareSyncService(
    TushareDailySync, TushareRealtimeSync, TushareFinancialSync, TushareNewsSync
):
    """
    Tushare数据同步服务（完整版）
    继承所有专用同步类，提供完整的同步功能
    """

    async def initialize(self):
        """初始化同步服务"""
        # 调用基类的初始化
        success = await self.provider.connect()
        if not success:
            raise RuntimeError("❌ Tushare连接失败，无法启动同步服务")

        # 初始化历史数据服务
        self.historical_service = await self.historical_data_service()

        # 初始化新闻数据服务
        self.news_service = await self.news_data_service()

        logger.info("✅ Tushare同步服务初始化完成")


async def get_tushare_sync_service() -> TushareSyncService:
    """获取Tushare同步服务实例"""
    global _tushare_sync_service
    if _tushare_sync_service is None:
        _tushare_sync_service = TushareSyncService()
        await _tushare_sync_service.initialize()
    return _tushare_sync_service
