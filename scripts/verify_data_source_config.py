#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据源配置优化验证脚本
验证实时行情和历史/财务数据源配置是否正确
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings


def check_config():
    """检查配置是否符合预期"""
    print("=" * 60)
    print("Data Source Config Verification")
    print("=" * 60)

    all_passed = True

    # ===== Phase 1: 实时同步调度任务 =====
    print("\n[Phase 1] 实时同步调度任务")
    print("-" * 40)

    checks = [
        ("QUOTES_INGEST_ENABLED", settings.QUOTES_INGEST_ENABLED, False),
        ("TUSHARE_QUOTES_SYNC_ENABLED", settings.TUSHARE_QUOTES_SYNC_ENABLED, False),
        (
            "TUSHARE_HOURLY_BULK_SYNC_ENABLED",
            settings.TUSHARE_HOURLY_BULK_SYNC_ENABLED,
            False,
        ),
        ("AKSHARE_QUOTES_SYNC_ENABLED", settings.AKSHARE_QUOTES_SYNC_ENABLED, False),
    ]

    for name, value, expected in checks:
        status = "[OK]" if value == expected else "[FAIL]"
        print(f"  {status} {name}: {value} (预期: {expected})")
        if value != expected:
            all_passed = False

    # ===== Phase 2: 实时行情配置 =====
    print("\n[Phase 2] 实时行情配置 (仅使用 AKShare)")
    print("-" * 40)

    checks = [
        ("REALTIME_QUOTE_ENABLED", settings.REALTIME_QUOTE_ENABLED, True),
        (
            "REALTIME_QUOTE_TUSHARE_ENABLED",
            settings.REALTIME_QUOTE_TUSHARE_ENABLED,
            False,
        ),
        (
            "REALTIME_QUOTE_AKSHARE_PRIORITY",
            settings.REALTIME_QUOTE_AKSHARE_PRIORITY,
            1,
        ),
        (
            "REALTIME_QUOTE_TUSHARE_PRIORITY",
            settings.REALTIME_QUOTE_TUSHARE_PRIORITY,
            2,
        ),
    ]

    for name, value, expected in checks:
        status = "[OK]" if value == expected else "[FAIL]"
        print(f"  {status} {name}: {value} (预期: {expected})")
        if value != expected:
            all_passed = False

    # ===== Phase 3: 盘后同步任务 =====
    print("\n[Phase 3] 盘后同步任务 (使用 Tushare)")
    print("-" * 40)

    checks = [
        (
            "TUSHARE_HISTORICAL_SYNC_ENABLED",
            settings.TUSHARE_HISTORICAL_SYNC_ENABLED,
            True,
        ),
        (
            "TUSHARE_FINANCIAL_SYNC_ENABLED",
            settings.TUSHARE_FINANCIAL_SYNC_ENABLED,
            True,
        ),
    ]

    for name, value, expected in checks:
        status = "[OK]" if value == expected else "[FAIL]"
        print(f"  {status} {name}: {value} (预期: {expected})")
        if value != expected:
            all_passed = False

    # ===== Phase 4: BaoStock 禁用状态 =====
    print("\n[Phase 4] BaoStock 禁用状态")
    print("-" * 40)

    baostock_checks = [
        ("BAOSTOCK_UNIFIED_ENABLED", settings.BAOSTOCK_UNIFIED_ENABLED),
        ("BAOSTOCK_BASIC_INFO_SYNC_ENABLED", settings.BAOSTOCK_BASIC_INFO_SYNC_ENABLED),
        (
            "BAOSTOCK_DAILY_QUOTES_SYNC_ENABLED",
            settings.BAOSTOCK_DAILY_QUOTES_SYNC_ENABLED,
        ),
        ("BAOSTOCK_HISTORICAL_SYNC_ENABLED", settings.BAOSTOCK_HISTORICAL_SYNC_ENABLED),
        ("BAOSTOCK_STATUS_CHECK_ENABLED", settings.BAOSTOCK_STATUS_CHECK_ENABLED),
    ]

    for name, value in baostock_checks:
        status = "[OK]" if value == False else "[FAIL]"
        print(f"  {status} {name}: {value} (预期: False)")
        if value != False:
            all_passed = False

    # ===== 汇总 =====
    print("\n" + "=" * 60)
    if all_passed:
        print("[SUCCESS] 所有配置验证通过！")
        print("\n预期行为:")
        print("  * 交易时段：不进行自动数据同步")
        print("  * 实时行情：分析时仅使用 AKShare 获取")
        print("  * 收盘后：Tushare 自动同步历史数据")
        print("  * 周日：Tushare 自动同步财务数据")
        return 0
    else:
        print("[ERROR] 部分配置验证失败，请检查 .env 文件")
        return 1


if __name__ == "__main__":
    sys.exit(check_config())
