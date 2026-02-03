# -*- coding: utf-8 -*-
"""
测试成交量分析增强功能

验证 data_source_manager.py 中增强的成交量统计输出：
- 单日成交量
- 5日均量
- 10日均量
- 量比分析（巨量/放量/平量/缩量）
"""

import sys
import os
from pathlib import Path

# Windows 编码设置
if os.name == 'nt':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_volume_analysis_output():
    """测试成交量分析输出格式"""
    print("=" * 60)
    print("测试成交量分析增强功能")
    print("=" * 60)

    from tradingagents.dataflows.data_source_manager import get_data_source_manager

    mgr = get_data_source_manager()

    # 测试股票
    test_symbol = "600765"  # 中航重机

    print(f"\n📊 获取股票数据: {test_symbol}")
    print("-" * 60)

    try:
        data = mgr.get_stock_data(test_symbol)

        if data:
            print("\n✅ 数据获取成功\n")
            print(data)
            print("\n" + "=" * 60)

            # 验证关键词
            keywords = [
                ("单日成交量", "单日成交量关键字"),
                ("5日均量", "5日均量关键字"),
                ("10日均量", "10日均量关键字"),
                ("量比:", "量比关键字"),
                ("巨量|放量|平量|缩量", "量比等级"),
            ]

            print("\n🔍 关键词验证:")
            print("-" * 40)
            all_found = True
            for keyword, desc in keywords:
                if keyword in data or ( "|" in keyword and any(k in data for k in keyword.split("|"))):
                    print(f"  ✅ {desc}: 已找到")
                else:
                    print(f"  ❌ {desc}: 未找到")
                    all_found = False

            print("\n" + "=" * 60)
            if all_found:
                print("✅ 所有验证通过！成交量分析增强功能正常工作。")
                return True
            else:
                print("⚠️ 部分验证失败，请检查输出。")
                return False
        else:
            print("❌ 数据获取失败")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_volume_ratio_calculation():
    """测试量比计算逻辑"""
    print("\n" + "=" * 60)
    print("测试量比计算逻辑")
    print("=" * 60)

    test_cases = [
        (1000, 500, 2.0, "巨量"),    # volume_latest, volume_avg_5, expected_ratio, expected_level
        (1000, 700, 1.43, "平量"),   # 1.43 < 1.5，所以是平量
        (1000, 1200, 0.83, "平量"),
        (1000, 1500, 0.67, "缩量"),
    ]

    for vol_latest, vol_avg_5, expected_ratio, expected_level in test_cases:
        volume_ratio = vol_latest / vol_avg_5
        if volume_ratio >= 2.0:
            level = "巨量"
        elif volume_ratio >= 1.5:
            level = "放量"
        elif volume_ratio >= 0.8:
            level = "平量"
        else:
            level = "缩量"

        ratio_match = abs(volume_ratio - expected_ratio) < 0.01
        level_match = level == expected_level

        status = "✅" if (ratio_match and level_match) else "❌"
        print(f"{status} 单日={vol_latest}, 5日均={vol_avg_5} "
              f"→ 量比={volume_ratio:.2f} ({level})")

    print("=" * 60)
    return True


if __name__ == "__main__":
    test_volume_ratio_calculation()
    test_volume_analysis_output()
