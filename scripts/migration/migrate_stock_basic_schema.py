# -*- coding: utf-8 -*-
"""
股票基础信息Schema迁移脚本

功能：
1. 扫描 stock_basic_info 集合
2. 检测 schema 版本
3. 执行字段转换和补全
4. 更新 data_version

使用方法：
    python scripts/migration/migrate_stock_basic_schema.py [--dry-run] [--limit N]
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import asdict

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from tradingagents.dataflows.schemas.stock_basic_schema import (
    StockBasicData,
    get_full_symbol,
    get_market_info,
    normalize_date,
    convert_to_float,
)
from tradingagents.utils.logging_init import get_logger

logger = get_logger("migration")


async def migrate_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    迁移单个文档到新Schema

    Args:
        doc: 原始文档

    Returns:
        迁移后的文档
    """
    if not doc:
        return doc

    current_version = doc.get("data_version", 0)
    if current_version >= 1:
        logger.debug(f"文档已是最新的 schema 版本: {doc.get('code')}")
        return doc

    code = doc.get("code") or doc.get("symbol", "")
    if not code:
        logger.warning(f"文档缺少 code 字段，跳过: {doc.get('_id')}")
        return doc

    code6 = code.split(".")[0] if "." in code else code
    market_info = get_market_info(code6)

    full_symbol = doc.get("full_symbol") or get_full_symbol(
        code6, market_info["exchange"]
    )

    migrated = doc.copy()

    migrated["code"] = code6
    migrated["symbol"] = doc.get("symbol", code6)
    migrated["ts_code"] = doc.get("ts_code") or full_symbol
    migrated["full_symbol"] = full_symbol

    if not migrated.get("market"):
        migrated["market"] = market_info["market"]
    if not migrated.get("exchange"):
        migrated["exchange"] = market_info["exchange"]
    if not migrated.get("exchange_name"):
        migrated["exchange_name"] = market_info["exchange_name"]

    migrated["list_date"] = normalize_date(doc.get("list_date")) or doc.get(
        "list_date", ""
    )
    migrated["delist_date"] = normalize_date(doc.get("delist_date"))

    pe = convert_to_float(doc.get("pe"))
    pe_ttm = convert_to_float(doc.get("pe_ttm"))
    pb = convert_to_float(doc.get("pb"))

    if not pe and pe_ttm:
        pe = pe_ttm
    if not pe_ttm and pe:
        pe_ttm = pe
    if not pb and doc.get("pb_mrq"):
        pb = convert_to_float(doc.get("pb_mrq"))

    migrated["pe"] = pe
    migrated["pe_ttm"] = pe_ttm
    migrated["pb"] = pb
    migrated["ps"] = convert_to_float(doc.get("ps"))
    migrated["pcf"] = convert_to_float(doc.get("pcf"))

    migrated["total_mv"] = convert_to_float(doc.get("total_mv"))
    migrated["circ_mv"] = convert_to_float(doc.get("circ_mv"))
    migrated["turnover_rate"] = convert_to_float(doc.get("turnover_rate"))
    migrated["volume_ratio"] = convert_to_float(doc.get("volume_ratio"))

    migrated["last_sync"] = doc.get("last_sync") or datetime.now().isoformat()
    migrated["data_version"] = 1

    if "_id" in migrated:
        del migrated["_id"]

    return migrated


async def migrate_collection(
    db, collection_name: str, dry_run: bool = True, limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    迁移整个集合

    Args:
        db: MongoDB数据库对象
        collection_name: 集合名称
        dry_run: 是否只预览不执行
        limit: 限制处理的文档数量

    Returns:
        迁移统计信息
    """
    coll = db[collection_name]

    stats = {"total": 0, "migrated": 0, "skipped": 0, "errors": 0, "dry_run": dry_run}

    try:
        total = coll.count_documents({})
        stats["total"] = total
        logger.info(f"开始迁移集合 {collection_name}，共 {total} 条记录")

        cursor = coll.find({}).limit(limit) if limit else coll.find({})

        batch_size = 100
        batch = []

        for doc in cursor:
            try:
                migrated = await migrate_document(doc)

                if doc.get("data_version", 0) < 1:
                    batch.append(migrated)
                    stats["migrated"] += 1
                else:
                    stats["skipped"] += 1

                if len(batch) >= batch_size:
                    if not dry_run:
                        for item in batch:
                            code = item.get("code")
                            coll.update_one(
                                {"$or": [{"symbol": code}, {"code": code}]},
                                {"$set": item},
                                upsert=True,
                            )
                    else:
                        logger.debug(f"[DRY-RUN] 将更新 {len(batch)} 条记录")
                    batch = []

            except Exception as e:
                logger.error(f"迁移文档失败: {e}")
                stats["errors"] += 1

        if batch:
            if not dry_run:
                for item in batch:
                    code = item.get("code")
                    coll.update_one(
                        {"$or": [{"symbol": code}, {"code": code}]},
                        {"$set": item},
                        upsert=True,
                    )
            else:
                logger.debug(f"[DRY-RUN] 将更新最后 {len(batch)} 条记录")

    except Exception as e:
        logger.error(f"迁移集合失败: {e}")
        stats["errors"] += 1

    return stats


async def run_migration(dry_run: bool = True, limit: Optional[int] = None):
    """
    运行迁移主流程

    Args:
        dry_run: 是否只预览不执行
        limit: 限制处理的文档数量
    """
    from tradingagents.config.database_manager import get_database_manager

    logger.info("=" * 60)
    logger.info("股票基础信息 Schema 迁移工具")
    logger.info(f"模式: {'预览(Dry-Run)' if dry_run else '执行'}")
    logger.info("=" * 60)

    try:
        db_manager = get_database_manager()
        db = db_manager.get_mongodb_db()

        collections = ["stock_basic_info", "stock_basic_info_hk", "stock_basic_info_us"]

        all_stats = {}

        for coll_name in collections:
            try:
                stats = await migrate_collection(db, coll_name, dry_run, limit)
                all_stats[coll_name] = stats

                mode = "预览" if dry_run else "执行"
                logger.info(
                    f"集合 {coll_name}: 迁移{mode}完成 - "
                    f"总计: {stats['total']}, "
                    f"迁移: {stats['migrated']}, "
                    f"跳过: {stats['skipped']}, "
                    f"错误: {stats['errors']}"
                )
            except Exception as e:
                logger.error(f"迁移集合 {coll_name} 失败: {e}")
                all_stats[coll_name] = {
                    "total": 0,
                    "migrated": 0,
                    "skipped": 0,
                    "errors": 1,
                }

        logger.info("=" * 60)
        logger.info("迁移汇总:")
        for coll_name, stats in all_stats.items():
            logger.info(f"  {coll_name}: 迁移 {stats['migrated']} 条记录")
        logger.info("=" * 60)

        if dry_run:
            logger.info("这是预览模式，未实际执行迁移。如需执行，请去掉 --dry-run 参数")

    except Exception as e:
        logger.error(f"迁移失败: {e}")
        raise


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="股票基础信息Schema迁移工具")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="预览模式（默认），不实际执行迁移",
    )
    parser.add_argument(
        "--execute", action="store_true", help="执行迁移（需要此参数才真正执行）"
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="限制处理的文档数量（用于测试）"
    )

    args = parser.parse_args()

    dry_run = not args.execute

    asyncio.run(run_migration(dry_run=dry_run, limit=args.limit))


if __name__ == "__main__":
    main()
