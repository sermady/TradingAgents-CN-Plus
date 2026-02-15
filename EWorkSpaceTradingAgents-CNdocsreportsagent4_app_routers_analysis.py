#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 4: 分析 app/routers/ 和 app/worker/ 目录
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
    base_path = Path('E:/WorkSpace/TradingAgents-CN/app')
    
    # 分析 routers
    print("="*60)
    print("分析 app/routers/ 目录")
    print("="*60)
    
    router_files = list((base_path / 'routers').glob('*.py'))
    router_files = [f for f in router_files if f.name != '__init__.py']
    
    for filepath in sorted(router_files, key=lambda x: x.stat().st_size, reverse=True)[:10]:
        data = analyze_file(filepath)
        if data:
            print(f"\n文件: {filepath.name} - {data['line_count']} 行")
            sorted_funcs = sorted(data['functions'], key=lambda x: x['lines'], reverse=True)[:3]
            for func in sorted_funcs:
                print(f"  - {func['name']}: {func['lines']} 行")
    
    # 分析 worker
    print("\n" + "="*60)
    print("分析 app/worker/ 目录")
    print("="*60)
    
    worker_files = list((base_path / 'worker').glob('*.py'))
    for filepath in worker_files:
        data = analyze_file(filepath)
        if data:
            print(f"\n文件: {filepath.name} - {data['line_count']} 行")
            sorted_funcs = sorted(data['functions'], key=lambda x: x['lines'], reverse=True)[:3]
            for func in sorted_funcs:
                print(f"  - {func['name']}: {func['lines']} 行")

if __name__ == '__main__':
    main()
