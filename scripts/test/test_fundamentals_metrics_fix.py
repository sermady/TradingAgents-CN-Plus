# -*- coding: utf-8 -*-
"""
测试基本面数据修复 - 验证财务指标N/A问题是否解决
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tradingagents.dataflows.china.fundamentals_loader import FundamentalsLoader


def test_get_financial_metrics():
    """测试财务指标获取功能"""
    print("=" * 60)
    print("测试基本面财务指标修复")
    print("=" * 60)

    loader = FundamentalsLoader()

    # 测试股票代码
    test_symbols = ["000001", "600519", "000858"]

    for symbol in test_symbols:
        print(f"\n📊 测试股票: {symbol}")
        print("-" * 40)

        try:
            metrics = loader._get_financial_metrics(symbol)

            # 检查各项指标
            print(f"  PE: {metrics.get('pe', 'N/A')}")
            print(f"  PB: {metrics.get('pb', 'N/A')}")
            print(f"  ROE: {metrics.get('roe', 'N/A')}")
            print(f"  ROA: {metrics.get('roa', 'N/A')}")
            print(f"  毛利率: {metrics.get('gross_margin', 'N/A')}")
            print(f"  净利率: {metrics.get('net_margin', 'N/A')}")
            print(f"  基本面评分: {metrics.get('fundamental_score', 'N/A')}/10")
            print(f"  估值评分: {metrics.get('valuation_score', 'N/A')}/10")
            print(f"  成长评分: {metrics.get('growth_score', 'N/A')}/10")
            print(f"  风险等级: {metrics.get('risk_level', 'N/A')}")

            # 验证是否有非N/A的值
            non_na_count = sum(
                1 for k, v in metrics.items()
                if v != "N/A" and k not in ['fundamental_score', 'valuation_score', 'growth_score', 'risk_level']
            )

            if non_na_count > 0:
                print(f"  ✅ 成功获取 {non_na_count} 项真实财务指标")
            else:
                print(f"  ⚠️ 未获取到真实财务指标（MongoDB可能无数据）")

        except Exception as e:
            print(f"  ❌ 获取失败: {e}")


def test_generate_report():
    """测试报告生成功能"""
    print("\n" + "=" * 60)
    print("测试基本面报告生成")
    print("=" * 60)

    loader = FundamentalsLoader()

    # 测试一个股票
    symbol = "000001"
    print(f"\n📊 生成报告: {symbol}")
    print("-" * 40)

    try:
        report = loader._generate_fundamentals_report(symbol, "standard")

        # 检查报告中是否包含N/A
        na_count = report.count("N/A")

        print(f"报告长度: {len(report)} 字符")
        print(f"报告中 'N/A' 出现次数: {na_count}")

        # 显示报告部分内容
        print("\n📄 报告预览:")
        print(report[:500] + "..." if len(report) > 500 else report)

        if na_count < 5:
            print(f"\n✅ 报告质量良好，N/A数量较少")
        else:
            print(f"\n⚠️ 报告中仍有较多N/A，可能需要检查数据源")

    except Exception as e:
        print(f"❌ 报告生成失败: {e}")
        import traceback
        traceback.print_exc()


def test_score_calculation():
    """测试评分计算逻辑"""
    print("\n" + "=" * 60)
    print("测试评分计算逻辑")
    print("=" * 60)

    loader = FundamentalsLoader()

    # 测试数据
    test_cases = [
        {
            "name": "高盈利企业",
            "raw_data": {
                "financial_indicators": [{
                    "roe": 25.0,
                    "roa": 15.0,
                    "grossprofit_margin": 45.0,
                    "netprofit_margin": 25.0,
                    "debt_to_assets": 35.0
                }]
            }
        },
        {
            "name": "一般企业",
            "raw_data": {
                "financial_indicators": [{
                    "roe": 10.0,
                    "roa": 5.0,
                    "grossprofit_margin": 25.0,
                    "netprofit_margin": 10.0,
                    "debt_to_assets": 50.0
                }]
            }
        },
        {
            "name": "亏损企业",
            "raw_data": {
                "financial_indicators": [{
                    "roe": -5.0,
                    "roa": -2.0,
                    "grossprofit_margin": 10.0,
                    "netprofit_margin": -5.0,
                    "debt_to_assets": 85.0
                }]
            }
        }
    ]

    for case in test_cases:
        print(f"\n📊 {case['name']}")
        print("-" * 40)

        financial_doc = {"raw_data": case["raw_data"]}

        fundamental_score = loader._calculate_fundamental_score(financial_doc)
        growth_score = loader._calculate_growth_score(financial_doc)

        print(f"  基本面评分: {fundamental_score:.1f}/10")
        print(f"  成长评分: {growth_score:.1f}/10")


if __name__ == "__main__":
    print("🔍 基本面数据修复验证测试")
    print("=" * 60)

    # 运行测试
    test_get_financial_metrics()
    test_generate_report()
    test_score_calculation()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
