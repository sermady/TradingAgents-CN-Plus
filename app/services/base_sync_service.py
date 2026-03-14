# -*- coding: utf-8 -*-
"""
数据同步服务抽象基类
提供同步服务的通用方法和工具函数
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
import asyncio
import logging

logger = logging.getLogger(__name__)


@dataclass
class SyncStats:
    """同步统计信息（标准化统计类）"""

    total_processed: int = 0
    success_count: int = 0
    error_count: int = 0
    skipped_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.utcnow()

    @property
    def duration(self) -> float:
        """计算同步持续时间（秒）"""
        end = self.end_time or datetime.utcnow()
        if self.start_time is None:
            return 0.0
        return (end - self.start_time).total_seconds()

    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.total_processed == 0:
            return 0.0
        return (self.success_count / self.total_processed) * 100

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_processed": self.total_processed,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "skipped_count": self.skipped_count,
            "created_count": self.created_count,
            "updated_count": self.updated_count,
            "duration": self.duration,
            "success_rate": f"{self.success_rate:.1f}%",
            "errors": self.errors[:10],  # 只返回前10个错误
        }


class BaseSyncService(ABC):
    """数据同步服务抽象基类"""

    def __init__(self):
        self.provider = None
        self.db = None
        self.historical_service = None
        self.news_service = None
        self.batch_size = 100
        self.rate_limit_delay = 0.2

    @property
    @abstractmethod
    def data_source(self) -> str:
        """数据源标识符（如 'tushare', 'akshare', 'baostock'）"""
        raise NotImplementedError

    @abstractmethod
    async def initialize(self):
        """初始化同步服务"""
        raise NotImplementedError

    # ==================== 通用工具方法 ====================

    def _is_data_fresh(self, updated_at: Any, hours: int = 24) -> bool:
        """检查数据是否新鲜

        Args:
            updated_at: 最后更新时间
            hours: 新鲜度阈值（小时）

        Returns:
            True 如果数据新鲜
        """
        if not updated_at:
            return False

        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except ValueError:
                return False

        threshold = datetime.utcnow() - timedelta(hours=hours)
        return updated_at > threshold

    async def _get_last_sync_date(self, symbol: str = None) -> str:
        """获取最后同步日期

        Args:
            symbol: 股票代码，如果提供则返回该股票的最后日期+1天

        Returns:
            日期字符串 (YYYY-MM-DD)
        """
        try:
            if self.historical_service is None:
                from app.services.historical_data_service import (
                    get_historical_data_service,
                )

                self.historical_service = await get_historical_data_service()

            if symbol:
                # 获取特定股票的最新日期
                latest_date = await self.historical_service.get_latest_date(
                    symbol, self.data_source
                )
                if latest_date:
                    # 返回最后日期的下一天（避免重复同步）
                    try:
                        last_date_obj = datetime.strptime(latest_date, "%Y-%m-%d")
                        next_date = last_date_obj + timedelta(days=1)
                        return next_date.strftime("%Y-%m-%d")
                    except (ValueError, TypeError):
                        # 如果日期格式不对，直接返回
                        return latest_date
                else:
                    # 没有历史数据时，从上市日期开始全量同步
                    stock_info = await self.db.stock_basic_info.find_one(
                        {"code": symbol}, {"list_date": 1}
                    )
                    if stock_info and stock_info.get("list_date"):
                        list_date = stock_info["list_date"]
                        # 处理不同的日期格式
                        if isinstance(list_date, str):
                            # 格式可能是 "20100101" 或 "2010-01-01"
                            if len(list_date) == 8 and list_date.isdigit():
                                return (
                                    f"{list_date[:4]}-{list_date[4:6]}-{list_date[6:]}"
                                )
                            else:
                                return list_date
                        else:
                            return list_date.strftime("%Y-%m-%d")

                    # 如果没有上市日期，从1990年开始
                    logger.warning(f"⚠️ {symbol}: 未找到上市日期，从1990-01-01开始同步")
                    return "1990-01-01"

            # 默认返回30天前（确保不漏数据）
            return (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        except Exception as e:
            logger.error(f"❌ 获取最后同步日期失败 {symbol}: {e}")
            # 出错时返回30天前，确保不漏数据
            return (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    async def _save_financial_data(
        self, symbol: str, financial_data: Dict[str, Any]
    ) -> bool:
        """保存财务数据

        Args:
            symbol: 股票代码
            financial_data: 财务数据字典

        Returns:
            True 如果保存成功
        """
        try:
            # 使用统一的财务数据服务
            from app.services.financial_data_service import get_financial_data_service

            financial_service = await get_financial_data_service()

            # 保存财务数据
            saved_count = await financial_service.save_financial_data(
                symbol=symbol,
                financial_data=financial_data,
                data_source=self.data_source,
                market="CN",
                report_period=financial_data.get("report_period"),
                report_type=financial_data.get("report_type", "quarterly"),
            )

            return saved_count > 0

        except Exception as e:
            logger.error(f"❌ 保存 {symbol} 财务数据失败: {e}")
            return False

    async def _process_news_batch(
        self,
        batch: List[str],
        max_news_per_stock: int,
        hours_back: int = None,
        rate_limiter=None,
    ) -> Dict[str, Any]:
        """处理新闻批次

        Args:
            batch: 股票代码批次
            max_news_per_stock: 每只股票最大新闻数
            hours_back: 获取多少小时内的新闻（可选）
            rate_limiter: 速率限制器（可选）

        Returns:
            批次处理统计
        """
        batch_stats = {
            "success_count": 0,
            "error_count": 0,
            "news_count": 0,
            "errors": [],
        }

        for symbol in batch:
            try:
                # 构建获取新闻的参数
                kwargs = {"symbol": symbol, "limit": max_news_per_stock}
                if hours_back is not None:
                    kwargs["hours_back"] = hours_back

                # 获取新闻数据
                news_data = await self.provider.get_stock_news(**kwargs)

                if news_data:
                    # 保存新闻数据
                    saved_count = await self.news_service.save_news_data(
                        news_data=news_data, data_source=self.data_source, market="CN"
                    )

                    batch_stats["success_count"] += 1
                    batch_stats["news_count"] += saved_count

                    logger.debug(f"✅ {symbol} 新闻同步成功: {saved_count}条")
                else:
                    logger.debug(f"⚠️ {symbol} 未获取到新闻数据")
                    batch_stats["success_count"] += 1  # 没有新闻也算成功

                # API限流
                if rate_limiter:
                    await rate_limiter.acquire()
                else:
                    await asyncio.sleep(self.rate_limit_delay)

            except Exception as e:
                batch_stats["error_count"] += 1
                error_msg = f"{symbol}: {str(e)}"
                batch_stats["errors"].append(error_msg)
                logger.error(f"❌ {symbol} 新闻同步失败: {e}")

                # 失败后也要休眠，避免"失败雪崩"
                await asyncio.sleep(1.0)

        return batch_stats

    async def _should_stop(self, job_id: str) -> bool:
        """检查任务是否应该停止

        Args:
            job_id: 任务ID

        Returns:
            True 如果任务应该停止
        """
        try:
            # 查询执行记录，检查 cancel_requested 标记
            execution = await self.db.scheduler_executions.find_one(
                {"job_id": job_id, "status": "running"}, sort=[("timestamp", -1)]
            )

            if execution and execution.get("cancel_requested"):
                return True

            return False

        except Exception as e:
            logger.error(f"❌ 检查任务停止标记失败: {e}")
            return False

    async def _update_progress(self, job_id: str, progress: int, message: str):
        """更新任务进度

        Args:
            job_id: 任务ID
            progress: 进度百分比 (0-100)
            message: 进度消息
        """
        try:
            from app.services.scheduler import TaskCancelledException

            logger.info(f"📊 [进度更新] 任务 {job_id} 进度: {progress}% - {message}")

            # 更新执行记录
            await self.db.scheduler_executions.update_one(
                {"job_id": job_id, "status": "running"},
                {
                    "$set": {
                        "progress": progress,
                        "progress_message": message,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )

            # 检查是否被取消
            if await self._should_stop(job_id):
                raise TaskCancelledException(f"任务 {job_id} 已被取消")

        except TaskCancelledException:
            raise
        except Exception as e:
            logger.error(f"❌ 更新任务进度失败: {e}")

    # ==================== 批量处理模板方法 ====================

    async def execute_batch_sync(
        self,
        items: List[Any],
        process_func: Callable[[Any], Any],
        stats: Optional[SyncStats] = None,
        batch_size: Optional[int] = None,
        rate_limit_delay: Optional[float] = None,
        task_name: str = "同步任务",
    ) -> SyncStats:
        """
        执行批量同步的模板方法

        🔥 这个方法封装了标准的批量处理流程：
        1. 分批处理数据
        2. 统计成功/失败数量
        3. 速率限制控制
        4. 错误收集

        Args:
            items: 要处理的数据项列表
            process_func: 处理单个数据项的函数
            stats: 同步统计对象（如不提供则自动创建）
            batch_size: 批次大小（默认使用 self.batch_size）
            rate_limit_delay: 速率限制延迟（默认使用 self.rate_limit_delay）
            task_name: 任务名称（用于日志）

        Returns:
            SyncStats: 同步统计信息
        """
        if stats is None:
            stats = SyncStats()

        batch_size = batch_size or self.batch_size
        rate_limit_delay = rate_limit_delay or self.rate_limit_delay

        total_items = len(items)
        stats.total_processed = total_items

        logger.info(f"🔄 开始{task_name}: 共 {total_items} 项，批次大小 {batch_size}")

        # 分批处理
        for i in range(0, total_items, batch_size):
            batch = items[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_items + batch_size - 1) // batch_size

            logger.info(f"📦 处理批次 {batch_num}/{total_batches} ({len(batch)} 项)")

            for item in batch:
                try:
                    result = await process_func(item)

                    if result:
                        stats.success_count += 1
                    else:
                        stats.skipped_count += 1

                    # 速率限制
                    await asyncio.sleep(rate_limit_delay)

                except Exception as e:
                    stats.error_count += 1
                    error_msg = f"处理失败: {item}: {str(e)}"
                    stats.errors.append(error_msg)
                    logger.error(f"❌ {error_msg}")

                    # 失败后也要休眠，避免"失败雪崩"
                    await asyncio.sleep(1.0)

            # 批次进度日志
            progress = min(100, int((i + len(batch)) / total_items * 100))
            logger.info(
                f"📊 {task_name}进度: {progress}% ({stats.success_count} 成功, {stats.error_count} 失败)"
            )

        stats.end_time = datetime.utcnow()
        logger.info(
            f"✅ {task_name}完成: {stats.success_count}/{total_items} 成功 ({stats.success_rate:.1f}%)"
        )

        return stats


# 导出公共接口
__all__ = [
    "BaseSyncService",
    "SyncStats",
]
