# -*- coding: utf-8 -*-
"""
Tushare财务数据同步
负责财务数据的同步
"""

from datetime import datetime
from typing import List, Dict, Any
import logging

from .base import TushareSyncBase

logger = logging.getLogger(__name__)


class TushareFinancialSync(TushareSyncBase):
    """
    Tushare财务数据同步服务
    负责财务数据的同步
    """

    async def sync_financial_data(
        self, symbols: List[str] = None, limit: int = 20, job_id: str = None
    ) -> Dict[str, Any]:
        """
        同步财务数据

        Args:
            symbols: 股票代码列表，None表示同步所有股票
            limit: 获取财报期数，默认20期（约5年数据）
            job_id: 任务ID（用于进度跟踪）
        """
        logger.info(f"🔄 开始同步财务数据 (获取最近 {limit} 期)...")

        stats = {
            "total_processed": 0,
            "success_count": 0,
            "error_count": 0,
            "start_time": datetime.utcnow(),
            "errors": [],
        }

        try:
            # 获取股票列表
            if symbols is None:
                cursor = self.db.stock_basic_info.find(
                    {
                        "$or": [
                            {"market_info.market": "CN"},  # 新数据结构
                            {"category": "stock_cn"},  # 旧数据结构
                            {
                                "market": {
                                    "$in": ["主板", "创业板", "科创板", "北交所"]
                                }
                            },  # 按市场类型
                        ]
                    },
                    {"code": 1},
                )
                symbols = [doc["code"] async for doc in cursor]
                logger.info(f"📋 从 stock_basic_info 获取到 {len(symbols)} 只股票")

            stats["total_processed"] = len(symbols)
            logger.info(f"📊 需要同步 {len(symbols)} 只股票财务数据")

            # 批量处理
            for i, symbol in enumerate(symbols):
                try:
                    # 速率限制
                    await self.rate_limiter.acquire()

                    # 获取财务数据（指定获取期数）
                    financial_data = await self.provider.get_financial_data(
                        symbol, limit=limit
                    )

                    if financial_data:
                        # 保存财务数据
                        success = await self._save_financial_data(
                            symbol, financial_data
                        )
                        if success:
                            stats["success_count"] += 1
                        else:
                            stats["error_count"] += 1
                    else:
                        logger.warning(f"⚠️ {symbol}: 无财务数据")

                    # 进度日志和进度跟踪
                    if (i + 1) % 20 == 0:
                        progress = int((i + 1) / len(symbols) * 100)
                        logger.info(
                            f"📈 财务数据同步进度: {i + 1}/{len(symbols)} ({progress}%) "
                            f"(成功: {stats['success_count']}, 错误: {stats['error_count']})"
                        )
                        # 输出速率限制器统计
                        limiter_stats = self.rate_limiter.get_stats()
                        logger.info(
                            f"   速率限制: {limiter_stats['current_calls']}/{limiter_stats['max_calls']}次"
                        )

                        # 更新任务进度
                        if job_id:
                            from app.services.scheduler import (
                                update_job_progress,
                                TaskCancelledException,
                            )

                            try:
                                await update_job_progress(
                                    job_id=job_id,
                                    progress=progress,
                                    message=f"正在同步 {symbol} 财务数据",
                                    current_item=symbol,
                                    total_items=len(symbols),
                                    processed_items=i + 1,
                                )
                            except TaskCancelledException:
                                # 任务被取消，记录并退出
                                logger.warning(
                                    f"⚠️ 财务数据同步任务被用户取消 (已处理 {i + 1}/{len(symbols)})"
                                )
                                stats["end_time"] = datetime.utcnow()
                                stats["duration"] = (
                                    stats["end_time"] - stats["start_time"]
                                ).total_seconds()
                                stats["cancelled"] = True
                                raise

                except Exception as e:
                    stats["error_count"] += 1
                    stats["errors"].append(
                        {
                            "code": symbol,
                            "error": str(e),
                            "context": "sync_financial_data",
                        }
                    )
                    logger.error(f"❌ {symbol} 财务数据同步失败: {e}")

            # 完成统计
            stats["end_time"] = datetime.utcnow()
            stats["duration"] = (
                stats["end_time"] - stats["start_time"]
            ).total_seconds()

            logger.info(
                f"✅ 财务数据同步完成: "
                f"成功 {stats['success_count']}/{stats['total_processed']}, "
                f"错误 {stats['error_count']} 个, "
                f"耗时 {stats['duration']:.2f} 秒"
            )

            return stats

        except Exception as e:
            logger.error(f"❌ 财务数据同步失败: {e}")
            stats["errors"].append({"error": str(e), "context": "sync_financial_data"})
            return stats

    # _save_financial_data 方法继承自 BaseSyncService
