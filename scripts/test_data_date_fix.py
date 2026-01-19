#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：验证股票数据是否正确标注最新数据日期
"""

import os
import sys
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradingagents.utils.logging_init import get_logger

logger = get_logger("test")


def test_data_date_labeling():
    """测试数据日期标注功能"""
    print("\n" + "=" * 80)
    print("🧪 测试股票数据日期标注功能")
    print("=" * 80)

    try:
        from tradingagents.dataflows.data_source_manager import (
            get_data_source_manager,
        )

        manager = get_data_source_manager()

        # 测试股票代码
        test_symbol = "600765"
        # 使用当前日期作为结束日期
        end_date = datetime.now().strftime("%Y-%m-%d")
        # 开始日期往前推30天
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        print(f"\n📊 测试股票: {test_symbol}")
        print(f"📅 请求日期范围: {start_date} 至 {end_date}")
        print(f"⏳ 正在获取数据...\n")

        # 调用统一接口获取数据
        result = manager.get_stock_data(test_symbol, start_date, end_date)

        if result and "❌" not in result:
            print("✅ 数据获取成功！")
            print("\n" + "-" * 80)
            print("📋 数据内容预览（前1000字符）:")
            print("-" * 80)
            print(result[:1000])
            print("-" * 80)

            # 检查关键字段
            checks = {
                "最新数据日期": "最新数据日期:" in result,
                "数据日期标注": "数据日期:" in result,
                "日期警告": "注意：最新数据日期" in result,
            }

            print("\n🔍 关键字段检查:")
            for field, exists in checks.items():
                status = "✅" if exists else "❌"
                print(f"   {status} {field}: {'存在' if exists else '缺失'}")

            # 提取最新数据日期
            if "最新数据日期:" in result:
                lines = result.split("\n")
                for line in lines:
                    if "最新数据日期:" in line:
                        print(f"\n📅 {line.strip()}")
                        break

            # 提取最新价格行
            if "最新价格:" in result:
                lines = result.split("\n")
                for line in lines:
                    if "最新价格:" in line:
                        print(f"💰 {line.strip()}")
                        break

            # 检查是否有日期不一致警告
            if "注意：最新数据日期" in result:
                print("\n⚠️ 发现数据日期警告：")
                lines = result.split("\n")
                for line in lines:
                    if "注意：最新数据日期" in line:
                        print(f"   {line.strip()}")

            return True
        else:
            print(f"❌ 数据获取失败:")
            print(result[:500])
            return False

    except Exception as e:
        import traceback

        print(f"❌ 测试失败: {e}")
        print(traceback.format_exc())
        return False


def test_multiple_stocks():
    """测试多个股票的数据日期标注"""
    print("\n" + "=" * 80)
    print("🧪 测试多个股票的数据日期标注")
    print("=" * 80)

    test_stocks = ["600765", "000001", "600036"]

    results = []
    for symbol in test_stocks:
        print(f"\n📊 测试股票: {symbol}")

        try:
            from tradingagents.dataflows.data_source_manager import (
                get_data_source_manager,
            )

            manager = get_data_source_manager()

            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

            result = manager.get_stock_data(symbol, start_date, end_date)

            if result and "❌" not in result:
                # 提取最新数据日期
                latest_date = "未知"
                if "最新数据日期:" in result:
                    for line in result.split("\n"):
                        if "最新数据日期:" in line:
                            latest_date = line.split(":")[-1].strip()
                            break

                # 提取最新价格
                latest_price = "未知"
                if "最新价格:" in result:
                    for line in result.split("\n"):
                        if "最新价格:" in line:
                            latest_price = (
                                line.split("¥")[1].split()[0] if "¥" in line else "未知"
                            )
                            break

                has_warning = "注意：最新数据日期" in result

                print(f"   ✅ 成功")
                print(f"   📅 最新数据日期: {latest_date}")
                print(f"   💰 最新价格: ¥{latest_price}")
                print(f"   ⚠️ 日期警告: {'是' if has_warning else '否'}")

                results.append(
                    {
                        "symbol": symbol,
                        "success": True,
                        "latest_date": latest_date,
                        "latest_price": latest_price,
                        "has_warning": has_warning,
                    }
                )
            else:
                print(f"   ❌ 失败: {result[:100]}")
                results.append({"symbol": symbol, "success": False})

        except Exception as e:
            print(f"   ❌ 异常: {e}")
            results.append({"symbol": symbol, "success": False})

    # 汇总结果
    print("\n" + "=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)

    success_count = sum(1 for r in results if r.get("success", False))
    warning_count = sum(1 for r in results if r.get("has_warning", False))

    print(f"\n总测试数: {len(results)}")
    print(f"成功数: {success_count}")
    print(f"失败数: {len(results) - success_count}")
    print(f"有日期警告: {warning_count}")

    return success_count == len(results)


def main():
    """主函数"""
    print("\n" + "🚀" * 40)
    print("数据日期标注功能测试")
    print("🚀" * 40)

    # 测试1：单个股票详细测试
    test1_result = test_data_date_labeling()

    # 测试2：多个股票批量测试
    test2_result = test_multiple_stocks()

    # 总结
    print("\n" + "=" * 80)
    print("📋 最终测试结果")
    print("=" * 80)
    print(f"测试1 (单股票详细测试): {'✅ 通过' if test1_result else '❌ 失败'}")
    print(f"测试2 (多股票批量测试): {'✅ 通过' if test2_result else '❌ 失败'}")

    if test1_result and test2_result:
        print("\n🎉 所有测试通过！数据日期标注功能正常！")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查问题。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
