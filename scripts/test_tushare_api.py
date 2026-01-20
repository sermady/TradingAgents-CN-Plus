#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
Tushare API 验证测试脚本
用于检查 Tushare API 是否正常工作
"""

import os
import sys
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradingagents.utils.logging_init import get_logger

logger = get_logger("test")


def test_tushare_import():
    """测试 Tushare 库是否已安装"""
    print("\n" + "=" * 80)
    print("1️⃣ 测试 Tushare 库导入")
    print("=" * 80)

    try:
        import tushare as ts

        print(f"✅ Tushare 已安装")
        print(f"   版本: {ts.__version__ if hasattr(ts, '__version__') else '未知'}")
        return True
    except ImportError as e:
        print(f"❌ Tushare 未安装: {e}")
        print("   请运行: pip install tushare")
        return False


def test_tushare_token_config():
    """测试 Tushare Token 配置"""
    print("\n" + "=" * 80)
    print("2️⃣ 测试 Tushare Token 配置")
    print("=" * 80)

    # 检查环境变量
    env_token = os.getenv("TUSHARE_TOKEN")
    print(f"\n📍 环境变量 (TUSHARE_TOKEN):")
    if env_token:
        print(f"   ✅ 已配置 (长度: {len(env_token)})")
        print(f"   前10字符: {env_token[:10]}...")
    else:
        print(f"   ❌ 未配置")

    # 检查数据库配置
    print(f"\n📍 数据库配置:")
    try:
        from tradingagents.dataflows.providers.china.tushare import TushareProvider

        provider = TushareProvider()
        db_token = provider._get_token_from_database()

        if db_token:
            print(f"   ✅ 已配置 (长度: {len(db_token)})")
            print(f"   前10字符: {db_token[:10]}...")
        else:
            print(f"   ❌ 未配置或无效")
    except Exception as e:
        print(f"   ⚠️ 无法读取: {e}")

    return bool(env_token or db_token)


def test_tushare_provider_init():
    """测试 TushareProvider 初始化"""
    print("\n" + "=" * 80)
    print("3️⃣ 测试 TushareProvider 初始化")
    print("=" * 80)

    try:
        from tradingagents.dataflows.providers.china.tushare import (
            get_tushare_provider,
        )

        print("\n🔄 正在初始化 TushareProvider...")
        provider = get_tushare_provider()

        if provider:
            print(f"✅ TushareProvider 初始化成功")
            print(f"   连接状态: {provider.connected}")
            print(f"   Token来源: {provider.token_source or '未知'}")
            print(f"   API对象: {provider.api is not None}")
            return True
        else:
            print(f"❌ TushareProvider 初始化失败")
            return False

    except Exception as e:
        import traceback

        print(f"❌ 初始化异常: {e}")
        print(traceback.format_exc())
        return False


def test_tushare_connection():
    """测试 Tushare API 连接"""
    print("\n" + "=" * 80)
    print("4️⃣ 测试 Tushare API 连接")
    print("=" * 80)

    try:
        from tradingagents.dataflows.providers.china.tushare import (
            get_tushare_provider,
        )

        provider = get_tushare_provider()

        if not provider or not provider.connected:
            print("❌ Provider 未连接，跳过测试")
            return False

        print("\n🔄 测试 API 连接...")

        # 测试1: 获取股票列表（同步方法）
        print("\n📋 测试1: 获取股票列表 (同步)")
        try:
            df = provider.get_stock_list_sync(limit=5)
            if df is not None and not df.empty:
                print(f"   ✅ 成功获取 {len(df)} 条股票数据")
                print(f"   数据预览:")
                for _, row in df.iterrows():
                    print(
                        f"      {row.get('ts_code', 'N/A')} - {row.get('name', 'N/A')}"
                    )
            else:
                print(f"   ❌ 未获取到数据")
                return False
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            return False

        # 测试2: 获取股票基本信息（异步方法）
        print("\n📋 测试2: 获取股票基本信息 (异步)")
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            stock_info = loop.run_until_complete(
                provider.get_stock_basic_info("000001")
            )

            if stock_info:
                print(f"   ✅ 成功获取股票信息")
                print(f"   股票代码: {stock_info.get('ts_code', 'N/A')}")
                print(f"   股票名称: {stock_info.get('name', 'N/A')}")
                print(f"   所属行业: {stock_info.get('industry', 'N/A')}")
            else:
                print(f"   ❌ 未获取到数据")
                return False
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            return False

        # 测试3: 获取历史数据
        print("\n📋 测试3: 获取历史数据 (异步)")
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=10)

            hist_data = loop.run_until_complete(
                provider.get_historical_data(
                    "000001",
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d"),
                )
            )

            if hist_data is not None and not hist_data.empty:
                print(f"   ✅ 成功获取 {len(hist_data)} 条历史数据")
                print(
                    f"   日期范围: {hist_data['date'].min()} 至 {hist_data['date'].max()}"
                )
                print(f"   最新价格: ¥{hist_data['close'].iloc[-1]:.2f}")
            else:
                print(f"   ❌ 未获取到数据")
                return False
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            return False

        print("\n✅ 所有 API 测试通过")
        return True

    except Exception as e:
        import traceback

        print(f"❌ 测试异常: {e}")
        print(traceback.format_exc())
        return False


def test_tushare_in_data_source_manager():
    """测试 Tushare 在 DataSourceManager 中的使用"""
    print("\n" + "=" * 80)
    print("5️⃣ 测试 Tushare 在 DataSourceManager 中的使用")
    print("=" * 80)

    try:
        from tradingagents.dataflows.data_source_manager import (
            get_data_source_manager,
        )

        manager = get_data_source_manager()

        print(f"\n📊 当前数据源: {manager.current_source.value}")
        print(f"📊 可用数据源: {[s.value for s in manager.available_sources]}")

        # 检查 Tushare 是否在可用数据源中
        from tradingagents.dataflows.data_source_manager import ChinaDataSource

        if ChinaDataSource.TUSHARE in manager.available_sources:
            print(f"✅ Tushare 在可用数据源列表中")
        else:
            print(f"❌ Tushare 不在可用数据源列表中")
            return False

        # 测试获取数据
        print(f"\n🔄 测试获取股票数据...")
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

        result = manager.get_stock_data("000001", start_date, end_date)

        if result and "❌" not in result:
            print(f"✅ 成功获取数据")
            print(f"\n数据预览（前300字符）:")
            print("-" * 80)
            print(result[:300])
            print("-" * 80)
            return True
        else:
            print(f"❌ 获取数据失败")
            print(result[:200] if result else "无返回数据")
            return False

    except Exception as e:
        import traceback

        print(f"❌ 测试异常: {e}")
        print(traceback.format_exc())
        return False


def test_tushare_rate_limit():
    """测试 Tushare API 频率限制处理"""
    print("\n" + "=" * 80)
    print("6️⃣ 测试 Tushare API 频率限制处理")
    print("=" * 80)

    try:
        from tradingagents.dataflows.providers.china.tushare import (
            get_tushare_provider,
        )

        provider = get_tushare_provider()

        if not provider or not provider.connected:
            print("❌ Provider 未连接，跳过测试")
            return False

        print("\n🔄 快速连续调用 API（测试频率限制处理）...")

        import asyncio

        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        success_count = 0
        fail_count = 0

        for i in range(5):
            try:
                print(f"\n   调用 {i + 1}/5...")
                stock_info = loop.run_until_complete(
                    provider.get_stock_basic_info(f"00000{i + 1}")
                )
                if stock_info:
                    success_count += 1
                    print(f"   ✅ 成功")
                else:
                    fail_count += 1
                    print(f"   ⚠️ 无数据")
            except Exception as e:
                fail_count += 1
                print(f"   ❌ 失败: {e}")

        print(f"\n📊 结果统计:")
        print(f"   成功: {success_count}/5")
        print(f"   失败: {fail_count}/5")

        if success_count >= 3:
            print(f"✅ 频率限制处理正常（允许部分失败）")
            return True
        else:
            print(f"⚠️ 成功率较低，可能存在问题")
            return False

    except Exception as e:
        import traceback

        print(f"❌ 测试异常: {e}")
        print(traceback.format_exc())
        return False


def main():
    """主测试函数"""
    print("\n" + "🚀" * 40)
    print("Tushare API 验证测试套件")
    print("🚀" * 40)

    results = {}

    # 测试1: 库导入
    results["test1"] = test_tushare_import()
    if not results["test1"]:
        print("\n❌ Tushare 库未安装，无法继续测试")
        return 1

    # 测试2: Token 配置
    results["test2"] = test_tushare_token_config()
    if not results["test2"]:
        print("\n⚠️ Tushare Token 未配置，部分测试可能失败")

    # 测试3: Provider 初始化
    results["test3"] = test_tushare_provider_init()

    # 测试4: API 连接
    results["test4"] = test_tushare_connection()

    # 测试5: DataSourceManager 集成
    results["test5"] = test_tushare_in_data_source_manager()

    # 测试6: 频率限制处理
    results["test6"] = test_tushare_rate_limit()

    # 总结
    print("\n" + "=" * 80)
    print("📋 测试结果汇总")
    print("=" * 80)

    test_names = {
        "test1": "Tushare 库导入",
        "test2": "Token 配置检查",
        "test3": "TushareProvider 初始化",
        "test4": "API 连接测试",
        "test5": "DataSourceManager 集成",
        "test6": "频率限制处理",
    }

    success_count = 0
    for test_id, test_name in test_names.items():
        status = "✅ 通过" if results.get(test_id, False) else "❌ 失败"
        print(f"{test_name}: {status}")
        if results.get(test_id, False):
            success_count += 1

    print(f"\n总计: {success_count}/{len(results)} 测试通过")

    # 诊断建议
    if success_count < len(results):
        print("\n" + "=" * 80)
        print("🔧 诊断建议")
        print("=" * 80)

        if not results.get("test1", False):
            print("\n❌ Tushare 库未安装")
            print("   解决方案: pip install tushare")

        if not results.get("test2", False):
            print("\n❌ Tushare Token 未配置")
            print("   解决方案:")
            print("   1. 在 Web 后台配置 Tushare Token")
            print("   2. 或在 .env 文件中添加: TUSHARE_TOKEN=your_token_here")
            print("   3. Token 获取: https://tushare.pro/register")

        if not results.get("test3", False):
            print("\n❌ TushareProvider 初始化失败")
            print("   可能原因:")
            print("   1. Token 无效或过期")
            print("   2. 数据库连接问题")
            print("   3. 配置格式错误")

        if not results.get("test4", False):
            print("\n❌ API 连接失败")
            print("   可能原因:")
            print("   1. Token 无效")
            print("   2. 网络连接问题")
            print("   3. Tushare 服务异常")
            print("   4. 积分不足（需要检查权限）")

        if not results.get("test5", False):
            print("\n❌ DataSourceManager 集成问题")
            print("   可能原因:")
            print("   1. Tushare 未在可用数据源列表中")
            print("   2. 数据源配置错误")
            print("   3. Provider 连接失败")

        if not results.get("test6", False):
            print("\n⚠️ 频率限制处理异常")
            print("   可能原因:")
            print("   1. API 调用频率过高")
            print("   2. 积分不足")
            print("   3. 账户权限问题")

    if success_count == len(results):
        print("\n🎉 所有测试通过！Tushare API 工作正常！")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请根据诊断建议进行修复。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
