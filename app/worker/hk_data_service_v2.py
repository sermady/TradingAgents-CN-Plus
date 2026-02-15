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

    # 注意：_normalize_code 和 _normalize_stock_info 方法现在继承自基类
    # 基类使用统一的 normalize_stock_code 和 normalize_stock_info 函数


# ==================== 全局实例管理 ====================

_hk_data_service = None


async def get_hk_data_service() -> HKDataService:
    """获取港股数据服务实例（单例模式）"""
    global _hk_data_service
    if _hk_data_service is None:
        _hk_data_service = HKDataService()
        await _hk_data_service.initialize()
    return _hk_data_service
