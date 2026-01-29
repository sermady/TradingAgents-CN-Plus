#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试成交量单位是否正确（手）
测试股票：600391
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
from tradingagents.utils.logging_init import get_logger

logger = get_logger("scripts.test_volume")


async def test_tushare_volume():
    """测试 Tushare 成交量单位"""
    print("\n" + "=" * 60)
    print("[测试 Tushare]")
    print("=" * 60)

    try:
        from tradingagents.dataflows.providers.china.tushare import TushareProvider

        provider = TushareProvider()

        # 获取实时行情
        print("\n[1] 测试实时行情...")
        quote = await provider.get_stock_quotes("600391")

        if quote:
            volume = quote.get("volume", 0)
            volume_unit = quote.get("volume_unit", "unknown")
            amount = quote.get("amount", 0)

            print(f"  股票: 600391")
            print(f"  成交量: {volume:,.0f}")
            print(f"  单位: {volume_unit}")
            print(f"  成交额: {amount:,.0f} 元")

            # 验证：成交量单位应为"lots"
            if volume_unit == "lots":
                print(f"  ✅ volume_unit 标注正确: lots")
            else:
                print(f"  ❌ volume_unit 标注错误: {volume_unit} (应为 lots)")

            # 验证：成交量数值应该在合理范围（手）
            # 正常情况下，单日成交量应该在几千到几十万手之间
            if 1000 <= volume <= 1000000:
                print(f"  ✅ 成交量数值合理（手单位）")
            elif volume > 1000000:
                print(f"  ⚠️ 成交量数值过大 ({volume:,.0f})，可能还是股单位")
            else:
                print(f"  ⚠️ 成交量数值过小 ({volume:,.0f})，请检查")
        else:
            print("  ❌ 获取实时行情失败")

    except Exception as e:
        print(f"  ❌ Tushare 测试失败: {e}")
        logger.error(f"Tushare 测试失败: {e}", exc_info=True)


async def test_akshare_volume():
    """测试 AKShare 成交量单位"""
    print("\n" + "=" * 60)
    print("[测试 AKShare]")
    print("=" * 60)

    try:
        from tradingagents.dataflows.providers.china.akshare import AKShareProvider

        provider = AKShareProvider()
        await provider.connect()

        # 获取实时行情
        print("\n[1] 测试实时行情...")
        quote = await provider.get_stock_quotes("600391")

        if quote:
            volume = quote.get("volume", 0)
            volume_unit = quote.get("volume_unit", "unknown")
            amount = quote.get("amount", 0)

            print(f"  股票: 600391")
            print(f"  成交量: {volume:,.0f}")
            print(f"  单位: {volume_unit}")
            print(f"  成交额: {amount:,.0f} 元")

            # 验证：成交量单位应为"lots"
            if volume_unit == "lots":
                print(f"  ✅ volume_unit 标注正确: lots")
            else:
                print(f"  ❌ volume_unit 标注错误: {volume_unit} (应为 lots)")

            # 验证：成交量数值应该在合理范围（手）
            if 1000 <= volume <= 1000000:
                print(f"  ✅ 成交量数值合理（手单位）")
            elif volume > 1000000:
                print(f"  ⚠️ 成交量数值过大 ({volume:,.0f})，可能还是股单位")
            else:
                print(f"  ⚠️ 成交量数值过小 ({volume:,.0f})，请检查")
        else:
            print("  ❌ 获取实时行情失败")

    except Exception as e:
        print(f"  ❌ AKShare 测试失败: {e}")
        logger.error(f"AKShare 测试失败: {e}", exc_info=True)


async def test_baostock_volume():
    """测试 BaoStock 成交量单位"""
    print("\n" + "=" * 60)
    print("[测试 BaoStock]")
    print("=" * 60)

    try:
        from tradingagents.dataflows.providers.china.baostock import BaoStockProvider

        provider = BaoStockProvider()
        await provider.connect()

        # 获取实时行情
        print("\n[1] 测试实时行情...")
        quote = await provider.get_stock_quotes("600391")

        if quote:
            volume = quote.get("volume", 0)
            volume_unit = quote.get("volume_unit", "unknown")
            amount = quote.get("amount", 0)

            print(f"  股票: 600391")
            print(f"  成交量: {volume:,.0f}")
            print(f"  单位: {volume_unit}")
            print(f"  成交额: {amount:,.0f} 元")

            # 验证：成交量单位应为"lots"
            if volume_unit == "lots":
                print(f"  ✅ volume_unit 标注正确: lots")
            else:
                print(f"  ❌ volume_unit 标注错误: {volume_unit} (应为 lots)")

            # 验证：成交量数值应该在合理范围（手）
            if 1000 <= volume <= 1000000:
                print(f"  ✅ 成交量数值合理（手单位）")
            elif volume > 1000000:
                print(f"  ⚠️ 成交量数值过大 ({volume:,.0f})，可能还是股单位")
            else:
                print(f"  ⚠️ 成交量数值过小 ({volume:,.0f})，请检查")
        else:
            print("  ❌ 获取实时行情失败")

    except Exception as e:
        print(f"  ❌ BaoStock 测试失败: {e}")
        logger.error(f"BaoStock 测试失败: {e}", exc_info=True)


async def test_data_source_manager():
    """测试数据源管理器"""
    print("\n" + "=" * 60)
    print("[测试 DataSourceManager]")
    print("=" * 60)

    try:
        from tradingagents.dataflows.data_source_manager import get_data_source_manager

        manager = get_data_source_manager()

        print("\n[1] 测试获取股票数据...")
        result = await manager.get_stock_data("600391", "2025-01-01", "2025-01-29")

        if result:
            print(f"  ✅ 成功获取数据")
            # 解析数据中的成交量
            if isinstance(result, str):
                # 如果是字符串格式，查找成交量信息
                import re

                volume_match = re.search(r"成交量[:\s]+([\d,]+)", result)
                if volume_match:
                    volume_str = volume_match.group(1).replace(",", "")
                    volume = float(volume_str)
                    print(f"  解析到成交量: {volume:,.0f}")

                    if 1000 <= volume <= 1000000:
                        print(f"  ✅ 成交量数值合理（手单位）")
                    elif volume > 1000000:
                        print(f"  ⚠️ 成交量数值过大，可能还是股单位")
            else:
                print(f"  数据类型: {type(result)}")
        else:
            print("  ❌ 获取数据失败")

    except Exception as e:
        print(f"  ❌ DataSourceManager 测试失败: {e}")
        logger.error(f"DataSourceManager 测试失败: {e}", exc_info=True)


async def main():
    """主函数"""
    print("\n" + "🔥" * 30)
    print("成交量单位测试脚本")
    print("目标：验证成交量单位已从股转换为手")
    print("🔥" * 30)

    print("\n测试股票: 600391")
    print("预期结果:")
    print("  - volume_unit = 'lots'")
    print("  - 成交量数值 = 几千到几十万（手）")
    print("  - 成交额单位 = 元")

    # 运行所有测试
    await test_tushare_volume()
    await test_akshare_volume()
    await test_baostock_volume()
    await test_data_source_manager()

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n结果分析:")
    print("  ✅ = 测试通过，单位正确")
    print("  ⚠️ = 需要关注，可能有问题")
    print("  ❌ = 测试失败，需要修复")
    print("\n如果所有测试都显示 ✅，说明成交量单位已正确转换为手！")


if __name__ == "__main__":
    asyncio.run(main())
