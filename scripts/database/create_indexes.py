# -*- coding: utf-8 -*-
"""
数据库索引优化脚本
为常用查询字段创建索引，提升数据库查询性能
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradingagents.utils.logging_init import get_logger

logger = get_logger("database_indexes")


def create_mongodb_indexes():
    """创建 MongoDB 索引"""

    logger.info("=" * 60)
    logger.info("创建 MongoDB 索引")
    logger.info("=" * 60)

    try:
        from app.core.database import get_mongo_db_sync

        db = get_mongo_db_sync()

        # 创建缓存集合索引
        cache_collection = db.cache_collection
        logger.info("\n📝 创建缓存集合索引...")

        cache_indexes = [
            # 主要键唯一索引
            {
                "key": [("key", 1)],
                "unique": True,
                "name": "cache_key_unique",
                "background": True,
            },
            # 创建时间索引
            {
                "key": [("created_at", -1)],
                "name": "cache_created_at_idx",
                "background": True,
            },
            # TTL 索引
            {"key": [("ttl", 1)], "name": "cache_ttl_idx", "background": True},
            # 数据类型 + 创建时间复合索引
            {
                "key": [("data_type", 1), ("created_at", -1)],
                "name": "cache_type_created_idx",
                "background": True,
            },
        ]

        for index_spec in cache_indexes:
            try:
                cache_collection.create_index(**index_spec)
                logger.info(f"  ✅ {index_spec['name']}: {index_spec}")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"  ⚠️ 索引创建失败: {index_spec['name']}: {e}")

        # 创建 Token 使用集合索引
        token_usage_collection = db.token_usage
        logger.info("\n📝 创建 Token 使用集合索引...")

        token_indexes = [
            # 提供商索引
            {"key": [("provider", 1)], "name": "provider_idx", "background": True},
            # 日期索引
            {"key": [("date", -1)], "name": "date_idx", "background": True},
            # 提供商 + 日期复合索引
            {
                "key": [("provider", 1), ("date", -1)],
                "name": "provider_date_idx",
                "background": True,
            },
        ]

        for index_spec in token_indexes:
            try:
                token_usage_collection.create_index(**index_spec)
                logger.info(f"  ✅ {index_spec['name']}: {index_spec}")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"  ⚠️ 索引创建失败: {index_spec['name']}: {e}")

        # 创建用户配置集合索引
        system_configs_collection = db.system_configs
        logger.info("\n📝 创建系统配置集合索引...")

        config_indexes = [
            # 激活配置索引
            {"key": [("is_active", -1)], "name": "is_active_idx", "background": True},
            # 版本索引
            {"key": [("version", -1)], "name": "version_idx", "background": True},
        ]

        for index_spec in config_indexes:
            try:
                system_configs_collection.create_index(**index_spec)
                logger.info(f"  ✅ {index_spec['name']}: {index_spec}")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"  ⚠️ 索引创建失败: {index_spec['name']}: {e}")

        # 验证索引
        logger.info("\n🔍 验证索引...")

        # 缓存集合索引验证
        logger.info("  cache_collection 索引列表:")
        for index in cache_collection.list_indexes():
            logger.info(f"    - {index['name']}: {index['key']}")

        # Token 使用集合索引验证
        logger.info("  token_usage 索引列表:")
        for index in token_usage_collection.list_indexes():
            logger.info(f"    - {index['name']}: {index.get('key', 'N/A')}")

        # 系统配置集合索引验证
        logger.info("  system_configs 索引列表:")
        for index in system_configs_collection.list_indexes():
            logger.info(f"    - {index['name']}: {index.get('key', 'N/A')}")

        logger.info("\n" + "=" * 60)
        logger.info("✅ 索引创建完成！")
        logger.info("=" * 60 + "\n")

        return True

    except Exception as e:
        logger.error(f"\n❌ 创建索引失败: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


def verify_indexes():
    """验证索引是否创建成功"""

    logger.info("\n" + "=" * 60)
    logger.info("验证索引效果")
    logger.info("=" * 60)

    try:
        from app.core.database import get_mongo_db_sync

        db = get_mongo_db_sync()

        # 测试查询：查找今天之前的缓存数据
        from datetime import datetime, timedelta

        threshold = datetime.now() - timedelta(days=7)

        logger.info("\n🧪 测试查询：查找7天前的缓存记录...")

        cache_collection = db.cache_collection
        count = cache_collection.count_documents({"created_at": {"$lt": threshold}})
        logger.info(f"  📊 7天前的缓存记录数: {count}")

        # 测试查询：按提供商和日期聚合 Token 使用
        logger.info("\n🧪 测试查询：按提供商聚合 Token 使用...")

        token_usage_collection = db.token_usage
        pipeline = [
            {
                "$group": {
                    "_id": {"provider": "$provider", "date": "$date"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.date": -1}},
            {"$limit": 5},
        ]

        results = list(token_usage_collection.aggregate(pipeline))
        logger.info(f"  📊 最近的 Token 使用记录:")
        for result in results:
            provider = result["_id"]["provider"]
            date = result["_id"]["date"]
            count = result["count"]
            logger.info(f"    {provider} @ {date}: {count} 次调用")

        logger.info("\n✅ 索引验证完成！")

        return True

    except Exception as e:
        logger.error(f"\n❌ 索引验证失败: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return False


def main():
    """主函数"""

    logger.info("=" * 60)
    logger.info("数据库索引优化脚本")
    logger.info("=" * 60)

    # 1. 创建索引
    create_success = create_mongodb_indexes()

    if create_success:
        # 2. 验证索引
        verify_success = verify_indexes()

    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("总结")
    logger.info("=" * 60)
    logger.info(f"  索引创建: {'✅ 成功' if create_success else '❌ 失败'}")
    logger.info(f"  索引验证: {'✅ 成功' if verify_success else '❌ 失败'}")

    if create_success and verify_success:
        logger.info("\n✅ 数据库索引优化完成！")
        return 0
    else:
        logger.error("\n❌ 数据库索引优化失败！")
        return 1


if __name__ == "__main__":
    sys.exit(main())
