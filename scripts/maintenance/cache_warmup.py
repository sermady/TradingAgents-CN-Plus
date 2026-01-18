# -*- coding: utf-8 -*-
"""
缓存预热脚本
Cache Warmup Script

预加载热门股票和市场数据到缓存，提升查询性能。
Preloads hot stocks and market data into cache to improve query performance.

使用场景 Use Cases:
1. 系统启动后预热缓存 Warm up cache after system startup
2. 定时任务刷新热数据 Scheduled refresh of hot data
3. 缓存失效后的恢复 Recover cache after invalidation

作者 Author: Claude
创建日期 Created: 2026-01-18
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import logging
import sys

from tradingagents.dataflows.data_source_manager import (
    get_data_source_manager,
    get_china_stock_data_unified,
)
from tradingagents.dataflows.cache.smart_cache import SmartCache, CacheMonitor


# 创建UTF-8编码的StreamHandler
class UTF8StreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # 确保使用UTF-8编码输出
            if hasattr(stream, "buffer"):
                stream.buffer.write((msg + self.terminator).encode("utf-8"))
                stream.buffer.flush()
            else:
                stream.write(msg + self.terminator)
                stream.flush()
        except Exception:
            self.handleError(record)


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/cache_warmup.log", encoding="utf-8"),
        UTF8StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class CacheWarmupManager:
    """缓存预热管理器 Cache Warmup Manager"""

    def __init__(self):
        """初始化预热管理器 Initialize warmup manager"""
        self.data_source = get_data_source_manager()
        self.stats = {
            "total_tasks": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": None,
            "end_time": None,
            "errors": [],
        }

    async def warmup_all(self, parallel_tasks: int = 10) -> Dict[str, Any]:
        """
        执行全部预热任务 Execute all warmup tasks

        Args:
            parallel_tasks: 并发任务数 Number of parallel tasks

        Returns:
            预热统计信息 Warmup statistics
        """
        logger.info("=" * 60)
        logger.info("开始缓存预热 Starting cache warmup")
        logger.info(f"并发任务数 Parallel tasks: {parallel_tasks}")
        logger.info("=" * 60)

        self.stats["start_time"] = time.time()

        try:
            # 1. 预热热门股票列表
            logger.info("\n[1/3] 预热热门股票列表 Warming up hot stock list...")
            await self._warmup_hot_stocks(parallel_tasks)

            # 2. 预热大盘指数
            logger.info("\n[2/3] 预热大盘指数 Warming up major indices...")
            await self._warmup_major_indices(parallel_tasks)

            # 3. 预热最新新闻
            logger.info("\n[3/3] 预热最新新闻 Warming up latest news...")
            await self._warmup_news()

        except Exception as e:
            logger.error(
                f"预热过程发生错误 Error during warmup: {str(e)}", exc_info=True
            )
            self.stats["errors"].append(str(e))

        self.stats["end_time"] = time.time()
        self.stats["duration"] = self.stats["end_time"] - self.stats["start_time"]

        # 打印统计信息
        self._print_statistics()

        return self.stats

    async def _warmup_hot_stocks(self, parallel_tasks: int):
        """预热热门股票列表 Warm up hot stock list"""
        # 使用内置的热门股票列表
        hot_stocks = [
            "600519.SH",  # 贵州茅台
            "000858.SZ",  # 五粮液
            "600036.SH",  # 招商银行
            "000333.SZ",  # 美的集团
            "600030.SH",  # 中信证券
            "601318.SH",  # 中国平安
            "000651.SZ",  # 格力电器
            "600276.SH",  # 恒瑞医药
            "002415.SZ",  # 海康威视
            "600009.SH",  # 上海机场
        ]

        logger.info(
            f"预热 {len(hot_stocks)} 只热门股票 Warming up {len(hot_stocks)} hot stocks"
        )

        tasks = []
        for i, stock_code in enumerate(hot_stocks):
            logger.info(f"预热股票 Warming stock: {stock_code}")
            tasks.append(self._warmup_stock_data(stock_code))

            # 每5只股票等待一下，避免过载
            if (i + 1) % 5 == 0:
                await self._execute_tasks_parallel(tasks, parallel_tasks)
                tasks = []
                logger.info(
                    f"已处理 {i + 1}/{len(hot_stocks)} 只股票 Processed {i + 1}/{len(hot_stocks)} stocks"
                )

        # 执行剩余任务
        if tasks:
            await self._execute_tasks_parallel(tasks, parallel_tasks)

    async def _warmup_major_indices(self, parallel_tasks: int):
        """预热大盘指数 Warm up major indices"""
        major_indices = [
            "000001.SH",  # 上证指数
            "399001.SZ",  # 深证成指
            "399006.SZ",  # 创业板指
        ]

        logger.info(
            f"预热 {len(major_indices)} 个大盘指数 Warming up {len(major_indices)} major indices"
        )

        tasks = []
        for code in major_indices:
            logger.info(f"预热指数 Warming index: {code}")
            tasks.append(self._warmup_stock_data(code))

        await self._execute_tasks_parallel(tasks, parallel_tasks)

    async def _warmup_news(self):
        """预热最新新闻 Warm up latest news"""
        logger.info("预热市场新闻 Warming up market news...")

        try:
            # 获取最新市场新闻（同步方法）
            loop = asyncio.get_event_loop()
            news_data = await loop.run_in_executor(
                None, lambda: self.data_source.get_news_data(limit=50)
            )
            logger.info(
                f"成功预热 {len(news_data)} 条新闻数据 Successfully warmed up news data"
            )
            self.stats["successful"] += 1

        except Exception as e:
            logger.warning(f"预热新闻失败 Failed to warm up news: {str(e)}")
            self.stats["failed"] += 1
            self.stats["errors"].append(f"News warmup: {str(e)}")

    async def _warmup_stock_data(self, stock_code: str):
        """预热股票数据 Warm up stock data"""
        try:
            logger.debug(f"预热股票数据 Warming stock data: {stock_code}")

            # 使用统一数据接口获取股票数据（会自动缓存）- 同步方法
            end_date = datetime.now()
            start_date = end_date - timedelta(days=60)

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: get_china_stock_data_unified(
                    stock_code,
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"),
                ),
            )

            self.stats["successful"] += 1

        except Exception as e:
            logger.debug(
                f"预热股票数据失败 Failed to warm stock data: {stock_code} - {str(e)}"
            )
            self.stats["failed"] += 1

    async def _execute_tasks_parallel(self, tasks: List, parallel_tasks: int):
        """并行执行预热任务 Execute warmup tasks in parallel"""
        if not tasks:
            return

        self.stats["total_tasks"] += len(tasks)

        # 使用信号量控制并发数
        semaphore = asyncio.Semaphore(parallel_tasks)

        async def run_with_semaphore(task):
            async with semaphore:
                await task

        # 执行所有任务
        await asyncio.gather(*[run_with_semaphore(task) for task in tasks])

    def _print_statistics(self):
        """打印预热统计信息 Print warmup statistics"""
        logger.info("\n" + "=" * 60)
        logger.info("预热统计信息 Warmup Statistics")
        logger.info("=" * 60)
        logger.info(f"总任务数 Total tasks: {self.stats['total_tasks']}")
        logger.info(f"成功数 Successful: {self.stats['successful']}")
        logger.info(f"失败数 Failed: {self.stats['failed']}")
        logger.info(f"跳过数 Skipped: {self.stats['skipped']}")

        if self.stats["total_tasks"] > 0:
            logger.info(
                f"成功率 Success rate: {self.stats['successful'] / self.stats['total_tasks'] * 100:.2f}%"
            )

        if self.stats["start_time"] and self.stats["end_time"]:
            logger.info(f"耗时 Duration: {self.stats['duration']:.2f} 秒 seconds")

        if self.stats["errors"]:
            logger.info(f"\n错误列表 Error List:")
            for error in self.stats["errors"][:10]:  # 只显示前10个错误
                logger.info(f"  - {error}")

        logger.info("=" * 60 + "\n")


async def main():
    """主函数 Main function"""
    # 创建日志目录
    import os

    os.makedirs("logs", exist_ok=True)

    # 创建预热管理器
    manager = CacheWarmupManager()

    # 执行预热
    stats = await manager.warmup_all(parallel_tasks=5)

    # 返回状态码
    return 0 if stats["failed"] < stats["total_tasks"] * 0.1 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
