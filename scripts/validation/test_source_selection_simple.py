# -*- coding: utf-8 -*-
"""
简化版测试 - 实时行情数据源选择
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from tradingagents.dataflows.data_source_manager import DataSourceManager, ChinaDataSource


def main():
    print("=" * 60)
    print("实时行情数据源选择测试")
    print("=" * 60)

    manager = DataSourceManager()

    # 检查当前是否交易时间
    is_trading = manager._is_trading_hours()
    print(f"\n当前是否交易时间: {is_trading}")

    # 测试关键指标的数据源选择
    print("\n关键指标数据源选择:")
    print("-" * 40)

    metrics = ['current_price', 'volume', 'PE', 'MA5', 'market_cap']
    for metric in metrics:
        source = manager.get_best_source_for_metric(metric)
        print(f"{metric:15} -> {source}")

    # 验证实时行情数据源
    print("\n" + "-" * 40)
    price_source = manager.get_best_source_for_metric('current_price')
    print(f"\n验证结果:")
    print(f"  当前价格数据源: {price_source}")

    if is_trading:
        if price_source == 'akshare':
            print("  [OK] 盘中正确使用 AkShare (实时)")
        else:
            print(f"  [ERROR] 盘中应该用 AkShare, 实际: {price_source}")
    else:
        print(f"  [OK] 盘后使用 {price_source}")

    # 显示数据源实时能力
    print("\n" + "-" * 40)
    print("数据源实时能力:")
    for source in [ChinaDataSource.TUSHARE, ChinaDataSource.AKSHARE]:
        if source in manager.available_sources:
            caps = manager.is_realtime_capable(source)
            print(f"\n{source.value}:")
            print(f"  延迟: {caps['delay_seconds']}秒")
            print(f"  说明: {caps['description']}")

    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()
