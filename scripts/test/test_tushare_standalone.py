# -*- coding: utf-8 -*-
"""
独立测试脚本：直接读取.env并测试Tushare
"""

import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

print("=" * 80)
print("Testing Tushare Financial Data for 600765 (Standalone)")
print("=" * 80)

# 检查Token
token = os.getenv("TUSHARE_TOKEN")
print(f"\n[1] Tushare Token Check")
print("-" * 80)
if token and not token.startswith("your_"):
    print(f"OK: Token found (length: {len(token)})")
    print(f"Token: {token[:20]}...")
else:
    print("FAIL: Token not configured or invalid")
    exit(1)

# 设置token并测试
import tushare as ts

ts.set_token(token)
pro = ts.pro_api()

# 测试基础连接
print("\n[2] Testing Basic Connection")
print("-" * 80)
try:
    test_data = pro.stock_basic(list_status="L", limit=1)
    print(f"OK: Basic connection successful (returned {len(test_data)} records)")
except Exception as e:
    print(f"FAIL: Connection failed: {e}")
    import traceback

    traceback.print_exc()
    exit(1)

# 测试600765股票信息
print("\n[3] Testing Stock Basic Info for 600765")
print("-" * 80)
try:
    stock_info = pro.stock_basic(ts_code="600765.SH", list_status="L")

    if stock_info is not None and not stock_info.empty:
        print(f"OK: Found stock info")
        print(stock_info.to_string())
    else:
        print("FAIL: No stock info found")
except Exception as e:
    print(f"FAIL: Stock info failed: {e}")
    import traceback

    traceback.print_exc()

# 测试财务指标
print("\n[4] Testing Fina Indicator")
print("-" * 80)
try:
    df = pro.fina_indicator(
        ts_code="600765.SH", start_date="20240101", end_date="20250118"
    )

    if df is not None and not df.empty:
        print(f"OK: Got {len(df)} records from fina_indicator")
        print(f"Columns: {list(df.columns)[:20]}")

        # 查看最新一条数据
        print(f"\nLatest record:")
        latest = df.iloc[-1]
        print(latest.to_string())
    else:
        print("FAIL: No data from fina_indicator")

except Exception as e:
    print(f"FAIL: fina_indicator failed: {e}")
    import traceback

    traceback.print_exc()

# 测试日收益
print("\n[5] Testing Daily Info")
print("-" * 80)
try:
    df = pro.daily(ts_code="600765.SH", start_date="20250101", end_date="20250118")

    if df is not None and not df.empty:
        print(f"OK: Got {len(df)} daily records")
        print(f"Latest:")
        print(df.iloc[-1].to_string())
    else:
        print("FAIL: No daily data")

except Exception as e:
    print(f"FAIL: daily failed: {e}")

print("\n" + "=" * 80)
print("Test Complete")
print("=" * 80)
