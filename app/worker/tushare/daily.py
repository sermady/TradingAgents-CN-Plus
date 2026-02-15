# -*- coding: utf-8 -*-
"""
Tushare日线数据同步
负责历史数据和日线数据的同步
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

from tradingagents.utils.time_utils import get_today_str, get_days_ago_str, get_timestamp
from tradingagents.utils.trading_hours import is_weekend

from .base import TushareSyncBase

logger = logging.getLogger(__name__)


class TushareDailySync(TushareSyncBase):
    """
    Tushare日线数据同步服务
    负责历史数据和日线数据的同步
    """

    async def sync_stock_basic_info(
        self, force_update: bool = False, job_id: str = None
    ) -> Dict[str, Any]:
        """
        同步股票基础信息

        Args:
            force_update: 是否强制更新所有数据
            job_id: 任务ID（用于进度跟踪）

        Returns:
            同步结果统计
        """
        logger.info("🔄 开始同步股票基础信息...")

        stats = {
            "total_processed": 0,
            "success_count": 0,
            "error_count": 0,
            "skipped_count": 0,
            "start_time": datetime.utcnow(),
            "errors": [],
        }

        try:
            # 1. 从Tushare获取股票列表
            stock_list = await self.provider.get_stock_list(market="CN")
            if not stock_list:
                logger.error("❌ 无法获取股票列表")
                return stats

            stats["total_processed"] = len(stock_list)
            logger.info(f"📊 获取到 {len(stock_list)} 只股票信息")

            # 2. 批量处理
            for i in range(0, len(stock_list), self.batch_size):
                # 检查是否需要退出
                if job_id and await self._should_stop(job_id):
                    logger.warning(f"⚠️ 任务 {job_id} 收到停止信号，正在退出...")
                    stats["stopped"] = True
                    break

                batch = stock_list[i : i + self.batch_size]
                batch_stats = await self._process_basic_info_batch(batch, force_update)

                # 更新统计
                stats["success_count"] += batch_stats["success_count"]
                stats["error_count"] += batch_stats["error_count"]
                stats["skipped_count"] += batch_stats["skipped_count"]
                stats["errors"].extend(batch_stats["errors"])

                # 进度日志和进度更新
                progress = min(i + self.batch_size, len(stock_list))
                progress_percent = int((progress / len(stock_list)) * 100)
                logger.info(
                    f"📈 基础信息同步进度: {progress}/{len(stock_list)} ({progress_percent}%) "
                    f"(成功: {stats['success_count']}, 错误: {stats['error_count']})"
                )

                # 更新任务进度
                if job_id:
                    await self._update_progress(
                        job_id,
                        progress_percent,
                        f"已处理 {progress}/{len(stock_list)} 只股票",
                    )

                # API限流
                if i + self.batch_size < len(stock_list):
                    import asyncio
                    await asyncio.sleep(self.rate_limit_delay)

            # 3. 完成统计
            stats["end_time"] = datetime.utcnow()
            stats["duration"] = (
                stats["end_time"] - stats["start_time"]
            ).total_seconds()

            logger.info(
                f"✅ 股票基础信息同步完成: "
                f"总计 {stats['total_processed']} 只, "
                f"成功 {stats['success_count']} 只, "
                f"错误 {stats['error_count']} 只, "
                f"跳过 {stats['skipped_count']} 只, "
                f"耗时 {stats['duration']:.2f} 秒"
            )

            return stats

        except Exception as e:
            logger.error(f"❌ 股票基础信息同步失败: {e}")
            stats["errors"].append(
                {"error": str(e), "context": "sync_stock_basic_info"}
            )
            return stats

    async def _process_basic_info_batch(
        self, batch: List[Dict[str, Any]], force_update: bool
    ) -> Dict[str, Any]:
        """处理基础信息批次"""
        batch_stats = {
            "success_count": 0,
            "error_count": 0,
            "skipped_count": 0,
            "errors": [],
        }

        for stock_info in batch:
            try:
                # 🔥 先转换为字典格式（如果是Pydantic模型）
                if hasattr(stock_info, "model_dump"):
                    stock_data = stock_info.model_dump()
                elif hasattr(stock_info, "dict"):
                    stock_data = stock_info.dict()
                else:
                    stock_data = stock_info

                code = stock_data["code"]

                # 检查是否需要更新
                if not force_update:
                    existing = await self.stock_service.get_stock_basic_info(code)
                    if existing:
                        # 🔥 existing 也可能是 Pydantic 模型，需要安全获取属性
                        existing_dict = (
                            existing.model_dump()
                            if hasattr(existing, "model_dump")
                            else (
                                existing.dict()
                                if hasattr(existing, "dict")
                                else existing
                            )
                        )
                        if self._is_data_fresh(
                            existing_dict.get("updated_at"), hours=24
                        ):
                            batch_stats["skipped_count"] += 1
                            continue

                # 更新到数据库（指定数据源为 tushare）
                success = await self.stock_service.update_stock_basic_info(
                    code, stock_data, source="tushare"
                )
                if success:
                    batch_stats["success_count"] += 1
                else:
                    batch_stats["error_count"] += 1
                    batch_stats["errors"].append(
                        {
                            "code": code,
                            "error": "数据库更新失败",
                            "context": "update_stock_basic_info",
                        }
                    )

            except Exception as e:
                batch_stats["error_count"] += 1
                # 🔥 安全获取 code（处理 Pydantic 模型和字典）
                try:
                    if hasattr(stock_info, "code"):
                        code = stock_info.code
                    elif hasattr(stock_info, "model_dump"):
                        code = stock_info.model_dump().get("code", "unknown")
                    elif hasattr(stock_info, "dict"):
                        code = stock_info.dict().get("code", "unknown")
                    else:
                        code = stock_info.get("code", "unknown")
                except:
                    code = "unknown"

                batch_stats["errors"].append(
                    {
                        "code": code,
                        "error": str(e),
                        "context": "_process_basic_info_batch",
                    }
                )

        return batch_stats

    async def sync_historical_data(
        self,
        symbols: List[str] = None,
        start_date: str = None,
        end_date: str = None,
        incremental: bool = True,
        all_history: bool = False,
        period: str = "daily",
        job_id: str = None,
    ) -> Dict[str, Any]:
        """
        同步历史数据

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            incremental: 是否增量同步
            all_history: 是否同步所有历史数据
            period: 数据周期 (daily/weekly/monthly)
            job_id: 任务ID（用于进度跟踪）

        Returns:
            同步结果统计
        """
        period_name = {"daily": "日线", "weekly": "周线", "monthly": "月线"}.get(
            period, period
        )
        logger.info(f"🔄 开始同步{period_name}历史数据...")

        stats = {
            "total_processed": 0,
            "success_count": 0,
            "error_count": 0,
            "total_records": 0,
            "start_time": datetime.utcnow(),
            "errors": [],
        }

        try:
            # 1. 获取股票列表（排除退市股票）
            if symbols is None:
                # 查询所有A股股票（兼容不同的数据结构），排除退市股票
                # 优先使用 market_info.market，降级到 category 字段
                cursor = self.db.stock_basic_info.find(
                    {
                        "$and": [
                            {
                                "$or": [
                                    {"market_info.market": "CN"},  # 新数据结构
                                    {"category": "stock_cn"},  # 旧数据结构
                                    {
                                        "market": {
                                            "$in": [
                                                "主板",
                                                "创业板",
                                                "科创板",
                                                "北交所",
                                            ]
                                        }
                                    },  # 按市场类型
                                ]
                            },
                            # 排除退市股票
                            {
                                "$or": [
                                    {"status": {"$ne": "D"}},  # status 不是 D（退市）
                                    {
                                        "status": {"$exists": False}
                                    },  # 或者 status 字段不存在
                                ]
                            },
                        ]
                    },
                    {"code": 1},
                )
                symbols = [doc["code"] async for doc in cursor]
                logger.info(
                    f"📋 从 stock_basic_info 获取到 {len(symbols)} 只股票（已排除退市股票）"
                )

            stats["total_processed"] = len(symbols)

            # 2. 确定全局结束日期
            if not end_date:
                end_date = get_today_str()

            # 3. 确定全局起始日期（仅用于日志显示）
            global_start_date = start_date
            if not global_start_date:
                if all_history:
                    global_start_date = "1990-01-01"
                elif incremental:
                    global_start_date = "各股票最后日期"
                else:
                    global_start_date = get_days_ago_str(365)

            logger.info(
                f"📊 历史数据同步: 结束日期={end_date}, 股票数量={len(symbols)}, 模式={'增量' if incremental else '全量'}"
            )

            # 4. 批量处理
            for i, symbol in enumerate(symbols):
                # 记录单个股票开始时间
                stock_start_time = get_timestamp()

                try:
                    # 检查是否需要退出
                    if job_id and await self._should_stop(job_id):
                        logger.warning(f"⚠️ 任务 {job_id} 收到停止信号，正在退出...")
                        stats["stopped"] = True
                        break

                    # 速率限制
                    await self.rate_limiter.acquire()

                    # 确定该股票的起始日期
                    symbol_start_date = start_date
                    if not symbol_start_date:
                        if all_history:
                            symbol_start_date = "1990-01-01"
                        elif incremental:
                            # 增量同步：获取该股票的最后日期
                            symbol_start_date = await self._get_last_sync_date(symbol)
                            logger.debug(
                                f"📅 {symbol}: 从 {symbol_start_date} 开始同步"
                            )
                        else:
                            symbol_start_date = (
                                datetime.now() - timedelta(days=365)
                            ).strftime("%Y-%m-%d")

                    # 记录请求参数
                    logger.debug(
                        f"🔍 {symbol}: 请求{period_name}数据 "
                        f"start={symbol_start_date}, end={end_date}, period={period}"
                    )

                    # ⏱️ 性能监控：API 调用
                    api_start = get_timestamp()
                    df = await self.provider.get_historical_data(
                        symbol, symbol_start_date, end_date, period=period
                    )
                    api_duration = (datetime.now() - api_start).total_seconds()

                    if df is not None and not df.empty:
                        # ⏱️ 性能监控：数据保存
                        save_start = datetime.now()
                        records_saved = await self._save_historical_data(
                            symbol, df, period=period
                        )
                        save_duration = (datetime.now() - save_start).total_seconds()

                        stats["success_count"] += 1
                        stats["total_records"] += records_saved

                        # 计算单个股票耗时
                        stock_duration = (
                            datetime.now() - stock_start_time
                        ).total_seconds()
                        logger.info(
                            f"✅ {symbol}: 保存 {records_saved} 条{period_name}记录，"
                            f"总耗时 {stock_duration:.2f}秒 "
                            f"(API: {api_duration:.2f}秒, 保存: {save_duration:.2f}秒)"
                        )
                    else:
                        stock_duration = (
                            datetime.now() - stock_start_time
                        ).total_seconds()
                        logger.warning(
                            f"⚠️ {symbol}: 无{period_name}数据 "
                            f"(start={symbol_start_date}, end={end_date})，耗时 {stock_duration:.2f}秒"
                        )

                    # 每个股票都更新进度
                    progress_percent = int(((i + 1) / len(symbols)) * 100)

                    # 更新任务进度
                    if job_id:
                        await self._update_progress(
                            job_id,
                            progress_percent,
                            f"正在同步 {symbol} ({i + 1}/{len(symbols)})",
                        )

                    # 每50个股票输出一次详细日志
                    if (i + 1) % 50 == 0 or (i + 1) == len(symbols):
                        logger.info(
                            f"📈 {period_name}数据同步进度: {i + 1}/{len(symbols)} ({progress_percent}%) "
                            f"(成功: {stats['success_count']}, 记录: {stats['total_records']})"
                        )

                        # 输出速率限制器统计
                        limiter_stats = self.rate_limiter.get_stats()
                        logger.info(
                            f"   速率限制: {limiter_stats['current_calls']}/{limiter_stats['max_calls']}次, "
                            f"等待次数: {limiter_stats['total_waits']}, "
                            f"总等待时间: {limiter_stats['total_wait_time']:.1f}秒"
                        )

                except Exception as e:
                    import traceback

                    error_details = traceback.format_exc()
                    stats["error_count"] += 1
                    stats["errors"].append(
                        {
                            "code": symbol,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "context": f"sync_historical_data_{period}",
                            "traceback": error_details,
                        }
                    )
                    logger.error(
                        f"❌ {symbol} {period_name}数据同步失败\n"
                        f"   参数: start={symbol_start_date if 'symbol_start_date' in locals() else 'N/A'}, "
                        f"end={end_date}, period={period}\n"
                        f"   错误类型: {type(e).__name__}\n"
                        f"   错误信息: {str(e)}\n"
                        f"   堆栈跟踪:\n{error_details}"
                    )

            # 4. 完成统计
            stats["end_time"] = datetime.utcnow()
            stats["duration"] = (
                stats["end_time"] - stats["start_time"]
            ).total_seconds()

            logger.info(
                f"✅ {period_name}数据同步完成: "
                f"股票 {stats['success_count']}/{stats['total_processed']}, "
                f"记录 {stats['total_records']} 条, "
                f"错误 {stats['error_count']} 个, "
                f"耗时 {stats['duration']:.2f} 秒"
            )

            return stats

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            logger.error(
                f"❌ 历史数据同步失败（外层异常）\n"
                f"   错误类型: {type(e).__name__}\n"
                f"   错误信息: {str(e)}\n"
                f"   堆栈跟踪:\n{error_details}"
            )
            stats["errors"].append(
                {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "context": "sync_historical_data",
                    "traceback": error_details,
                }
            )
            return stats

    async def _save_historical_data(
        self, symbol: str, df, period: str = "daily"
    ) -> int:
        """保存历史数据到数据库"""
        try:
            historical_service = await self.historical_data_service()

            # 使用统一历史数据服务保存（指定周期）
            saved_count = await historical_service.save_historical_data(
                symbol=symbol,
                data=df,
                data_source="tushare",
                market="CN",
                period=period,
            )

            return saved_count

        except Exception as e:
            logger.error(f"❌ 保存{period}数据失败 {symbol}: {e}")
            return 0
