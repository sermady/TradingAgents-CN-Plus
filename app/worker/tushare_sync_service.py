# -*- coding: utf-8 -*-
"""
Tushare数据同步服务 - Facade模式
此文件作为对外接口，从 tushare 子模块导入所有功能

注意：此文件保持向后兼容性，所有新功能应从 app.worker.tushare 导入
"""

# 从子模块导入所有公共API
from app.worker.tushare import (
    TushareSyncService,
    get_tushare_sync_service,
    TushareSyncBase,
    TushareDailySync,
    TushareRealtimeSync,
    TushareFinancialSync,
    TushareNewsSync,
    get_utc8_now,
)

# 从子模块导入任务函数
from app.worker.tushare.tasks import (
    run_tushare_basic_info_sync,
    run_tushare_quotes_sync,
    run_tushare_hourly_bulk_sync,
    run_tushare_historical_sync,
    run_tushare_financial_sync,
    run_tushare_status_check,
    run_tushare_news_sync,
)

# 导出所有公共接口
__all__ = [
    # 服务类
    "TushareSyncService",
    "TushareSyncBase",
    "TushareDailySync",
    "TushareRealtimeSync",
    "TushareFinancialSync",
    "TushareNewsSync",
    # 服务获取函数
    "get_tushare_sync_service",
    # 工具函数
    "get_utc8_now",
    # APScheduler任务函数
    "run_tushare_basic_info_sync",
    "run_tushare_quotes_sync",
    "run_tushare_hourly_bulk_sync",
    "run_tushare_historical_sync",
    "run_tushare_financial_sync",
    "run_tushare_status_check",
    "run_tushare_news_sync",
]
