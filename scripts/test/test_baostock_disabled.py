# -*- coding: utf-8 -*-
"""
BaoStock 禁用验证脚本
验证所有 BaoStock 配置是否正确设置为 false
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from app.core.config import settings

    print("=" * 60)
    print("BaoStock Configuration Verification")
    print("=" * 60)

    # 检查所有 BaoStock 相关配置
    baostock_configs = {
        "BAOSTOCK_UNIFIED_ENABLED": settings.BAOSTOCK_UNIFIED_ENABLED,
        "BAOSTOCK_BASIC_INFO_SYNC_ENABLED": settings.BAOSTOCK_BASIC_INFO_SYNC_ENABLED,
        "BAOSTOCK_DAILY_QUOTES_SYNC_ENABLED": settings.BAOSTOCK_DAILY_QUOTES_SYNC_ENABLED,
        "BAOSTOCK_HISTORICAL_SYNC_ENABLED": settings.BAOSTOCK_HISTORICAL_SYNC_ENABLED,
        "BAOSTOCK_STATUS_CHECK_ENABLED": settings.BAOSTOCK_STATUS_CHECK_ENABLED,
    }

    all_disabled = True
    for config_name, config_value in baostock_configs.items():
        status = "[OK]" if config_value is False else "[FAIL]"
        print(f"{status} {config_name}: {config_value}")
        if config_value is not False:
            all_disabled = False

    print("=" * 60)
    if all_disabled:
        print("[SUCCESS] All BaoStock configurations are disabled")
        print("=" * 60)
        sys.exit(0)
    else:
        print("[FAILED] Some configurations are not properly disabled")
        print("=" * 60)
        sys.exit(1)

except ImportError as e:
    print(f"[ERROR] Cannot import config module: {e}")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Verification failed: {e}")
    sys.exit(1)
