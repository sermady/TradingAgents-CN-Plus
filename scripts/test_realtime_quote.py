#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
测试脚本：验证实时行情功能
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradingagents.utils.logging_init import get_logger

logger = get_logger("test")


def test_market_time_detection():
    """测试交易时间判断"""
    print("\n" + "=" * 80)
    print("🕐 测试交易时间判断")
    print("=" * 80)

    try:
        from tradingagents.utils.market_time import MarketTimeUtils

        test_symbols = [
            ("600765", "中航重机-A股"),
            ("00700.HK", "腾讯控股-港股"),
            ("AAPL", "苹果-美股"),
        ]

        for symbol, name in test_symbols:
            print(f"\n📊 {name} ({symbol})")
            status = MarketTimeUtils.get_market_status(symbol)
            print(f"   市场: {status['market']}")
            print(f"   当前时间: {status['current_time']}")
            print(f"   市场状态: {status['status']}")
            print(f"   是否交易中: {'✅ 是' if status['is_trading'] else '❌ 否'}")
            print(
                f"   是否使用实时行情: {'✅ 是' if status['should_use_realtime'] else '❌ 否'}"
            )
            print(f"   原因: {status['reason']}")

        return True

    except Exception as e:
        import traceback

        print(f"❌ 测试失败: {e}")
        print(traceback.format_exc())
        return False


def test_realtime_quote_fetch():
    """测试实时行情获取"""
    print("\n" + "=" * 80)
    print("💰 测试实时行情获取")
    print("=" * 80)

    try:
        from tradingagents.dataflows.data_source_manager import get_data_source_manager
        from tradingagents.utils.market_time import is_trading_time

        manager = get_data_source_manager()

        test_symbols = ["600765", "000001", "600036"]

        for symbol in test_symbols:
            print(f"\n📊 测试股票: {symbol}")

            # 检查是否是交易时间
            is_trading = is_trading_time(symbol)
            print(f"   是否交易时间: {'✅ 是' if is_trading else '❌ 否'}")

            # 尝试获取实时行情
            quote = manager.get_realtime_quote(symbol)

            if quote:
                print(f"   ✅ 实时行情获取成功")
                print(f"   💰 价格: ¥{quote['price']:.2f}")
                print(
                    f"   📈 涨跌: {quote['change']:+.2f} ({quote['change_pct']:+.2f}%)"
                )
                print(f"   📊 今开: ¥{quote['open']:.2f}")
                print(f"   📊 最高: ¥{quote['high']:.2f}")
                print(f"   📊 最低: ¥{quote['low']:.2f}")
                print(f"   📊 成交量: {quote['volume']:,.0f}")
                print(f"   🕐 时间: {quote.get('date', 'N/A')} {quote.get('time', '')}")
                print(f"   📡 来源: {quote['source']}")
            else:
                print(f"   ⚠️ 实时行情未获取到（可能不是交易时间或数据源不支持）")

        return True

    except Exception as e:
        import traceback

        print(f"❌ 测试失败: {e}")
        print(traceback.format_exc())
        return False


def test_integrated_data_with_realtime():
    """测试集成实时行情的完整数据获取"""
    print("\n" + "=" * 80)
    print("🔄 测试集成实时行情的完整数据流程")
    print("=" * 80)

    try:
        from datetime import datetime, timedelta

        from tradingagents.dataflows.data_source_manager import get_data_source_manager

        manager = get_data_source_manager()

        test_symbol = "600765"
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

        print(f"\n📊 测试股票: {test_symbol}")
        print(f"📅 日期范围: {start_date} 至 {end_date}")
        print(f"⏳ 正在获取数据...\n")

        # 调用统一接口（会自动判断是否使用实时行情）
        result = manager.get_stock_data(test_symbol, start_date, end_date)

        if result and "❌" not in result:
            print("✅ 数据获取成功！")
            print("\n" + "-" * 80)
            print("📋 数据内容预览（前1500字符）:")
            print("-" * 80)
            print(result[:1500])
            print("-" * 80)

            # 检查是否包含实时行情标识
            has_realtime = "⚡ 实时行情（盘中）" in result
            print(
                f"\n{'✅' if has_realtime else '❌'} 包含实时行情标识: {has_realtime}"
            )

            if has_realtime:
                print("🎉 实时行情功能正常工作！")
            else:
                print("ℹ️ 当前非交易时间或实时行情未获取到，使用历史数据")

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


def test_cache_timeout_strategy():
    """测试缓存超时策略"""
    print("\n" + "=" * 80)
    print("⏱️ 测试缓存超时策略")
    print("=" * 80)

    try:
        from tradingagents.utils.market_time import get_realtime_cache_timeout

        test_symbols = [
            ("600765", "A股"),
            ("00700.HK", "港股"),
            ("AAPL", "美股"),
        ]

        for symbol, market_name in test_symbols:
            timeout = get_realtime_cache_timeout(symbol)
            print(f"\n📊 {market_name} ({symbol})")
            print(f"   缓存超时: {timeout}秒")
            if timeout <= 60:
                print(f"   状态: 盘中短缓存（{timeout}秒）")
            else:
                print(f"   状态: 盘后长缓存（{timeout / 3600:.1f}小时）")

        return True

    except Exception as e:
        import traceback

        print(f"❌ 测试失败: {e}")
        print(traceback.format_exc())
        return False


def test_realtime_vs_historical():
    """对比实时行情和历史数据"""
    print("\n" + "=" * 80)
    print("🔍 对比实时行情和历史数据")
    print("=" * 80)

    try:
        from datetime import datetime, timedelta

        from tradingagents.dataflows.data_source_manager import get_data_source_manager

        manager = get_data_source_manager()
        test_symbol = "600765"

        # 1. 获取实时行情
        print(f"\n1️⃣ 获取实时行情...")
        realtime_quote = manager.get_realtime_quote(test_symbol)

        if realtime_quote:
            print(f"   ✅ 实时价格: ¥{realtime_quote['price']:.2f}")
            print(f"   📊 涨跌幅: {realtime_quote['change_pct']:+.2f}%")
            print(
                f"   🕐 时间: {realtime_quote.get('date', 'N/A')} {realtime_quote.get('time', '')}"
            )
        else:
            print(f"   ⚠️ 实时行情未获取到")

        # 2. 获取历史数据（最后一天）
        print(f"\n2️⃣ 获取历史数据...")
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

        result = manager.get_stock_data(test_symbol, start_date, end_date)

        if result:
            # 提取历史数据中的最新价格
            for line in result.split("\n"):
                if "💰 最新价格:" in line or "实时价格:" in line:
                    print(f"   历史数据: {line.strip()}")
                    break

        # 3. 对比
        print(f"\n3️⃣ 数据对比:")
        if realtime_quote:
            print(f"   实时行情来源: {realtime_quote['source']}")
            print(f"   实时行情标识: {realtime_quote.get('is_realtime', False)}")

        print(f"   说明: 盘中时应优先使用实时行情，盘后使用历史数据")

        return True

    except Exception as e:
        import traceback

        print(f"❌ 测试失败: {e}")
        print(traceback.format_exc())
        return False


def main():
    """主函数"""
    print("\n" + "🚀" * 40)
    print("实时行情功能测试套件")
    print("🚀" * 40)

    results = {}

    # 测试1：交易时间判断
    results["test1"] = test_market_time_detection()

    # 测试2：实时行情获取
    results["test2"] = test_realtime_quote_fetch()

    # 测试3：集成实时行情的完整数据流程
    results["test3"] = test_integrated_data_with_realtime()

    # 测试4：缓存超时策略
    results["test4"] = test_cache_timeout_strategy()

    # 测试5：对比实时行情和历史数据
    results["test5"] = test_realtime_vs_historical()

    # 总结
    print("\n" + "=" * 80)
    print("📋 测试结果汇总")
    print("=" * 80)

    test_names = {
        "test1": "交易时间判断",
        "test2": "实时行情获取",
        "test3": "集成实时行情的完整数据流程",
        "test4": "缓存超时策略",
        "test5": "对比实时行情和历史数据",
    }

    success_count = 0
    for test_id, test_name in test_names.items():
        status = "✅ 通过" if results.get(test_id, False) else "❌ 失败"
        print(f"{test_name}: {status}")
        if results.get(test_id, False):
            success_count += 1

    print(f"\n总计: {success_count}/{len(results)} 测试通过")

    if success_count == len(results):
        print("\n🎉 所有测试通过！实时行情功能正常！")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查问题。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
