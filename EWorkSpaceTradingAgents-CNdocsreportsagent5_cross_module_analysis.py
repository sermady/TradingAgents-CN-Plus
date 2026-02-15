#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 5: 跨模块重复代码分析
"""

import ast
from pathlib import Path
from collections import defaultdict
import re

def extract_function_signature(content, func_node):
    """提取函数签名用于比较"""
    lines = content.split('\n')
    func_lines = lines[func_node.lineno-1:func_node.end_lineno if func_node.end_lineno else func_node.lineno]
    
    # 提取函数体（去掉具体变量名）
    body = '\n'.join(func_lines[1:])  # 跳过定义行
    # 归一化：去掉注释、空行、具体值
    body = re.sub(r'#.*', '', body)
    body = re.sub(r'"""[\s\S]*?"""', '', body)
    body = re.sub(r"'''[\s\S]*?'''", '', body)
    body = re.sub(r'\s+', ' ', body)
    return body[:500]  # 限制长度

def find_common_patterns(directory):
    """查找跨文件的共同模式"""
    patterns = defaultdict(list)
    
    for py_file in directory.rglob('*.py'):
        if '__pycache__' in str(py_file):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                
                # 查找常见的重复模式
                if 'async def ' in line and 'get_' in line:
                    patterns['async_getters'].append((str(py_file.relative_to(directory.parent)), i+1, line_stripped[:80]))
                elif 'def ' in line and 'validate_' in line:
                    patterns['validators'].append((str(py_file.relative_to(directory.parent)), i+1, line_stripped[:80]))
                elif 'try:' in line:
                    patterns['try_blocks'].append(str(py_file.relative_to(directory.parent)))
                elif 'except' in line and 'Exception' in line:
                    patterns['broad_exceptions'].append((str(py_file.relative_to(directory.parent)), i+1))
                elif 'logger.' in line or 'self.logger' in line:
                    patterns['logging'].append(str(py_file.relative_to(directory.parent)))
                elif 'MongoClient' in line or 'redis' in line.lower():
                    patterns['db_connections'].append(str(py_file.relative_to(directory.parent)))
                    
        except Exception as e:
            pass
    
    return patterns

def main():
    base_path = Path('E:/WorkSpace/TradingAgents-CN')
    
    print("="*60)
    print("跨模块重复代码分析")
    print("="*60)
    
    patterns = find_common_patterns(base_path)
    
    print("\n1. 异步获取函数 (async def get_*):")
    files_with_async_getters = set()
    for occ in patterns['async_getters']:
        files_with_async_getters.add(occ[0])
    print(f"   涉及 {len(files_with_async_getters)} 个文件, {len(patterns['async_getters'])} 处")
    for f in list(files_with_async_getters)[:5]:
        print(f"   - {f}")
    
    print("\n2. 验证函数 (def validate_*):")
    files_with_validators = set()
    for occ in patterns['validators']:
        files_with_validators.add(occ[0])
    print(f"   涉及 {len(files_with_validators)} 个文件, {len(patterns['validators'])} 处")
    
    print("\n3. Try-Except 块:")
    files_with_try = set(patterns['try_blocks'])
    print(f"   涉及 {len(files_with_try)} 个文件")
    
    print("\n4. 宽泛的异常捕获 (except Exception):")
    print(f"   发现 {len(patterns['broad_exceptions'])} 处")
    for occ in patterns['broad_exceptions'][:5]:
        print(f"   - {occ[0]}:{occ[1]}")
    
    print("\n5. 日志记录:")
    files_with_logging = set(patterns['logging'])
    print(f"   涉及 {len(files_with_logging)} 个文件")
    
    print("\n6. 数据库连接:")
    files_with_db = set(patterns['db_connections'])
    print(f"   涉及 {len(files_with_db)} 个文件")
    for f in files_with_db:
        print(f"   - {f}")

if __name__ == '__main__':
    main()
