# -*- coding: utf-8 -*-
"""
测试 Tushare 完整财务数据获取

验证：
1. 估值指标 (PE, PB, PS)
2. 财务指标 (ROE, ROA, 毛利率等)
3. 财务报表 (利润表、资产负债表、现金流量表)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    print("=" * 80)
    print("Tushare 完整财务数据获取测试")
    print("=" * 80)
    print()

    from tradingagents.dataflows.data_source_manager import get_data_source_manager, ChinaDataSource

    # 获取数据源管理器
    mgr = get_data_source_manager()

    # 切换到 Tushare 数据源
    mgr.current_source = ChinaDataSource.TUSHARE
    logger.info(f"数据源设置为: {mgr.current_source.value}")

    test_symbol = "605589"  # 圣泉集团

    print(f"测试股票: {test_symbol}")
    print()

    # 测试 1: 估值指标
    print("=" * 80)
    print("测试 1: 估值指标 (PE, PB, PS)")
    print("=" * 80)
    result1 = mgr._get_tushare_fundamentals(test_symbol)
    print(result1)
    print()

    # 测试 2: 财务指标
    print("=" * 80)
    print("测试 2: 财务指标 (ROE, ROA 等)")
    print("=" * 80)
    result2 = mgr._get_tushare_financial_indicators(test_symbol)
    print(result2)
    print()

    # 测试 3: 财务报表
    print("=" * 80)
    print("测试 3: 财务报表 (利润表、资产负债表、现金流量表)")
    print("=" * 80)
    result3 = mgr._get_tushare_financial_reports(test_symbol)
    print(result3)
    print()

    # 测试 4: 完整基本面数据
    print("=" * 80)
    print("测试 4: 完整基本面数据（综合）")
    print("=" * 80)
    result4 = mgr.get_fundamentals_data(test_symbol)
    print(result4)
    print()

    # 保存完整结果到文件
    output_file = Path(__file__).parent / "results" / f"tushare_fundamentals_{test_symbol}.txt"
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(result4)
    print(f"完整结果已保存到: {output_file}")


if __name__ == '__main__':
    main()
