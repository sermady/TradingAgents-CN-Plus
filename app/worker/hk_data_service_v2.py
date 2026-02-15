# -*- coding: utf-8 -*-
"""
港股数据服务（按需获取+缓存模式）

功能：
1. 按需从数据源获取港股信息（yahoo/akshare）
2. 自动缓存到 MongoDB，避免重复请求
3. 支持多数据源：同一股票可有多个数据源记录
4. 使用 (code, source) 联合查询进行 upsert 操作

设计说明：
- 采用按需获取+缓存模式，避免批量同步触发速率限制
- 参考A股数据源管理方式（Tushare/AKShare/BaoStock）
- 缓存时长可配置（默认24小时）
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

# 导入港股数据提供器
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tradingagents.dataflows.providers.hk.hk_stock import HKStockProvider
from tradingagents.dataflows.providers.hk.improved_hk import ImprovedHKStockProvider
from app.worker.foreign_data_service_base import ForeignDataBaseService

logger = logging.getLogger(__name__)


class HKDataService(ForeignDataBaseService):
    """港股数据服务（按需获取+缓存模式）"""

    def __init__(self):
        super().__init__(market_type='hk', region='HK')

        # 数据提供器映射
        self.providers = {
            "yahoo": HKStockProvider(),
            "akshare": ImprovedHKStockProvider(),
        }

    def _normalize_code(self, stock_code: str) -> str:
        """标准化港股代码

        港股代码通常是5位数字，可能带前导0。

        Args:
            stock_code: 原始股票代码

        Returns:
            标准化后的5位代码
        """
        return stock_code.strip().lstrip('0').zfill(5)

    def _normalize_stock_info(self, stock_info: Dict, source: str) -> Dict:
        """标准化港股信息格式

        Args:
            stock_info: 原始股票信息
            source: 数据源

        Returns:
            标准化后的股票信息
        """
        normalized = {
            "name": stock_info.get("name", ""),
            "currency": stock_info.get("currency", "HKD"),
            "exchange": stock_info.get("exchange", "HKEX"),
            "market": stock_info.get("market", "香港交易所"),
            "area": stock_info.get("area", "香港"),
        }

        # 可选字段
        optional_fields = [
            "industry", "sector", "list_date", "total_mv", "circ_mv",
            "pe", "pb", "ps", "pcf", "market_cap", "shares_outstanding",
            "float_shares", "employees", "website", "description"
        ]

        for field in optional_fields:
            if field in stock_info and stock_info[field]:
                normalized[field] = stock_info[field]

        return normalized


# ==================== 全局实例管理 ====================

_hk_data_service = None


async def get_hk_data_service() -> HKDataService:
    """获取港股数据服务实例（单例模式）"""
    global _hk_data_service
    if _hk_data_service is None:
        _hk_data_service = HKDataService()
        await _hk_data_service.initialize()
    return _hk_data_service
