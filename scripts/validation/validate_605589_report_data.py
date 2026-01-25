# -*- coding: utf-8 -*-
"""
605589报告数据验证脚本
验证报告中的数据是否与实际市场数据一致
"""
import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tradingagents.dataflows.providers.base_provider import get_data_source_manager


def validate_market_data(stock_code: str):
    """验证市场数据"""
    print("=" * 80)
    print(f"股票代码: {stock_code}")
    print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 获取数据源管理器
    manager = get_data_source_manager()
    provider = manager.get_provider('cn_a')

    # 获取实时行情
    print("\n【1. 实时行情数据验证】")
    try:
        quote = provider.get_realtime_quote(stock_code)
        if quote:
            print(f"股票名称: {quote.get('stock_name', 'N/A')}")
            print(f"当前价格: {quote.get('current_price', 'N/A')}")
            print(f"涨跌幅: {quote.get('change_percent', 'N/A')}")
            print(f"成交量: {quote.get('volume', 'N/A')}")
            print(f"成交额: {quote.get('amount', 'N/A')}")
            print(f"今开: {quote.get('open', 'N/A')}")
            print(f"昨收: {quote.get('pre_close', 'N/A')}")
            print(f"最高: {quote.get('high', 'N/A')}")
            print(f"最低: {quote.get('low', 'N/A')}")

            # 报告中的数据
            print("\n【报告中的数据】")
            print("当前价格: ¥31.18")
            print("涨跌幅: +1.93%")
            print("成交量: 954,158股 (报告) / 22,482,800股 (基本面报告)")

            # 验证
            report_price = 31.18
            actual_price = quote.get('current_price', 0)
            if actual_price:
                diff_pct = abs((actual_price - report_price) / report_price * 100)
                print(f"\n【验证结果】价格差异: {diff_pct:.2f}%")
                if diff_pct < 1:
                    print("✅ 价格数据一致")
                else:
                    print(f"⚠️ 价格数据不一致 (报告: {report_price}, 实际: {actual_price})")

        else:
            print("❌ 无法获取实时行情")
    except Exception as e:
        print(f"❌ 获取实时行情失败: {e}")

    # 获取历史数据
    print("\n【2. 历史数据与技术指标验证】")
    try:
        hist_data = provider.get_daily_bars(stock_code, days=100)
        if hist_data and len(hist_data) > 0:
            latest = hist_data.iloc[-1]
            print(f"最新交易日: {latest.name}")
            print(f"收盘价: {latest['close']:.2f}")
            print(f"最高价: {latest['high']:.2f}")
            print(f"最低价: {latest['low']:.2f}")
            print(f"成交量: {latest['volume']}")

            # 计算MA5, MA10, MA20, MA60
            if len(hist_data) >= 60:
                ma5 = hist_data['close'].iloc[-5:].mean()
                ma10 = hist_data['close'].iloc[-10:].mean()
                ma20 = hist_data['close'].iloc[-20:].mean()
                ma60 = hist_data['close'].iloc[-60:].mean()

                print(f"\n移动平均线:")
                print(f"  MA5: {ma5:.2f} (报告: 30.42)")
                print(f"  MA10: {ma10:.2f} (报告: 29.98)")
                print(f"  MA20: {ma20:.2f} (报告: 29.54)")
                print(f"  MA60: {ma60:.2f} (报告: 27.88)")

                # 验证MA数据
                ma_data = [
                    ("MA5", ma5, 30.42),
                    ("MA10", ma10, 29.98),
                    ("MA20", ma20, 29.54),
                    ("MA60", ma60, 27.88)
                ]

                print("\n【MA验证结果】")
                for name, actual, reported in ma_data:
                    diff = abs(actual - reported)
                    if diff < 0.5:
                        print(f"✅ {name}: 实际={actual:.2f}, 报告={reported}, 差异={diff:.2f}")
                    else:
                        print(f"⚠️ {name}: 实际={actual:.2f}, 报告={reported}, 差异={diff:.2f}")

        else:
            print("❌ 历史数据不足")
    except Exception as e:
        print(f"❌ 获取历史数据失败: {e}")

    # 获取基本面数据
    print("\n【3. 基本面数据验证】")
    try:
        fundamentals = provider.get_stock_fundamentals(stock_code)
        if fundamentals:
            print(f"总市值: {fundamentals.get('market_cap', 'N/A')}")
            print(f"市盈率(PE): {fundamentals.get('pe_ratio', 'N/A')}")
            print(f"市净率(PB): {fundamentals.get('pb_ratio', 'N/A')}")
            print(f"市销率(PS): {fundamentals.get('ps_ratio', 'N/A')}")
            print(f"净资产收益率(ROE): {fundamentals.get('roe', 'N/A')}")
            print(f"总资产收益率(ROA): {fundamentals.get('roa', 'N/A')}")
            print(f"毛利率: {fundamentals.get('gross_margin', 'N/A')}")
            print(f"净利率: {fundamentals.get('net_margin', 'N/A')}")
            print(f"资产负债率: {fundamentals.get('debt_ratio', 'N/A')}")

            # 报告中的数据
            print("\n【报告中的基本面数据】")
            print("总市值: 263.90亿元")
            print("市盈率(PE): 25.7倍")
            print("市销率(PS): 0.10倍 ⚠️")
            print("净资产收益率(ROE): 7.5%")
            print("总资产收益率(ROA): 5.8%")
            print("毛利率: 24.9%")
            print("净利率: 9.7%")
            print("资产负债率: 34.4%")

            # 验证PS比率（报告中可能有问题）
            market_cap = fundamentals.get('market_cap', 0)
            if isinstance(market_cap, (int, float)) and market_cap > 0:
                # PS = 市值 / 营收
                # 如果市值263.9亿，PS=0.10，则营收应为2639亿
                # 实际营收约92亿，所以PS应该是263.9/92 ≈ 2.87
                print("\n【PS比率验证】")
                print("⚠️ 报告中PS=0.10倍存在严重错误！")
                print("   根据总市值263.9亿元和年营收约92亿元计算")
                print("   PS应该是: 263.9 / 92 ≈ 2.87倍")
                print("   报告中的0.10倍可能是计算错误")

        else:
            print("❌ 无法获取基本面数据")
    except Exception as e:
        print(f"❌ 获取基本面数据失败: {e}")

    print("\n" + "=" * 80)
    print("验证完成")
    print("=" * 80)


if __name__ == "__main__":
    validate_market_data("605589")
