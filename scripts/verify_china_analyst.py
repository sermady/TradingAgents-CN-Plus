# -*- coding: utf-8 -*-
"""
验证中国特色分析师默认启用修改
"""

import os
import sys

# 动态检测项目根目录，避免硬编码路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def check_defaults():
    """检查默认参数是否正确修改"""
    import re

    print("=" * 70)
    print("验证中国特色分析师默认启用")
    print("=" * 70)

    errors = []

    # 1. 检查 trading_graph.py
    print("\n1. 检查 tradingagents/graph/trading_graph.py")
    try:
        with open("tradingagents/graph/trading_graph.py", "r", encoding="utf-8") as f:
            content = f.read()
            # 使用正则表达式，忽略空格差异
            normalized = re.sub(r"\s+", "", content)
            if (
                'selected_analysts=["market","social","news","fundamentals","china"]'
                in normalized
            ):
                print("   [OK] 已包含 'china'")
            else:
                print("   [FAIL] 未包含 'china'")
                errors.append("trading_graph.py")
    except Exception as e:
        print(f"   [ERROR] {e}")
        errors.append("trading_graph.py")

    # 2. 检查 parallel_analysts.py
    print("\n2. 检查 tradingagents/graph/parallel_analysts.py")
    try:
        with open(
            "tradingagents/graph/parallel_analysts.py", "r", encoding="utf-8"
        ) as f:
            content = f.read()
            # 使用正则表达式，忽略空格差异
            normalized = re.sub(r"\s+", "", content)
            if (
                'selected_analysts=["market","social","news","fundamentals","china"]'
                in normalized
            ):
                print("   [OK] 已包含 'china'")
            else:
                print("   [FAIL] 未包含 'china'")
                errors.append("parallel_analysts.py")
    except Exception as e:
        print(f"   [ERROR] {e}")
        errors.append("parallel_analysts.py")

    # 3. 检查 app/models/analysis.py
    print("\n3. 检查 app/models/analysis.py")
    try:
        with open("app/models/analysis.py", "r", encoding="utf-8") as f:
            content = f.read()
            # 使用正则表达式，忽略空格差异
            normalized = re.sub(r"\s+", "", content)
            if '["market","fundamentals","news","social","china"]' in normalized:
                print("   [OK] 已包含 'china'")
            else:
                print("   [FAIL] 未包含 'china'")
                errors.append("analysis.py")
    except Exception as e:
        print(f"   [ERROR] {e}")
        errors.append("analysis.py")

    # 4. 运行时验证
    print("\n4. 运行时验证")
    try:
        # 验证模型默认值
        try:
            from app.models.analysis import AnalysisParameters
        except ImportError as ie:
            print(f"   [ERROR] 无法导入 AnalysisParameters: {ie}")
            print("   提示：请确保在正确的目录下运行脚本")
            print(f"   当前工作目录: {os.getcwd()}")
            print(f"   Python 路径: {sys.path[:3]}")  # 只显示前3个路径
            errors.append("import_error")
            raise

        params = AnalysisParameters()
        if "china" in params.selected_analysts:
            print("   [OK] AnalysisParameters 默认包含 'china'")
            print(f"   默认分析师: {params.selected_analysts}")
        else:
            print("   [FAIL] AnalysisParameters 默认不包含 'china'")
            print(f"   默认分析师: {params.selected_analysts}")
            errors.append("AnalysisParameters")
    except Exception as e:
        print(f"   [ERROR] {e}")
        if "import_error" not in errors:
            errors.append("runtime")

    print("\n" + "=" * 70)
    if not errors:
        print("[SUCCESS] 所有检查通过！中国特色分析师已默认启用")
    else:
        print(f"[FAIL] 发现 {len(errors)} 个错误")
        for err in errors:
            print(f"   - {err}")
    print("=" * 70)

    return len(errors) == 0


if __name__ == "__main__":
    import sys

    success = check_defaults()
    sys.exit(0 if success else 1)
