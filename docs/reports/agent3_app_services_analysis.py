#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 3: 分析 app/services/ 目录
"""

import ast
from pathlib import Path

def analyze_file(filepath):
    """分析单个Python文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    line_count = len(lines)

    try:
        tree = ast.parse(content)
    except:
        return None

    functions = []
    classes = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_lines = node.end_lineno - node.lineno if node.end_lineno else 0
            functions.append({
                'name': node.name,
                'lines': func_lines,
            })
        elif isinstance(node, ast.ClassDef):
            class_lines = node.end_lineno - node.lineno if node.end_lineno else 0
            classes.append({
                'name': node.name,
                'lines': class_lines,
            })

    return {
        'filepath': filepath,
        'line_count': line_count,
        'functions': functions,
        'classes': classes,
        'content': content
    }

def main():
    base_path = Path('E:/WorkSpace/TradingAgents-CN/app/services')

    # 获取所有服务文件
    service_files = list(base_path.glob('*.py'))
    service_files = [f for f in service_files if f.name != '__init__.py']

    # 添加子目录中的文件
    for subdir in ['data_sources', 'database', 'basics_sync', 'analysis']:
        subdir_path = base_path / subdir
        if subdir_path.exists():
            service_files.extend(subdir_path.glob('*.py'))

    files_data = []
    for filepath in service_files:
        data = analyze_file(filepath)
        if data and data['line_count'] > 200:  # 只分析大文件
            files_data.append(data)
            print(f"\n{'='*60}")
            print(f"文件: {filepath.name}")
            print(f"总行数: {data['line_count']}")
            print(f"类数量: {len(data['classes'])}")
            print(f"函数数量: {len(data['functions'])}")

            sorted_funcs = sorted(data['functions'], key=lambda x: x['lines'], reverse=True)[:5]
            print("\n最大的5个函数:")
            for func in sorted_funcs:
                print(f"  - {func['name']}: {func['lines']} 行")

if __name__ == '__main__':
    main()
