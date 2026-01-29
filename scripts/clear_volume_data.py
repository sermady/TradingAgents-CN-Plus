#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清除 MongoDB 中的成交量数据，为重新同步做准备
用于将成交量单位从"股"转换为"手"后重新获取数据

用法:
    python scripts/clear_volume_data.py          # 交互式确认
    python scripts/clear_volume_data.py --force  # 自动确认
    python scripts/clear_volume_data.py -y       # 自动确认
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 检查命令行参数
AUTO_CONFIRM = "--force" in sys.argv or "-y" in sys.argv

from tradingagents.utils.logging_init import get_logger

logger = get_logger("scripts.clear_volume")


def clear_volume_data():
    """清除 stock_daily_quotes 集合中的 volume 字段"""
    try:
        from pymongo import MongoClient

        # 连接 MongoDB - 从环境变量读取配置
        mongodb_host = os.getenv("MONGODB_HOST", "localhost")
        mongodb_port = os.getenv("MONGODB_PORT", "27017")
        mongodb_username = os.getenv("MONGODB_USERNAME", "")
        mongodb_password = os.getenv("MONGODB_PASSWORD", "")
        mongodb_db = os.getenv("MONGODB_DATABASE", "tradingagents")
        mongodb_auth_source = os.getenv("MONGODB_AUTH_SOURCE", "admin")

        # 构建连接字符串
        if mongodb_username and mongodb_password:
            mongodb_url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_host}:{mongodb_port}/?authSource={mongodb_auth_source}"
        else:
            mongodb_url = f"mongodb://{mongodb_host}:{mongodb_port}/"

        client = MongoClient(mongodb_url)
        db = client[mongodb_db]

        print("=" * 60)
        print("MongoDB 成交量数据清除工具")
        print("=" * 60)
        print()

        # 检查集合是否存在
        collections = db.list_collection_names()

        # 1. 清除 stock_daily_quotes 集合中的 volume 字段
        if "stock_daily_quotes" in collections:
            count = db.stock_daily_quotes.count_documents({"volume": {"$exists": True}})
            print(f"📊 stock_daily_quotes 集合:")
            print(f"   - 包含 volume 字段的文档数: {count}")

            if count > 0:
                result = db.stock_daily_quotes.update_many(
                    {}, {"$unset": {"volume": ""}}
                )
                print(f"   - 已清除 {result.modified_count} 条记录的 volume 字段")
                logger.info(
                    f"已清除 stock_daily_quotes 的 volume 字段: {result.modified_count} 条"
                )
        else:
            print("⚠️ stock_daily_quotes 集合不存在")

        # 2. 清除 realtime_quotes 集合（如果有）
        if "realtime_quotes" in collections:
            count = db.realtime_quotes.count_documents({})
            print(f"\n📊 realtime_quotes 集合:")
            print(f"   - 文档数: {count}")

            if count > 0:
                db.realtime_quotes.delete_many({})
                print(f"   - 已清除所有 {count} 条实时行情数据")
                logger.info(f"已清除 realtime_quotes: {count} 条")
        else:
            print("\n⚠️ realtime_quotes 集合不存在")

        # 3. 清除 market_quotes 集合中的 volume（如果有）
        if "market_quotes" in collections:
            count = db.market_quotes.count_documents({"volume": {"$exists": True}})
            print(f"\n📊 market_quotes 集合:")
            print(f"   - 包含 volume 字段的文档数: {count}")

            if count > 0:
                result = db.market_quotes.update_many({}, {"$unset": {"volume": ""}})
                print(f"   - 已清除 {result.modified_count} 条记录的 volume 字段")
                logger.info(
                    f"已清除 market_quotes 的 volume 字段: {result.modified_count} 条"
                )
        else:
            print("\n⚠️ market_quotes 集合不存在")

        client.close()

        print("\n" + "=" * 60)
        print("✅ 数据清除完成！")
        print("=" * 60)
        print("\n下一步操作:")
        print("1. 运行数据导入脚本重新获取数据:")
        print(
            "   python scripts/import/import_a_stocks_unified.py --data-source tushare"
        )
        print("2. 运行测试脚本验证单位是否正确:")
        print("   python scripts/test_volume_unit.py")

        return True

    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保已安装 pymongo: pip install pymongo")
        return False
    except Exception as e:
        print(f"❌ 清除数据失败: {e}")
        logger.error(f"清除数据失败: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    # 获取数据库名用于显示
    mongodb_db = os.getenv("MONGODB_DB", "trading_agents")

    # 确认提示
    print("\n" + "⚠️" * 30)
    print("警告：这将清除 MongoDB 中的成交量数据！")
    print("⚠️" * 30)
    print()
    print("当前操作:")
    print(f"  - 数据库: {mongodb_db}")
    print(
        "  - 清除内容: stock_daily_quotes, realtime_quotes, market_quotes 中的 volume 数据"
    )
    print("  - 目的: 将成交量单位从'股'转换为'手'后重新获取")
    print()

    if AUTO_CONFIRM:
        response = "yes"
        print("自动确认模式 (--force/-y)")
    else:
        response = input("确认继续? (yes/no): ")

    if response.lower() == "yes":
        if clear_volume_data():
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        print("\n已取消操作")
        sys.exit(0)
