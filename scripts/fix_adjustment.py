# -*- coding: utf-8 -*-
"""



1. tradingagents/dataflows/providers/china/akshare.py 841
   adjust="" → adjust="qfq"

2. tradingagents/dataflows/providers/china/baostock.py 390
   adjustflag="3" → adjustflag="2"


- / → 
-  → 
- PE/PB→ 
"""

import os
from pathlib import Path

# 
PROJECT_ROOT = Path(__file__).parent.parent

# 
FIXES = [
    {
        "file": PROJECT_ROOT / "tradingagents/dataflows/providers/china/akshare.py",
        "line": 841,
        "old": 'return self.ak.stock_zh_a_hist(symbol=code, period="daily", adjust="")',
        "new": 'return self.ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")  # ',
        "description": "AkShare ",
    },
    {
        "file": PROJECT_ROOT / "tradingagents/dataflows/providers/china/baostock.py",
        "line": 390,
        "old": '                    adjustflag="3"',
        "new": '                    adjustflag="2"  # "3"',
        "description": "Baostock K",
    },
]


def fix_file(file_path, line_num, old_text, new_text, description):
    """"""
    print(f"\n{'=' * 70}")
    print(f": {description}")
    print(f": {file_path}")
    print(f": {line_num}")
    print(f"{'=' * 70}")

    # 
    if not file_path.exists():
        print(f" : {file_path}")
        return False

    # 
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if line_num > len(lines):
            print(f"  {len(lines)}  {line_num}")
            return False

        # 
        original_line = lines[line_num - 1].rstrip()
        print(f"\n ({line_num}):")
        print(f"  {original_line}")

        # 
        if old_text not in original_line:
            print(f"\n : {line_num}")
            print(f"  : {old_text}")
            print(f"  : {original_line}")
            print(f"\n ...")

            # 
            key_part = "adjust" if "adjust" in old_text else "adjustflag"
            found_lines = []
            for i, line in enumerate(lines, 1):
                if key_part in line and old_text.split("=")[1] in line:
                    found_lines.append((i, line.rstrip()))

            if found_lines:
                print(f"\n  {len(found_lines)} :")
                for i, line in found_lines[:3]:  # 3
                    print(f"  {i}: {line[:80]}...")
                print(f"\n  {found_lines[0][0]} ")
                line_num = found_lines[0][0]
                original_line = lines[line_num - 1].rstrip()
            else:
                print(f"  '{key_part}' ")
                return False

        # 
        lines[line_num - 1] = new_text + "\n"

        # 
        print(f"\n ({line_num}):")
        print(f"  {lines[line_num - 1].rstrip()}")

        # 
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        print(f"\n !")
        return True

    except Exception as e:
        print(f"\n : {e}")
        return False


def verify_fixes():
    """"""
    print(f"\n{'=' * 70}")
    print("")
    print(f"{'=' * 70}\n")

    all_fixed = True

    for fix in FIXES:
        file_path = fix["file"]
        new_text = fix["new"]

        print(f"\n: {fix['description']}")
        print(f": {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if new_text.split("  #")[0].strip() in content:
                print(f" : ")
            else:
                print(f" : ")
                all_fixed = False

        except Exception as e:
            print(f" : {e}")
            all_fixed = False

    return all_fixed


def main():
    """"""
    print("\n" + "=" * 70)
    print(" ")
    print("=" * 70)

    print(f"\n: {PROJECT_ROOT}")
    print(f": {len(FIXES)}")

    # 
    print(f"\n:")
    for i, fix in enumerate(FIXES, 1):
        print(f"\n{i}. {fix['description']}")
        print(f"   : {fix['file']}")
        print(f"   : {fix['line']}")
        print(f"   : {fix['old'][:50]}...")
        print(f"   :   {fix['new'][:50]}...")

    # Windows 
    try:
        response = input(f"\n(y/n): ").strip().lower()
        if response not in ["y", "yes", "", ""]:
            print("\n ")
            return
    except (EOFError, KeyboardInterrupt):
        print("\n\n ")
        return

    # 
    success_count = 0
    for fix in FIXES:
        if fix_file(
            file_path=fix["file"],
            line_num=fix["line"],
            old_text=fix["old"],
            new_text=fix["new"],
            description=fix["description"],
        ):
            success_count += 1

    # 
    print(f"\n{'=' * 70}")
    print(f": {success_count}/{len(FIXES)} ")
    print(f"{'=' * 70}")

    if success_count > 0:
        if verify_fixes():
            print(f"\n{'=' * 70}")
            print(" !")
            print(f"{'=' * 70}\n")

            print(" :")
            print("    AkShare : ")
            print("    Baostock K: ")
            print("    : ")
            print("\n :")
            print("   - MAMACDRSI")
            print("   - K")
            print("   - /")
            print("\n :")
            print("   1. : python scripts/test_adjustment_fix.py")
            print(
                "   2. : python scripts/test_technical_indicators.py"
            )
            print(
                "   3. : git add . && git commit -m 'fix: '"
            )
        else:
            print(f"\n{'=' * 70}")
            print(" ")
            print(f"{'=' * 70}\n")
    else:
        print("\n ")


if __name__ == "__main__":
    main()
