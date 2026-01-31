# -*- coding: utf-8 -*-
"""
数据库索引创建脚本（夜间执行）

功能：
1. 创建缺失的关键索引以提升查询性能
2. 支持后台创建（不阻塞前台操作）
3. 提供索引创建报告
4. 支持索引验证和回滚

运行方式:
    # 测试模式（查看将要创建的索引，但不实际创建）
    python scripts/create_database_indexes.py --dry-run

    # 生产模式（实际创建索引）
    python scripts/create_database_indexes.py

    # 后台创建（低峰期执行）
    python scripts/create_database_indexes.py --background

建议：
    - 在夜间低峰期运行（如 02:00-05:00）
    - 大数据集上创建索引可能需要数分钟
    - 使用 --background 参数避免阻塞
"""

import asyncio
import argparse
import sys
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

sys.path.insert(0, "E:\\WorkSpace\\TradingAgents-CN")

# 导入应用配置
from app.core.config import settings

# 配置 - 使用应用的标准配置
MONGO_URI = settings.MONGO_URI
DATABASE_NAME = settings.MONGO_DB


# 需要创建的索引配置
INDEX_CONFIG = {
    "analysis_tasks": [
        {
            "keys": [("user_id", 1), ("created_at", -1)],
            "name": "user_id_created_at_idx",
            "description": "支持用户查询分析任务列表（按时间倒序）",
            "priority": "high",
        },
        {
            "keys": [("status", 1), ("created_at", -1)],
            "name": "status_created_at_idx",
            "description": "支持按状态查询任务（如查询所有'running'状态）",
            "priority": "medium",
        },
        {
            "keys": [("stock_code", 1), ("analysis_date", -1)],
            "name": "stock_analysis_date_idx",
            "description": "支持查询特定股票的历史分析",
            "priority": "medium",
        },
    ],
    "operation_logs": [
        {
            "keys": [("timestamp", -1)],
            "name": "timestamp_idx",
            "description": "支持按时间查询日志",
            "priority": "high",
            "expireAfterSeconds": 2592000,  # 30天后自动过期
        },
        {
            "keys": [("user_id", 1), ("timestamp", -1)],
            "name": "user_timestamp_idx",
            "description": "支持查询特定用户的操作日志",
            "priority": "medium",
        },
    ],
    "user_favorites": [
        {
            "keys": [("user_id", 1), ("stock_code", 1)],
            "name": "user_stock_unique_idx",
            "unique": True,
            "description": "确保用户的自选股唯一（联合唯一索引）",
            "priority": "high",
        },
        {
            "keys": [("user_id", 1), ("added_at", -1)],
            "name": "user_added_at_idx",
            "description": "支持按添加时间排序",
            "priority": "low",
        },
    ],
    "cache_store": [
        {
            "keys": [("expires_at", 1)],
            "name": "expires_at_ttl_idx",
            "description": "自动清理过期缓存（TTL索引）",
            "priority": "high",
            "expireAfterSeconds": 0,  # 立即过期
        },
        {
            "keys": [("key", 1)],
            "name": "key_idx",
            "unique": True,
            "description": "快速查找缓存键",
            "priority": "high",
        },
    ],
    "historical_data": [
        {
            "keys": [("symbol", 1), ("trade_date", -1), ("data_source", 1)],
            "name": "symbol_date_source_idx",
            "description": "加速历史数据查询（股票+日期+数据源）",
            "priority": "high",
        },
    ],
    "market_quotes": [
        {
            "keys": [("code", 1), ("timestamp", -1)],
            "name": "code_timestamp_idx",
            "description": "加速实时行情时间序列查询",
            "priority": "medium",
        },
    ],
}


async def get_database():
    """获取数据库连接"""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        client = AsyncIOMotorClient(MONGO_URI)
        return client[DATABASE_NAME]
    except Exception as e:
        print(f"[错误] 连接 MongoDB 失败: {e}")
        sys.exit(1)


async def get_existing_indexes(db, collection_name: str) -> List[str]:
    """获取集合现有索引列表"""
    try:
        collection = db[collection_name]
        indexes = await collection.list_indexes().to_list(length=None)
        return [idx["name"] for idx in indexes if "name" in idx]
    except Exception as e:
        print(f"[警告]  获取 {collection_name} 索引失败: {e}")
        return []


async def check_collection_exists(db, collection_name: str) -> bool:
    """检查集合是否存在"""
    try:
        collections = await db.list_collection_names()
        return collection_name in collections
    except Exception as e:
        print(f"[警告]  检查集合 {collection_name} 失败: {e}")
        return False


async def create_index(
    db,
    collection_name: str,
    index_config: Dict[str, Any],
    dry_run: bool = False,
    background: bool = True,
) -> bool:
    """创建单个索引"""
    index_name = index_config["name"]
    keys = index_config["keys"]

    try:
        collection = db[collection_name]

        # 准备索引选项
        index_options = {
            "name": index_name,
            "background": background,  # 后台创建，不阻塞
        }

        if index_config.get("unique"):
            index_options["unique"] = True

        if "expireAfterSeconds" in index_config:
            index_options["expireAfterSeconds"] = index_config["expireAfterSeconds"]

        if dry_run:
            print(f"   [DRY-RUN] 将创建索引: {index_name}")
            print(f"             字段: {keys}")
            print(f"             选项: {index_options}")
            return True

        # 实际创建索引
        start_time = time.time()
        await collection.create_index(keys, **index_options)
        elapsed = time.time() - start_time

        print(f"   [OK] 索引创建成功: {index_name} ({elapsed:.2f}s)")
        return True

    except Exception as e:
        print(f"   [错误] 索引创建失败: {index_name} - {e}")
        return False


async def drop_index(db, collection_name: str, index_name: str) -> bool:
    """删除索引（用于回滚）"""
    try:
        collection = db[collection_name]
        await collection.drop_index(index_name)
        print(f"   [OK] 索引已删除: {collection_name}.{index_name}")
        return True
    except Exception as e:
        print(f"   [警告]  索引删除失败: {collection_name}.{index_name} - {e}")
        return False


async def main(
    dry_run: bool = False, background: bool = True, verify_only: bool = False
):
    """主函数"""
    print("=" * 70)
    print("[工具] MongoDB 索引创建工具")
    print(f"[时间]  当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[数据] 数据库: {DATABASE_NAME}")
    print(f"[日志] 模式: {'DRY-RUN (仅预览)' if dry_run else 'PRODUCTION (实际创建)'}")
    print(f"[配置]  后台创建: {'是' if background else '否'}")
    print("=" * 70)

    db = await get_database()

    # 统计信息
    stats = {
        "total_collections": len(INDEX_CONFIG),
        "total_indexes": sum(len(indexes) for indexes in INDEX_CONFIG.values()),
        "existing_indexes": 0,
        "to_create": 0,
        "created": 0,
        "failed": 0,
        "skipped": 0,
    }

    created_indexes = []  # 记录成功创建的索引（用于回滚）

    print("\n[计划] 索引创建计划:\n")

    for collection_name, indexes in INDEX_CONFIG.items():
        print(f"[集合] 集合: {collection_name}")

        # 检查集合是否存在
        if not await check_collection_exists(db, collection_name):
            print(f"   [警告]  集合不存在，跳过")
            stats["skipped"] += len(indexes)
            continue

        # 获取现有索引
        existing = await get_existing_indexes(db, collection_name)
        stats["existing_indexes"] += len(existing)

        for idx_config in indexes:
            index_name = idx_config["name"]
            priority = idx_config.get("priority", "medium")
            description = idx_config.get("description", "")

            # 检查是否已存在
            if index_name in existing:
                print(f"   [跳过]  已存在: {index_name} ({priority})")
                stats["skipped"] += 1
                continue

            stats["to_create"] += 1

            # 显示信息
            print(f"   {'[DRY-RUN] ' if dry_run else ''}即将创建: {index_name}")
            print(f"              优先级: {priority}")
            print(f"              说明: {description}")

            if verify_only:
                continue

            # 创建索引
            success = await create_index(
                db, collection_name, idx_config, dry_run, background
            )

            if success:
                if not dry_run:
                    created_indexes.append((collection_name, index_name))
                    stats["created"] += 1
            else:
                stats["failed"] += 1

        print()

    # 打印统计报告
    print("=" * 70)
    print("[数据] 索引创建报告")
    print("=" * 70)
    print(f"总集合数: {stats['total_collections']}")
    print(f"总索引数: {stats['total_indexes']}")
    print(f"现有索引: {stats['existing_indexes']}")
    print(f"待创建: {stats['to_create']}")
    print(f"[OK] 成功创建: {stats['created']}")
    print(f"[错误] 失败: {stats['failed']}")
    print(f"[跳过]  跳过（已存在）: {stats['skipped']}")

    if dry_run:
        print("\n[提示] 这是 DRY-RUN 模式，没有实际创建索引")
        print("   运行以下命令实际创建索引:")
        print(f"   python {sys.argv[0]}")
    elif stats["failed"] > 0:
        print(f"\n[警告]  有 {stats['failed']} 个索引创建失败")
        print("   请检查错误信息并手动处理")
    elif stats["created"] > 0:
        print(f"\n[OK] 成功创建 {stats['created']} 个索引！")
        print("\n[日志] 回滚命令（如需删除新索引）:")
        print("   python scripts/create_database_indexes.py --rollback")

    print("\n[查询] 验证索引:")
    print("   # 查看所有索引")
    for collection_name in INDEX_CONFIG.keys():
        print(f"   db.{collection_name}.getIndexes()")

    return stats["failed"] == 0


async def rollback_indexes():
    """回滚：删除本次创建的索引"""
    print("=" * 70)
    print("[回滚] 索引回滚模式")
    print("[警告]  这将删除本次脚本创建的所有索引")
    print("=" * 70)

    confirm = input("\n确认删除索引? (输入 'yes' 确认): ")
    if confirm.lower() != "yes":
        print("[错误] 操作已取消")
        return False

    db = await get_database()

    deleted = 0
    failed = 0

    for collection_name, indexes in INDEX_CONFIG.items():
        for idx_config in indexes:
            index_name = idx_config["name"]
            success = await drop_index(db, collection_name, index_name)
            if success:
                deleted += 1
            else:
                failed += 1

    print(f"\n[OK] 删除完成: {deleted} 个索引")
    if failed > 0:
        print(f"[警告]  失败: {failed} 个索引")

    return failed == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MongoDB 索引创建工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 预览模式（查看将要创建的索引）
  python %(prog)s --dry-run
  
  # 生产模式（实际创建索引）
  python %(prog)s
  
  # 后台创建（推荐用于大数据集）
  python %(prog)s --background
  
  # 回滚（删除创建的索引）
  python %(prog)s --rollback
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式：显示将要创建的索引但不实际创建",
    )

    parser.add_argument(
        "--background",
        action="store_true",
        default=True,
        help="后台创建索引（不阻塞其他操作）",
    )

    parser.add_argument(
        "--foreground",
        action="store_true",
        help="前台创建索引（更快但会短暂阻塞）",
    )

    parser.add_argument(
        "--rollback",
        action="store_true",
        help="回滚模式：删除本次创建的所有索引",
    )

    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="仅验证：检查索引状态但不创建",
    )

    args = parser.parse_args()

    # 设置后台/前台模式
    background = not args.foreground

    if args.rollback:
        success = asyncio.run(rollback_indexes())
    else:
        success = asyncio.run(
            main(
                dry_run=args.dry_run,
                background=background,
                verify_only=args.verify_only,
            )
        )

    sys.exit(0 if success else 1)
