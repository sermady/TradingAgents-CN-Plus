#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行测试覆盖率分析脚本
"""

import subprocess
import sys
import os


def run_coverage_analysis():
    """运行测试并生成覆盖率报告"""

    # 确保 coverage 目录存在
    os.makedirs("coverage", exist_ok=True)

    # 运行单元测试并收集覆盖率
    cmd = [
        "python",
        "-m",
        "pytest",
        "tests/unit/",
        "--cov=tradingagents",
        "--cov=app",
        "--cov-report=term-missing",
        "--cov-report=html:coverage/html",
        "--cov-report=json:coverage/coverage-summary.json",
        "-v",
        "--tb=short",
    ]

    print("=" * 60)
    print("运行测试覆盖率分析...")
    print("=" * 60)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5分钟超时
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return result.returncode
    except subprocess.TimeoutExpired:
        print("测试运行超时（5分钟）")
        return 1
    except Exception as e:
        print(f"运行测试时出错: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run_coverage_analysis())
