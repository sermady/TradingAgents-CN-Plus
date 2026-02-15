# -*- coding: utf-8 -*-
"""
Tushare新闻数据同步
负责新闻数据的同步
"""

from datetime import datetime
from typing import List, Dict, Any
import logging
import asyncio

from .base import TushareSyncBase

logger = logging.getLogger(__name__)


class TushareNewsSync(TushareSyncBase):
    """
    Tushare新闻数据同步服务
    负责新闻数据的同步
    """

    async def sync_news_data(
        self,
        symbols: List[str] = None,
        hours_back: int = 24,
        max_news_per_stock: int = 20,
        force_update: bool = False,
        job_id: str = None,
    ) -> Dict[str, Any]:
        """
        同步新闻数据

        Args:
            symbols: 股票代码列表，为None时获取所有股票
            hours_back: 回溯小时数，默认24小时
            max_news_per_stock: 每只股票最大新闻数量
            force_update: 是否强制更新
            job_id: 任务ID（用于进度跟踪）

        Returns:
            同步结果统计
        """
        logger.info("🔄 开始同步新闻数据...")

        stats = {
            "total_processed": 0,
            "success_count": 0,
            "error_count": 0,
            "news_count": 0,
            "start_time": datetime.utcnow(),
            "errors": [],
        }

        try:
            # 1. 获取股票列表
            if symbols is None:
                stock_list = await self.stock_service.get_all_stocks()
                symbols = [stock["code"] for stock in stock_list]

            if not symbols:
                logger.warning("⚠️ 没有找到需要同步新闻的股票")
                return stats

            stats["total_processed"] = len(symbols)
            logger.info(f"📊 需要同步 {len(symbols)} 只股票的新闻")

            # 2. 批量处理
            for i in range(0, len(symbols), self.batch_size):
                # 检查是否需要退出
                if job_id and await self._should_stop(job_id):
                    logger.warning(f"⚠️ 任务 {job_id} 收到停止信号，正在退出...")
                    stats["stopped"] = True
                    break

                batch = symbols[i : i + self.batch_size]
                batch_stats = await self._process_news_batch(
                    batch=batch,
                    max_news_per_stock=max_news_per_stock,
                    hours_back=hours_back,
                    rate_limiter=self.rate_limiter,
                )

                # 更新统计
                stats["success_count"] += batch_stats["success_count"]
                stats["error_count"] += batch_stats["error_count"]
                stats["news_count"] += batch_stats["news_count"]
                stats["errors"].extend(batch_stats["errors"])

                # 进度日志和进度更新
                progress = min(i + self.batch_size, len(symbols))
                progress_percent = int((progress / len(symbols)) * 100)
                logger.info(
                    f"📈 新闻同步进度: {progress}/{len(symbols)} ({progress_percent}%) "
                    f"(成功: {stats['success_count']}, 新闻: {stats['news_count']})"
                )

                # 更新任务进度
                if job_id:
                    await self._update_progress(
                        job_id,
                        progress_percent,
                        f"已处理 {progress}/{len(symbols)} 只股票，获取 {stats['news_count']} 条新闻",
                    )

            # 3. 完成统计
            stats["end_time"] = datetime.utcnow()
            stats["duration"] = (
                stats["end_time"] - stats["start_time"]
            ).total_seconds()

            logger.info(
                f"✅ 新闻数据同步完成: "
                f"总计 {stats['total_processed']} 只股票, "
                f"成功 {stats['success_count']} 只, "
                f"获取 {stats['news_count']} 条新闻, "
                f"错误 {stats['error_count']} 只, "
                f"耗时 {stats['duration']:.2f} 秒"
            )

            return stats

        except Exception as e:
            logger.error(f"❌ 新闻数据同步失败: {e}")
            stats["errors"].append({"error": str(e), "context": "sync_news_data"})
            return stats

    async def _process_news_batch(
        self,
        batch: List[str],
        max_news_per_stock: int,
        hours_back: int,
        rate_limiter,
    ) -> Dict[str, Any]:
        """处理新闻批次"""
        batch_stats = {
            "success_count": 0,
            "error_count": 0,
            "news_count": 0,
            "errors": [],
        }

        news_service = await self.news_data_service()

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
                    saved_count = await news_service.save_news_data(
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
