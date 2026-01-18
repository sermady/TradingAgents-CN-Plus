# -*- coding: utf-8 -*-
"""
测试 Tushare Token 连接修复
根据 tushareReadme.txt 的要求测试连接
"""

import os
import sys
import io

# Windows 控制台编码设置
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_tushare_connection():
    """测试 Tushare 连接"""

    print("=" * 80)
    print("测试 Tushare Token 连接修复")
    print("=" * 80)

    # 1. 读取环境变量（尝试从 .env 文件加载）
    from dotenv import load_dotenv

    # 尝试加载 .env 文件
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        ".env",
    )
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        print(f"✅ 已加载 .env 文件: {env_path}")

    token = os.getenv("TUSHARE_TOKEN")
    if not token:
        print("❌ 错误：未找到 TUSHARE_TOKEN 环境变量")
        return False

    print(f"✅ 找到 TUSHARE_TOKEN (长度: {len(token)})")

    # 2. 导入 tushare 库
    try:
        import tushare as ts

        print("✅ tushare 库导入成功")
    except ImportError:
        print("❌ 错误：未安装 tushare 库，请运行: pip install tushare")
        return False

    # 3. 设置 token 和 API
    try:
        ts.set_token(token)
        pro = ts.pro_api()
        print("✅ 创建 pro_api 对象成功")

        # 4. 🔥 根据 tushareReadme.txt 要求，设置必要的属性
        pro._DataApi__token = token
        pro._DataApi__http_url = "https://jiaoch.site"
        print("✅ 已设置 _DataApi__token 和 _DataApi__http_url 属性")

    except Exception as e:
        print(f"❌ 设置 API 失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    # 5. 测试连接 - 调用 stock_basic API
    try:
        print("\n🔄 测试调用 stock_basic API...")
        df = pro.stock_basic(list_status="L", limit=5)

        if df is not None and not df.empty:
            print(f"✅ API 调用成功！返回 {len(df)} 条股票数据")
            print("\n数据示例:")
            print(df.head())
            return True
        else:
            print("❌ API 返回空数据")
            return False

    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_provider_class():
    """测试 TushareProvider 类"""
    print("\n" + "=" * 80)
    print("测试 TushareProvider 类")
    print("=" * 80)

    try:
        from tradingagents.dataflows.providers.china.tushare import TushareProvider

        provider = TushareProvider()
        print("✅ TushareProvider 实例化成功")

        # 测试同步连接
        print("\n🔄 测试 connect_sync()...")
        success = provider.connect_sync()

        if success:
            print("✅ connect_sync() 连接成功")
            print(f"✅ Token 来源: {provider.token_source}")
            return True
        else:
            print("❌ connect_sync() 连接失败")
            return False

    except Exception as e:
        print(f"❌ TushareProvider 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 测试 1: 直接使用 tushare 库
    result1 = test_tushare_connection()

    # 测试 2: 使用 TushareProvider 类
    result2 = test_provider_class()

    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"直接测试 tushare 库: {'✅ 通过' if result1 else '❌ 失败'}")
    print(f"测试 TushareProvider 类: {'✅ 通过' if result2 else '❌ 失败'}")
    print("=" * 80)

    if result1 and result2:
        print("\n🎉 所有测试通过！Tushare Token 连接修复成功！")
        sys.exit(0)
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息")
        sys.exit(1)
