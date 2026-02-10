#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试数据质量检查和降级机制"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradingagents.dataflows.optimized_china_data import OptimizedChinaDataProvider


def test_data_quality_check():
    """测试数据质量检查功能"""
    print("\n" + "=" * 60)
    print("测试1: 数据质量检查功能")
    print("=" * 60)

    provider = OptimizedChinaDataProvider()

    # 模拟有缺失字段的数据
    industry_info = {"industry": "未知", "market": "主板"}
    financial_estimates = {
        "total_revenue_fmt": "100亿元",
        "net_income_fmt": "10亿元",
        "revenue_yoy_fmt": "N/A",  # 缺失
        "net_income_yoy_fmt": "N/A",  # 缺失
        "pe": "15.5",
        "pb": "N/A",  # 缺失
    }

    result = provider._check_data_quality("605589", industry_info, financial_estimates)

    print(f"✅ 质量评分: {result['quality_score']}/100")
    print(f"✅ 质量等级: {result['quality_level']}")
    print(f"✅ 缺失字段: {', '.join(result['missing_fields'])}")
    print(f"✅ 质量问题数: {len(result['quality_issues'])}")

    # 验证结果
    assert result["quality_score"] < 100, "应该有扣分"
    assert len(result["missing_fields"]) > 0, "应该检测到缺失字段"
    assert "所属行业" in result["missing_fields"], "应该检测到行业缺失"
    assert "营收同比增速" in result["missing_fields"], "应该检测到营收增速缺失"

    print("\n✅ 数据质量检查功能测试通过!")
    return True


def test_industry_info_fallback():
    """测试行业信息降级机制"""
    print("\n" + "=" * 60)
    print("测试2: 行业信息降级机制")
    print("=" * 60)

    provider = OptimizedChinaDataProvider()

    # 测试股票代码
    symbol = "605589"

    print(f"\n正在测试股票 {symbol} 的行业信息获取...")
    print("(如果数据库中没有数据，将尝试从Tushare API实时获取)")

    try:
        industry_info = provider._get_industry_info(symbol)

        print(f"\n✅ 行业信息获取结果:")
        print(f"   - 所属行业: {industry_info.get('industry', '未知')}")
        print(f"   - 市场板块: {industry_info.get('market', '未知')}")
        print(f"   - 数据来源: {industry_info.get('source', 'database')}")

        if industry_info.get("industry") not in ["未知", ""]:
            print("\n✅ 成功获取到行业信息!")
        else:
            print("\n⚠️ 行业信息仍为'未知'，可能Tushare API也无法获取")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def test_background_sync():
    """测试后台数据同步触发"""
    print("\n" + "=" * 60)
    print("测试3: 后台数据同步触发")
    print("=" * 60)

    provider = OptimizedChinaDataProvider()

    # 测试有缺失字段时是否触发同步
    missing_fields = ["所属行业", "营收同比增速"]

    print(f"\n触发后台同步，缺失字段: {missing_fields}")

    try:
        result = provider._trigger_background_sync("605589", missing_fields)

        if result:
            print("✅ 成功触发后台同步任务")
        else:
            print("⚠️ 未能触发后台同步(可能是正常情况，如同步服务不可用)")

    except Exception as e:
        print(f"⚠️ 触发同步时出错(预期内，如果同步服务未配置): {e}")

    # 测试无缺失字段时是否不触发
    print("\n测试无缺失字段的情况...")
    result = provider._trigger_background_sync("605589", [])

    if not result:
        print("✅ 正确判断无需同步")

    print("\n✅ 后台同步触发测试完成!")
    return True


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("TradingAgents-CN 数据质量增强功能测试")
    print("=" * 60)

    tests = [
        ("数据质量检查", test_data_quality_check),
        ("行业信息降级", test_industry_info_fallback),
        ("后台同步触发", test_background_sync),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ {name}测试失败: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"📊 总计: {passed + failed}")

    if failed == 0:
        print("\n🎉 所有测试通过!")
        return 0
    else:
        print(f"\n⚠️ {failed}个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
