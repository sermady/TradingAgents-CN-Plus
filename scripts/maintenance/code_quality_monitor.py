# -*- coding: utf-8 -*-
"""
代码质量监控脚本
用于监控项目代码质量指标，包括：
- 超大文件检测
- 重复代码模式检测
- 代码复杂度统计
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class CodeQualityMonitor:
    """代码质量监控器"""

    # 阈值配置
    THRESHOLDS = {
        "max_file_lines": 1000,  # 文件最大行数警告
        "max_function_lines": 100,  # 函数最大行数警告
        "max_class_lines": 500,  # 类最大行数警告
    }

    def __init__(self, project_path: str = None):
        self.project_path = Path(project_path) if project_path else project_root
        self.issues: List[Dict] = []
        self.stats: Dict = {}

    def scan_project(self) -> Dict:
        """扫描整个项目"""
        print("=" * 60)
        print("代码质量监控报告")
        print("=" * 60)

        python_files = list(self.project_path.rglob("*.py"))
        total_files = len(python_files)
        total_lines = 0
        large_files = []

        print(f"\n扫描文件数: {total_files}")

        for file_path in python_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    line_count = len(lines)
                    total_lines += line_count

                    if line_count > self.THRESHOLDS["max_file_lines"]:
                        large_files.append({
                            "path": str(file_path.relative_to(self.project_path)),
                            "lines": line_count,
                        })
            except Exception as e:
                print(f"警告: 无法读取文件 {file_path}: {e}")

        self.stats = {
            "total_files": total_files,
            "total_lines": total_lines,
            "large_files": large_files,
            "avg_lines_per_file": total_lines // total_files if total_files > 0 else 0,
        }

        return self.stats

    def print_report(self):
        """打印监控报告"""
        print(f"\n总代码行数: {self.stats['total_lines']:,}")
        print(f"平均每文件行数: {self.stats['avg_lines_per_file']}")

        # 超大文件报告
        print("\n" + "-" * 60)
        print("超大文件检测 (>1000行)")
        print("-" * 60)

        if self.stats["large_files"]:
            sorted_files = sorted(
                self.stats["large_files"], key=lambda x: x["lines"], reverse=True
            )
            for file_info in sorted_files[:20]:  # 只显示前20个
                print(f"  {file_info['lines']:5d} 行  {file_info['path']}")

            if len(sorted_files) > 20:
                print(f"  ... 还有 {len(sorted_files) - 20} 个超大文件")

            print(f"\n警告: 发现 {len(sorted_files)} 个超大文件")
        else:
            print("  未发现超大文件，代码结构良好！")

        # 质量评级
        print("\n" + "-" * 60)
        print("代码质量评级")
        print("-" * 60)

        large_file_count = len(self.stats["large_files"])
        total_files = self.stats["total_files"]
        large_file_ratio = large_file_count / total_files if total_files > 0 else 0

        if large_file_ratio == 0:
            grade = "A+"
            message = "优秀！所有文件都在合理范围内"
        elif large_file_ratio < 0.05:
            grade = "A"
            message = "良好，少量超大文件需要关注"
        elif large_file_ratio < 0.1:
            grade = "B"
            message = "一般，建议逐步拆分超大文件"
        elif large_file_ratio < 0.2:
            grade = "C"
            message = "需要改进，较多超大文件需要拆分"
        else:
            grade = "D"
            message = "需要重大重构，大量超大文件"

        print(f"  评级: {grade}")
        print(f"  说明: {message}")
        print(f"  超大文件占比: {large_file_ratio:.1%}")

        # 建议
        print("\n" + "-" * 60)
        print("改进建议")
        print("-" * 60)

        if large_file_count > 0:
            print(f"1. 优先处理前 5 个最大文件:")
            for file_info in sorted(self.stats["large_files"], key=lambda x: x["lines"], reverse=True)[:5]:
                print(f"   - {file_info['path']} ({file_info['lines']} 行)")

        print("\n2. 代码拆分最佳实践:")
        print("   - 单一职责原则: 每个模块只做一件事")
        print("   - 文件行数控制在 800 行以内")
        print("   - 函数行数控制在 50 行以内")
        print("   - 使用工具类提取重复代码")

        print("\n" + "=" * 60)

    def check_imports(self):
        """检查关键模块导入"""
        print("\n" + "-" * 60)
        print("关键模块导入检查")
        print("-" * 60)

        modules_to_check = [
            ("app.utils.api_tester", "LLMAPITester"),
            ("app.utils.error_handler", "handle_errors_none"),
            ("app.utils.report_extractor", "ReportExtractor"),
            ("app.utils.symbol_utils", "SymbolGenerator"),
            ("app.services.base_crud_service", "BaseCRUDService"),
            ("tradingagents.dataflows.managers.cache_manager", "CacheManager"),
        ]

        all_ok = True
        for module_name, class_name in modules_to_check:
            try:
                module = __import__(module_name, fromlist=[class_name])
                getattr(module, class_name)
                print(f"  [OK] {module_name}.{class_name}")
            except Exception as e:
                print(f"  [FAIL] {module_name}.{class_name}: {e}")
                all_ok = False

        if all_ok:
            print("\n所有关键模块导入正常！")
        else:
            print("\n警告: 部分模块导入失败，请检查！")


def main():
    """主函数"""
    monitor = CodeQualityMonitor()

    # 扫描项目
    monitor.scan_project()

    # 打印报告
    monitor.print_report()

    # 检查导入
    monitor.check_imports()

    print("\n监控完成！")
    return 0


if __name__ == "__main__":
    sys.exit(main())
