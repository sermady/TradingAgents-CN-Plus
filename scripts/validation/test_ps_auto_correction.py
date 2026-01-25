# -*- coding: utf-8 -*-
"""测试PS比率自动修正功能 - 输出到文件"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    handlers=[
        logging.FileHandler('temp/test_ps_auto_correction.log', encoding='utf-8')
    ]
)

def main():
    symbol = "605589"

    output = []
    output.append("=" * 80)
    output.append("PS比率自动修正功能测试")
    output.append("=" * 80)
    output.append("")

    # ========== 测试1: PS错误的报告（应该被修正）==========
    output.append("【测试1】模拟605589 PS错误报告")
    output.append("-" * 80)
    output.append("")

    wrong_report = f"""
**605589 基本面分析报告**

**估值指标**:
   总市值: 263.90亿元
   市盈率(PE): 25.7倍
   市销率(PS): 0.10倍
   市净率(PB): 3.2倍

**财务数据**:
   营业总收入: 80.72亿元
   净利润: 7.59亿元
   ROE: 7.5%

**投资建议**: 基于当前PS=0.10的低估值，建议买入
"""

    output.append("原始报告（PS=0.10错误）:")
    output.append("-" * 40)
    output.append(wrong_report)
    output.append("-" * 40)
    output.append("")

    try:
        from tradingagents.agents.utils.data_validation_integration import (
            add_data_validation_to_fundamentals_report
        )

        # 应用PS自动修正
        corrected_report = add_data_validation_to_fundamentals_report(
            symbol,
            wrong_report,
            validation_enabled=True
        )

        output.append("修正后的报告:")
        output.append("-" * 40)
        output.append(corrected_report)
        output.append("-" * 40)
        output.append("")

        # 检查是否包含修正说明
        if "数据修正" in corrected_report:
            output.append("✅ PS自动修正成功！")
            output.append("")

            # 提取修正说明
            if "**⚠️ 数据修正**" in corrected_report:
                start = corrected_report.find("**⚠️ 数据修正**")
                end = corrected_report.find("---", start + 100) + 3
                if end > start:
                    correction_note = corrected_report[start:end]
                    output.append("修正说明:")
                    output.append(correction_note)
        else:
            output.append("⚠️ 未发现修正说明")

    except Exception as e:
        output.append(f"错误: {e}")
        import traceback
        output.append(traceback.format_exc())

    output.append("")
    output.append("=" * 80)
    output.append("测试完成")
    output.append("=" * 80)

    # 保存到文件
    output_file = Path('temp/test_ps_auto_correction_result.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))

    print(f"结果已保存到: {output_file}")

if __name__ == '__main__':
    main()
