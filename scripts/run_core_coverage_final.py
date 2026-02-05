#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终覆盖率测试运行脚本
"""

import subprocess
import sys


def run_final_coverage():
    """运行最终覆盖率测试"""

    print("=" * 80)
    print("app/core/ 模块最终覆盖率测试")
    print("=" * 80)

    # 运行覆盖率测试
    cmd = [
        "python",
        "-m",
        "pytest",
        "tests/unit/core/",
        "--cov=app.core",
        "--cov-report=term",
        "--cov-report=html:coverage/core_final",
        "-q",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    return result.returncode


if __name__ == "__main__":
    sys.exit(run_final_coverage())
