#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""探索 MongoDB 数据库结构，查找分析结果"""

import sys
import io

# 设置标准输出为 UTF-8 编码
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from pymongo import MongoClient
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

# 连接数据库
mongodb_username = os.getenv("MONGODB_USERNAME", "")
mongodb_password = os.getenv("MONGODB_PASSWORD", "")
mongodb_port = os.getenv("MONGODB_PORT", "27017")
mongodb_database = os.getenv("MONGODB_DATABASE", "tradingagents")
mongodb_auth_source = os.getenv("MONGODB_AUTH_SOURCE", "admin")

# 本地环境使用 localhost
mongodb_host = "localhost"

# 如果有认证信息，使用带认证的连接
if mongodb_username and mongodb_password:
    connection_string = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_host}:{mongodb_port}/?authSource={mongodb_auth_source}"
else:
    connection_string = f"mongodb://{mongodb_host}:{mongodb_port}/"

client = MongoClient(connection_string)
db = client[mongodb_database]

print(f"📡 连接数据库: {mongodb_host}:{mongodb_port}")
print(f"📦 数据库名称: {mongodb_database}")
print("=" * 80)

# 显示所有集合
print(f"\n📋 数据库中的所有集合:")
collections = db.list_collection_names()
for collection in collections:
    count = db[collection].count_documents({})
    print(f"  - {collection}: {count} 条记录")

print("=" * 80)

# 查找包含 "analysis" 的集合
print(f"\n🔍 查找与分析相关的集合:")
analysis_collections = [c for c in collections if "analysis" in c.lower()]
if analysis_collections:
    for collection in analysis_collections:
        print(f"\n  集合名称: {collection}")
        count = db[collection].count_documents({})
        print(f"  记录数: {count}")

        if count > 0:
            # 显示第一条记录的字段结构
            sample = db[collection].find_one()
            print(f"  字段结构:")
            for key, value in sample.items():
                if key != "_id":
                    print(f"    - {key}: {type(value).__name__}")

            # 显示最近 5 条记录
            print(f"\n  最近的 5 条记录:")
            recent = db[collection].find().sort("created_at", -1).limit(5)
            for i, record in enumerate(recent, 1):
                print(f"\n  记录 {i}:")
                for key, value in record.items():
                    if key in [
                        "analysis_id",
                        "stock_code",
                        "stock_name",
                        "status",
                        "created_at",
                    ]:
                        print(f"    {key}: {value}")
else:
    print("  未找到包含 'analysis' 的集合")

# 查找 600765 相关的数据
print(f"\n" + "=" * 80)
print(f"🔍 查找股票代码 600765 的所有相关数据:")
print("=" * 80)

for collection in collections:
    try:
        # 尝试不同的字段名
        count_by_code = db[collection].count_documents({"stock_code": "600765"})
        count_by_ts_code = db[collection].count_documents({"ts_code": "600765.SH"})

        if count_by_code > 0 or count_by_ts_code > 0:
            print(f"\n  集合: {collection}")
            print(f"  stock_code='600765' 记录数: {count_by_code}")
            print(f"  ts_code='600765.SH' 记录数: {count_by_ts_code}")

            # 显示一条样例记录
            if count_by_code > 0:
                sample = db[collection].find_one({"stock_code": "600765"})
            else:
                sample = db[collection].find_one({"ts_code": "600765.SH"})

            print(f"  样例记录字段:")
            for key, value in sample.items():
                if key != "_id":
                    val_str = str(value)[:100] if len(str(value)) > 100 else str(value)
                    print(f"    {key}: {val_str}")
    except Exception as e:
        continue

print(f"\n" + "=" * 80)
print(f"✅ 探索完成")
