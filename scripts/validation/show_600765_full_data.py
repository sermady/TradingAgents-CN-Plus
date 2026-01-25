# -*- coding: utf-8 -*-
"""显示600765的完整数据 - 输出到文件"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
import logging

# 禁用日志
logging.basicConfig(level=logging.ERROR)

def main():
    symbol = "600765"
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')

    output = []
    output.append("=" * 80)
    output.append(f"600765 完整数据展示")
    output.append(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append("=" * 80)
    output.append("")

    try:
        from tradingagents.dataflows.data_source_manager import get_data_source_manager

        manager = get_data_source_manager()

        # 获取技术数据
        output.append("【技术数据】")
        output.append("-" * 80)
        market_data = manager.get_stock_data(symbol, start_date, end_date)
        output.append(market_data)
        output.append("")

        # 获取基本面数据
        output.append("【基本面数据】")
        output.append("-" * 80)
        fundamentals_data = manager.get_fundamentals_data(symbol)
        output.append(fundamentals_data)
        output.append("")

    except Exception as e:
        output.append(f"错误: {e}")
        import traceback
        output.append(traceback.format_exc())

    # 保存到文件
    output_file = Path('temp/600765_full_data.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))

    print(f"结果已保存到: {output_file}")

if __name__ == '__main__':
    main()
