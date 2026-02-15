# -*- coding: utf-8 -*-
"""
测试stock_normalizer统一功能

验证normalize_stock_info和normalize_stock_code函数的正确性
"""

# 添加项目根目录到Python路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.worker.utils import normalize_stock_info, normalize_stock_code


def test_normalize_stock_code():
    """测试股票代码标准化"""
    print("\n=== 测试 normalize_stock_code ===\n")

    # 港股代码（5位格式，去掉前导零后补齐）
    hk_code_1 = normalize_stock_code(" 00700  ", market_type="hk")
    print(f"港股代码 ' 00700  ' → '{hk_code_1}'")
    # 注意：原始实现返回"00700"（5位，保留格式）
    assert hk_code_1 == "00700", f"Expected '00700', got '{hk_code_1}'"

    hk_code_2 = normalize_stock_code("9988", market_type="hk")
    print(f"港股代码 '9988' → '{hk_code_2}'")
    # 9988已经是4位，补齐到5位
    assert hk_code_2 == "09988", f"Expected '09988', got '{hk_code_2}'"

    # 美股代码（大写）
    us_code_1 = normalize_stock_code("aapl", market_type="us")
    print(f"美股代码 'aapl' → '{us_code_1}'")
    assert us_code_1 == "AAPL", f"Expected 'AAPL', got '{us_code_1}'"

    us_code_2 = normalize_stock_code("  TSLA  ", market_type="us")
    print(f"美股代码 '  TSLA  ' → '{us_code_2}'")
    assert us_code_2 == "TSLA", f"Expected 'TSLA', got '{us_code_2}'"

    print("\n✅ 股票代码标准化测试通过！\n")


def test_normalize_stock_info():
    """测试股票信息标准化"""
    print("\n=== 测试 normalize_stock_info ===\n")

    # 测试港股信息
    hk_info = {
        "name": "腾讯控股",
        "industry": "科技",
        "market_cap": 3000000000000,
    }

    normalized_hk = normalize_stock_info(hk_info, market_type="hk")
    print(f"港股信息标准化:")
    print(f"  货币: {normalized_hk['currency']}")
    print(f"  交易所: {normalized_hk['exchange']}")
    print(f"  市场: {normalized_hk['market']}")
    print(f"  地区: {normalized_hk['area']}")
    print(f"  行业: {normalized_hk.get('industry', 'N/A')}")

    assert normalized_hk['currency'] == 'HKD', "港股货币应该是HKD"
    assert normalized_hk['exchange'] == 'HKEX', "港股交易所应该是HKEX"
    assert normalized_hk['market'] == '香港交易所', "港股市场应该是香港交易所"
    assert normalized_hk['area'] == '香港', "港股地区应该是香港"
    assert normalized_hk.get('industry') == '科技', "行业应该被保留"

    # 测试美股信息
    us_info = {
        "name": "Apple Inc.",
        "industry": "Technology",
        "market_cap": 2500000000000,
    }

    normalized_us = normalize_stock_info(us_info, market_type="us")
    print(f"\n美股信息标准化:")
    print(f"  货币: {normalized_us['currency']}")
    print(f"  交易所: {normalized_us['exchange']}")
    print(f"  市场: {normalized_us['market']}")
    print(f"  地区: {normalized_us['area']}")
    print(f"  行业: {normalized_us.get('industry', 'N/A')}")

    assert normalized_us['currency'] == 'USD', "美股货币应该是USD"
    assert normalized_us['exchange'] == 'NASDAQ', "美股交易所应该是NASDAQ"
    assert normalized_us['market'] == '美国市场', "美股市场应该是美国市场"
    assert normalized_us['area'] == '美国', "美股地区应该是美国"
    assert normalized_us.get('industry') == 'Technology', "行业应该被保留"

    # 测试字段覆盖
    custom_info = {
        "name": "测试公司",
        "currency": "CNY",  # 自定义货币应该被保留
        "exchange": "CUSTOM",  # 自定义交易所应该被保留
        "pe": 15.5,
        "pb": 2.3,
        "description": "这是一个测试公司",
    }

    normalized_custom = normalize_stock_info(custom_info, market_type="us")
    print(f"\n自定义信息标准化:")
    print(f"  货币: {normalized_custom['currency']} (应该保留CNY)")
    print(f"  交易所: {normalized_custom['exchange']} (应该保留CUSTOM)")
    print(f"  PE: {normalized_custom.get('pe', 'N/A')}")
    print(f"  PB: {normalized_custom.get('pb', 'N/A')}")

    assert normalized_custom['currency'] == 'CNY', "自定义货币应该被保留"
    assert normalized_custom['exchange'] == 'CUSTOM', "自定义交易所应该被保留"
    assert normalized_custom.get('pe') == 15.5, "PE应该被保留"
    assert normalized_custom.get('pb') == 2.3, "PB应该被保留"

    print("\n✅ 股票信息标准化测试通过！\n")


def test_backwards_compatibility():
    """测试向后兼容性"""
    print("\n=== 测试向后兼容性 ===\n")

    # 测试不提供market_type时的默认行为（应该是美股）
    default_info = {"name": "默认测试"}

    normalized_default = normalize_stock_info(default_info)
    print(f"默认market_type测试:")
    print(f"  货币: {normalized_default['currency']} (应该是USD)")
    print(f"  市场: {normalized_default['market']} (应该是美国市场)")

    assert normalized_default['currency'] == 'USD', "默认应该是USD"
    assert normalized_default['market'] == '美国市场', "默认应该是美国市场"

    print("\n✅ 向后兼容性测试通过！\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Stock Normalizer 功能测试")
    print("=" * 60)

    try:
        test_normalize_stock_code()
        test_normalize_stock_info()
        test_backwards_compatibility()

        print("\n" + "=" * 60)
        print("🎉 所有测试通过！stock_normalizer工作正常！")
        print("=" * 60 + "\n")

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}\n")
        raise
    except Exception as e:
        print(f"\n❌ 测试出错: {e}\n")
        raise
