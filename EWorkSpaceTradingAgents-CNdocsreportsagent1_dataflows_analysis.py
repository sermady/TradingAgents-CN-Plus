#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 1: 分析 tradingagents/dataflows/ 目录中未分析的大文件
"""

import ast
import os
from pathlib import Path
from collections import defaultdict

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
    
    # 统计函数和类
    functions = []
    classes = []
    imports = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_lines = node.end_lineno - node.lineno if node.end_lineno else 0
            functions.append({
                'name': node.name,
                'lines': func_lines,
                'node': node
            })
        elif isinstance(node, ast.ClassDef):
            class_lines = node.end_lineno - node.lineno if node.end_lineno else 0
            classes.append({
                'name': node.name,
                'lines': class_lines,
                'node': node
            })
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(ast.dump(node))
    
    return {
        'filepath': filepath,
        'line_count': line_count,
        'functions': functions,
        'classes': classes,
        'imports': imports,
        'content': content
    }

def find_duplicate_patterns(files_data):
    """查找重复代码模式"""
    patterns = defaultdict(list)
    
    for data in files_data:
        content = data['content']
        lines = content.split('\n')
        
        # 查找常见的重复模式
        for i, line in enumerate(lines):
            line = line.strip()
            # 查找异常处理模式
            if 'try:' in line:
                patterns['try_blocks'].append((data['filepath'], i+1))
            # 查找日志记录
            if 'logger.' in line or 'logging.' in line:
                patterns['logging'].append((data['filepath'], i+1, line))
            # 查找配置读取
            if 'os.getenv' in line or 'os.environ' in line:
                patterns['config_read'].append((data['filepath'], i+1, line))
            # 查找事件循环处理
            if 'asyncio.get_event_loop' in line or 'asyncio.new_event_loop' in line:
                patterns['asyncio_loop'].append((data['filepath'], i+1))
    
    return patterns

def main():
    base_path = Path('E:/WorkSpace/TradingAgents-CN/tradingagents/dataflows')
    
    # 重点分析的文件
    target_files = [
        'providers/china/tushare.py',
        'providers/china/akshare.py',
        'providers/china/baostock.py',
        'providers/hk/improved_hk.py',
        'providers/hk/hk_stock.py',
        'providers/us/optimized.py',
        'news/realtime_news.py',
        'cache/file_cache.py',
        'cache/db_cache.py',
    ]
    
    files_data = []
    for rel_path in target_files:
        filepath = base_path / rel_path
        if filepath.exists():
            data = analyze_file(filepath)
            if data:
                files_data.append(data)
                print(f"\n{'='*60}")
                print(f"文件: {rel_path}")
                print(f"总行数: {data['line_count']}")
                print(f"类数量: {len(data['classes'])}")
                print(f"函数数量: {len(data['functions'])}")
                
                # 显示最大的函数
                sorted_funcs = sorted(data['functions'], key=lambda x: x['lines'], reverse=True)[:5]
                print("\n最大的5个函数:")
                for func in sorted_funcs:
                    print(f"  - {func['name']}: {func['lines']} 行")
    
    # 查找重复模式
    patterns = find_duplicate_patterns(files_data)
    
    print("\n" + "="*60)
    print("重复模式分析:")
    print("="*60)
    
    for pattern_name, occurrences in patterns.items():
        print(f"\n{pattern_name}: {len(occurrences)} 次出现")
        if len(occurrences) <= 10:
            for occ in occurrences[:5]:
                print(f"  - {occ}")

if __name__ == '__main__':
    main()
