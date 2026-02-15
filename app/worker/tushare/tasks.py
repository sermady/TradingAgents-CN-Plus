# -*- coding: utf-8 -*-
"""
Tushare同步服务 - APScheduler任务函数
提供定时任务的各种同步函数
"""

from datetime import datetime
from zoneinfo import ZoneInfo
import logging

from app.core.config import get_settings
from app.core.redis_client import get_redis
from tradingagents.utils.time_utils import get_timestamp
from tradingagents.utils.trading_hours import is_weekend

logger = logging.getLogger(__name__)


async def run_tushare_basic_info_sync(force_update: bool = False):
    """APScheduler任务：同步股票基础信息"""
    try:
        from . import get_tushare_sync_service

        service = await get_tushare_sync_service()
        result = await service.sync_stock_basic_info(
            force_update, job_id="tushare_basic_info_sync"
        )
        logger.info(f"✅ Tushare基础信息同步完成: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Tushare基础信息同步失败: {e}")
        raise


async def run_tushare_quotes_sync(force: bool = False):
    """
    APScheduler任务：同步实时行情

    Args:
        force: 是否强制执行（跳过交易时间检查），默认 False
    """
    try:
        from . import get_tushare_sync_service

        service = await get_tushare_sync_service()
        result = await service.sync_realtime_quotes(force=force)
        logger.info(f"✅ Tushare行情同步完成: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Tushare行情同步失败: {e}")
        raise


async def run_tushare_hourly_bulk_sync():
    """
    APScheduler任务：每小时批量同步全市场实时行情（Tushare rt_k接口）

    特点：
    - 使用rt_k批量接口一次性获取全市场数据（约5000+只股票）
    - 同时存储到MongoDB和Redis
    - 只在交易时段执行（9:30-11:30, 13:00-15:00）
    - 每小时执行一次，整点触发
    """
    settings = get_settings()
    tz = ZoneInfo(settings.TIMEZONE)
    now = datetime.now(tz)

    # 检查是否在交易时段（工作日 9:30-15:30）
    if now.weekday() > 4:  # 周末
        logger.info("⏭️ [Tushare Hourly Bulk] 非交易日，跳过同步")
        return {"skipped": True, "reason": "非交易日"}

    current_time = now.time()

    # 检查是否在交易时段（上午 9:30-11:30，下午 13:00-15:00）
    is_morning_session = datetime.time(9, 30) <= current_time <= datetime.time(11, 30)
    is_afternoon_session = datetime.time(13, 0) <= current_time <= datetime.time(15, 0)

    if not (is_morning_session or is_afternoon_session):
        logger.info("⏭️ [Tushare Hourly Bulk] 非交易时段，跳过同步")
        return {"skipped": True, "reason": "非交易时段"}

    # ==================== 频率限制检查 ====================
    # 生成当前小时的唯一标识（格式：YYYYMMDD_HH）
    current_hour_key = now.strftime("%Y%m%d_%H")
    rate_limit_key = f"tushare_rt_k_rate_limit:{current_hour_key}"

    try:
        redis = get_redis()
        if redis:
            # 使用 SET NX EX 原子操作检查并设置频率限制标记
            # NX = 仅当key不存在时才设置（原子性检查）
            # EX = 设置过期时间为3600秒
            is_first_call = await redis.set(
                rate_limit_key, now.isoformat(), nx=True, ex=3600
            )

            if not is_first_call:
                # Key 已存在，说明本小时内已经调用过
                existing = await redis.get(rate_limit_key)
                logger.info(
                    f"⏭️ [Tushare Hourly Bulk] 本小时({current_hour_key})已调用过rt_k接口，"
                    f"跳过同步以避免频率限制"
                )
                return {
                    "skipped": True,
                    "reason": f"频率限制：本小时({current_hour_key})已调用",
                    "last_call": existing.decode()
                    if isinstance(existing, bytes)
                    else existing,
                }

            logger.info(f"🔒 [Tushare Hourly Bulk] 设置频率限制标记: {rate_limit_key}")
    except Exception as e:
        # Redis 不可用时的降级处理：继续执行但记录警告
        logger.warning(f"⚠️ [Tushare Hourly Bulk] Redis频率限制检查失败: {e}，继续执行")

    logger.info("🚀 [Tushare Hourly Bulk] 开始每小时批量同步全市场实时行情...")

    try:
        from . import get_tushare_sync_service

        service = await get_tushare_sync_service()

        # 使用批量接口获取全市场数据
        logger.info("📡 [Tushare Hourly Bulk] 调用 rt_k 批量接口获取全市场数据...")
        quotes_map = await service.provider.get_realtime_quotes_batch()

        if not quotes_map:
            logger.warning("⚠️ [Tushare Hourly Bulk] 未获取到行情数据")
            return {"success": False, "reason": "未获取到数据"}

        logger.info(f"✅ [Tushare Hourly Bulk] 获取到 {len(quotes_map)} 只股票行情")

        # 1. 保存到MongoDB
        mongo_success = 0
        mongo_error = 0
        for symbol, quote_data in quotes_map.items():
            try:
                result = await service.stock_service.update_market_quotes(
                    symbol, quote_data
                )
                if result:
                    mongo_success += 1
                else:
                    mongo_error += 1
            except Exception as e:
                mongo_error += 1
                logger.warning(
                    f"❌ [Tushare Hourly Bulk] 保存 {symbol} 到MongoDB失败: {e}"
                )

        logger.info(
            f"💾 [Tushare Hourly Bulk] MongoDB: 成功 {mongo_success} 只, 失败 {mongo_error} 只"
        )

        # 2. 保存到Redis（缓存，10分钟过期）
        redis_success = 0
        redis_error = 0
        try:
            import json

            redis = get_redis()
            if redis:
                # 使用pipeline批量写入
                pipeline = redis.pipeline()
                timestamp = now.strftime("%Y%m%d%H%M%S")

                for symbol, quote_data in quotes_map.items():
                    try:
                        key = f"realtime_quote:{symbol}"
                        data = {
                            "symbol": symbol,
                            "close": quote_data.get("close"),
                            "pct_chg": quote_data.get("pct_chg"),
                            "volume": quote_data.get("volume"),
                            "amount": quote_data.get("amount"),
                            "timestamp": timestamp,
                            "source": "tushare_hourly_bulk",
                        }
                        pipeline.setex(key, 600, json.dumps(data))  # 10分钟过期
                        redis_success += 1
                    except Exception as e:
                        redis_error += 1
                        logger.debug(
                            f"❌ [Tushare Hourly Bulk] 保存 {symbol} 到Redis失败: {e}"
                        )

                await pipeline.execute()
                logger.info(
                    f"💾 [Tushare Hourly Bulk] Redis: 成功 {redis_success} 只, 失败 {redis_error} 只"
                )
            else:
                logger.warning("⚠️ [Tushare Hourly Bulk] Redis不可用，跳过缓存")
        except Exception as e:
            logger.error(f"❌ [Tushare Hourly Bulk] Redis缓存失败: {e}")

        result = {
            "success": True,
            "total": len(quotes_map),
            "mongo_success": mongo_success,
            "mongo_error": mongo_error,
            "redis_success": redis_success,
            "redis_error": redis_error,
            "timestamp": now.isoformat(),
        }

        logger.info(
            f"✅ [Tushare Hourly Bulk] 同步完成: "
            f"总计 {result['total']} 只, "
            f"MongoDB: {mongo_success}/{mongo_error}, "
            f"Redis: {redis_success}/{redis_error}"
        )

        return result

    except Exception as e:
        logger.error(f"❌ [Tushare Hourly Bulk] 同步失败: {e}")
        import traceback

        logger.error(f"详细错误: {traceback.format_exc()}")
        raise


async def run_tushare_historical_sync(incremental: bool = True):
    """APScheduler任务：同步历史数据"""
    logger.info(
        f"🚀 [APScheduler] 开始执行 Tushare 历史数据同步任务 (incremental={incremental})"
    )
    try:
        from . import get_tushare_sync_service

        service = await get_tushare_sync_service()
        logger.info(f"✅ [APScheduler] Tushare 同步服务已初始化")
        result = await service.sync_historical_data(
            incremental=incremental, job_id="tushare_historical_sync"
        )
        logger.info(f"✅ [APScheduler] Tushare历史数据同步完成: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ [APScheduler] Tushare历史数据同步失败: {e}")
        import traceback

        logger.error(f"详细错误: {traceback.format_exc()}")
        raise


async def run_tushare_financial_sync():
    """APScheduler任务：同步财务数据（获取最近20期，约5年）"""
    try:
        from . import get_tushare_sync_service

        service = await get_tushare_sync_service()
        result = await service.sync_financial_data(
            limit=20, job_id="tushare_financial_sync"
        )  # 获取最近20期（约5年数据）
        logger.info(f"✅ Tushare财务数据同步完成: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Tushare财务数据同步失败: {e}")
        raise


async def run_tushare_status_check():
    """APScheduler任务：检查同步状态"""
    try:
        from . import get_tushare_sync_service

        service = await get_tushare_sync_service()
        result = await service.get_sync_status()
        logger.info(f"✅ Tushare状态检查完成: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Tushare状态检查失败: {e}")
        return {"error": str(e)}


async def run_tushare_news_sync(hours_back: int = 24, max_news_per_stock: int = 20):
    """APScheduler任务：同步新闻数据"""
    try:
        from . import get_tushare_sync_service

        service = await get_tushare_sync_service()
        result = await service.sync_news_data(
            hours_back=hours_back,
            max_news_per_stock=max_news_per_stock,
            job_id="tushare_news_sync",
        )
        logger.info(f"✅ Tushare新闻数据同步完成: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ Tushare新闻数据同步失败: {e}")
        raise
