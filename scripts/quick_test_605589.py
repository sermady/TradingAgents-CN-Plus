# -*- coding: utf-8 -*-
"""
命令行股票分析测试工具 - 简化版

用于快速验证605589等股票的数据获取
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    """主测试函数"""
    from datetime import datetime, timedelta

    symbol = "605589"

    print("=" * 80)
    print(f"股票分析测试: {symbol}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 测试数据源获取
    print("\n【步骤1】数据源获取测试")
    print("-" * 80)

    try:
        from tradingagents.dataflows.data_source_manager import get_data_source_manager

        manager = get_data_source_manager()
        print(f"✅ 数据源: {manager.current_source.value}")

        # 获取数据
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

        print(f"📊 获取 {symbol} 数据...")
        stock_data = manager.get_stock_data(symbol, start_date, end_date)

        if stock_data and len(stock_data) > 100:
            print(f"✅ 数据获取成功! 长度: {len(stock_data)} 字符\n")
            print("数据预览:")
            print("-" * 40)
            # 只显示前800字符
            preview = stock_data[:800] if len(stock_data) > 800 else stock_data
            print(preview)
            print("-" * 40)
        else:
            print("❌ 数据获取失败或数据为空")
            return

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return

    # 测试验证器
    print("\n【步骤2】数据验证器测试")
    print("-" * 80)

    try:
        from tradingagents.dataflows.validators.fundamentals_validator import FundamentalsValidator

        validator = FundamentalsValidator()

        # 构造测试数据（模拟605589报告中的数据）
        test_data = {
            'market_cap': 263.9,
            'revenue': 92.0,
            'PS': 0.10,  # 错误的PS值
            'PE': 25.7,
            'PB': 3.2,
            'ROE': 7.5,
            'source': 'test'
        }

        print("🔍 验证PS比率（605589报告中的错误）:")
        result = validator.validate(symbol, test_data)

        print(f"   验证结果: {'通过 ✅' if result.is_valid else '失败 ❌'}")
        print(f"   置信度: {result.confidence:.1%}")

        if result.discrepancies:
            print(f"   发现问题: {len(result.discrepancies)} 个")
            for issue in result.discrepancies:
                print(f"     - [{issue.severity.value}] {issue.message}")
                if issue.suggested_value:
                    print(f"       建议值: {issue.suggested_value}")

    except Exception as e:
        print(f"⚠️ 验证器测试失败: {e}")

    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)
    print("\n💡 运行完整分析:")
    print("   python scripts/test_stock_analysis_cli.py 605589 --depth 1")
    print("\n💡 只测试数据（不调用LLM）:")
    print("   python scripts/test_stock_analysis_cli.py 605589 --depth 1 --skip-llm")
    print("=" * 80)


if __name__ == '__main__':
    main()
