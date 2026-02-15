#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 2: 分析 tradingagents/agents/ 和 graph/ 目录
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
    base_path = Path('E:/WorkSpace/TradingAgents-CN/tradingagents')
    
    target_files = [
        'agents/utils/agent_utils.py',
        'agents/utils/google_tool_handler.py',
        'agents/utils/memory.py',
        'agents/trader/trader.py',
        'graph/trading_graph.py',
        'graph/data_coordinator.py',
        'graph/parallel_analysts_v2.py',
        'utils/stock_validator.py',
        'utils/prompt_builder.py',
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
                
                sorted_funcs = sorted(data['functions'], key=lambda x: x['lines'], reverse=True)[:5]
                print("\n最大的5个函数:")
                for func in sorted_funcs:
                    print(f"  - {func['name']}: {func['lines']} 行")

if __name__ == '__main__':
    main()
