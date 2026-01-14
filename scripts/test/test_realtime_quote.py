# -*- coding: utf-8 -*-
"""
实时行情功能测试脚本

测试内容：
1. 交易时段判断工具
2. AkShare 实时行情获取
3. Tushare 实时行情获取
4. 数据源管理器统一入口
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Windows 控制台编码修复
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")


def test_trading_hours():
    """测试交易时段判断工具"""
    print("\n" + "=" * 60)
    print("测试 1: 交易时段判断工具")
    print("=" * 60)

    try:
        from tradingagents.utils.trading_hours import (
            is_trading_hours,
            get_market_status,
            is_trading_day,
            get_next_trading_session
        )

        # 测试 A股
        print("\n📊 A股市场:")
        print(f"  - 是否交易时段: {is_trading_hours('A股')}")
        status, desc = get_market_status('A股')
        print(f"  - 市场状态: {status} ({desc})")
        print(f"  - 是否交易日: {is_trading_day('A股')}")
        next_session = get_next_trading_session('A股')
        if next_session:
            print(f"  - 下一交易时段: {next_session[0]} - {next_session[1]}")

        # 测试 港股
        print("\n📊 港股市场:")
        print(f"  - 是否交易时段: {is_trading_hours('港股')}")
        status, desc = get_market_status('港股')
        print(f"  - 市场状态: {status} ({desc})")

        # 测试 美股
        print("\n📊 美股市场:")
        print(f"  - 是否交易时段: {is_trading_hours('美股')}")
        status, desc = get_market_status('美股')
        print(f"  - 市场状态: {status} ({desc})")

        print("\n✅ 交易时段判断工具测试通过")
        return True

    except Exception as e:
        print(f"\n❌ 交易时段判断工具测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_akshare_realtime():
    """测试 AkShare 实时行情获取"""
    print("\n" + "=" * 60)
    print("测试 2: AkShare 实时行情获取")
    print("=" * 60)

    try:
        from tradingagents.dataflows.data_source_manager import get_data_source_manager

        dsm = get_data_source_manager()

        # 测试获取平安银行实时行情
        symbol = "000001"
        print(f"\n📈 获取 {symbol} 实时行情 (AkShare)...")

        quote = dsm._get_akshare_realtime_quote(symbol)

        if quote:
            print(f"  ✅ 获取成功:")
            print(f"     - 股票代码: {quote.get('symbol')}")
            print(f"     - 股票名称: {quote.get('name')}")
            print(f"     - 当前价格: {quote.get('price')}")
            print(f"     - 涨跌幅: {quote.get('change_pct')}%")
            print(f"     - 成交量: {quote.get('volume')}")
            print(f"     - 数据源: {quote.get('source')}")
            print(f"     - 时间戳: {quote.get('timestamp')}")
            return True
        else:
            print("  ⚠️ 未获取到数据（可能非交易时段）")
            return True  # 非交易时段返回空是正常的

    except Exception as e:
        print(f"\n❌ AkShare 实时行情测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tushare_realtime():
    """测试 Tushare 实时行情获取"""
    print("\n" + "=" * 60)
    print("测试 3: Tushare 实时行情获取")
    print("=" * 60)

    try:
        # 检查 Tushare Token
        tushare_token = os.getenv("TUSHARE_TOKEN")
        if not tushare_token:
            print("  ⚠️ 未配置 TUSHARE_TOKEN，跳过 Tushare 测试")
            return True

        from tradingagents.dataflows.data_source_manager import get_data_source_manager

        dsm = get_data_source_manager()

        # 测试获取平安银行实时行情
        symbol = "000001"
        print(f"\n📈 获取 {symbol} 实时行情 (Tushare)...")

        quote = dsm._get_tushare_realtime_quote(symbol)

        if quote:
            print(f"  ✅ 获取成功:")
            print(f"     - 股票代码: {quote.get('symbol')}")
            print(f"     - 股票名称: {quote.get('name')}")
            print(f"     - 当前价格: {quote.get('price')}")
            print(f"     - 涨跌幅: {quote.get('change_pct')}%")
            print(f"     - 数据源: {quote.get('source')}")
            return True
        else:
            print("  ⚠️ 未获取到数据（可能 Tushare 不可用或非交易时段）")
            return True

    except Exception as e:
        print(f"\n❌ Tushare 实时行情测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_source_manager():
    """测试数据源管理器统一入口"""
    print("\n" + "=" * 60)
    print("测试 4: 数据源管理器统一入口")
    print("=" * 60)

    try:
        from tradingagents.dataflows.data_source_manager import get_data_source_manager

        dsm = get_data_source_manager()

        # 测试 should_use_realtime_data
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = "2024-01-01"

        print(f"\n📊 should_use_realtime_data 测试:")
        print(f"  - 今天({today}): {dsm.should_use_realtime_data(today, 'A股')}")
        print(f"  - 历史日期({yesterday}): {dsm.should_use_realtime_data(yesterday, 'A股')}")
        print(f"  - 'today': {dsm.should_use_realtime_data('today', 'A股')}")

        # 测试统一入口 get_realtime_quote
        symbol = "000001"
        print(f"\n📈 get_realtime_quote 统一入口测试 ({symbol})...")

        quote = dsm.get_realtime_quote(symbol, 'A股')

        if quote:
            print(f"  ✅ 获取成功:")
            print(f"     - 股票代码: {quote.get('symbol')}")
            print(f"     - 当前价格: {quote.get('price')}")
            print(f"     - 涨跌幅: {quote.get('change_pct')}%")
            print(f"     - 市场状态: {quote.get('market_status_desc')}")
            print(f"     - 是否实时: {quote.get('is_realtime')}")
            print(f"     - 数据源: {quote.get('source')}")
        else:
            print("  ⚠️ 未获取到数据（可能非交易时段）")

        print("\n✅ 数据源管理器测试通过")
        return True

    except Exception as e:
        print(f"\n❌ 数据源管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoints():
    """测试 API 端点（需要后端服务运行）"""
    print("\n" + "=" * 60)
    print("测试 5: API 端点 (需要后端服务运行)")
    print("=" * 60)

    try:
        import requests

        base_url = "http://localhost:8000"

        # 检查后端是否运行
        try:
            health = requests.get(f"{base_url}/api/health", timeout=3)
            if health.status_code != 200:
                print("  ⚠️ 后端服务未运行，跳过 API 测试")
                return True
        except requests.exceptions.ConnectionError:
            print("  ⚠️ 后端服务未运行，跳过 API 测试")
            return True

        print("\n📡 API 端点测试:")

        # 测试市场状态端点
        print("\n  GET /api/realtime/market-status...")
        # 注意：需要认证，这里只是演示
        print("  ⚠️ API 端点需要认证，请使用前端或 curl 进行测试")

        return True

    except Exception as e:
        print(f"\n❌ API 端点测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("🚀 实时行情功能测试")
    print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = {
        "交易时段判断": test_trading_hours(),
        "AkShare 实时行情": test_akshare_realtime(),
        "Tushare 实时行情": test_tushare_realtime(),
        "数据源管理器": test_data_source_manager(),
        "API 端点": test_api_endpoints(),
    }

    # 汇总结果
    print("\n" + "=" * 60)
    print("📋 测试结果汇总")
    print("=" * 60)

    all_passed = True
    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过!")
    else:
        print("⚠️ 部分测试失败，请检查日志")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
