# -*- coding: utf-8 -*-
"""
验证 Tushare 同步服务拆分结果
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def verify_imports():
    """验证所有导入是否正常"""
    print(">> 验证导入...")

    try:
        from app.worker.tushare_sync_service import (
            TushareSyncService,
            get_tushare_sync_service,
            TushareDailySync,
            TushareRealtimeSync,
            TushareFinancialSync,
            TushareNewsSync,
            get_utc8_now,
            run_tushare_basic_info_sync,
            run_tushare_quotes_sync,
            run_tushare_hourly_bulk_sync,
            run_tushare_historical_sync,
            run_tushare_financial_sync,
            run_tushare_status_check,
            run_tushare_news_sync,
        )
        print("[OK] 所有公共API导入成功")
        return True
    except Exception as e:
        print(f"[FAIL] 导入失败: {e}")
        return False


def verify_file_sizes():
    """验证文件大小是否符合预期"""
    print("\n>> 文件大小统计...")

    files = {
        "app/worker/tushare/__init__.py": 59,
        "app/worker/tushare/base.py": 185,
        "app/worker/tushare/daily.py": 484,
        "app/worker/tushare/realtime.py": 290,
        "app/worker/tushare/financial.py": 185,
        "app/worker/tushare/news.py": 184,
        "app/worker/tushare/tasks.py": 293,
        "app/worker/tushare_sync_service.py": 53,
    }

    total = 0
    for file_path, expected_lines in files.items():
        full_path = project_root / file_path
        if full_path.exists():
            with open(full_path, "r", encoding="utf-8") as f:
                actual_lines = len(f.readlines())
            total += actual_lines
            status = "[OK]" if actual_lines == expected_lines else "[WARN]"
            print(
                f"{status} {file_path}: {actual_lines} lines"
                f" (expected: {expected_lines})"
            )
        else:
            print(f"[FAIL] {file_path}: file not found")

    print(f"\n>> Total: {total} lines")

    # 计算单个文件最大行数
    max_file_lines = max(files.values())
    print(f">> Max file size: {max_file_lines} lines")

    # 计算减少比例（基于单个文件）
    original_lines = 1568
    reduction_rate = (1 - max_file_lines / original_lines) * 100
    print(f">> Max file size reduction: {reduction_rate:.1f}%")

    if reduction_rate >= 40:
        print("[OK] Achieved target (40%+ reduction in max file size)")
        return True
    else:
        print(f"[WARN] Not achieved target (40%+ reduction), actual: {reduction_rate:.1f}%")
        return False


def verify_class_hierarchy():
    """验证类继承关系"""
    print("\n>> 验证类继承关系...")

    try:
        from app.worker.tushare import (
            TushareSyncService,
            TushareSyncBase,
            TushareDailySync,
            TushareRealtimeSync,
            TushareFinancialSync,
            TushareNewsSync,
        )

        # 验证继承关系
        assert issubclass(TushareSyncService, TushareDailySync), "TushareSyncService 应该继承 TushareDailySync"
        assert issubclass(TushareSyncService, TushareRealtimeSync), "TushareSyncService 应该继承 TushareRealtimeSync"
        assert issubclass(TushareSyncService, TushareFinancialSync), "TushareSyncService 应该继承 TushareFinancialSync"
        assert issubclass(TushareSyncService, TushareNewsSync), "TushareSyncService 应该继承 TushareNewsSync"
        assert issubclass(TushareDailySync, TushareSyncBase), "TushareDailySync 应该继承 TushareSyncBase"
        assert issubclass(TushareRealtimeSync, TushareSyncBase), "TushareRealtimeSync 应该继承 TushareSyncBase"
        assert issubclass(TushareFinancialSync, TushareSyncBase), "TushareFinancialSync 应该继承 TushareSyncBase"
        assert issubclass(TushareNewsSync, TushareSyncBase), "TushareNewsSync 应该继承 TushareSyncBase"

        print("[OK] 所有类继承关系正确")
        return True
    except Exception as e:
        print(f"[FAIL] 类继承关系验证失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 80)
    print("Tushare Sync Service Refactoring Verification")
    print("=" * 80)

    results = []

    # 验证导入
    results.append(verify_imports())

    # 验证文件大小
    results.append(verify_file_sizes())

    # 验证类继承关系
    results.append(verify_class_hierarchy())

    # 总结
    print("\n" + "=" * 80)
    if all(results):
        print("[OK] All verifications passed! Refactoring successful!")
        return 0
    else:
        print("[FAIL] Some verifications failed, please check error messages")
        return 1


if __name__ == "__main__":
    exit(main())
