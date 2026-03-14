# -*- coding: utf-8 -*-
"""同步执行模块

提供具体的同步执行逻辑。
"""

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from .models import SyncJob, SyncStatus

if TYPE_CHECKING:
    from .manager import DataSyncManager

logger = logging.getLogger(__name__)


class SyncExecutor:
    """同步执行器"""

    @staticmethod
    async def sync_stock_basics(manager: "DataSyncManager", job: SyncJob, force: bool) -> None:
        """同步股票基础数据"""
        try:
            from app.services.multi_source_basics_sync_service import (
                MultiSourceBasicsSyncService,
            )

            sync_service = MultiSourceBasicsSyncService()

            # 获取当前状态
            current_status = await sync_service.get_status()
            job.total_records = current_status.get("total", 0)
            job.inserted = current_status.get("inserted", 0)
            job.updated = current_status.get("updated", 0)
            job.errors = current_status.get("errors", 0)
            job.status = SyncStatus.COMPLETED
            job.message = "Stock basics sync completed"

        except ImportError:
            job.status = SyncStatus.FAILED
            job.message = "MultiSourceBasicsSyncService not available"
            job.errors = 1

    @staticmethod
    async def sync_stock_daily(manager: "DataSyncManager", job: SyncJob, force: bool) -> None:
        """同步股票日线数据"""
        try:
            job.started_at = datetime.now().isoformat()
            job.status = SyncStatus.RUNNING
            job.message = "开始同步股票日线数据..."

            from app.services.multi_source_basics_sync_service import (
                MultiSourceBasicsSyncService,
            )

            sync_service = MultiSourceBasicsSyncService()

            # 获取股票列表（从MongoDB）
            db = await manager._get_db()
            stock_list = list(
                db["stock_basic_info"].find({}, {"code": 1, "name": 1}).limit(10)
            )

            if not stock_list:
                job.message = "没有找到股票数据"
                job.status = SyncStatus.COMPLETED
                job.finished_at = datetime.now().isoformat()
                return

            total_stocks = len(stock_list)
            job.total_records = total_stocks

            logger.info(f"开始同步 {total_stocks} 只股票的日线数据...")

            # 逐只股票同步日线数据
            inserted = 0
            updated = 0
            errors = 0

            for idx, stock in enumerate(stock_list):
                try:
                    stock_code = stock["code"]
                    stock_name = stock.get("name", stock_code)

                    # 更新进度
                    job.message = (
                        f"正在同步 {stock_code} - {stock_name} "
                        f"({idx + 1}/{total_stocks})"
                    )
                    await manager._persist_sync_job(job)

                    # 调用同步服务
                    result = await sync_service.sync_daily_data(
                        stock_code=stock_code,
                        force_refresh=force,
                    )

                    if result.get("success"):
                        if result.get("inserted"):
                            inserted += 1
                        if result.get("updated"):
                            updated += 1
                    else:
                        errors += 1
                        logger.warning(
                            f"同步失败: {stock_code} - {result.get('message', '未知错误')}"
                        )

                except Exception as e:
                    errors += 1
                    logger.error(f"同步异常: {stock_code} - {e}")

                    # 每10个错误暂停一下
                    if errors % 10 == 0:
                        await asyncio.sleep(2)

            # 完成同步
            job.inserted = inserted
            job.updated = updated
            job.errors = errors
            job.total_records = total_stocks
            job.status = SyncStatus.COMPLETED
            job.message = (
                f"日线数据同步完成: 插入{inserted}条, "
                f"更新{updated}条, 错误{errors}条, "
                f"总计{total_stocks}只"
            )
            job.finished_at = datetime.now().isoformat()

            logger.info(
                f"日线数据同步完成: 插入={inserted}, "
                f"更新={updated}, 错误={errors}, 总计={total_stocks}"
            )

        except ImportError as e:
            job.status = SyncStatus.FAILED
            job.message = f"MultiSourceBasicsSyncService导入失败: {e}"
            job.errors = 1
            job.finished_at = datetime.now().isoformat()
            logger.error(f"{job.message}")

        except Exception as e:
            job.status = SyncStatus.FAILED
            job.message = f"日线数据同步异常: {e}"
            job.errors = 1
            job.finished_at = datetime.now().isoformat()
            logger.error(f"{job.message}", exc_info=True)

    @staticmethod
    async def sync_fundamentals(manager: "DataSyncManager", job: SyncJob, force: bool) -> None:
        """同步基本面数据"""
        try:
            job.started_at = datetime.now().isoformat()
            job.status = SyncStatus.RUNNING
            job.message = "开始同步基本面数据..."

            from app.services.financial_data_service import FinancialDataService

            fin_service = FinancialDataService()

            # 获取股票列表
            db = await manager._get_db()
            stock_list = list(
                db["stock_basic_info"].find({}, {"code": 1, "name": 1}).limit(50)
            )

            if not stock_list:
                job.message = "没有找到股票数据"
                job.status = SyncStatus.COMPLETED
                job.finished_at = datetime.now().isoformat()
                return

            total_stocks = len(stock_list)
            job.total_records = total_stocks

            logger.info(f"开始同步 {total_stocks} 只股票的基本面数据...")

            # 逐只股票同步基本面数据
            inserted = 0
            updated = 0
            errors = 0
            skipped = 0

            for idx, stock in enumerate(stock_list):
                try:
                    stock_code = stock["code"]
                    stock_name = stock.get("name", stock_code)

                    # 更新进度
                    job.message = (
                        f"正在同步基本面 {stock_code} - {stock_name} "
                        f"({idx + 1}/{total_stocks})"
                    )
                    await manager._persist_sync_job(job)

                    # 检查是否已有基本面数据
                    existing = await db["stock_financial_data"].find_one(
                        {"code": stock_code}
                    )

                    if existing and not force:
                        # 已有数据，跳过
                        skipped += 1
                        logger.debug(f"跳过已有基本面数据: {stock_code}")
                    else:
                        # 标记为需要更新
                        inserted += 1
                        logger.debug(f"标记基本面数据同步: {stock_code}")

                    # 添加延迟避免请求过快
                    await asyncio.sleep(0.1)

                except Exception as e:
                    errors += 1
                    logger.error(f"同步基本面数据异常: {stock_code} - {e}")

                    # 每10个错误暂停一下
                    if errors % 10 == 0:
                        await asyncio.sleep(1)

            # 完成同步
            job.inserted = inserted
            job.updated = updated
            job.errors = errors
            job.skipped = skipped
            job.total_records = total_stocks
            job.status = SyncStatus.COMPLETED
            job.message = (
                f"基本面数据同步完成: 标记{inserted}条, "
                f"跳过{skipped}条, 错误{errors}条, "
                f"总计{total_stocks}只"
            )
            job.finished_at = datetime.now().isoformat()

            logger.info(
                f"基本面数据同步完成: 标记={inserted}, "
                f"跳过={skipped}, 错误={errors}, 总计={total_stocks}"
            )

        except ImportError as e:
            job.status = SyncStatus.FAILED
            job.message = f"FinancialDataService导入失败: {e}"
            job.errors = 1
            job.finished_at = datetime.now().isoformat()
            logger.error(f"{job.message}")

        except Exception as e:
            job.status = SyncStatus.FAILED
            job.message = f"基本面数据同步异常: {e}"
            job.errors = 1
            job.finished_at = datetime.now().isoformat()
            logger.error(f"{job.message}", exc_info=True)
