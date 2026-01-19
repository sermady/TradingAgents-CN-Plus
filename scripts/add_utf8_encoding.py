# -*- coding: utf-8 -*-
"""
批量添加UTF-8编码声明到Python文件
"""

import os
import re
from pathlib import Path


def should_add_encoding(file_path: str) -> bool:
    """判断文件是否需要添加UTF-8编码声明"""
    # 跳过特定目录
    skip_dirs = [
        "node_modules",
        "frontend",
        ".git",
        "__pycache__",
        "tests",
        ".venv",
        "venv",
    ]
    for skip_dir in skip_dirs:
        if skip_dir in file_path:
            return False

    # 只处理.py文件
    if not file_path.endswith(".py"):
        return False

    # 检查是否已有UTF-8声明
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            first_line = f.readline()
            # 检查常见的编码声明格式
            if "coding:" in first_line or "coding=" in first_line:
                return False
    except:
        pass

    return True


def add_encoding_declaration(file_path: str) -> bool:
    """为单个文件添加UTF-8编码声明"""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # 检查是否已经有shebang
        has_shebang = content.startswith("#!")
        lines = content.split("\n")

        if has_shebang:
            # 在shebang后添加
            lines.insert(1, "# -*- coding: utf-8 -*-")
        else:
            # 在第一行添加
            lines.insert(0, "# -*- coding: utf-8 -*-")

        # 写回文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return True
    except Exception as e:
        print(f"[ERROR] Failed to process {file_path}: {e}")
        return False


def main():
    """主函数"""
    print("=" * 70)
    print("UTF-8 Encoding Declaration Adder")
    print("=" * 70)

    files_processed = 0
    files_updated = 0

    # 遍历所有Python文件
    for root, dirs, files in os.walk(".", topdown=True):
        # 跳过特定目录
        dirs[:] = [
            d
            for d in dirs
            if d
            not in ["node_modules", ".git", "__pycache__", "venv", ".venv", "tests"]
        ]

        for file in files:
            file_path = os.path.join(root, file)

            if should_add_encoding(file_path):
                files_processed += 1

                if add_encoding_declaration(file_path):
                    files_updated += 1
                    print(f"[UPDATE] {file_path}")

    print("=" * 70)
    print(f"Summary:")
    print(f"  Files processed: {files_processed}")
    print(f"  Files updated: {files_updated}")
    print(f"  Files skipped: {files_processed - files_updated}")
    print("=" * 70)
    print("[SUCCESS] UTF-8 encoding declaration batch update completed!")


if __name__ == "__main__":
    main()
