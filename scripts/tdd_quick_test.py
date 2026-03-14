#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TDD 快速测试脚本

用于快速运行测试和生成覆盖率报告。

用法:
    python scripts/tdd_quick_test.py              # 快速测试（核心模块）
    python scripts/tdd_quick_test.py --coverage   # 生成覆盖率报告
    python scripts/tdd_quick_test.py --all        # 运行所有单元测试
"""

import subprocess
import sys
import argparse
from pathlib import Path


def quick_test() -> int:
    """快速测试 - 运行核心模块测试"""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/unit/core/",
        "tests/unit/utils/",
        "-v",
        "--tb=short",
        "-x",  # 首次失败即停止
    ]
    return subprocess.run(cmd).returncode


def run_with_coverage() -> int:
    """运行测试并生成覆盖率报告"""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-m",
        "unit",
        "-v",
        "--cov=tradingagents",
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--tb=short",
        "--maxfail=5",
    ]

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("📊 HTML覆盖率报告: htmlcov/index.html")
        print("=" * 60)

    return result.returncode


def run_all_unit_tests() -> int:
    """运行所有单元测试"""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-m",
        "unit",
        "-v",
        "--tb=short",
        "--maxfail=10",
    ]
    return subprocess.run(cmd).returncode


def main():
    parser = argparse.ArgumentParser(description="TDD 快速测试脚本")
    parser.add_argument("--coverage", "-c", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--all", "-a", action="store_true", help="运行所有单元测试")

    args = parser.parse_args()

    # 确保在项目根目录运行
    project_root = Path(__file__).parent.parent
    import os

    os.chdir(project_root)

    if args.coverage:
        exit_code = run_with_coverage()
    elif args.all:
        exit_code = run_all_unit_tests()
    else:
        exit_code = quick_test()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
