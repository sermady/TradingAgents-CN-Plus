# -*- coding: utf-8 -*-
"""
Tushare实时行情同步
负责实时行情数据的同步
"""

from datetime import datetime
from typing import List, Dict, Any
import logging
import asyncio

from .base import TushareSyncBase

logger = logging.getLogger(__name__)


class TushareRealtimeSync(TushareSyncBase):
    """
    Tushare实时行情同步服务
    负责实时行情数据的同步
    """

    async def sync_realtime_quotes(
        self, symbols: List[str] = None, force: bool = False
    ) -> Dict[str, Any]:
        """
        同步实时行情数据

        策略：
        - 如果指定了少量股票（≤10只），自动切换到 AKShare 接口（避免浪费 Tushare rt_k 配额）
        - 如果指定了大量股票或全市场，使用 Tushare 批量接口一次性获取

        Args:
            symbols: 指定股票代码列表，为空则同步所有股票；如果指定了股票列表，则只保存这些股票的数据
            force: 是否强制执行（跳过交易时间检查），默认 False

        Returns:
            同步结果统计
        """
        stats = {
            "total_processed": 0,
            "success_count": 0,
            "error_count": 0,
            "start_time": datetime.utcnow(),
            "errors": [],
            "stopped_by_rate_limit": False,
            "skipped_non_trading_time": False,
            "switched_to_akshare": False,  # 是否切换到 AKShare
        }

        try:
            # 检查是否在交易时间（手动同步时可以跳过检查）
            if not force and not self.is_trading_time():
                logger.info(
                    "⏸️ 当前不在交易时间，跳过实时行情同步（使用 force=True 可强制执行）"
                )
                stats["skipped_non_trading_time"] = True
                return stats

            # 🔥 策略选择：少量股票切换到 AKShare，大量股票或全市场用 Tushare 批量接口
            USE_AKSHARE_THRESHOLD = 10  # 少于等于10只股票时切换到 AKShare

            if symbols and len(symbols) <= USE_AKSHARE_THRESHOLD:
                # 🔥 自动切换到 AKShare（避免浪费 Tushare rt_k 配额，每小时只能调用2次）
                logger.info(
                    f"💡 股票数量 ≤{USE_AKSHARE_THRESHOLD} 只，自动切换到 AKShare 接口"
                    f"（避免浪费 Tushare rt_k 配额，每小时只能调用2次）"
                )
                logger.info(
                    f"🎯 使用 AKShare 同步 {len(symbols)} 只股票的实时行情: {symbols}"
                )

                # 调用 AKShare 服务
                from app.worker.akshare_sync_service import get_akshare_sync_service

                akshare_service = await get_akshare_sync_service()

                if not akshare_service:
                    logger.error("❌ AKShare 服务不可用，回退到 Tushare 批量接口")
                    # 回退到 Tushare 批量接口
                    quotes_map = await self.provider.get_realtime_quotes_batch()
                    if quotes_map and symbols:
                        quotes_map = {
                            symbol: quotes_map[symbol]
                            for symbol in symbols
                            if symbol in quotes_map
                        }
                else:
                    # 使用 AKShare 同步
                    akshare_result = await akshare_service.sync_realtime_quotes(
                        symbols=symbols, force=force
                    )
                    stats["switched_to_akshare"] = True
                    stats["success_count"] = akshare_result.get("success_count", 0)
                    stats["error_count"] = akshare_result.get("error_count", 0)
                    stats["total_processed"] = akshare_result.get("total_processed", 0)
                    stats["errors"] = akshare_result.get("errors", [])
                    stats["end_time"] = datetime.utcnow()
                    stats["duration"] = (
                        stats["end_time"] - stats["start_time"]
                    ).total_seconds()

                    logger.info(
                        f"✅ AKShare 实时行情同步完成: "
                        f"总计 {stats['total_processed']} 只, "
                        f"成功 {stats['success_count']} 只, "
                        f"错误 {stats['error_count']} 只, "
                        f"耗时 {stats['duration']:.2f} 秒"
                    )
                    return stats
            else:
                # 使用 Tushare 批量接口一次性获取全市场行情
                if symbols:
                    logger.info(
                        f"📊 使用 Tushare 批量接口同步 {len(symbols)} 只股票的实时行情（从全市场数据中筛选）"
                    )
                else:
                    logger.info("📊 使用 Tushare 批量接口同步全市场实时行情...")

                logger.info("📡 调用 rt_k 批量接口获取全市场实时行情...")
                quotes_map = await self.provider.get_realtime_quotes_batch()

                if not quotes_map:
                    logger.warning("⚠️ 未获取到实时行情数据")
                    return stats

                logger.info(f"✅ 获取到 {len(quotes_map)} 只股票的实时行情")

                # 🔥 如果指定了股票列表，只处理这些股票
                if symbols:
                    # 过滤出指定的股票
                    filtered_quotes_map = {
                        symbol: quotes_map[symbol]
                        for symbol in symbols
                        if symbol in quotes_map
                    }

                    # 检查是否有股票未找到
                    missing_symbols = [s for s in symbols if s not in quotes_map]
                    if missing_symbols:
                        logger.warning(
                            f"⚠️ 以下股票未在实时行情中找到: {missing_symbols}"
                        )

                    quotes_map = filtered_quotes_map
                    logger.info(f"🔍 过滤后保留 {len(quotes_map)} 只指定股票的行情")

            if not quotes_map:
                logger.warning("⚠️ 未获取到任何实时行情数据")
                return stats

            stats["total_processed"] = len(quotes_map)

            # 批量保存到数据库
            success_count = 0
            error_count = 0

            for symbol, quote_data in quotes_map.items():
                try:
                    # 保存到数据库
                    result = await self.stock_service.update_market_quotes(
                        symbol, quote_data
                    )
                    if result:
                        success_count += 1
                    else:
                        error_count += 1
                        stats["errors"].append(
                            {
                                "code": symbol,
                                "error": "更新数据库失败",
                                "context": "sync_realtime_quotes",
                            }
                        )
                except Exception as e:
                    error_count += 1
                    stats["errors"].append(
                        {
                            "code": symbol,
                            "error": str(e),
                            "context": "sync_realtime_quotes",
                        }
                    )

            stats["success_count"] = success_count
            stats["error_count"] = error_count

            # 完成统计
            stats["end_time"] = datetime.utcnow()
            stats["duration"] = (
                stats["end_time"] - stats["start_time"]
            ).total_seconds()

            logger.info(
                f"✅ 实时行情同步完成: "
                f"总计 {stats['total_processed']} 只, "
                f"成功 {stats['success_count']} 只, "
                f"错误 {stats['error_count']} 只, "
                f"耗时 {stats['duration']:.2f} 秒"
            )

            return stats

        except Exception as e:
            # 检查是否为限流错误
            error_msg = str(e)
            if self.is_rate_limit_error(error_msg):
                stats["stopped_by_rate_limit"] = True
                logger.error(f"❌ 实时行情同步失败（API限流）: {e}")
            else:
                logger.error(f"❌ 实时行情同步失败: {e}")

            stats["errors"].append({"error": str(e), "context": "sync_realtime_quotes"})
            return stats

    async def _get_and_save_quotes(self, symbol: str) -> bool:
        """获取并保存单个股票行情"""
        try:
            quotes = await self.provider.get_stock_quotes(symbol)
            if quotes:
                # 转换为字典格式（如果是Pydantic模型）
                if hasattr(quotes, "model_dump"):
                    quotes_data = quotes.model_dump()
                elif hasattr(quotes, "dict"):
                    quotes_data = quotes.dict()
                else:
                    quotes_data = quotes

                return await self.stock_service.update_market_quotes(
                    symbol, quotes_data
                )
            return False
        except Exception as e:
            error_msg = str(e)
            # 检测限流错误，直接抛出让上层处理
            if self.is_rate_limit_error(error_msg):
                logger.error(f"❌ 获取 {symbol} 行情失败（限流）: {e}")
                raise  # 抛出限流错误
            logger.error(f"❌ 获取 {symbol} 行情失败: {e}")
            return False

    async def _process_quotes_batch(self, batch: List[str]) -> Dict[str, Any]:
        """处理行情批次"""
        batch_stats = {
            "success_count": 0,
            "error_count": 0,
            "errors": [],
            "rate_limit_hit": False,
        }

        # 并发获取行情数据
        tasks = []
        for symbol in batch:
            task = self._get_and_save_quotes(symbol)
            tasks.append(task)

        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计结果
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_msg = str(result)
                batch_stats["error_count"] += 1
                batch_stats["errors"].append(
                    {
                        "code": batch[i],
                        "error": error_msg,
                        "context": "_process_quotes_batch",
                    }
                )

                # 检测 API 限流错误
                if self.is_rate_limit_error(error_msg):
                    batch_stats["rate_limit_hit"] = True
                    logger.warning(f"⚠️ 检测到 API 限流错误: {error_msg}")

            elif result:
                batch_stats["success_count"] += 1
            else:
                batch_stats["error_count"] += 1
                batch_stats["errors"].append(
                    {
                        "code": batch[i],
                        "error": "获取行情数据失败",
                        "context": "_process_quotes_batch",
                    }
                )

        return batch_stats
