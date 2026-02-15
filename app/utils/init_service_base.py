# -*- coding: utf-8 -*-
"""数据初始化服务基类

统一 AKShare 和 Tushare 初始化服务中的公共方法
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Protocol
import logging

logger = logging.getLogger(__name__)


class SyncServiceProtocol(Protocol):
    """同步服务协议，用于类型提示"""

    async def sync_stock_basic_info(self, force_update: bool = False) -> Dict[str, Any]: ...
    async def sync_historical_data(
        self,
        start_date: str,
        end_date: str,
        incremental: bool = False,
        period: str = "daily"
    ) -> Dict[str, Any]: ...
    async def sync_financial_data(self) -> Dict[str, Any]: ...
    async def sync_realtime_quotes(self) -> Dict[str, Any]: ...
    async def sync_news_data(
        self,
        hours_back: Optional[int] = None,
        max_news_per_stock: int = 20
    ) -> Dict[str, Any]: ...


class InitServiceBase(ABC):
    """数据初始化服务基类

    提供通用的数据初始化功能，支持多种数据源
    """

    def __init__(self):
        self.db = None
        self.sync_service: Optional[SyncServiceProtocol] = None
        self.stats = None
        self.data_source_name: str = "unknown"

    @abstractmethod
    async def initialize(self):
        """初始化服务"""
        pass

    async def _step_check_database_status(
        self,
        skip_if_exists: bool,
        collection_names: Optional[Dict[str, str]] = None
    ) -> bool:
        """步骤1: 检查数据库状态

        Args:
            skip_if_exists: 如果数据已存在是否跳过
            collection_names: 自定义集合名称映射，默认使用 stock_basic_info 和 market_quotes

        Returns:
            bool: 是否继续初始化（True=继续，False=跳过）

        Raises:
            Exception: 如果数据已存在且 skip_if_exists=True
        """
        if collection_names is None:
            collection_names = {
                "basic_info": "stock_basic_info",
                "quotes": "market_quotes"
            }

        self.stats.current_step = "检查数据库状态"
        logger.info(f"📊 {self.stats.current_step}...")

        # 检查各集合的数据量
        basic_count = await self.db[collection_names["basic_info"]].count_documents({})
        quotes_count = await self.db[collection_names["quotes"]].count_documents({})

        logger.info(f"  当前数据状态:")
        logger.info(f"    股票基础信息: {basic_count}条")
        logger.info(f"    行情数据: {quotes_count}条")

        if skip_if_exists and basic_count > 0:
            logger.info("⚠️ 检测到已有数据，跳过初始化（可通过skip_if_exists=False强制初始化）")
            raise Exception("数据已存在，跳过初始化")

        self.stats.completed_steps += 1
        logger.info(f"✅ {self.stats.current_step}完成")
        return True

    async def _step_initialize_basic_info(self) -> bool:
        """步骤2: 初始化股票基础信息

        Returns:
            bool: 是否成功

        Raises:
            Exception: 如果初始化失败
        """
        self.stats.current_step = "初始化股票基础信息"
        logger.info(f"📋 {self.stats.current_step}...")

        # 强制更新所有基础信息
        result = await self.sync_service.sync_stock_basic_info(force_update=True)

        if result:
            self.stats.basic_info_count = result.get("success_count", 0)
            logger.info(f"✅ 基础信息初始化完成: {self.stats.basic_info_count}只股票")
        else:
            raise Exception("基础信息初始化失败")

        self.stats.completed_steps += 1
        return True

    async def _step_initialize_historical_data(self, historical_days: int) -> bool:
        """步骤3: 同步历史日线数据

        Args:
            historical_days: 历史天数

        Returns:
            bool: 是否成功
        """
        self.stats.current_step = f"同步历史数据({historical_days}天)"
        logger.info(f"📊 {self.stats.current_step}...")

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
        result = await self.sync_service.sync_historical_data(
            start_date=start_date,
            end_date=end_date,
            incremental=False  # 全量同步
        )

        if result:
            self.stats.historical_records = result.get("total_records", 0)
            logger.info(f"✅ 历史数据初始化完成: {self.stats.historical_records}条记录")
        else:
            logger.warning("⚠️ 历史数据初始化部分失败，继续后续步骤")

        self.stats.completed_steps += 1
        return True

    async def _step_initialize_weekly_data(self, historical_days: int) -> bool:
        """步骤4a: 同步周线数据

        Args:
            historical_days: 历史天数

        Returns:
            bool: 是否成功
        """
        self.stats.current_step = f"同步周线数据({historical_days}天)"
        logger.info(f"📊 {self.stats.current_step}...")

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
            result = await self.sync_service.sync_historical_data(
                start_date=start_date,
                end_date=end_date,
                incremental=False,
                period="weekly"  # 指定周线
            )

            if result:
                weekly_records = result.get("total_records", 0)
                self.stats.weekly_records = weekly_records
                logger.info(f"✅ 周线数据初始化完成: {weekly_records}条记录")
            else:
                logger.warning("⚠️ 周线数据初始化部分失败，继续后续步骤")
        except Exception as e:
            logger.warning(f"⚠️ 周线数据初始化失败: {e}（继续后续步骤）")

        self.stats.completed_steps += 1
        return True

    async def _step_initialize_monthly_data(self, historical_days: int) -> bool:
        """步骤4b: 同步月线数据

        Args:
            historical_days: 历史天数

        Returns:
            bool: 是否成功
        """
        self.stats.current_step = f"同步月线数据({historical_days}天)"
        logger.info(f"📊 {self.stats.current_step}...")

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
            result = await self.sync_service.sync_historical_data(
                start_date=start_date,
                end_date=end_date,
                incremental=False,
                period="monthly"  # 指定月线
            )

            if result:
                monthly_records = result.get("total_records", 0)
                self.stats.monthly_records = monthly_records
                logger.info(f"✅ 月线数据初始化完成: {monthly_records}条记录")
            else:
                logger.warning("⚠️ 月线数据初始化部分失败，继续后续步骤")
        except Exception as e:
            logger.warning(f"⚠️ 月线数据初始化失败: {e}（继续后续步骤）")

        self.stats.completed_steps += 1
        return True

    async def _step_initialize_financial_data(self) -> bool:
        """步骤5: 同步财务数据

        Returns:
            bool: 是否成功
        """
        self.stats.current_step = "同步财务数据"
        logger.info(f"💰 {self.stats.current_step}...")

        try:
            result = await self.sync_service.sync_financial_data()

            if result:
                self.stats.financial_records = result.get("success_count", 0)
                logger.info(f"✅ 财务数据初始化完成: {self.stats.financial_records}条记录")
            else:
                logger.warning("⚠️ 财务数据初始化失败")
        except Exception as e:
            logger.warning(f"⚠️ 财务数据初始化失败: {e}（继续后续步骤）")

        self.stats.completed_steps += 1
        return True

    async def _step_initialize_quotes(self) -> bool:
        """步骤6: 同步最新行情

        Returns:
            bool: 是否成功
        """
        self.stats.current_step = "同步最新行情"
        logger.info(f"📈 {self.stats.current_step}...")

        try:
            result = await self.sync_service.sync_realtime_quotes()

            if result:
                self.stats.quotes_count = result.get("success_count", 0)
                logger.info(f"✅ 最新行情初始化完成: {self.stats.quotes_count}只股票")
            else:
                logger.warning("⚠️ 最新行情初始化失败")
        except Exception as e:
            logger.warning(f"⚠️ 最新行情初始化失败: {e}（继续后续步骤）")

        self.stats.completed_steps += 1
        return True

    async def _step_initialize_news_data(
        self,
        historical_days: Optional[int] = None,
        max_news_per_stock: int = 20
    ) -> bool:
        """步骤7: 同步新闻数据

        Args:
            historical_days: 历史天数（用于计算回溯小时数），None表示使用默认值7天
            max_news_per_stock: 每只股票最大新闻数

        Returns:
            bool: 是否成功
        """
        self.stats.current_step = "同步新闻数据"
        logger.info(f"📰 {self.stats.current_step}...")

        try:
            # 计算回溯小时数
            if historical_days:
                hours_back = min(historical_days * 24, 24 * 7)  # 最多回溯7天新闻
            else:
                hours_back = 24 * 7  # 默认7天

            result = await self.sync_service.sync_news_data(
                hours_back=hours_back,
                max_news_per_stock=max_news_per_stock
            )

            if result:
                self.stats.news_count = result.get("news_count", 0)
                logger.info(f"✅ 新闻数据初始化完成: {self.stats.news_count}条新闻")
            else:
                logger.warning("⚠️ 新闻数据初始化失败")
        except Exception as e:
            logger.warning(f"⚠️ 新闻数据初始化失败: {e}（继续后续步骤）")

        self.stats.completed_steps += 1
        return True

    async def _step_verify_data_integrity(self) -> bool:
        """步骤8: 验证数据完整性

        Returns:
            bool: 是否成功

        Raises:
            Exception: 如果没有基础数据
        """
        self.stats.current_step = "验证数据完整性"
        logger.info(f"🔍 {self.stats.current_step}...")

        # 检查最终数据状态
        basic_count = await self.db.stock_basic_info.count_documents({})
        quotes_count = await self.db.market_quotes.count_documents({})

        # 检查数据质量
        extended_count = await self.db.stock_basic_info.count_documents({
            "full_symbol": {"$exists": True},
            "market_info": {"$exists": True}
        })

        logger.info(f"  数据完整性验证:")
        logger.info(f"    股票基础信息: {basic_count}条")
        if basic_count > 0:
            logger.info(f"    扩展字段覆盖: {extended_count}条 ({extended_count/basic_count*100:.1f}%)")
        logger.info(f"    行情数据: {quotes_count}条")

        if basic_count == 0:
            raise Exception("数据初始化失败：无基础数据")

        if basic_count > 0 and extended_count / basic_count < 0.9:  # 90%以上应该有扩展字段
            logger.warning("⚠️ 扩展字段覆盖率较低，可能存在数据质量问题")

        self.stats.completed_steps += 1
        logger.info(f"✅ {self.stats.current_step}完成")
        return True

    def _get_initialization_summary(self) -> Dict[str, Any]:
        """获取初始化总结

        Returns:
            Dict: 包含初始化结果的字典
        """
        duration = 0
        if self.stats.finished_at:
            duration = (self.stats.finished_at - self.stats.started_at).total_seconds()

        return {
            "success": self.stats.completed_steps == self.stats.total_steps,
            "started_at": self.stats.started_at,
            "finished_at": self.stats.finished_at,
            "duration": duration,
            "completed_steps": self.stats.completed_steps,
            "total_steps": self.stats.total_steps,
            "progress": f"{self.stats.completed_steps}/{self.stats.total_steps}",
            "data_summary": {
                "basic_info_count": self.stats.basic_info_count,
                "historical_records": self.stats.historical_records,
                "daily_records": getattr(self.stats, 'historical_records', 0),  # 日线数据
                "weekly_records": getattr(self.stats, 'weekly_records', 0),     # 周线数据
                "monthly_records": getattr(self.stats, 'monthly_records', 0),   # 月线数据
                "financial_records": self.stats.financial_records,
                "quotes_count": self.stats.quotes_count,
                "news_count": self.stats.news_count
            },
            "errors": self.stats.errors,
            "current_step": self.stats.current_step
        }
