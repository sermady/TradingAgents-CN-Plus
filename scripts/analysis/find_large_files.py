# -*- coding: utf-8 -*-
"""查找项目中超过指定行数的Python文件"""

import os
from pathlib import Path


def count_lines(filepath: Path) -> int:
    """计算文件行数"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def find_large_files(root_dir: Path, min_lines: int = 1500) -> list[tuple[Path, int]]:
    """查找超过min_lines行的Python文件"""
    large_files = []

    for py_file in root_dir.rglob('*.py'):
        # 跳过虚拟环境和缓存目录
        if any(part in py_file.parts for part in ['venv', '__pycache__', '.git', 'node_modules']):
            continue

        line_count = count_lines(py_file)
        if line_count > min_lines:
            large_files.append((py_file, line_count))

    # 按行数排序
    large_files.sort(key=lambda x: x[1], reverse=True)
    return large_files


if __name__ == '__main__':
    import sys

    # 设置 UTF-8 编码输出
    sys.stdout.reconfigure(encoding='utf-8')

    root = Path(__file__).parent.parent.parent

    print('Scanning for large files...')
    large_files = find_large_files(root, min_lines=1500)

    if not large_files:
        print('No files over 1500 lines found!')
    else:
        print(f'\nFound {len(large_files)} large files:\n')
        for filepath, line_count in large_files[:20]:  # Show top 20
            # Calculate relative path
            rel_path = filepath.relative_to(root)
            print(f'  {line_count:5d} lines  {rel_path}')

        print(f'\nTotal: {len(large_files)} files over 1500 lines')
