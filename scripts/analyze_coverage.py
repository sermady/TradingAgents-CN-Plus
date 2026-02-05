#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析覆盖率报告"""

import json

# 读取覆盖率报告
with open("coverage.json", "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()
    cov = json.loads(content)

# 过滤 app/core 目录下的文件
core_files = []
for file_path in cov["files"].keys():
    if "app" in file_path and "core" in file_path:
        core_files.append(file_path)

print("=== app/core/ Coverage Analysis ===\n")

# 按覆盖率排序
sorted_files = []
for file_path in core_files:
    summary = cov["files"][file_path]["summary"]
    file_name = file_path.replace("\\", "/").split("/")[-1]
    sorted_files.append((file_name, summary, file_path))

sorted_files.sort(key=lambda x: x[1]["percent_covered"])

total_statements = 0
total_covered = 0

for file_name, summary, file_path in sorted_files:
    num_statements = summary["num_statements"]
    covered = summary["covered_lines"]
    percent = summary["percent_covered"]
    total_statements += num_statements
    total_covered += covered

    status = "LOW" if percent < 60 else "MED" if percent < 80 else "HIGH"
    print(
        f"{status:6s} {file_name:35s} {percent:5.1f}% ({covered:4d}/{num_statements:4d})"
    )

print(
    f"\nTotal: {total_covered}/{total_statements} = {100 * total_covered / total_statements:.1f}%"
)

print("\n=== Files below 80% coverage ===\n")
below_80 = []
for file_name, summary, file_path in sorted_files:
    percent = summary["percent_covered"]
    if percent < 80:
        below_80.append((file_name, percent, file_path))

for file_name, percent, file_path in below_80:
    file_data = cov["files"][file_path]
    missing = file_data["missing_lines"]
    print(f"[LOW] {file_name} ({percent:.1f}%) - {len(missing)} lines missing")
    if missing:
        print(f"   Missing line ranges (first 10): {sorted(missing)[:10]}")
    print()

# 保存低于80%的文件列表用于生成测试
print("\n=== Files needing more tests ===")
for file_name, percent, file_path in below_80:
    print(file_name)
