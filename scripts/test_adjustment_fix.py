# -*- coding: utf-8 -*-
"""



"""

import asyncio
import sys
from pathlib import Path

# 
sys.path.insert(0, str(Path(__file__).parent.parent))

from tradingagents.dataflows.providers.china.akshare import AKShareProvider
from tradingagents.dataflows.providers.china.baostock import BaoStockProvider


async def test_akshare_adjustment():
    """ AkShare """
    print("=" * 70)
    print(" AkShare ")
    print("=" * 70)

    provider = AKShareProvider()

    if not provider.connected:
        print(" AkShare ")
        return False

    print(" AkShare ")

    # 1
    print("\n1: ")
    try:
        data = await provider.get_spot_data("000001")
        if data and "close" in data:
            print(f" ")
            print(f"   : {data['close']}")
            if "change_percent" in data:
                print(f"   : {data['change_percent']}%")
        else:
            print(" ")
            return False
    except Exception as e:
        print(f" : {e}")
        return False

    # 2
    print("\n2: ")
    try:
        akshare_file = (
            Path(__file__).parent.parent
            / "tradingagents/dataflows/providers/china/akshare.py"
        )
        with open(akshare_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 841
        lines = content.split("\n")
        line_841 = lines[840].strip() if len(lines) > 840 else ""

        print(f"   841: {line_841[:80]}...")

        if 'adjust="qfq"' in line_841:
            print('  (adjust="qfq")')
            return True
        elif 'adjust=""' in line_841:
            print('  (adjust="")')
            return False
        else:
            print(f" : {line_841}")
            return False

    except Exception as e:
        print(f" : {e}")
        return False


async def test_baostock_adjustment():
    """ Baostock """
    print("\n" + "=" * 70)
    print(" Baostock ")
    print("=" * 70)

    provider = BaoStockProvider()

    if not provider.connected:
        print(" Baostock ")
        return False

    print(" Baostock ")

    # 1
    print("\n1: ")
    try:
        data = await provider.get_spot_data("000001")
        if data and "close" in data:
            print(f" ")
            print(f"   : {data['close']}")
            if "change_percent" in data:
                print(f"   : {data['change_percent']}%")
        else:
            print(" ")
            return False
    except Exception as e:
        print(f" : {e}")
        return False

    # 2
    print("\n2: ")
    try:
        baostock_file = (
            Path(__file__).parent.parent
            / "tradingagents/dataflows/providers/china/baostock.py"
        )
        with open(baostock_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 390_get_latest_kline_data 
        lines = content.split("\n")
        line_390 = lines[389].strip() if len(lines) > 389 else ""

        print(f"   390: {line_390[:80]}...")

        if 'adjustflag="2"' in line_390:
            print('  (adjustflag="2")')
            return True
        elif 'adjustflag="3"' in line_390:
            print('  (adjustflag="3")')
            return False
        else:
            print(f" : {line_390}")
            return False

    except Exception as e:
        print(f" : {e}")
        return False


async def test_technical_indicators():
    """"""
    print("\n" + "=" * 70)
    print("")
    print("=" * 70)

    try:
        from tradingagents.dataflows.interface import get_china_stock_data_unified

        symbol = "000001"
        print(f"\n {symbol} ...")

        data = await get_china_stock_data_unified(symbol, period="daily", count=100)

        if not data:
            print(f"  {symbol} ")
            return False

        print(f"  {symbol} ")

        # 
        print("\n:")
        if "MA5" in data:
            print(f"    MA5: {data['MA5']}")
        if "MA20" in data:
            print(f"    MA20: {data['MA20']}")
        if "MACD" in data:
            print(f"    MACD: {data['MACD']}")
        if "RSI" in data:
            print(f"    RSI: {data['RSI']}")

        # 
        if "" in data:
            import pandas as pd

            df = pd.DataFrame(data[""])

            print(f"\n:")
            print(f"   : {len(df)}")
            print(f"   : {df['close'].min():.2f}")
            print(f"   : {df['close'].max():.2f}")
            print(f"   : {df['close'].iloc[-1]:.2f}")

            # 
            df["pct_change"] = df["close"].pct_change()
            extreme_changes = df[abs(df["pct_change"]) > 0.2]  # 20%

            if len(extreme_changes) > 0:
                print(f"\n     {len(extreme_changes)} :")
                for idx, row in extreme_changes.iterrows():
                    print(f"      - {row['date']}: {row['pct_change'] * 100:.2f}%")
                print(f"    : ")
            else:
                print(f"\n    ")

        return True

    except Exception as e:
        print(f" : {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """"""
    print("\n" + "=" * 70)
    print("[] ")
    print("=" * 70)

    results = []

    #  AkShare
    result = await test_akshare_adjustment()
    results.append(("AkShare", result))

    #  Baostock
    result = await test_baostock_adjustment()
    results.append(("Baostock", result))

    # 
    result = await test_technical_indicators()
    results.append(("", result))

    # 
    print("\n" + "=" * 70)
    print("")
    print("=" * 70)

    for name, result in results:
        status = " " if result else " "
        print(f"   {name}: {status}")

    all_passed = all(result for _, result in results)

    print("\n" + "=" * 70)
    if all_passed:
        print(" !")
        print("=" * 70)
        print("\n :")
        print("    AkShare : ")
        print("    Baostock K: ")
        print("    : ")
        print("\n :")
        print("   - MAMACDRSI")
        print("   - ")
        print("   - ")
    else:
        print(" ")
        print("=" * 70)
        print("\n :")
        print("   1. ")
        print("   2. ")
        print("   3. ")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
