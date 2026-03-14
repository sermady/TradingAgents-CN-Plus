# -*- coding: utf-8 -*-
"""行情数据回填模块

提供从历史数据集合回填行情数据的功能。
"""

import logging
from typing import Optional
from datetime import datetime

from app.core.database import get_mongo_db
from app.services.data_sources.manager import DataSourceManager

from .utils import normalize_stock_code

logger = logging.getLogger(__name__)


class BackfillMixin:
    """数据回填混入类"""

    async def backfill_from_historical_data(self) -> None:
        """
        从历史数据集合导入前一天的收盘数据到 market_quotes
        - 如果 market_quotes 集合为空，导入所有数据
        - 如果 market_quotes 集合不为空，检查并修复缺失的成交量字段
        """
        try:
            # 检查 market_quotes 是否为空
            is_empty = await self._collection_empty()

            if not is_empty:
                # 集合不为空，检查是否有成交量缺失的记录
                logger.info("market_quotes not empty, checking for missing volume data...")
                await self._fix_missing_volume()
                return

            logger.info("market_quotes is empty, importing from historical data")

            db = get_mongo_db()
            manager = DataSourceManager()

            # 获取最新交易日
            try:
                latest_trade_date = manager.find_latest_trade_date_with_fallback()
                if not latest_trade_date:
                    logger.warning("Cannot get latest trade date, skipping historical import")
                    return
            except Exception as e:
                logger.warning(f"Failed to get latest trade date: {e}, skipping")
                return

            logger.info(f"Importing {latest_trade_date} close data from historical data to market_quotes")

            # 从 stock_daily_quotes 集合查询最新交易日的数据
            daily_quotes_collection = db["stock_daily_quotes"]
            cursor = daily_quotes_collection.find({
                "trade_date": latest_trade_date,
                "period": "daily"
            })

            docs = await cursor.to_list(length=None)

            if not docs:
                logger.warning(f"No data found for {latest_trade_date} in historical data")
                return

            logger.info(f"Found {len(docs)} records in historical data")

            # 转换为 quotes_map 格式
            quotes_map = {}
            for doc in docs:
                code = doc.get("symbol") or doc.get("code")
                if not code:
                    continue
                code6 = str(code).zfill(6)

                volume_value = doc.get("volume") or doc.get("vol")
                data_source = doc.get("data_source", "")

                if code6 in ["300750", "000001", "600000"]:
                    logger.info(f"[Backfill] {code6} - volume={doc.get('volume')}, vol={doc.get('vol')}, source={data_source}")

                quotes_map[code6] = {
                    "close": doc.get("close"),
                    "pct_chg": doc.get("pct_chg"),
                    "amount": doc.get("amount"),
                    "volume": volume_value,
                    "open": doc.get("open"),
                    "high": doc.get("high"),
                    "low": doc.get("low"),
                    "pre_close": doc.get("pre_close"),
                }

            if quotes_map:
                await self._bulk_upsert(quotes_map, latest_trade_date, "historical_data")
                logger.info(f"Successfully imported {len(quotes_map)} records from historical data")
            else:
                logger.warning("Converted quotes map is empty, cannot import")

        except Exception as e:
            logger.error(f"Historical data import failed: {e}")
            import traceback
            logger.error(f"Stack trace:\n{traceback.format_exc()}")

    async def backfill_last_close_snapshot(self) -> None:
        """一次性补齐上一笔收盘快照（用于冷启动或数据陈旧）。允许在休市期调用。"""
        try:
            manager = DataSourceManager()
            # 使用智能快照获取策略：优先实时接口，失败则降级到日线数据
            quotes_map, source = manager.get_snapshot_with_fallback()

            if not quotes_map:
                logger.error("Backfill: All sources failed to get quotes data, skipping")
                return

            try:
                if "_daily" in str(source):
                    trade_date = manager.find_latest_trade_date_with_fallback() or datetime.now(self.tz).strftime("%Y%m%d")
                else:
                    trade_date = manager.find_latest_trade_date_with_fallback() or datetime.now(self.tz).strftime("%Y%m%d")
            except Exception:
                trade_date = datetime.now(self.tz).strftime("%Y%m%d")

            logger.info(f"[Backfill] Got {len(quotes_map)} records (Source: {source}, Date: {trade_date}), writing to DB...")
            await self._bulk_upsert(quotes_map, trade_date, source)

        except Exception as e:
            logger.error(f"Backfill quotes failed: {e}")

    async def backfill_last_close_snapshot_if_needed(self) -> None:
        """若集合为空或 trade_date 落后于最新交易日，则执行一次 backfill"""
        try:
            is_empty = await self._collection_empty()

            # 如果集合为空，优先从历史数据导入
            if is_empty:
                logger.info("market_quotes is empty, trying historical data import")
                await self.backfill_from_historical_data()
                return

            # 如果集合不为空但数据陈旧，使用实时接口更新
            manager = DataSourceManager()
            latest_td = manager.find_latest_trade_date_with_fallback()
            if await self._collection_stale(latest_td):
                logger.info("Triggering backfill for stale data")
                await self.backfill_last_close_snapshot()
        except Exception as e:
            logger.warning(f"Backfill check failed (ignored): {e}")

    async def _fix_missing_volume(self) -> None:
        """修复缺失的成交量字段"""
        try:
            db = get_mongo_db()
            coll = db[self.collection_name]

            # 查找没有 volume 字段或 volume 为 null 的文档
            cursor = coll.find({
                "$or": [
                    {"volume": {"$exists": False}},
                    {"volume": None}
                ]
            }).limit(100)

            docs_to_fix = await cursor.to_list(length=100)

            if not docs_to_fix:
                logger.info("No documents with missing volume found")
                return

            logger.info(f"Found {len(docs_to_fix)} documents with missing volume")

            # 这里可以实现具体的修复逻辑
            # 例如从其他数据源获取缺失的成交量数据

        except Exception as e:
            logger.warning(f"Failed to fix missing volume: {e}")
