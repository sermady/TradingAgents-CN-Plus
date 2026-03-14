# -*- coding: utf-8 -*-
"""行情采集核心逻辑模块

提供行情数据的采集、批量入库和同步状态管理。
"""

import logging
from typing import Dict, Optional
from datetime import datetime

from pymongo import UpdateOne

from app.core.config import settings
from app.core.database import get_mongo_db

from .utils import normalize_stock_code

logger = logging.getLogger(__name__)


class IngestionMixin:
    """行情采集混入类"""

    def __init__(self):
        self.collection_name = "market_quotes"
        self.status_collection_name = "quotes_ingestion_status"

    async def ensure_indexes(self) -> None:
        """确保必要的索引存在"""
        db = get_mongo_db()
        coll = db[self.collection_name]
        try:
            await coll.create_index("code", unique=True)
            await coll.create_index("updated_at")
        except Exception as e:
            logger.warning(f"Failed to create indexes (ignored): {e}")

    async def _record_sync_status(
        self,
        success: bool,
        source: Optional[str] = None,
        records_count: int = 0,
        error_msg: Optional[str] = None
    ) -> None:
        """
        记录同步状态

        Args:
            success: 是否成功
            source: 数据源名称
            records_count: 记录数量
            error_msg: 错误信息
        """
        try:
            db = get_mongo_db()
            status_coll = db[self.status_collection_name]

            now = datetime.now(self.tz)

            status_doc = {
                "job": "quotes_ingestion",
                "last_sync_time": now,
                "last_sync_time_iso": now.isoformat(),
                "success": success,
                "data_source": source,
                "records_count": records_count,
                "interval_seconds": settings.QUOTES_INGEST_INTERVAL_SECONDS,
                "error_message": error_msg,
                "updated_at": now,
            }

            await status_coll.update_one(
                {"job": "quotes_ingestion"},
                {"$set": status_doc},
                upsert=True
            )

        except Exception as e:
            logger.warning(f"Failed to record sync status (ignored): {e}")

    async def get_sync_status(self) -> Dict[str, any]:
        """
        获取同步状态

        Returns:
            同步状态字典
        """
        try:
            db = get_mongo_db()
            status_coll = db[self.status_collection_name]

            doc = await status_coll.find_one({"job": "quotes_ingestion"})

            if not doc:
                return {
                    "last_sync_time": None,
                    "last_sync_time_iso": None,
                    "interval_seconds": settings.QUOTES_INGEST_INTERVAL_SECONDS,
                    "interval_minutes": settings.QUOTES_INGEST_INTERVAL_SECONDS / 60,
                    "data_source": None,
                    "success": None,
                    "records_count": 0,
                    "error_message": "Not synced yet"
                }

            doc.pop("_id", None)
            doc.pop("job", None)
            doc["interval_minutes"] = doc.get("interval_seconds", 0) / 60

            # 格式化时间
            if "last_sync_time" in doc and doc["last_sync_time"]:
                dt = doc["last_sync_time"]
                if dt.tzinfo is None:
                    from zoneinfo import ZoneInfo
                    dt = dt.replace(tzinfo=ZoneInfo("UTC"))
                dt_local = dt.astimezone(self.tz)
                doc["last_sync_time"] = dt_local.strftime("%Y-%m-%d %H:%M:%S")

            return doc

        except Exception as e:
            logger.error(f"Failed to get sync status: {e}")
            return {
                "last_sync_time": None,
                "interval_seconds": settings.QUOTES_INGEST_INTERVAL_SECONDS,
                "interval_minutes": settings.QUOTES_INGEST_INTERVAL_SECONDS / 60,
                "data_source": None,
                "success": False,
                "records_count": 0,
                "error_message": str(e)
            }

    async def _bulk_upsert(
        self,
        quotes_map: Dict[str, Dict],
        trade_date: str,
        source: Optional[str] = None
    ) -> None:
        """
        批量插入或更新行情数据

        Args:
            quotes_map: 行情数据字典
            trade_date: 交易日期
            source: 数据源名称
        """
        db = get_mongo_db()
        coll = db[self.collection_name]
        ops = []
        updated_at = datetime.now(self.tz)

        for code, q in quotes_map.items():
            if not code:
                continue

            code6 = normalize_stock_code(code)
            if not code6:
                continue

            volume = q.get("volume")
            if code6 in ["300750", "000001", "600000"]:
                logger.info(f"[Write market_quotes] {code6} - volume={volume}, amount={q.get('amount')}, source={source}")

            ops.append(
                UpdateOne(
                    {"code": code6},
                    {"$set": {
                        "code": code6,
                        "symbol": code6,
                        "close": q.get("close"),
                        "pct_chg": q.get("pct_chg"),
                        "amount": q.get("amount"),
                        "volume": volume,
                        "open": q.get("open"),
                        "high": q.get("high"),
                        "low": q.get("low"),
                        "pre_close": q.get("pre_close"),
                        "trade_date": trade_date,
                        "updated_at": updated_at,
                    }},
                    upsert=True,
                )
            )

        if not ops:
            logger.info("No data to write, skipping")
            return

        result = await coll.bulk_write(ops, ordered=False)
        logger.info(
            f"Quotes ingested: source={source}, matched={result.matched_count}, "
            f"upserted={len(result.upserted_ids) if result.upserted_ids else 0}, "
            f"modified={result.modified_count}"
        )

    async def _collection_empty(self) -> bool:
        """检查集合是否为空"""
        db = get_mongo_db()
        coll = db[self.collection_name]
        try:
            count = await coll.estimated_document_count()
            return count == 0
        except Exception:
            return True

    async def _collection_stale(self, latest_trade_date: Optional[str]) -> bool:
        """检查数据是否陈旧"""
        if not latest_trade_date:
            return False
        db = get_mongo_db()
        coll = db[self.collection_name]
        try:
            cursor = coll.find({}, {"trade_date": 1}).sort("trade_date", -1).limit(1)
            docs = await cursor.to_list(length=1)
            if not docs:
                return True
            doc_td = str(docs[0].get("trade_date") or "")
            return doc_td < str(latest_trade_date)
        except Exception:
            return True

    async def run_once(self) -> None:
        """
        执行一次采集与入库

        核心逻辑：
        1. 检测 Tushare 权限（首次运行）
        2. 按轮换顺序尝试获取行情
        3. 任意一个接口成功即入库，失败则跳过本次采集
        """
        from app.services.data_sources.manager import DataSourceManager

        if not self._is_trading_time():
            if settings.QUOTES_BACKFILL_ON_OFFHOURS:
                await self.backfill_last_close_snapshot_if_needed()
            else:
                logger.info("Non-trading hours, skipping quotes ingestion")
            return

        try:
            # 首次运行：检测 Tushare 权限
            if settings.QUOTES_AUTO_DETECT_TUSHARE_PERMISSION and not self._tushare_permission_checked:
                logger.info("First run, checking Tushare rt_k permission...")
                has_premium = self._check_tushare_permission()

                if has_premium:
                    logger.info("Tushare premium detected! Consider reducing interval to 5-60 seconds")
                else:
                    logger.info(f"Tushare free user, hourly limit: {self._tushare_hourly_limit}")

            # 获取下一个数据源
            source_type, akshare_api = self._get_next_source()

            # 尝试获取行情
            quotes_map, source_name = self._fetch_quotes_from_source(source_type, akshare_api)

            # Tushare 失败时的即时降级策略
            if not quotes_map and source_type == "tushare":
                logger.warning("Tushare failed, trying AKShare (Eastmoney)...")
                quotes_map, source_name = self._fetch_quotes_from_source("akshare", "eastmoney")

            if not quotes_map:
                logger.warning(f"{source_name or source_type} returned no data, skipping")
                await self._record_sync_status(
                    success=False,
                    source=source_name or source_type,
                    records_count=0,
                    error_msg="No data retrieved"
                )
                return

            # 获取交易日
            try:
                manager = DataSourceManager()
                trade_date = manager.find_latest_trade_date_with_fallback() or datetime.now(self.tz).strftime("%Y%m%d")
            except Exception:
                trade_date = datetime.now(self.tz).strftime("%Y%m%d")

            # 入库
            await self._bulk_upsert(quotes_map, trade_date, source_name)

            # 记录成功状态
            await self._record_sync_status(
                success=True,
                source=source_name,
                records_count=len(quotes_map),
                error_msg=None
            )

        except Exception as e:
            logger.error(f"Quotes ingestion failed: {e}")
            await self._record_sync_status(
                success=False,
                source=None,
                records_count=0,
                error_msg=str(e)
            )
