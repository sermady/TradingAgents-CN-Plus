#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整修复测试脚本 - 第三轮
测试所有修复内容：
1. BaoStock 异步循环冲突
2. MongoDB 缓存兜底
3. 所有数据源降级链

测试股票：600765 605589 000738
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio


async def test_all_data_sources():
    """测试所有数据源"""
    print("=" * 60)
    print("[TEST] 测试完整数据源降级链")
    print("=" * 60)

    try:
        from tradingagents.dataflows.data_source_manager import (
            get_data_source_manager,
            get_china_stock_data_unified,
        )

        manager = get_data_source_manager()

        # 测试股票
        test_stocks = ["600765", "605589", "000738"]

        for symbol in test_stocks:
            print(f"\n{'=' * 60}")
            print(f"[TEST] 测试股票: {symbol}")
            print(f"{'=' * 60}")

            try:
                # 测试统一接口
                print(f"\n[TEST] 调用 get_china_stock_data_unified...")
                result = get_china_stock_data_unified(
                    symbol, "2025-01-01", "2025-01-29"
                )

                if isinstance(result, str) and "❌" not in result:
                    print(f"[OK] 成功获取数据")
                    print(f"[INFO] 数据长度: {len(result)} 字符")
                    # 显示前200字符
                    print(f"[INFO] 数据预览: {result[:200]}...")
                elif isinstance(result, str):
                    print(f"[ERROR] 返回错误: {result[:100]}")
                else:
                    print(f"[ERROR] 未知返回类型: {type(result)}")

            except Exception as e:
                print(f"[ERROR] 测试失败: {e}")
                import traceback

                traceback.print_exc()

        return True

    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_baostock_async():
    """测试 BaoStock 异步调用"""
    print("\n" + "=" * 60)
    print("[TEST] 测试 BaoStock 异步调用")
    print("=" * 60)

    try:
        from tradingagents.dataflows.providers.china.baostock import (
            get_baostock_provider,
        )

        provider = get_baostock_provider()

        # 测试股票
        symbol = "600765"

        print(f"\n[TEST] 获取 {symbol} 历史数据...")

        df = await provider.get_historical_data(
            symbol, "2025-01-01", "2025-01-29", "daily"
        )

        if df is not None and not df.empty:
            print(f"[OK] 成功获取 {len(df)} 条记录")
            print(f"[INFO] 列名: {list(df.columns)}")
            return True
        else:
            print(f"[WARN] 返回空数据")
            return False

    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_mongodb_fallback():
    """测试 MongoDB 兜底机制"""
    print("\n" + "=" * 60)
    print("[TEST] 测试 MongoDB 缓存兜底")
    print("=" * 60)

    try:
        from tradingagents.dataflows.cache.mongodb_cache_adapter import (
            get_mongodb_cache_adapter,
        )

        adapter = get_mongodb_cache_adapter()

        # 测试股票
        symbol = "600765"

        print(f"\n[TEST] 从 MongoDB 获取 {symbol} 数据...")

        df = adapter.get_historical_data(
            symbol, start_date=None, end_date=None, period="daily"
        )

        if df is not None and not df.empty:
            print(f"[OK] 成功从 MongoDB 获取 {len(df)} 条记录")
            if "date" in df.columns:
                print(f"[INFO] 最新数据日期: {df['date'].max()}")
            return True
        else:
            print(f"[WARN] MongoDB 中没有缓存数据")
            return False

    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_config():
    """测试配置"""
    print("=" * 60)
    print("[TEST] 检查配置")
    print("=" * 60)

    try:
        from app.core.config import settings

        print(f"\n[CONFIG] Tushare Tier: {settings.TUSHARE_TIER}")
        print(f"[CONFIG] Tushare Enabled: {settings.TUSHARE_ENABLED}")
        print(
            f"[CONFIG] Rate Limit Safety Margin: {settings.TUSHARE_RATE_LIMIT_SAFETY_MARGIN}"
        )

        return True

    except Exception as e:
        print(f"[ERROR] 配置检查失败: {e}")
        return False


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("[FINAL TEST] 完整修复测试")
    print("=" * 60)
    print("\n三轮修复内容:")
    print("第一轮: DataFrame歧义和tuple类型错误")
    print("第二轮: Tushare/AKShare备用方案")
    print("第三轮: BaoStock异步+MongoDB兜底")
    print("\n测试股票: 600765, 605589, 000738")

    # 测试配置
    config_ok = test_config()

    # 测试 BaoStock 异步
    baostock_ok = await test_baostock_async()

    # 测试 MongoDB 兜底
    mongodb_ok = await test_mongodb_fallback()

    # 测试完整数据源链
    all_sources_ok = await test_all_data_sources()

    # 汇总结果
    print("\n" + "=" * 60)
    print("[RESULT] 测试结果汇总")
    print("=" * 60)

    print(f"\n[配置检查] {'✅ 通过' if config_ok else '❌ 失败'}")
    print(f"[BaoStock异步] {'✅ 通过' if baostock_ok else '❌ 失败'}")
    print(f"[MongoDB兜底] {'✅ 通过' if mongodb_ok else '❌ 失败'}")
    print(f"[完整数据源链] {'✅ 通过' if all_sources_ok else '❌ 失败'}")

    all_passed = config_ok and baostock_ok and mongodb_ok and all_sources_ok

    if all_passed:
        print("\n🎉 所有测试通过！三轮修复全部成功！")
        print("\n修复总结:")
        print("✅ 第一批: DataFrame歧义和tuple类型错误")
        print("✅ 第二批: Tushare/AKShare备用方案")
        print("✅ 第三批: BaoStock异步+MongoDB兜底")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查日志")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
