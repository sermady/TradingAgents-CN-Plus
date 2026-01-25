# -*- coding: utf-8 -*-
"""
数据验证功能演示脚本
展示成交量和PE验证的实际应用
"""

import sys
import os

# 添加项目根目录
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app.services.data_consistency_checker import DataConsistencyChecker


def demo_volume_validation():
    """演示成交量验证功能"""
    print("\n" + "="*60)
    print("📊 成交量验证演示")
    print("="*60)
    
    checker = DataConsistencyChecker()
    
    # 测试场景1：合理的成交量数据
    print("\n【场景1】合理的成交量数据")
    volume = 5_554_100  # 股
    price = 53.65
    
    is_valid, error_msg, diagnostic = checker.validate_volume_consistency(volume, price)
    
    print(f"  输入: 成交量={volume:,}股, 价格={price}元")
    print(f"  结果: {'✅ 有效' if is_valid else '❌ 无效'}")
    print(f"  单位: {diagnostic.get('input_unit', 'unknown')}")
    print(f"  成交额: {diagnostic.get('corrected_amount', 0):,.0f}元")
    
    # 测试场景2：成交量单位可能是"手"
    print("\n【场景2】成交量单位为'手'（需要转换）")
    volume = 555_410  # 手
    price = 53.65
    
    is_valid, error_msg, diagnostic = checker.validate_volume_consistency(volume, price)
    
    print(f"  输入: 成交量={volume:,}手, 价格={price}元")
    print(f"  结果: {'✅ 有效' if is_valid else '❌ 无效'}")
    print(f"  检测到的单位: {diagnostic.get('input_unit', 'unknown')}")
    print(f"  转换为股: {diagnostic.get('volume_in_shares', 0):,}股")
    print(f"  成交额: {diagnostic.get('calculated_amount_hand', 0):,.0f}元")
    
    # 测试场景3：异常的成交量数据
    print("\n【场景3】异常的成交量数据")
    volume = 999_999_999  # 不合理的成交量
    price = 53.65
    
    is_valid, error_msg, diagnostic = checker.validate_volume_consistency(volume, price)
    
    print(f"  输入: 成交量={volume:,}, 价格={price}元")
    print(f"  结果: {'✅ 有效' if is_valid else '❌ 无效'}")
    if error_msg:
        print(f"  错误信息: {error_msg}")


def demo_pe_validation():
    """演示PE验证功能"""
    print("\n" + "="*60)
    print("📈 PE验证演示")
    print("="*60)
    
    checker = DataConsistencyChecker()
    
    # 测试场景1：PE计算正确
    print("\n【场景1】PE计算正确")
    symbol = "600391"
    reported_pe = 397.7
    current_price = 53.65
    total_shares = 332_000_000  # 3.32亿股
    net_profit = 44_600_000  # 4460万净利润
    
    is_valid, error_msg, diagnostic = checker.validate_pe_calculation(
        symbol, reported_pe, current_price, total_shares, net_profit
    )
    
    print(f"  股票: {symbol}")
    print(f"  报告PE: {reported_pe}")
    print(f"  计算PE: {diagnostic.get('calculated_pe', 0):.2f}")
    print(f"  差异: {diagnostic.get('pe_difference_pct', 0)*100:.1f}%")
    print(f"  结果: {'✅ PE计算正确' if is_valid else '❌ PE计算异常'}")
    
    # 测试场景2：净利润期间不匹配
    print("\n【场景2】净利润期间不匹配")
    # 假设报告用的是全年净利润，但实际只用了Q1-Q3
    net_profit_full = 54_600_000  # 全年净利润（包含Q4）
    
    is_valid, error_msg, diagnostic = checker.validate_pe_calculation(
        symbol, reported_pe, current_price, total_shares, net_profit_full, "Annual"
    )
    
    print(f"  净利润期间: 全年")
    print(f"  报告PE: {reported_pe}")
    print(f"  计算PE: {diagnostic.get('calculated_pe', 0):.2f}")
    print(f"  差异: {diagnostic.get('pe_difference_pct', 0)*100:.1f}%")
    print(f"  结果: {'✅ PE计算正确' if is_valid else '❌ PE计算异常（期间不匹配）'}")
    
    # 测试场景3：EPS为负（亏损）
    print("\n【场景3】净利润为负（亏损公司）")
    is_valid, error_msg, diagnostic = checker.validate_pe_calculation(
        symbol, 397.7, 53.65, 332_000_000, -10_000_000  # 亏损
    )
    
    print(f"  净利润: -10,000,000元")
    print(f"  结果: {'✅ PE计算正确' if is_valid else '❌ 无法计算PE（亏损）'}")
    if error_msg:
        print(f"  原因: {error_msg}")


def demo_real_world_scenario():
    """演示真实场景：分析报告数据验证"""
    print("\n" + "="*60)
    print("🌐 真实场景：分析报告数据验证")
    print("="*60)
    
    checker = DataConsistencyChecker()
    
    # 模拟600391的分析报告数据
    print("\n【600391 江苏国泰】")
    print("  假设技术报告和基本面报告数据不一致")
    
    # 技术报告数据
    volume_tech = 1_904_255  # 技术报告的成交量
    price = 53.65
    
    is_valid_tech, error_tech, diag_tech = checker.validate_volume_consistency(volume_tech, price)
    
    print(f"\n  技术报告:")
    print(f"    成交量: {volume_tech:,}")
    print(f"    验证结果: {'✅ 合理' if is_valid_tech else '⚠️ 需要检查'}")
    print(f"    检测单位: {diag_tech.get('input_unit', 'unknown')}")
    print(f"    计算成交额: {diag_tech.get('corrected_amount', 0):,.0f}元")
    
    # 基本面报告数据
    volume_fund = 55_544_100  # 基本面报告的成交量（多了个零）
    
    is_valid_fund, error_fund, diag_fund = checker.validate_volume_consistency(volume_fund, price)
    
    print(f"\n  基本面报告:")
    print(f"    成交量: {volume_fund:,}")
    print(f"    验证结果: {'✅ 合理' if is_valid_fund else '⚠️ 需要检查'}")
    print(f"    检测单位: {diag_fund.get('input_unit', 'unknown')}")
    print(f"    计算成交额: {diag_fund.get('corrected_amount', 0):,.0f}元")
    
    # 对比分析
    print(f"\n  【数据质量检查结果】")
    amount_tech = diag_tech.get('corrected_amount', 0)
    amount_fund = diag_fund.get('corrected_amount', 0)
    
    if amount_tech > 0 and amount_fund > 0:
        ratio = max(amount_tech, amount_fund) / min(amount_tech, amount_fund)
        print(f"    两个报告的成交额差异: {ratio:.1f}倍")
        
        if ratio > 2:
            print(f"    ⚠️ 警告: 数据差异较大，可能存在数据质量问题")
            print(f"    建议: 核实数据来源，检查是否存在单位混淆或数据错误")
        else:
            print(f"    ✅ 数据差异在合理范围内")


def main():
    """主函数"""
    print("\n" + "🚀" * 30)
    print("\n📊 TradingAgents-CN 数据验证功能演示")
    print("   展示成交量和PE验证的核心功能")
    print("\n" + "🚀" * 30)
    
    demo_volume_validation()
    demo_pe_validation()
    demo_real_world_scenario()
    
    print("\n" + "="*60)
    print("✅ 演示完成")
    print("="*60)
    print("\n💡 提示:")
    print("   - 成交量验证自动检测单位（手/股）")
    print("   - PE验证检查计算公式和净利润期间")
    print("   - 所有验证结果都会记录在诊断信息中")
    print("   - 可用于分析报告的数据质量检查")


if __name__ == "__main__":
    main()
