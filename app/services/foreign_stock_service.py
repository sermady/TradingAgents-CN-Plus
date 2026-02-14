# -*- coding: utf-8 -*-
"""
港股和美股数据服务（Facade模式）
🔥 复用统一数据源管理器（UnifiedStockService）
🔥 按照数据库配置的数据源优先级调用API
🔥 请求去重机制：防止并发请求重复调用API

这是一个 Facade 类，用于向后兼容。实际功能已拆分到：
- app/services/foreign/hk_service.py - 港股服务
- app/services/foreign/us_service.py - 美股服务
- app/services/foreign/base.py - 基础类和工具函数
"""
from typing import Dict, List
import logging

from .foreign.hk_service import HKStockService
from .foreign.us_service import USStockService

logger = logging.getLogger(__name__)


class ForeignStockService:
    """港股和美股数据服务（Facade模式，向后兼容）

    使用方法：
        service = ForeignStockService(db=db)

        # 获取行情
        quote = await service.get_quote('HK', '00700')

        # 获取基础信息
        info = await service.get_basic_info('US', 'AAPL')

        # 获取K线
        kline = await service.get_kline('HK', '00700', period='day', limit=120)
    """

    def __init__(self, db=None):
        """初始化服务

        Args:
            db: MongoDB 数据库连接
        """
        self.hk_service = HKStockService(db=db)
        self.us_service = USStockService(db=db)

        # 缓存时间配置（秒） - 用于向后兼容
        self.CACHE_TTL = {
            "HK": {
                "quote": 600,        # 10分钟（实时行情）
                "info": 86400,       # 1天（基础信息）
                "kline": 7200,       # 2小时（K线数据）
            },
            "US": {
                "quote": 600,        # 10分钟
                "info": 86400,       # 1天
                "kline": 7200,       # 2小时
            }
        }

        logger.info("✅ ForeignStockService 初始化完成（Facade模式）")

    async def get_quote(self, market: str, code: str, force_refresh: bool = False) -> Dict:
        """获取实时行情

        Args:
            market: 市场类型 (HK/US)
            code: 股票代码
            force_refresh: 是否强制刷新（跳过缓存）

        Returns:
            实时行情数据
        """
        if market == 'HK':
            return await self.hk_service.get_quote(code, force_refresh)
        elif market == 'US':
            return await self.us_service.get_quote(code, force_refresh)
        else:
            raise ValueError(f"不支持的市场类型: {market}")

    async def get_basic_info(self, market: str, code: str, force_refresh: bool = False) -> Dict:
        """获取基础信息

        Args:
            market: 市场类型 (HK/US)
            code: 股票代码
            force_refresh: 是否强制刷新

        Returns:
            基础信息数据
        """
        if market == 'HK':
            return await self.hk_service.get_basic_info(code, force_refresh)
        elif market == 'US':
            return await self.us_service.get_basic_info(code, force_refresh)
        else:
            raise ValueError(f"不支持的市场类型: {market}")

    async def get_kline(self, market: str, code: str, period: str = 'day',
                       limit: int = 120, force_refresh: bool = False) -> List[Dict]:
        """获取K线数据

        Args:
            market: 市场类型 (HK/US)
            code: 股票代码
            period: 周期 (day/week/month)
            limit: 数据条数
            force_refresh: 是否强制刷新

        Returns:
            K线数据列表
        """
        if market == 'HK':
            return await self.hk_service.get_kline(code, period, limit, force_refresh)
        elif market == 'US':
            return await self.us_service.get_kline(code, period, limit, force_refresh)
        else:
            raise ValueError(f"不支持的市场类型: {market}")

    async def get_hk_news(self, code: str, days: int = 2, limit: int = 50) -> Dict:
        """获取港股新闻

        Args:
            code: 股票代码
            days: 回溯天数
            limit: 返回数量限制

        Returns:
            包含新闻列表和数据源的字典
        """
        return await self.hk_service.get_news(code, days, limit)

    async def get_us_news(self, code: str, days: int = 2, limit: int = 50) -> Dict:
        """获取美股新闻

        Args:
            code: 股票代码
            days: 回溯天数
            limit: 返回数量限制

        Returns:
            包含新闻列表和数据源的字典
        """
        return await self.us_service.get_news(code, days, limit)
