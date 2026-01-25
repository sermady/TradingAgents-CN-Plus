# -*- coding: utf-8 -*-
"""
测试600765数据一致性

验证：
1. 技术分析师获取的数据
2. 基本面分析师获取的数据
3. 各个指标的一致性
4. 报告中数据的一致性
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
import logging

# 配置日志
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('temp/test_600765_consistency.log', encoding='utf-8')
    ]
)

def extract_metrics_from_data(data_str: str, category: str) -> dict:
    """从数据字符串中提取指标"""
    metrics = {}

    try:
        lines = data_str.split('\n')
        for line in lines:
            line = line.strip()

            # 解析格式: "指标: 值" 或 "**指标**: 值"
            if ':' in line or '：' in line:
                if '：' in line:
                    parts = line.split('：', 1)
                else:
                    parts = line.split(':', 1)

                if len(parts) == 2:
                    key = parts[0].strip('*').strip()
                    value_str = parts[1].strip()

                    # 移除单位和符号
                    value_str = value_str.replace('¥', '').replace('$', '').replace('￥', '')
                    value_str = value_str.replace(',', '').replace(' ', '')
                    value_str = value_str.replace('亿元', '').replace('亿', '')
                    value_str = value_str.replace('万元', '').replace('万', '')
                    value_str = value_str.replace('股', '').replace('%', '')
                    value_str = value_str.replace('倍', '').replace('（', '').replace('）', '')

                    try:
                        if '.' in value_str or value_str.isdigit():
                            value = float(value_str)
                        else:
                            value = value_str
                        metrics[key] = value
                    except:
                        metrics[key] = value_str
    except Exception as e:
        print(f"  解析失败: {e}")

    return metrics

def compare_metrics(data1_name: str, data1: dict, data2_name: str, data2: dict) -> list:
    """比较两组指标，返回差异列表"""
    differences = []

    # 找出所有共同的指标
    all_keys = set(data1.keys()) | set(data2.keys())

    for key in all_keys:
        val1 = data1.get(key)
        val2 = data2.get(key)

        if val1 is not None and val2 is not None:
            # 两个都有，比较是否一致
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                # 数值比较
                if abs(val1 - val2) > 0.01:  # 允许0.01的误差
                    diff_pct = abs((val1 - val2) / val2) * 100 if val2 != 0 else 0
                    differences.append({
                        'metric': key,
                        'value1': f"{val1}",
                        'value2': f"{val2}",
                        'diff_pct': f"{diff_pct:.1f}%"
                    })
            elif val1 != val2:
                # 非数值比较
                differences.append({
                    'metric': key,
                    'value1': str(val1),
                    'value2': str(val2),
                    'diff_pct': 'N/A'
                })
        elif val1 is not None or val2 is not None:
            # 只有一个有
            differences.append({
                'metric': key,
                'value1': str(val1) if val1 is not None else '缺失',
                'value2': str(val2) if val2 is not None else '缺失',
                'diff_pct': 'N/A'
            })

    return differences

def main():
    symbol = "600765"
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

    output = []
    output.append("=" * 80)
    output.append(f"600765 数据一致性测试")
    output.append(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append("=" * 80)
    output.append("")

    try:
        from tradingagents.dataflows.data_source_manager import get_data_source_manager
        from tradingagents.agents.utils.data_validation_integration import (
            add_data_validation_to_market_report,
            add_data_validation_to_fundamentals_report
        )
        from tradingagents.dataflows.validators.price_validator import PriceValidator
        from tradingagents.dataflows.validators.fundamentals_validator import FundamentalsValidator
        from tradingagents.dataflows.validators.volume_validator import VolumeValidator

        manager = get_data_source_manager()

        # ========== 测试1: 获取原始数据 ==========
        output.append("【测试1】获取原始数据")
        output.append("-" * 80)
        output.append("")

        # 获取技术数据
        output.append("1.1 获取技术数据...")
        market_data = manager.get_stock_data(symbol, start_date, end_date)
        if market_data:
            output.append(f"  成功! 数据长度: {len(market_data)} 字符")
        else:
            output.append("  失败!")
        output.append("")

        # 获取基本面数据
        output.append("1.2 获取基本面数据...")
        fundamentals_data = manager.get_fundamentals_data(symbol)
        if fundamentals_data:
            output.append(f"  成功! 数据长度: {len(fundamentals_data)} 字符")
        else:
            output.append("  失败!")
        output.append("")

        # ========== 测试2: 提取和解析指标 ==========
        output.append("【测试2】提取和解析指标")
        output.append("-" * 80)
        output.append("")

        # 解析技术指标
        output.append("2.1 解析技术指标...")
        market_metrics = extract_metrics_from_data(market_data, "market")
        output.append(f"  提取到 {len(market_metrics)} 个技术指标")

        # 显示关键技术指标
        key_market_metrics = ['当前价格', '最新价格', 'MA5', 'MA10', 'MA20', 'MA60', 'RSI', 'MACD', 'BOLL', '成交量', '换手率']
        output.append("  关键技术指标:")
        for metric in key_market_metrics:
            if metric in market_metrics:
                output.append(f"    {metric}: {market_metrics[metric]}")
        output.append("")

        # 解析基本面指标
        output.append("2.2 解析基本面指标...")
        fundamentals_metrics = extract_metrics_from_data(fundamentals_data, "fundamentals")
        output.append(f"  提取到 {len(fundamentals_metrics)} 个基本面指标")

        # 显示关键基本面指标
        key_fundamentals_metrics = ['总市值', '市盈率', '市销率', '市净率', 'PE', 'PS', 'PB', 'ROE', 'ROA', '毛利率', '净利率', '资产负债率']
        output.append("  关键基本面指标:")
        for metric in key_fundamentals_metrics:
            if metric in fundamentals_metrics:
                output.append(f"    {metric}: {fundamentals_metrics[metric]}")
        output.append("")

        # ========== 测试3: 验证数据质量 ==========
        output.append("【测试3】验证数据质量")
        output.append("-" * 80)
        output.append("")

        # 验证技术数据
        output.append("3.1 验证技术数据...")
        price_validator = PriceValidator()
        volume_validator = VolumeValidator()

        price_result = price_validator.validate(symbol, market_metrics)
        volume_result = volume_validator.validate(symbol, market_metrics)

        output.append(f"  价格验证: {'通过' if price_result.is_valid else '失败'} (置信度: {price_result.confidence:.1%})")
        output.append(f"  成交量验证: {'通过' if volume_result.is_valid else '失败'} (置信度: {volume_result.confidence:.1%})")

        if price_result.discrepancies:
            output.append(f"  价格问题: {len(price_result.discrepancies)} 个")
        if volume_result.discrepancies:
            output.append(f"  成交量问题: {len(volume_result.discrepancies)} 个")
        output.append("")

        # 验证基本面数据
        output.append("3.2 验证基本面数据...")
        fundamentals_validator = FundamentalsValidator()
        fund_result = fundamentals_validator.validate(symbol, fundamentals_metrics)

        output.append(f"  基本面验证: {'通过' if fund_result.is_valid else '失败'} (置信度: {fund_result.confidence:.1%})")

        if fund_result.discrepancies:
            output.append(f"  基本面问题: {len(fund_result.discrepancies)} 个")
            output.append("")
            output.append("  问题详情:")
            for issue in fund_result.discrepancies[:5]:  # 只显示前5个
                output.append(f"    - [{issue.severity.value.upper()}] {issue.field}: {issue.message}")
                if issue.suggested_value is not None:
                    output.append(f"      建议值: {issue.suggested_value}")
        output.append("")

        # ========== 测试4: 检查报告中数据一致性 ==========
        output.append("【测试4】检查报告中数据一致性")
        output.append("-" * 80)
        output.append("")

        # 应用验证到报告
        output.append("4.1 生成验证后的市场报告...")
        validated_market = add_data_validation_to_market_report(symbol, market_data, validation_enabled=True)

        if "## ⚠️ 数据验证发现问题" in validated_market:
            output.append("  市场报告中发现数据问题!")
        elif "## ✅ 市场数据验证通过" in validated_market:
            output.append("  市场报告验证通过")
        output.append("")

        output.append("4.2 生成验证后的基本面报告...")
        validated_fundamentals = add_data_validation_to_fundamentals_report(symbol, fundamentals_data, validation_enabled=True)

        if "## ⚠️ 数据验证发现问题" in validated_fundamentals:
            output.append("  基本面报告中发现数据问题!")
        elif "## ✅ 基本面数据验证通过" in validated_fundamentals:
            output.append("  基本面报告验证通过")
        output.append("")

        # ========== 测试5: PS比率专项检查 ==========
        output.append("【测试5】PS比率专项检查")
        output.append("-" * 80)
        output.append("")

        # 检查PS数据
        ps_values = {}
        if 'PS' in fundamentals_metrics:
            ps_values['报告PS'] = fundamentals_metrics['PS']
        if '市销率' in fundamentals_metrics:
            ps_values['市销率'] = fundamentals_metrics['市销率']
        if '总市值' in fundamentals_metrics and '营业总收入' in fundamentals_metrics:
            market_cap = fundamentals_metrics['总市值']
            revenue = fundamentals_metrics['营业总收入']
            if revenue > 0:
                calculated_ps = market_cap / revenue
                ps_values['计算PS'] = calculated_ps
        output.append("  PS数据:")
        for key, value in ps_values.items():
            output.append(f"    {key}: {value}")

        if len(ps_values) > 1:
            output.append("")
            output.append("  ⚠️ 发现多个PS值，需要验证一致性")
        output.append("")

        # ========== 总结 ==========
        output.append("=" * 80)
        output.append("测试总结")
        output.append("=" * 80)
        output.append(f"股票代码: {symbol}")
        output.append(f"技术指标: {len(market_metrics)} 个")
        output.append(f"基本面指标: {len(fundamentals_metrics)} 个")
        output.append(f"价格验证: {'通过 ✅' if price_result.is_valid else '失败 ❌'}")
        output.append(f"基本面验证: {'通过 ✅' if fund_result.is_valid else '失败 ❌'}")
        output.append(f"总体置信度: {(price_result.confidence + fund_result.confidence) / 2:.1%}")

        if price_result.discrepancies or fund_result.discrepancies:
            total_issues = len(price_result.discrepancies) + len(fund_result.discrepancies)
            output.append(f"发现问题: {total_issues} 个")
            output.append("")
            output.append("⚠️ 建议: 检查数据源和报告生成逻辑")
        else:
            output.append("")
            output.append("✅ 所有数据验证通过")

        output.append("=" * 80)

    except Exception as e:
        output.append(f"[ERROR] 测试失败: {e}")
        import traceback
        output.append(traceback.format_exc())

    # 保存结果
    output_file = Path('temp/test_600765_consistency_result.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))

    # 同时输出到控制台
    print('\n'.join(output))
    print()
    print(f"完整结果已保存到: {output_file}")

if __name__ == '__main__':
    main()
