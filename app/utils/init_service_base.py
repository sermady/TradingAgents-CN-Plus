# -*- coding: utf-8 -*-
"""数据初始化服务基类

统一 AKShare 和 Tushare 初始化服务中的公共方法
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class InitServiceBase(ABC):
    """数据初始化服务基类

    提供通用的数据初始化功能，支持多种数据源
    """

    def __init__(self):
        self.db = None
        self.sync_service = None
        self.stats = None

    @abstractmethod
    async def initialize(self):
        """初始化服务"""
        pass

    async def _step_initialize_weekly_data(
        self,
        historical_days: int,
        sync_service: Any,
        stats: Any
    ) -> bool:
        """同步周线数据

        Args:
            historical_days: 历史天数
            sync_service: 数据同步服务实例
            stats: 统计信息对象

        Returns:
            bool: 是否成功
        """
        stats.current_step = f"同步周线数据({historical_days}天)"
        logger.info(f"📊 {stats.current_step}...")

        # 计算日期范围
        end_date = datetime.now().strftime('%Y-%m-%d')

        # 如果 historical_days 大于等于10年（3650天），则同步全历史
        if historical_days >= 3650:
            start_date = "1990-01-01"  # 全历史同步
            logger.info(f"  周线数据范围: 全历史（从1990-01-01到{end_date}）")
        else:
            start_date = (datetime.now() - timedelta(days=historical_days)).strftime('%Y-%m-%d')
            logger.info(f"  周线数据范围: {start_date} 到 {end_date}")

        try:
            # 同步周线数据
            result = await sync_service.sync_historical_data(
                start_date=start_date,
                end_date=end_date,
                incremental=False,
                period="weekly"  # 指定周线
            )

            if result:
                weekly_records = result.get("total_records", 0)
                stats.weekly_records = weekly_records
                logger.info(f"✅ 周线数据初始化完成: {weekly_records}条记录")
            else:
                logger.warning("⚠️ 周线数据初始化部分失败，继续后续步骤")
        except Exception as e:
            logger.warning(f"⚠️ 周线数据初始化失败: {e}（继续后续步骤）")

        stats.completed_steps += 1
        return True

    async def _step_initialize_monthly_data(
        self,
        historical_days: int,
        sync_service: Any,
        stats: Any
    ) -> bool:
        """同步月线数据

        Args:
            historical_days: 历史天数
            sync_service: 数据同步服务实例
            stats: 统计信息对象

        Returns:
            bool: 是否成功
        """
        stats.current_step = f"同步月线数据({historical_days}天)"
        logger.info(f"📊 {stats.current_step}...")

        # 计算日期范围
        end_date = datetime.now().strftime('%Y-%m-%d')

        # 如果 historical_days 大于等于10年（3650天），则同步全历史
        if historical_days >= 3650:
            start_date = "1990-01-01"  # 全历史同步
            logger.info(f"  月线数据范围: 全历史（从1990-01-01到{end_date}）")
        else:
            start_date = (datetime.now() - timedelta(days=historical_days)).strftime('%Y-%m-%d')
            logger.info(f"  月线数据范围: {start_date} 到 {end_date}")

        try:
            # 同步月线数据
            result = await sync_service.sync_historical_data(
                start_date=start_date,
                end_date=end_date,
                incremental=False,
                period="monthly"  # 指定月线
            )

            if result:
                monthly_records = result.get("total_records", 0)
                stats.monthly_records = monthly_records
                logger.info(f"✅ 月线数据初始化完成: {monthly_records}条记录")
            else:
                logger.warning("⚠️ 月线数据初始化部分失败，继续后续步骤")
        except Exception as e:
            logger.warning(f"⚠️ 月线数据初始化失败: {e}（继续后续步骤）")

        stats.completed_steps += 1
        return True

    async def _step_initialize_historical_data(
        self,
        historical_days: int,
        sync_service: Any,
        stats: Any
    ) -> bool:
        """同步历史日线数据

        Args:
            historical_days: 历史天数
            sync_service: 数据同步服务实例
            stats: 统计信息对象

        Returns:
            bool: 是否成功
        """
        stats.current_step = f"同步历史数据({historical_days}天)"
        logger.info(f"📊 {stats.current_step}...")

        # 计算日期范围
        end_date = datetime.now().strftime('%Y-%m-%d')

        # 如果 historical_days 大于等于10年（3650天），则同步全历史
        if historical_days >= 3650:
            start_date = "1990-01-01"  # 全历史同步
            logger.info(f"  历史数据范围: 全历史（从1990-01-01到{end_date}）")
        else:
            start_date = (datetime.now() - timedelta(days=historical_days)).strftime('%Y-%m-%d')
            logger.info(f"  历史数据范围: {start_date} 到 {end_date}")

        # 同步历史数据
        result = await sync_service.sync_historical_data(
            start_date=start_date,
            end_date=end_date,
            incremental=False  # 全量同步
        )

        if result:
            stats.historical_records = result.get("total_records", 0)
            logger.info(f"✅ 历史数据初始化完成: {stats.historical_records}条记录")
        else:
            logger.warning("⚠️ 历史数据初始化部分失败，继续后续步骤")

        stats.completed_steps += 1
        return True
