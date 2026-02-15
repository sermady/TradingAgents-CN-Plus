# -*- coding: utf-8 -*-
"""
美股数据服务（按需获取+缓存模式）

功能：
1. 按需从数据源获取美股信息（yahoo/finnhub）
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

# 导入美股数据提供器
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tradingagents.dataflows.providers.us.optimized import OptimizedUSDataProvider
from app.worker.foreign_data_service_base import ForeignDataBaseService

logger = logging.getLogger(__name__)


class USDataService(ForeignDataBaseService):
    """美股数据服务（按需获取+缓存模式）"""

    def __init__(self):
        super().__init__(market_type='us', region='US')

        # 数据提供器映射
        self.providers = {
            "yahoo": OptimizedUSDataProvider(),
            # 可以添加更多数据源，如 finnhub
        }

    # 注意：_normalize_code 和 _normalize_stock_info 方法现在继承自基类
    # 基类使用统一的 normalize_stock_code 和 normalize_stock_info 函数


# ==================== 全局实例管理 ====================

_us_data_service = None


async def get_us_data_service() -> USDataService:
    """获取美股数据服务实例（单例模式）"""
    global _us_data_service
    if _us_data_service is None:
        _us_data_service = USDataService()
        await _us_data_service.initialize()
    return _us_data_service
