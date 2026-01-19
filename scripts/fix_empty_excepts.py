# -*- coding: utf-8 -*-
"""
批量修复空except块
替换except:或except Exception:为带日志记录的版本
"""

import os
import re
from pathlib import Path


def should_fix_empty_except(file_path: str) -> bool:
    """判断文件是否需要修复"""
    # 跳过特定目录
    skip_dirs = ["node_modules", "frontend", ".git", "__pycache__", "tests"]
    for skip_dir in skip_dirs:
        if skip_dir in file_path:
            return False

    # 只处理.py文件
    if not file_path.endswith(".py"):
        return False

    return True


def fix_empty_except_in_file(file_path: str) -> int:
    """修复单个文件中的空except块，返回修复数量"""
    fixes = 0

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")

        fixed_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # 检测空except块模式
            # 模式1: except:
            if stripped == "except:":
                # 检查下一行是否是pass或空
                if i + 1 < len(lines):
                    next_line_stripped = lines[i + 1].strip()
                    if next_line_stripped == "pass" or next_line_stripped == "":
                        # 添加日志记录
                        indent = len(line) - len(line.lstrip())
                        indent_str = " " * indent
                        fixed_lines.append(f"{indent_str}except Exception as e:")
                        fixed_lines.append(
                            f'{indent_str}    logger.error(f"Error in {file_path}: {{e}}")'
                        )
                        if next_line_stripped == "":
                            fixed_lines.append(f"{indent_str}    pass")
                        i += 2  # 跳过下一行
                        fixes += 1
                        continue

            # 模式2: except Exception:
            elif stripped == "except Exception:":
                # 检查下一行是否是pass或空
                if i + 1 < len(lines):
                    next_line_stripped = lines[i + 1].strip()
                    if next_line_stripped == "pass" or next_line_stripped == "":
                        # 添加日志记录
                        indent = len(line) - len(line.lstrip())
                        indent_str = " " * indent
                        fixed_lines.append(f"{indent_str}except Exception as e:")
                        fixed_lines.append(
                            f'{indent_str}    logger.error(f"Error in {file_path}: {{e}}")'
                        )
                        if next_line_stripped == "":
                            fixed_lines.append(f"{indent_str}    pass")
                        i += 2
                        fixes += 1
                        continue

            fixed_lines.append(line)
            i += 1

        if fixes > 0:
            # 写回文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(fixed_lines))
            print(f"[FIXED] {file_path}: {fixes} exception(s)")

        return fixes

    except Exception as e:
        print(f"[ERROR] Failed to process {file_path}: {e}")
        return 0


def main():
    """主函数"""
    print("=" * 70)
    print("Empty Exception Block Fixer")
    print("=" * 70)

    total_fixes = 0
    processed_files = 0

    # 遍历所有Python文件
    for root, dirs, files in os.walk(".", topdown=True):
        # 跳过特定目录
        dirs[:] = [d for d in dirs if d not in ["node_modules", ".git", "__pycache__"]]

        for file in files:
            file_path = os.path.join(root, file)

            if should_fix_empty_except(file_path):
                fixes = fix_empty_except_in_file(file_path)
                if fixes > 0:
                    total_fixes += fixes
                    processed_files += 1

    print("=" * 70)
    print(f"Summary:")
    print(f"  Processed files: {processed_files}")
    print(f"  Total exceptions fixed: {total_fixes}")
    print("=" * 70)


if __name__ == "__main__":
    main()
