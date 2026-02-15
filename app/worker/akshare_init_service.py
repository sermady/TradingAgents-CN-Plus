# -*- coding: utf-8 -*-
"""
AKShare数据初始化服务
用于首次部署时的完整数据初始化，包括基础数据、历史数据、财务数据等
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from app.core.database import get_mongo_db
from tradingagents.utils.time_utils import get_today_str, get_days_ago_str, get_timestamp
from app.worker.akshare_sync_service import get_akshare_sync_service
from app.utils.init_service_base import InitServiceBase

logger = logging.getLogger(__name__)


@dataclass
class AKShareInitializationStats:
    """AKShare初始化统计信息"""
    started_at: datetime
    finished_at: Optional[datetime] = None
    total_steps: int = 0
    completed_steps: int = 0
    current_step: str = ""
    basic_info_count: int = 0
    historical_records: int = 0
    weekly_records: int = 0
    monthly_records: int = 0
    financial_records: int = 0
    quotes_count: int = 0
    news_count: int = 0
    errors: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class AKShareInitService(InitServiceBase):
    """
    AKShare数据初始化服务

    负责首次部署时的完整数据初始化：
    1. 检查数据库状态
    2. 初始化股票基础信息
    3. 同步历史数据（可配置时间范围）
    4. 同步财务数据
    5. 同步最新行情数据
    6. 验证数据完整性
    """

    def __init__(self):
        super().__init__()
        self.data_source_name = "AKShare"

    async def initialize(self):
        """初始化服务"""
        self.db = get_mongo_db()
        self.sync_service = await get_akshare_sync_service()
        logger.info("✅ AKShare初始化服务准备完成")

    async def run_full_initialization(
        self,
        historical_days: int = 365,
        skip_if_exists: bool = True,
        batch_size: int = 100,
        enable_multi_period: bool = False,
        sync_items: List[str] = None
    ) -> Dict[str, Any]:
        """
        运行完整的数据初始化

        Args:
            historical_days: 历史数据天数（默认1年）
            skip_if_exists: 如果数据已存在是否跳过
            batch_size: 批处理大小
            enable_multi_period: 是否启用多周期数据同步（日线、周线、月线）
            sync_items: 要同步的数据类型列表，可选值：
                - 'basic_info': 股票基础信息
                - 'historical': 历史行情数据（日线）
                - 'weekly': 周线数据
                - 'monthly': 月线数据
                - 'financial': 财务数据
                - 'quotes': 最新行情
                - 'news': 新闻数据
                - None: 同步所有数据（默认）

        Returns:
            初始化结果统计
        """
        # 如果未指定sync_items，则同步所有数据
        if sync_items is None:
            sync_items = ['basic_info', 'historical', 'financial', 'quotes']
            if enable_multi_period:
                sync_items.extend(['weekly', 'monthly'])

        logger.info("🚀 开始AKShare数据完整初始化...")
        logger.info(f"📋 同步项目: {', '.join(sync_items)}")

        # 计算总步骤数（检查状态 + 同步项目数 + 验证）
        total_steps = 1 + len(sync_items) + 1

        self.stats = AKShareInitializationStats(
            started_at=get_timestamp(),
            total_steps=total_steps
        )

        try:
            # 步骤1: 检查数据库状态
            # 只有在同步 basic_info 时才检查是否跳过
            if 'basic_info' in sync_items:
                await self._step_check_database_status(skip_if_exists)
            else:
                logger.info("📊 检查数据库状态...")
                basic_count = await self.db.stock_basic_info.count_documents({})
                logger.info(f"  当前股票基础信息: {basic_count}条")
                if basic_count == 0:
                    logger.warning("⚠️ 数据库中没有股票基础信息，建议先同步 basic_info")

            # 步骤2: 初始化股票基础信息
            if 'basic_info' in sync_items:
                await self._step_initialize_basic_info()
            else:
                logger.info("⏭️ 跳过股票基础信息同步")

            # 步骤3: 同步历史数据（日线）
            if 'historical' in sync_items:
                await self._step_initialize_historical_data(historical_days)
            else:
                logger.info("⏭️ 跳过历史数据（日线）同步")

            # 步骤4: 同步周线数据
            if 'weekly' in sync_items:
                await self._step_initialize_weekly_data(historical_days)
            else:
                logger.info("⏭️ 跳过周线数据同步")

            # 步骤5: 同步月线数据
            if 'monthly' in sync_items:
                await self._step_initialize_monthly_data(historical_days)
            else:
                logger.info("⏭️ 跳过月线数据同步")

            # 步骤6: 同步财务数据
            if 'financial' in sync_items:
                await self._step_initialize_financial_data()
            else:
                logger.info("⏭️ 跳过财务数据同步")

            # 步骤7: 同步最新行情
            if 'quotes' in sync_items:
                await self._step_initialize_quotes()
            else:
                logger.info("⏭️ 跳过最新行情同步")

            # 步骤8: 同步新闻数据
            if 'news' in sync_items:
                await self._step_initialize_news_data()
            else:
                logger.info("⏭️ 跳过新闻数据同步")

            # 最后: 验证数据完整性
            await self._step_verify_data_integrity()

            self.stats.finished_at = get_timestamp()
            duration = (self.stats.finished_at - self.stats.started_at).total_seconds()

            logger.info(f"🎉 AKShare数据初始化完成！耗时: {duration:.2f}秒")

            return self._get_initialization_summary()

        except Exception as e:
            logger.error(f"❌ AKShare数据初始化失败: {e}")
            self.stats.errors.append({
                "step": self.stats.current_step,
                "error": str(e),
                "timestamp": get_timestamp()
            })
            return self._get_initialization_summary()


# 全局初始化服务实例
_akshare_init_service = None


async def get_akshare_init_service() -> AKShareInitService:
    """获取AKShare初始化服务实例"""
    global _akshare_init_service
    if _akshare_init_service is None:
        _akshare_init_service = AKShareInitService()
        await _akshare_init_service.initialize()
    return _akshare_init_service


# APScheduler兼容的初始化任务函数
async def run_akshare_full_initialization(
    historical_days: int = 365,
    skip_if_exists: bool = True
):
    """APScheduler任务：运行完整的AKShare数据初始化"""
    try:
        service = await get_akshare_init_service()
        result = await service.run_full_initialization(
            historical_days=historical_days,
            skip_if_exists=skip_if_exists
        )
        logger.info(f"✅ AKShare完整初始化完成: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ AKShare完整初始化失败: {e}")
        raise
