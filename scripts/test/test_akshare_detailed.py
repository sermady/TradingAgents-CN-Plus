# -*- coding: utf-8 -*-
"""
详细测试AKShare数据格式
"""

import akshare as ak
import pandas as pd

print("=" * 80)
print("Detailed AKShare Data Test for 600765")
print("=" * 80)

code = "600765"

# 测试 stock_individual_info_em
print("\n[Testing] stock_individual_info_em")
print("-" * 80)
try:
    df = ak.stock_individual_info_em(symbol=code)
    if df is not None and not df.empty:
        print(f"OK: Got {len(df)} records")
        print(f"\nColumns: {list(df.columns)}")
        print(f"\nAll data:")
        print(df.to_string())
    else:
        print("FAIL: No data")
except Exception as e:
    print(f"FAIL: Exception: {e}")

# 测试所有可能包含财务数据的AKShare接口
financial_apis = [
    "stock_a_indicator",
    "stock_a_lg_indicator",
    "stock_a_share_indicator",
    "stock_financial_abstract",
    "stock_financial_analysis_indicator",
    "stock_individual_info_em",
    "stock_individual_info_xq",
]

print("\n\n" + "=" * 80)
print("Testing All AKShare Financial APIs")
print("=" * 80)

for api_name in financial_apis:
    print(f"\n[{api_name}]")
    print("-" * 80)
    try:
        func = getattr(ak, api_name)

        # 尝试调用接口
        result = func(symbol=code)

        if isinstance(result, pd.DataFrame):
            if result.empty:
                print(f"FAIL: Empty DataFrame")
            else:
                print(f"OK: Got {len(result)} records")
                print(f"Columns: {list(result.columns)}")
                if len(result) <= 3:
                    print(f"Data:\n{result.to_string()}")
        else:
            print(f"Result type: {type(result)}")
            print(f"Result: {result}")

    except Exception as e:
        print(f"FAIL: Exception: {e}")
        import traceback

        traceback.print_exc()

print("\n" + "=" * 80)
print("Test Complete")
print("=" * 80)
