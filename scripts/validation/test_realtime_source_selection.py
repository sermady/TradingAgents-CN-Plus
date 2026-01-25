# -*- coding: utf-8 -*-
"""
测试实时行情数据源选择逻辑

验证修正后的数据源选择是否正确:
- 盘中: AkShare (真正实时)
- 盘后: Tushare (完整数据)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from tradingagents.dataflows.data_source_manager import DataSourceManager, ChinaDataSource


def test_source_selection():
    """测试数据源选择逻辑"""

    print("=" * 60)
    print("测试实时行情数据源选择")
    print("=" * 60)

    # 初始化管理器
    manager = DataSourceManager()

    # 测试不同指标的数据源选择
    test_cases = [
        # 实时行情指标
        ('current_price', '当前价格'),
        ('open', '开盘价'),
        ('high', '最高价'),
        ('low', '最低价'),
        ('volume', '成交量'),
        ('turnover_rate', '换手率'),

        # 基本面指标
        ('PE', '市盈率'),
        ('PB', '市净率'),
        ('PS', '市销率'),
        ('ROE', '净资产收益率'),
        ('market_cap', '市值'),

        # 技术指标
        ('MA5', '5日均线'),
        ('MA20', '20日均线'),
        ('RSI', 'RSI指标'),
        ('MACD', 'MACD指标'),
    ]

    # 判断当前是否交易时间
    is_trading = manager._is_trading_hours()
    print(f"\n当前状态: {'🟢 盘中交易时间' if is_trading else '🔴 盘后/非交易时间'}")
    print(f"建议: {'应使用 AkShare 获取实时行情' if is_trading else '可使用 Tushare 获取完整数据'}")
    print()

    print("-" * 60)
    print("指标数据源选择结果:")
    print("-" * 60)

    for metric, name in test_cases:
        source = manager.get_best_source_for_metric(metric)
        print(f"✅ {name:12} ({metric:15}) → {source}")

    print("-" * 60)
    print()

    # 测试数据源实时能力
    print("-" * 60)
    print("数据源实时能力对比:")
    print("-" * 60)

    for source in ChinaDataSource:
        if source in manager.available_sources:
            caps = manager.is_realtime_capable(source)
            print(f"\n📊 {source.value}")
            print(f"   实时报价: {'✅' if caps['realtime_quote'] else '❌'}")
            print(f"   逐笔成交: {'✅' if caps['tick_data'] else '❌'}")
            print(f"   Level-2:  {'✅' if caps['level2'] else '❌'}")
            print(f"   延迟:     {caps['delay_seconds']}秒")
            print(f"   说明:     {caps['description']}")

    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)

    # 重点验证
    print("\n🎯 关键验证点:")
    realtime_source = manager.get_best_source_for_metric('current_price')
    if is_trading:
        if realtime_source == 'akshare':
            print("✅ 盘中正确选择 AkShare (真正实时)")
        else:
            print(f"❌ 错误! 盘中应选择 AkShare, 实际选择了 {realtime_source}")
    else:
        print(f"✅ 盘后选择 {realtime_source} (可以)")


def test_trading_hours_detection():
    """测试交易时间判断"""
    from datetime import datetime

    print("\n" + "=" * 60)
    print("交易时间判断测试")
    print("=" * 60)

    manager = DataSourceManager()
    now = datetime.now()

    print(f"\n当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"星期: {['周一', '周二', '周三', '周四', '周五', '周六', '周日'][now.weekday()]}")
    print(f"判断结果: {'交易中' if manager._is_trading_hours() else '非交易时间'}")

    # 交易时间说明
    print("\n📅 A股交易时间:")
    print("   上午: 09:30 - 11:30")
    print("   下午: 13:00 - 15:00")
    print("   延后: 15:00 - 15:30 (收盘后分析)")
    print("\n⏰ 当前时间判断:")

    current_time = now.hour * 100 + now.minute
    if 930 <= current_time <= 1200:
        print("   → 上午交易时段")
    elif 1300 <= current_time <= 1530:
        print("   → 下午交易时段")
    else:
        print("   → 非交易时间")

    if now.weekday() >= 5:
        print("   → 周末不交易")


if __name__ == '__main__':
    test_source_selection()
    test_trading_hours_detection()
