# -*- coding: utf-8 -*-
"""
测试 Tushare 官方接口连接
验证 Token 可用性和积分状态
"""

import os
import sys
from datetime import datetime, timedelta

# 设置 UTF-8 编码
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 导入 Tushare
try:
    import tushare as ts

    TUSHARE_AVAILABLE = True
except ImportError:
    TUSHARE_AVAILABLE = False
    print("❌ Tushare 库未安装，请运行: pip install tushare")
    sys.exit(1)

# 加载 .env 文件
try:
    from dotenv import load_dotenv

    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    load_dotenv(env_path)
    print(f"✓ 已加载 .env 文件: {env_path}")
except ImportError:
    print("⚠️ python-dotenv 未安装，跳过 .env 加载")
except Exception as e:
    print(f"⚠️ 加载 .env 文件失败: {e}")


def test_tushare_connection():
    """测试 Tushare 连接"""
    print("=" * 60)
    print("Tushare 官方接口连接测试")
    print("=" * 60)

    # 从环境变量读取 Token
    token = os.getenv("TUSHARE_TOKEN", "").strip()

    if not token:
        print("\n❌ 未找到 TUSHARE_TOKEN 环境变量")
        print("   请在 .env 文件中设置 TUSHARE_TOKEN")
        return False

    print(f"\n✓ Token 已配置（长度: {len(token)} 字符）")

    # 设置 Token
    print(f"\n📡 正在连接 Tushare Pro API...")
    ts.set_token(token)
    pro = ts.pro_api()

    try:
        # 测试基础接口 - 获取股票列表（仅获取1条记录测试连接）
        print("   测试 stock_basic 接口...")
        df = pro.stock_basic(
            list_status="L", fields="ts_code,name,area,industry,list_date", limit=1
        )

        if df is not None and not df.empty:
            print(f"   ✓ 连接成功！获取到 {len(df)} 条股票数据")
            print(f"   示例: {df.iloc[0]['ts_code']} - {df.iloc[0]['name']}")
        else:
            print("   ⚠️ 接口返回空数据")
            return False

    except Exception as e:
        print(f"   ❌ 连接失败: {e}")
        return False

    return True


def test_tushare_daily_quotes():
    """测试日线行情接口"""
    print(f"\n📊 测试日线行情接口...")

    token = os.getenv("TUSHARE_TOKEN", "").strip()
    ts.set_token(token)
    pro = ts.pro_api()

    try:
        # 获取平安银行（000001.SZ）最近一周的日线数据
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

        print(f"   查询: 000001.SZ，日期范围: {start_date} - {end_date}")
        df = pro.daily(ts_code="000001.SZ", start_date=start_date, end_date=end_date)

        if df is not None and not df.empty:
            print(f"   ✓ 成功获取 {len(df)} 条日线数据")
            print(f"   最新数据日期: {df.iloc[0]['trade_date']}")
            print(f"   收盘价: {df.iloc[0]['close']}，涨跌幅: {df.iloc[0]['pct_chg']}%")
        else:
            print("   ⚠️ 接口返回空数据")

    except Exception as e:
        print(f"   ❌ 查询失败: {e}")


def test_tushare_financial_indicators():
    """测试财务指标接口（需要积分）"""
    print(f"\n💰 测试财务指标接口...")

    token = os.getenv("TUSHARE_TOKEN", "").strip()
    ts.set_token(token)
    pro = ts.pro_api()

    try:
        # 获取平安银行（000001.SZ）的财务指标
        print(f"   查询: 000001.SZ 最近一期财务指标")
        df = pro.fina_indicator(ts_code="000001.SZ", limit=1)

        if df is not None and not df.empty:
            print(f"   ✓ 成功获取财务指标")
            row = df.iloc[0]
            print(f"   报告期: {row['end_date']}")
            print(f"   ROE: {row.get('roe', 'N/A')}%")
            print(f"   净资产收益率: {row.get('roe', 'N/A')}%")
            print(f"   毛利率: {row.get('grossprofit_margin', 'N/A')}%")
            print(f"   净利率: {row.get('netprofit_margin', 'N/A')}%")
        else:
            print("   ⚠️ 接口返回空数据（可能积分不足或无权限）")

    except Exception as e:
        if "积分" in str(e) or "point" in str(e).lower():
            print(f"   ⚠️ 积分不足，无法访问财务指标接口")
        else:
            print(f"   ❌ 查询失败: {e}")


def test_tushare_realtime_quotes():
    """测试实时行情接口（需要额外付费）"""
    print(f"\n⚡ 测试实时行情接口 (rt_k)...")

    token = os.getenv("TUSHARE_TOKEN", "").strip()
    ts.set_token(token)
    pro = ts.pro_api()

    try:
        # 尝试获取实时行情（使用通配符）
        print(f"   查询: 3*.SZ（创业板前10只）...")
        df = pro.rt_k(ts_code="3*.SZ")

        if df is not None and not df.empty:
            print(f"   ✓ 成功获取 {len(df)} 只股票实时行情")
            print(
                f"   示例: {df.iloc[0]['ts_code']} - {df.iloc[0]['name']} - 价格: {df.iloc[0]['close']}"
            )
        else:
            print("   ⚠️ 接口返回空数据")

    except Exception as e:
        error_msg = str(e)
        if "积分" in error_msg or "point" in error_msg.lower() or "权限" in error_msg:
            print(f"   ⚠️ 实时行情接口需要额外付费权限")
        elif "每分钟最多" in error_msg or "访问频率" in error_msg:
            print(f"   ⚠️ 已达到频率限制（免费用户每小时2次）")
        else:
            print(f"   ❌ 查询失败: {e}")


def get_tushare_tier_info():
    """根据 Token 估算积分等级"""
    print(f"\n📋 Tushare 积分等级说明:")
    print("-" * 60)
    print("积分等级        每分钟调用次数   主要权限")
    print("-" * 60)
    print("免费 (0-1999)      120次/分钟      基础行情、财务数据")
    print("标准 (2000+)        400次/分钟      增值数据、财务指标")
    print("高级 (12000+)        600次/分钟      行情快照、更多指标")
    print("VIP (20000+)         800次/分钟      全部接口、最高权限")
    print("-" * 60)

    token = os.getenv("TUSHARE_TOKEN", "").strip()
    print(f"\n您的 Token: {token[:10]}...{token[-4:]}")
    print(f"提示: 5120 积分属于「标准等级」，享有 400次/分钟 的调用限制")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print(" TradingAgents-CN - Tushare 接口测试")
    print(f" 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 测试连接
    if not test_tushare_connection():
        print("\n❌ Tushare 连接测试失败，请检查 Token 配置")
        sys.exit(1)

    # 测试各项接口
    test_tushare_daily_quotes()
    test_tushare_financial_indicators()
    test_tushare_realtime_quotes()

    # 显示积分等级信息
    get_tushare_tier_info()

    print("\n" + "=" * 60)
    print("✓ Tushare 接口测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
