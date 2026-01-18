# -*- coding: utf-8 -*-
"""
检查 stock_financial_abstract 数据结构
"""

import akshare as ak
import pandas as pd

print("=" * 80)
print("Checking stock_financial_abstract for 600765")
print("=" * 80)

code = "600765"

try:
    df = ak.stock_financial_abstract(symbol=code)

    if df is not None and not df.empty:
        print(f"OK: Got {len(df)} records")
        print(f"\nColumns ({len(df.columns)}):")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i}. {col}")

        print(f"\nFirst record:")
        first_record = df.iloc[0]
        print(first_record.to_string())

        print(f"\nLatest record:")
        latest_record = df.iloc[-1]
        print(latest_record.to_string())

        # 查看关键字段
        key_fields = [
            "roe",
            "pb",
            "pe",
            "total_assets",
            "total_liab",
            "net_profit",
            "revenue",
        ]
        print(f"\n\nKey financial fields in latest record:")
        for field in key_fields:
            if field in df.columns:
                value = latest_record.get(field)
                print(f"  {field}: {value}")
            else:
                print(f"  {field}: [NOT PRESENT]")

    else:
        print("FAIL: No data")

except Exception as e:
    print(f"FAIL: {e}")
    import traceback

    traceback.print_exc()
