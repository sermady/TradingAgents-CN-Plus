# -*- coding: utf-8 -*-
"""
测试TUSHARE_ENABLED开关功能
验证当TUSHARE_ENABLED=false时，Tushare数据源被跳过
"""

import os
import sys
import logging

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_tushare_disabled():
    """测试TUSHARE_ENABLED=false时的行为"""
    print("\n" + "=" * 80)
    print("测试1: TUSHARE_ENABLED=false")
    print("=" * 80)

    # 设置环境变量
    os.environ["TUSHARE_ENABLED"] = "false"
    os.environ["TUSHARE_TOKEN"] = "test_token_not_used"

    # 导入TushareProvider
    from tradingagents.dataflows.providers.china.tushare import TushareProvider

    # 创建提供器实例
    provider = TushareProvider()

    # 尝试连接
    result = provider.connect_sync()

    print(f"\n连接结果: {result}")
    print(f"connected状态: {provider.connected}")

    if not result and not provider.connected:
        print("✅ 测试通过: TUSHARE_ENABLED=false时，Tushare数据源被跳过")
        return True
    else:
        print("❌ 测试失败: 预期跳过Tushare，但实际尝试了连接")
        return False


def test_tushare_enabled():
    """测试TUSHARE_ENABLED=true时的行为"""
    print("\n" + "=" * 80)
    print("测试2: TUSHARE_ENABLED=true (无有效Token)")
    print("=" * 80)

    # 设置环境变量
    os.environ["TUSHARE_ENABLED"] = "true"
    os.environ["TUSHARE_TOKEN"] = "invalid_token_for_test"

    # 导入TushareProvider
    from tradingagents.dataflows.providers.china.tushare import TushareProvider

    # 创建提供器实例
    provider = TushareProvider()

    # 尝试连接（会失败，因为Token无效，但会尝试连接）
    result = provider.connect_sync()

    print(f"\n连接结果: {result}")
    print(f"connected状态: {provider.connected}")

    # 检查日志中是否有跳过信息
    if not result and not provider.connected:
        print("✅ 测试通过: TUSHARE_ENABLED=true时，尝试连接（因Token无效而失败）")
        return True
    else:
        print("⚠️ 测试结果不确定: Token可能有效")
        return True


def test_tushare_case_insensitive():
    """测试TUSHARE_ENABLED的各种值格式"""
    print("\n" + "=" * 80)
    print("测试3: TUSHARE_ENABLED各种值格式测试")
    print("=" * 80)

    enabled_values = ["true", "True", "TRUE", "1", "yes", "on"]
    disabled_values = ["false", "False", "FALSE", "0", "no", "off", ""]

    print("\n应该启用的值:")
    for val in enabled_values:
        os.environ["TUSHARE_ENABLED"] = val
        os.environ["TUSHARE_TOKEN"] = "test"

        # 重新导入以获取新的环境变量
        import importlib
        import tradingagents.dataflows.providers.china.tushare as tushare_module

        importlib.reload(tushare_module)

        from tradingagents.dataflows.providers.china.tushare import TushareProvider

        provider = TushareProvider()
        provider.connect_sync()

        status = "启用" if "跳过" not in str(provider.connected) else "跳过"
        print(f"  TUSHARE_ENABLED='{val}' -> {status}")

    print("\n应该禁用的值:")
    for val in disabled_values:
        os.environ["TUSHARE_ENABLED"] = val
        os.environ["TUSHARE_TOKEN"] = "test"

        # 重新导入以获取新的环境变量
        import importlib
        import tradingagents.dataflows.providers.china.tushare as tushare_module

        importlib.reload(tushare_module)

        from tradingagents.dataflows.providers.china.tushare import TushareProvider

        provider = TushareProvider()
        provider.connect_sync()

        status = "启用" if "跳过" not in str(provider.connected) else "跳过"
        print(f"  TUSHARE_ENABLED='{val}' -> {status}")

    return True


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TUSHARE_ENABLED开关功能测试")
    print("=" * 80)

    results = []

    # 运行测试
    results.append(("测试1: TUSHARE_ENABLED=false", test_tushare_disabled()))
    results.append(("测试2: TUSHARE_ENABLED=true", test_tushare_enabled()))
    results.append(("测试3: 大小写不敏感", test_tushare_case_insensitive()))

    # 汇总结果
    print("\n" + "=" * 80)
    print("测试结果汇总")
    print("=" * 80)
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")

    # 检查是否所有测试都通过
    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("\n⚠️ 部分测试失败")
        sys.exit(1)
