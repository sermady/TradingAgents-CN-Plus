# -*- coding: utf-8 -*-
"""
直接测试Tushare获取600765财务数据
"""

import tushare as ts
import os

print("=" * 80)
print("Testing Tushare Financial Data for 600765")
print("=" * 80)

# 检查Token
token = os.getenv("TUSHARE_TOKEN")
print(f"\n[1] Tushare Token Check")
print("-" * 80)
if token and not token.startswith("your_"):
    print(f"OK: Token found (length: {len(token)})")
else:
    print("FAIL: Token not configured or invalid")
    exit(1)

# 设置token
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
    exit(1)

# 测试财务指标接口
print("\n[3] Testing Fina Indicator Interface")
print("-" * 80)
try:
    # 方法1: fina_indicator
    df = pro.fina_indicator(
        ts_code="600765.SH", start_date="20240101", end_date="20250118"
    )

    if df is not None and not df.empty:
        print(f"OK: Got {len(df)} records from fina_indicator")
        print(f"Columns: {list(df.columns)}")
        print(f"\nLatest record:")
        print(df.iloc[-1].to_string())
    else:
        print("FAIL: No data returned from fina_indicator")

except Exception as e:
    print(f"FAIL: fina_indicator failed: {e}")

# 测试财务摘要接口
print("\n[4] Testing Financial Summary Interface")
print("-" * 80)
try:
    # 方法2: fina_indicator
    df = pro.fina_indicator(
        ts_code="600765.SH",
        start_date="20230101",
        end_date="20250118",
        fields="ts_code,end_date,ann_date,roe,eps,net_profit,net_assets",
    )

    if df is not None and not df.empty:
        print(f"OK: Got {len(df)} records from fina_indicator (fields)")
        print(f"\nLatest record:")
        print(df.iloc[-1].to_string())
    else:
        print("FAIL: No data returned from fina_indicator (fields)")

except Exception as e:
    print(f"FAIL: fina_indicator (fields) failed: {e}")

# 测试balance接口
print("\n[5] Testing Balance Sheet Interface")
print("-" * 80)
try:
    df = pro.balancesheet(
        ts_code="600765.SH", start_date="20240101", end_date="20250118"
    )

    if df is not None and not df.empty:
        print(f"OK: Got {len(df)} records from balancesheet")
        print(f"Columns: {list(df.columns)}")
    else:
        print("FAIL: No data returned from balancesheet")

except Exception as e:
    print(f"FAIL: balancesheet failed: {e}")

# 测试income接口
print("\n[6] Testing Income Statement Interface")
print("-" * 80)
try:
    df = pro.income(ts_code="600765.SH", start_date="20240101", end_date="20250118")

    if df is not None and not df.empty:
        print(f"OK: Got {len(df)} records from income")
        print(f"Columns: {list(df.columns)}")
    else:
        print("FAIL: No data returned from income")

except Exception as e:
    print(f"FAIL: income failed: {e}")

print("\n" + "=" * 80)
print("Test Complete")
print("=" * 80)
