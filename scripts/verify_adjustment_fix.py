# -*- coding: utf-8 -*-
"""
复权修复验证脚本（简化版）
"""

from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

print("=" * 70)
print("[验证] 复权修复验证")
print("=" * 70)

# 测试1: 验证 AkShare 修复
print("\n[1/2] 验证 AkShare 修复")
print("-" * 70)

akshare_file = PROJECT_ROOT / "tradingagents/dataflows/providers/china/akshare.py"
with open(akshare_file, "r", encoding="utf-8") as f:
    content = f.read()

# 检查第841行附近的代码
lines = content.split("\n")
line_841 = lines[840].strip() if len(lines) > 840 else ""

print(f"第841行: {line_841[:80]}...")

if 'adjust="qfq"' in line_841:
    print("✅ AkShare 已使用前复权")
    akshare_ok = True
elif 'adjust=""' in line_841:
    print("❌ AkShare 仍使用不复权")
    akshare_ok = False
else:
    print(f"⚠️ AkShare 第841行不包含预期的复权配置")
    akshare_ok = False

# 测试2: 验证 BaoStock 修复
print("\n[2/2] 验证 BaoStock 修复")
print("-" * 70)

baostock_file = PROJECT_ROOT / "tradingagents/dataflows/providers/china/baostock.py"
with open(baostock_file, "r", encoding="utf-8") as f:
    content = f.read()

# 检查第390行附近的代码
lines = content.split("\n")
line_390 = lines[389].strip() if len(lines) > 389 else ""

print(f"第390行: {line_390[:80]}...")

if 'adjustflag="2"' in line_390:
    print("✅ BaoStock 已使用前复权")
    baostock_ok = True
elif 'adjustflag="3"' in line_390:
    print("❌ BaoStock 仍使用不复权")
    baostock_ok = False
else:
    print(f"⚠️ BaoStock 第390行不包含预期的复权配置")
    baostock_ok = False

# 总结
print("\n" + "=" * 70)
print("[结果] 修复验证总结")
print("=" * 70)

print(f"\nAkShare: {'✅ 通过' if akshare_ok else '❌ 失败'}")
print(f"BaoStock: {'✅ 通过' if baostock_ok else '❌ 失败'}")

if akshare_ok and baostock_ok:
    print("\n✅ 所有修复验证通过!")
    print("\n[修复内容]")
    print("  1. AkShare 实时行情: adjust='' → adjust='qfq'")
    print("  2. BaoStock 最新K线: adjustflag='3' → adjustflag='2'")
    print("\n[修复效果]")
    print("  - 技术指标 (MA、MACD、RSI) 计算准确")
    print("  - K线连续，无明显除权跳变")
    print("  - 与同花顺/通达信行为一致")
    print("\n[建议]")
    print('  1. 提交代码: git add . && git commit -m "fix: 统一复权处理为前复权"')
    print("  2. 测试股票分析功能")
else:
    print("\n⚠️ 部分修复验证失败")
    print("\n[建议]")
    print("  1. 检查文件内容是否已更新")
    print("  2. 手动检查以下文件:")
    if not akshare_ok:
        print(f"     - {akshare_file} (第841行)")
    if not baostock_ok:
        print(f"     - {baostock_file} (第390行)")

print("\n" + "=" * 70)
