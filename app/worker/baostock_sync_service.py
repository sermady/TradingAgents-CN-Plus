#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BaoStock数据同步服务
提供BaoStock数据的批量同步功能，集成到APScheduler调度系统

重构：继承BaseSyncService，使用标准SyncStats和execute_batch_sync模板方法
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from app.core.config import get_settings
from app.core.database import get_database
from app.services.historical_data_service import get_historical_data_service
from app.services.base_sync_service import BaseSyncService, SyncStats
from tradingagents.dataflows.providers.china.baostock import BaoStockProvider
from tradingagents.utils.time_utils import get_today_str, get_days_ago_str, get_iso_timestamp

logger = logging.getLogger(__name__)


class BaoStockSyncService(BaseSyncService):
    """BaoStock数据同步服务"""

    @property
    def data_source(self) -> str:
        """数据源标识符"""
        return "baostock"

    def __init__(self):
        """
        初始化同步服务

        注意：数据库连接在 initialize() 方法中异步初始化
        """
        super().__init__()  # 🔥 调用基类初始化
        try:
            self.settings = get_settings()
            self.provider = BaoStockProvider()
            # historical_service 和 db 由基类初始化，这里设为None延迟初始化
            self.historical_service = None
            self.db = None

            logger.info("✅ BaoStock同步服务初始化成功")
        except Exception as e:
            logger.error(f"❌ BaoStock同步服务初始化失败: {e}")
            raise

    async def initialize(self):
        """异步初始化服务"""
        try:
            # 🔥 初始化数据库连接（必须在异步上下文中）
            from app.core.database import get_mongo_db
            self.db = get_mongo_db()

            # 初始化历史数据服务
            if self.historical_service is None:
                from app.services.historical_data_service import get_historical_data_service
                self.historical_service = await get_historical_data_service()

            logger.info("✅ BaoStock同步服务异步初始化完成")
        except Exception as e:
            logger.error(f"❌ BaoStock同步服务异步初始化失败: {e}")
            raise
    
    async def sync_stock_basic_info(self, batch_size: int = 100) -> SyncStats:
        """
        同步股票基础信息

        🔥 重构：使用基类的 execute_batch_sync 模板方法

        Args:
            batch_size: 批处理大小

        Returns:
            同步统计信息
        """
        logger.info("🔄 开始BaoStock股票基础信息同步...")

        # 获取股票列表
        stock_list = await self.provider.get_stock_list()
        if not stock_list:
            logger.warning("⚠️ BaoStock股票列表为空")
            return SyncStats()

        logger.info(f"📋 获取到{len(stock_list)}只股票，开始批量同步...")

        # 🔥 使用基类的 execute_batch_sync 模板方法
        stats = await self.execute_batch_sync(
            items=stock_list,
            process_func=self._process_single_stock_basic_info,
            batch_size=batch_size,
            rate_limit_delay=0.1,
            task_name="BaoStock基础信息同步"
        )

        logger.info(f"✅ BaoStock基础信息同步完成: {stats.success_count}条记录")
        return stats

    async def _process_single_stock_basic_info(self, stock: Dict[str, Any]) -> bool:
        """
        处理单个股票的基础信息（用于execute_batch_sync）

        Args:
            stock: 股票信息字典

        Returns:
            True 如果处理成功
        """
        try:
            code = stock['code']

            # 1. 获取基础信息
            basic_info = await self.provider.get_stock_basic_info(code)
            if not basic_info:
                logger.warning(f"⚠️ 获取{code}基础信息失败")
                return False

            # 2. 获取估值数据（PE、PB、PS、PCF等）
            try:
                valuation_data = await self.provider.get_valuation_data(code)
                if valuation_data:
                    basic_info.update({
                        'pe': valuation_data.get('pe_ttm'),
                        'pb': valuation_data.get('pb_mrq'),
                        'pe_ttm': valuation_data.get('pe_ttm'),
                        'pb_mrq': valuation_data.get('pb_mrq'),
                        'ps': valuation_data.get('ps_ttm'),
                        'pcf': valuation_data.get('pcf_ttm'),
                        'close': valuation_data.get('close'),
                    })

                    # 计算总市值
                    close_price = valuation_data.get('close')
                    if close_price and close_price > 0:
                        total_shares_wan = await self._get_total_shares(code)
                        if total_shares_wan and total_shares_wan > 0:
                            basic_info['total_mv'] = (close_price * total_shares_wan) / 10000
            except Exception as e:
                logger.debug(f"获取{code}估值数据失败: {e}")
                # 估值数据获取失败不影响基础信息同步

            # 3. 更新数据库
            await self._update_stock_basic_info(basic_info)
            return True

        except Exception as e:
            logger.error(f"处理{stock.get('code', 'unknown')}失败: {e}")
            return False
    
    async def _get_total_shares(self, code: str) -> Optional[float]:
        """
        获取股票总股本（万股）

        Args:
            code: 股票代码

        Returns:
            总股本（万股），如果获取失败返回 None
        """
        try:
            # 尝试从财务数据获取总股本
            financial_data = await self.provider.get_financial_data(code)

            if financial_data:
                # BaoStock 财务数据中的总股本字段
                # 盈利能力数据中有 totalShare（总股本，单位：万股）
                profit_data = financial_data.get('profit_data', {})
                if profit_data:
                    total_shares = profit_data.get('totalShare')
                    if total_shares:
                        return self._safe_float(total_shares)

                # 成长能力数据中也可能有总股本
                growth_data = financial_data.get('growth_data', {})
                if growth_data:
                    total_shares = growth_data.get('totalShare')
                    if total_shares:
                        return self._safe_float(total_shares)

            # 如果财务数据中没有，尝试从数据库中已有的数据获取
            collection = self.db.stock_financial_data
            doc = await collection.find_one(
                {"code": code},
                {"total_shares": 1, "totalShare": 1},
                sort=[("report_period", -1)]
            )

            if doc:
                total_shares = doc.get('total_shares') or doc.get('totalShare')
                if total_shares:
                    return self._safe_float(total_shares)

            return None

        except Exception as e:
            logger.debug(f"获取{code}总股本失败: {e}")
            return None

    def _safe_float(self, value) -> Optional[float]:
        """安全转换为浮点数"""
        try:
            if value is None or value == '' or value == 'None':
                return None
            return float(value)
        except (ValueError, TypeError):
            return None

    async def _update_stock_basic_info(self, basic_info: Dict[str, Any]):
        """更新股票基础信息到数据库"""
        try:
            collection = self.db.stock_basic_info

            # 确保 symbol 字段存在（标准化字段）
            if "symbol" not in basic_info and "code" in basic_info:
                basic_info["symbol"] = basic_info["code"]

            # 🔥 确保 source 字段存在
            if "source" not in basic_info:
                basic_info["source"] = "baostock"

            # 🔥 使用 (code, source) 联合查询条件
            await collection.update_one(
                {"code": basic_info["code"], "source": "baostock"},
                {"$set": basic_info},
                upsert=True
            )

        except Exception as e:
            logger.error(f"❌ 更新基础信息到数据库失败: {e}")
            raise
    
    async def sync_daily_quotes(self, batch_size: int = 50) -> SyncStats:
        """
        同步日K线数据（最新交易日）

        注意：BaoStock不支持实时行情，此方法获取最新交易日的日K线数据

        🔥 重构：使用基类的 execute_batch_sync 模板方法

        Args:
            batch_size: 批处理大小

        Returns:
            同步统计信息
        """
        logger.info("🔄 开始BaoStock日K线同步（最新交易日）...")
        logger.info("ℹ️ 注意：BaoStock不支持实时行情，此任务同步最新交易日的日K线数据")

        # 从数据库获取股票列表
        collection = self.db.stock_basic_info
        cursor = collection.find({"data_source": "baostock"}, {"code": 1})
        stock_codes = [doc["code"] async for doc in cursor]

        if not stock_codes:
            logger.warning("⚠️ 数据库中没有BaoStock股票数据")
            return SyncStats()

        logger.info(f"📈 开始同步{len(stock_codes)}只股票的日K线数据...")

        # 🔥 使用基类的 execute_batch_sync 模板方法
        stats = await self.execute_batch_sync(
            items=stock_codes,
            process_func=self._process_single_stock_quotes,
            batch_size=batch_size,
            rate_limit_delay=0.2,
            task_name="BaoStock日K线同步"
        )

        logger.info(f"✅ BaoStock日K线同步完成: {stats.success_count}条记录")
        return stats

    async def _process_single_stock_quotes(self, code: str) -> bool:
        """
        处理单个股票的日K线数据（用于execute_batch_sync）

        Args:
            code: 股票代码

        Returns:
            True 如果处理成功
        """
        try:
            quotes = await self.provider.get_stock_quotes(code)
            if quotes:
                await self._update_stock_quotes(quotes)
                return True
            else:
                logger.warning(f"⚠️ 获取{code}日K线失败")
                return False
        except Exception as e:
            logger.error(f"处理{code}日K线失败: {e}")
            return False
    

    async def _update_stock_quotes(self, quotes: Dict[str, Any]):
        """更新股票日K线到数据库"""
        try:
            collection = self.db.market_quotes

            # 确保 symbol 字段存在
            code = quotes.get("code", "")
            if code and "symbol" not in quotes:
                quotes["symbol"] = code

            # 使用upsert更新或插入
            await collection.update_one(
                {"code": code},
                {"$set": quotes},
                upsert=True
            )

        except Exception as e:
            logger.error(f"❌ 更新日K线到数据库失败: {e}")
            raise
    
    async def sync_historical_data(self, days: int = 30, batch_size: int = 20, period: str = "daily", incremental: bool = True) -> SyncStats:
        """
        同步历史数据

        🔥 重构：使用基类的 execute_batch_sync 模板方法

        Args:
            days: 同步天数（如果>=3650则同步全历史，如果<0则使用增量模式）
            batch_size: 批处理大小
            period: 数据周期 (daily/weekly/monthly)
            incremental: 是否增量同步（每只股票从自己的最后日期开始）

        Returns:
            同步统计信息
        """
        period_name = {"daily": "日线", "weekly": "周线", "monthly": "月线"}.get(period, "日线")

        # 计算日期范围
        end_date = get_today_str()
        use_incremental = incremental or days < 0

        # 从数据库获取股票列表
        collection = self.db.stock_basic_info
        cursor = collection.find({"data_source": "baostock"}, {"code": 1})
        stock_codes = [doc["code"] async for doc in cursor]

        if not stock_codes:
            logger.warning("⚠️ 数据库中没有BaoStock股票数据")
            return SyncStats()

        if use_incremental:
            logger.info(f"🔄 开始BaoStock{period_name}历史数据同步 (增量模式: 各股票从最后日期到{end_date})...")
        elif days >= 3650:
            logger.info(f"🔄 开始BaoStock{period_name}历史数据同步 (全历史: 1990-01-01到{end_date})...")
        else:
            logger.info(f"🔄 开始BaoStock{period_name}历史数据同步 (最近{days}天到{end_date})...")

        logger.info(f"📊 开始同步{len(stock_codes)}只股票的历史数据...")

        # 🔥 使用基类的 execute_batch_sync 模板方法
        # 需要包装处理函数以传递额外参数
        async def _process_with_params(code: str) -> int:
            """处理单个股票的历史数据，返回记录数"""
            try:
                # 确定该股票的起始日期
                if use_incremental:
                    start_date = await self._get_last_sync_date(code)
                    logger.debug(f"📅 {code}: 从 {start_date} 开始同步")
                elif days >= 3650:
                    start_date = "1990-01-01"
                else:
                    start_date = get_days_ago_str(days)

                hist_data = await self.provider.get_historical_data(code, start_date, end_date, period)

                if hist_data is not None and not hist_data.empty:
                    records_count = await self._update_historical_data(code, hist_data, period)
                    return records_count
                else:
                    logger.warning(f"⚠️ 获取{code}历史数据失败")
                    return 0
            except Exception as e:
                logger.error(f"处理{code}历史数据失败: {e}")
                return 0

        # 使用标准批量同步，但需要统计记录数
        stats = SyncStats()
        stats.total_processed = len(stock_codes)

        for i in range(0, len(stock_codes), batch_size):
            batch = stock_codes[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(stock_codes) + batch_size - 1) // batch_size

            logger.info(f"📦 处理批次 {batch_num}/{total_batches} ({len(batch)} 只股票)")

            for code in batch:
                records = await _process_with_params(code)
                if records > 0:
                    stats.success_count += 1
                else:
                    stats.error_count += 1
                await asyncio.sleep(0.5)  # 历史数据API限制更严格

            progress = min(100, int((i + len(batch)) / len(stock_codes) * 100))
            logger.info(f"📊 历史数据同步进度: {progress}% ({stats.success_count} 成功, {stats.error_count} 失败)")

        stats.end_time = datetime.utcnow()
        logger.info(f"✅ BaoStock历史数据同步完成: {stats.success_count}只成功 ({stats.success_rate:.1f}%)")
        return stats

    async def _update_historical_data(self, code: str, hist_data, period: str = "daily") -> int:
        """更新历史数据到数据库"""
        try:
            if hist_data is None or hist_data.empty:
                logger.warning(f"⚠️ {code} 历史数据为空，跳过保存")
                return 0

            # 初始化历史数据服务
            if self.historical_service is None:
                self.historical_service = await get_historical_data_service()

            # 保存到统一历史数据集合
            saved_count = await self.historical_service.save_historical_data(
                symbol=code,
                data=hist_data,
                data_source="baostock",
                market="CN",
                period=period
            )

            # 同时更新market_quotes集合的元信息（保持兼容性）
            if self.db is not None:
                collection = self.db.market_quotes
                latest_record = hist_data.iloc[-1] if not hist_data.empty else None

                await collection.update_one(
                    {"code": code},
                    {"$set": {
                        "historical_data_updated": get_iso_timestamp(),
                        "latest_historical_date": latest_record.get('date') if latest_record is not None else None,
                        "historical_records_count": saved_count
                    }},
                    upsert=True
                )

            return saved_count

        except Exception as e:
            logger.error(f"❌ 更新历史数据到数据库失败: {e}")
            return 0
    

    async def check_service_status(self) -> Dict[str, Any]:
        """检查服务状态"""
        try:
            # 测试BaoStock连接
            connection_ok = await self.provider.test_connection()
            
            # 检查数据库连接
            db_ok = True
            try:
                await self.db.stock_basic_info.count_documents({})
            except Exception:
                db_ok = False
            
            # 统计数据
            basic_info_count = await self.db.stock_basic_info.count_documents({"data_source": "baostock"})
            quotes_count = await self.db.market_quotes.count_documents({"data_source": "baostock"})
            
            return {
                "service": "BaoStock同步服务",
                "baostock_connection": connection_ok,
                "database_connection": db_ok,
                "basic_info_count": basic_info_count,
                "quotes_count": quotes_count,
                "status": "healthy" if connection_ok and db_ok else "unhealthy",
                "last_check": get_iso_timestamp()
            }

        except Exception as e:
            logger.error(f"❌ BaoStock服务状态检查失败: {e}")
            return {
                "service": "BaoStock同步服务",
                "status": "error",
                "error": str(e),
                "last_check": get_iso_timestamp()
            }


# APScheduler兼容的任务函数
async def run_baostock_basic_info_sync():
    """运行BaoStock基础信息同步任务"""
    try:
        service = BaoStockSyncService()
        await service.initialize()  # 🔥 必须先初始化
        stats = await service.sync_stock_basic_info()
        logger.info(f"🎯 BaoStock基础信息同步完成: {stats.success_count}条成功, {stats.error_count}个错误")
    except Exception as e:
        logger.error(f"❌ BaoStock基础信息同步任务失败: {e}")


async def run_baostock_daily_quotes_sync():
    """运行BaoStock日K线同步任务（最新交易日）"""
    try:
        service = BaoStockSyncService()
        await service.initialize()  # 🔥 必须先初始化
        stats = await service.sync_daily_quotes()
        logger.info(f"🎯 BaoStock日K线同步完成: {stats.success_count}条成功, {stats.error_count}个错误")
    except Exception as e:
        logger.error(f"❌ BaoStock日K线同步任务失败: {e}")


async def run_baostock_historical_sync():
    """运行BaoStock历史数据同步任务"""
    try:
        service = BaoStockSyncService()
        await service.initialize()  # 🔥 必须先初始化
        stats = await service.sync_historical_data()
        logger.info(f"🎯 BaoStock历史数据同步完成: {stats.success_count}只成功, {stats.error_count}个错误")
    except Exception as e:
        logger.error(f"❌ BaoStock历史数据同步任务失败: {e}")


async def run_baostock_status_check():
    """运行BaoStock状态检查任务"""
    try:
        service = BaoStockSyncService()
        await service.initialize()  # 🔥 必须先初始化
        status = await service.check_service_status()
        logger.info(f"🔍 BaoStock服务状态: {status['status']}")
    except Exception as e:
        logger.error(f"❌ BaoStock状态检查任务失败: {e}")
