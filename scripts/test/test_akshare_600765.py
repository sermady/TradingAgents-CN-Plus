# -*- coding: utf-8 -*-
"""
测试AKShare财务数据获取
"""

import akshare as ak
import pandas as pd

print("=" * 80)
print("Testing AKShare Financial Data for 600765")
print("=" * 80)

code = "600765"

# 1. 测试财务指标接口
print("\n[1] Testing stock_financial_analysis_indicator")
print("-" * 80)
try:
    df = ak.stock_financial_analysis_indicator(symbol=code)
    if df is not None and not df.empty:
        print(f"OK: Got {len(df)} records")
        print(f"\nColumns: {list(df.columns)}")
        print(f"\nFirst record:")
        print(df.iloc[-1].to_string())
    else:
        print(f"FAIL: No data returned or empty DataFrame")
except Exception as e:
    print(f"FAIL: Exception: {e}")

# 2. 测试个股信息接口
print("\n[2] Testing stock_individual_info_em")
print("-" * 80)
try:
    df_info = ak.stock_individual_info_em(symbol=code)
    if df_info is not None and not df_info.empty:
        print(f"OK: Got {len(df_info)} records")
        print(f"\nColumns: {list(df_info.columns)}")
        print(f"\nFirst 10 rows:")
        print(df_info.head(10))
    else:
        print(f"FAIL: No data returned or empty DataFrame")
except Exception as e:
    print(f"FAIL: Exception: {e}")

# 3. 测试股票基础信息
print("\n[3] Testing stock_individual_info_xq")
print("-" * 80)
try:
    df_basic = ak.stock_individual_info_xq(symbol=code)
    if df_basic is not None and not df_basic.empty:
        print(f"OK: Got basic info")
        print(f"\nColumns: {list(df_basic.columns)}")
        print(f"\nData:")
        print(df_basic.to_string())
    else:
        print(f"FAIL: No basic info returned")
except Exception as e:
    print(f"FAIL: Exception: {e}")

print("\n" + "=" * 80)
print("Test Complete")
print("=" * 80)
