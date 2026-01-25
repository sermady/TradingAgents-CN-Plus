# -*- coding: utf-8 -*-
"""
MongoDB缓存清理脚本 - 支持认证
"""
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def main():
    print("=" * 60)
    print(" MongoDB Cache Clear Tool (with Auth)")
    print("=" * 60)

    try:
        from pymongo import MongoClient
        from app.core.config import get_settings

        settings = get_settings()

        # 构建MongoDB连接URI
        if settings.MONGODB_USERNAME and settings.MONGODB_PASSWORD:
            mongo_uri = (
                f"mongodb://{settings.MONGODB_USERNAME}:{settings.MONGODB_PASSWORD}"
                f"@{settings.MONGODB_HOST}:{settings.MONGODB_PORT}/"
                f"?authSource={settings.MONGODB_AUTH_SOURCE}"
            )
        else:
            mongo_uri = f"mongodb://{settings.MONGODB_HOST}:{settings.MONGODB_PORT}/"

        print(f"\nConnecting to MongoDB: {settings.MONGODB_HOST}:{settings.MONGODB_PORT}")
        print(f"Database: {settings.MONGODB_DATABASE}")

        client = MongoClient(mongo_uri)
        db = client[settings.MONGODB_DATABASE]

        # 测试连接
        db.list_collection_names()
        print("Connected successfully!")

        # 列出所有集合
        collections = db.list_collection_names()

        # 统计清理前
        print("\n[Before Cleanup]")
        total_before = 0
        cache_collections = []

        for coll_name in collections:
            if any(keyword in coll_name.lower() for keyword in ['cache', 'quote', 'market', 'stock']):
                count = db[coll_name].count_documents({})
                print(f"  {coll_name}: {count:,} records")
                total_before += count
                cache_collections.append(coll_name)

        print(f"  Total: {total_before:,} records")

        if not cache_collections:
            print("\nNo cache collections found.")
            return

        # 确认清理
        print(f"\n[Clearing Cache]")
        total_deleted = 0
        skipped = 0

        for coll_name in cache_collections:
            try:
                count = db[coll_name].count_documents({})
                result = db[coll_name].delete_many({})
                print(f"  {coll_name}: deleted {count} records")
                total_deleted += count
            except Exception as e:
                # 跳过views和其他无法删除的集合
                if 'view' in str(e).lower() or '166' in str(e):
                    print(f"  {coll_name}: skipped (is a view)")
                    skipped += 1
                else:
                    raise

        print(f"\n[Cleanup Complete]")
        print(f"  Total deleted: {total_deleted:,} records")

        # 验证清理结果
        print("\n[After Cleanup]")
        total_after = 0
        for coll_name in cache_collections:
            count = db[coll_name].count_documents({})
            print(f"  {coll_name}: {count:,} records")
            total_after += count
        print(f"  Total: {total_after:,} records")

        if total_after == 0:
            print("\n[SUCCESS] All cache cleared!")
        else:
            print(f"\n[WARNING] {total_after:,} records remain")

        client.close()

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
