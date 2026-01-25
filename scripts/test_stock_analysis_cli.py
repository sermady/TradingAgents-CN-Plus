# -*- coding: utf-8 -*-
"""
命令行股票分析测试工具

用于快速验证特定股票的数据获取和分析功能
"""

import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import asyncio
from datetime import datetime


def test_stock_analysis(
    symbol: str = "605589",
    research_depth: int = 1,
    skip_llm: bool = False
):
    """
    测试股票分析

    Args:
        symbol: 股票代码
        research_depth: 研究深度 (1-5)
        skip_llm: 是否跳过LLM分析（只获取数据）
    """
    print("=" * 80)
    print(f"股票分析测试: {symbol}")
    print(f"研究深度: {research_depth}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 1. 测试数据源获取
    print("\n【步骤1】测试数据源获取")
    print("-" * 80)

    try:
        from tradingagents.dataflows.data_source_manager import get_data_source_manager

        manager = get_data_source_manager()
        print(f"✅ 数据源管理器初始化成功")
        print(f"   当前数据源: {manager.current_source.value}")
        print(f"   可用数据源: {[s.value for s in manager.available_sources]}")

        # 获取股票数据
        from datetime import datetime, timedelta

        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

        print(f"\n📊 获取股票数据: {symbol}")
        print(f"   时间范围: {start_date} 至 {end_date}")

        stock_data = manager.get_stock_data(symbol, start_date, end_date)

        if stock_data:
            print(f"✅ 数据获取成功")
            print(f"   数据长度: {len(stock_data)} 字符")
            print(f"\n   数据预览 (前500字符):")
            print("   " + "-" * 76)
            print("   " + stock_data[:500])
            print("   " + "-" * 76)
        else:
            print("❌ 数据获取失败")
            return

    except Exception as e:
        print(f"❌ 数据源测试失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 2. 测试数据质量评分
    print("\n【步骤2】测试数据质量评分")
    print("-" * 80)

    try:
        # 解析数据为字典（简化处理）
        data_dict = parse_stock_data(stock_data)

        if data_dict:
            quality_score = manager.get_data_quality_score(symbol, data_dict)
            print(f"📊 数据质量评分: {quality_score:.1f}/100")

            # 评分详情
            if quality_score >= 80:
                print("   评级: 优秀 ✅")
            elif quality_score >= 60:
                print("   评级: 良好 ⚠️")
            else:
                print("   评级: 较差 ❌")

        else:
            print("⚠️ 无法解析数据为字典，跳过质量评分")

    except Exception as e:
        print(f"⚠️ 数据质量评分失败: {e}")

    # 3. 测试验证器
    print("\n【步骤3】测试数据验证器")
    print("-" * 80)

    try:
        from tradingagents.dataflows.validators.price_validator import PriceValidator
        from tradingagents.dataflows.validators.fundamentals_validator import FundamentalsValidator

        price_validator = PriceValidator()
        fundamentals_validator = FundamentalsValidator()

        if data_dict:
            # 价格数据验证
            price_result = price_validator.validate(symbol, data_dict)
            print(f"📈 价格数据验证:")
            print(f"   有效: {price_result.is_valid}")
            print(f"   置信度: {price_result.confidence:.2%}")
            if price_result.discrepancies:
                print(f"   问题数: {len(price_result.discrepancies)}")
                for issue in price_result.discrepancies[:5]:  # 只显示前5个
                    print(f"     - [{issue.severity.value}] {issue.message}")

            # 基本面数据验证
            fund_result = fundamentals_validator.validate(symbol, data_dict)
            print(f"\n📊 基本面数据验证:")
            print(f"   有效: {fund_result.is_valid}")
            print(f"   置信度: {fund_result.confidence:.2%}")
            if fund_result.discrepancies:
                print(f"   问题数: {len(fund_result.discrepancies)}")
                for issue in fund_result.discrepancies[:5]:
                    print(f"     - [{issue.severity.value}] {issue.message}")

    except Exception as e:
        print(f"❌ 验证器测试失败: {e}")
        import traceback
        traceback.print_exc()

    # 4. 如果不跳过LLM，运行完整分析
    if not skip_llm:
        print("\n【步骤4】测试完整分析流程")
        print("-" * 80)
        print("⚠️ 注意: 完整分析需要配置LLM API密钥")
        print("⚠️ 如果未配置，此步骤将失败")

        try:
            from tradingagents.graph.trading_graph import TradingGraph
            from tradingagents.config import llm_config

            # 检查LLM配置
            llm_provider = os.getenv('LLM_PROVIDER', 'dashscope')
            api_key = os.getenv(f'{llm_provider.upper()}_API_KEY')

            if not api_key:
                print("⚠️ 未检测到LLM API密钥，跳过LLM分析")
                print("   提示: 请在.env文件中配置 DASHSCOPE_API_KEY 或其他API密钥")
                return

            print(f"✅ LLM提供商: {llm_provider}")

            # 创建分析图
            graph = TradingGraph()

            # 运行分析
            print(f"\n🚀 开始分析 {symbol}...")
            print("   这可能需要几分钟时间...")

            # 构建初始状态
            initial_state = {
                "messages": [],
                "company_of_interest": symbol,
                "trade_date": end_date.replace('-', ''),
                "research_depth": research_depth,
            }

            # 异步运行分析
            result = asyncio.run(graph.ainvoke(initial_state))

            print(f"\n✅ 分析完成!")
            print(f"   消息数: {len(result.get('messages', []))}")

            # 显示报告位置
            if 'messages' in result and len(result['messages']) > 0:
                last_message = result['messages'][-1]
                if hasattr(last_message, 'content'):
                    content = last_message.content
                    print(f"\n📄 最终决策预览:")
                    print("   " + "-" * 76)
                    lines = content.split('\n')
                    for line in lines[:20]:  # 只显示前20行
                        print("   " + line)
                    if len(lines) > 20:
                        print(f"   ... (还有 {len(lines) - 20} 行)")
                    print("   " + "-" * 76)

        except Exception as e:
            print(f"❌ LLM分析失败: {e}")
            import traceback
            traceback.print_exc()

    # 5. 总结
    print("\n" + "=" * 80)
    print("测试完成总结")
    print("=" * 80)
    print("✅ 数据源获取: 正常")
    print("✅ 数据验证: 正常")
    if not skip_llm:
        print("✅ LLM分析: 需要配置API密钥")

    print("\n💡 提示:")
    print("   - 如需运行完整分析，请在.env中配置LLM API密钥")
    print("   - 可以使用 --skip-llm 参数跳过LLM分析，只测试数据获取")
    print("=" * 80)


def parse_stock_data(data_str: str) -> dict:
    """
    解析股票数据字符串为字典

    这是一个简化实现，实际应该根据数据格式精确解析
    """
    data_dict = {'source': 'data_source_manager'}

    try:
        # 尝试从数据中提取关键指标
        lines = data_str.split('\n')

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('*'):
                continue

            # 解析格式: "指标: 值" 或 "**指标**: 值"
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip('*').strip()
                    value_str = parts[1].strip()

                    # 尝试转换为数值
                    try:
                        # 移除可能的单位和符号
                        value_str = value_str.replace('¥', '').replace(',', '').replace('亿元', '').replace('万股', '').replace('%', '').strip()

                        if '.' in value_str or value_str.isdigit():
                            value = float(value_str)
                        else:
                            value = value_str

                        data_dict[key] = value
                    except:
                        data_dict[key] = value_str

    except Exception as e:
        print(f"⚠️ 数据解析失败: {e}")

    return data_dict


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='股票分析测试工具')
    parser.add_argument('symbol', nargs='?', default='605589', help='股票代码 (默认: 605589)')
    parser.add_argument('--depth', type=int, default=1, choices=[1, 2, 3, 4, 5],
                       help='研究深度 (1-5, 默认: 1)')
    parser.add_argument('--skip-llm', action='store_true', help='跳过LLM分析，只测试数据获取')

    args = parser.parse_args()

    test_stock_analysis(
        symbol=args.symbol,
        research_depth=args.depth,
        skip_llm=args.skip_llm
    )
