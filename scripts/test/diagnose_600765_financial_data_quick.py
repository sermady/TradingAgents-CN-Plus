# -*- coding: utf-8 -*-
"""
快速诊断600765财务数据缺失问题
"""

import sys
import os
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

print("=" * 80)
print("600765 Financial Data Missing Quick Diagnosis")
print("=" * 80)

# 1. 检查环境变量
print("\n[1] Checking Environment Variables")
print("-" * 80)
env_vars = ["TUSHARE_TOKEN", "TUSHARE_ENABLED", "MONGODB_URL", "MONGODB_DATABASE_NAME"]

for var in env_vars:
    value = os.getenv(var)
    status = "[OK] Configured" if value else "[FAIL] Not Configured"
    print(f"{var}: {status}")
    if value:
        print(f"   Value: {value[:20]}...")

# 2. 检查MongoDB连接
print("\n[2] Checking MongoDB Connection")
print("-" * 80)
try:
    from app.core.database import get_mongo_db_sync

    db = get_mongo_db_sync()
    print("[OK] MongoDB connection successful")
    print(f"   Database name: {db.name}")

    # 检查600765财务数据
    collection = db.stock_financial_data
    doc = collection.find_one({"code": "600765"})

    if doc:
        print(f"[OK] Found 600765 financial data")
        print(f"   Report period: {doc.get('report_period')}")
        print(f"   Data source: {doc.get('data_source')}")
        print(f"   Fields: {list(doc.keys())[:10]}...")

        # 检查关键字段
        key_fields = ["pe", "pb", "roe", "net_profit", "total_revenue", "total_assets"]
        print(f"\n   Key fields check:")
        for field in key_fields:
            value = doc.get(field)
            status = "[OK]" if value else "[MISSING]"
            print(f"   {status} {field}: {value}")
    else:
        print(f"[FAIL] No 600765 financial data found in MongoDB")

    # 检查所有600765相关数据
    print(
        f"\n   Total 600765 financial data records: {collection.count_documents({'code': '600765'})}"
    )

except Exception as e:
    print(f"[FAIL] MongoDB connection failed: {e}")

# 3. 检查数据源配置
print("\n[3] Checking Data Source Configuration")
print("-" * 80)
try:
    from app.core.database import get_mongo_db_sync

    db = get_mongo_db_sync()
    config_collection = db.system_configs
    config = config_collection.find_one({"is_active": True})

    if config and config.get("data_source_configs"):
        print(f"[OK] Found active config (version: {config.get('version')})")

        for ds in config["data_source_configs"]:
            ds_type = ds.get("type")
            enabled = ds.get("enabled")
            priority = ds.get("priority")
            status = "[OK]" if enabled else "[DISABLED]"
            print(f"\n   {status} {ds_type}")
            print(f"      Enabled: {enabled}")
            print(f"      Priority: {priority}")
            print(f"      Market categories: {ds.get('market_categories', [])}")

            # 检查API Key
            if ds_type == "tushare":
                api_key = ds.get("api_key", "")
                if api_key and not api_key.startswith("your_"):
                    print(f"      API Key: [OK] Valid (length: {len(api_key)})")
                else:
                    print(f"      API Key: [FAIL] Invalid or not configured")
    else:
        print("[FAIL] No active data source configuration found")

except Exception as e:
    print(f"[FAIL] Failed to read config: {e}")

# 4. 测试数据源可用性
print("\n[4] Testing Data Source Availability")
print("-" * 80)

# 测试AKShare
try:
    import akshare as ak

    print("[OK] AKShare library installed")
except ImportError:
    print("[FAIL] AKShare library not installed")

# 测试Tushare
try:
    import tushare as ts

    print("[OK] Tushare library installed")

    # 测试连接
    token = os.getenv("TUSHARE_TOKEN")
    if token and not token.startswith("your_"):
        ts.set_token(token)
        pro = ts.pro_api()
        try:
            test_data = pro.stock_basic(list_status="L", limit=1)
            print(
                f"[OK] Tushare API connection successful (returned {len(test_data)} test records)"
            )
        except Exception as e:
            print(f"[FAIL] Tushare API connection failed: {e}")
    else:
        print("[FAIL] Tushare Token not configured or invalid")

except ImportError:
    print("[FAIL] Tushare library not installed")

# 5. 诊断总结
print("\n" + "=" * 80)
print("Diagnosis Summary")
print("=" * 80)
print("""
Recommended solutions:

1. Ensure MongoDB is running
2. Check and configure Tushare API Token
3. Run financial data sync task:
   python scripts/import/sync_financial_data.py 600765

4. If data exists but still reports error:
   - Check data source priority configuration
   - Check log files in logs/ for detailed error info

5. If it's a loss-making stock (net profit < 0):
   - PE ratio will display as N/A
   - This is normal and doesn't affect fundamental analysis
""")

print("\n" + "=" * 80)
print("Diagnosis Complete")
print("=" * 80)
