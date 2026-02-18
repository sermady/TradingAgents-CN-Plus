# -*- coding: utf-8 -*-
"""
Stock Sync Exception Simplifier

Specifically designed for stock_sync.py structure.
Simplifies 3 top-level try-except blocks:
1. sync_single_stock (lines ~138-556)
2. sync_batch_stocks (lines ~574-771)
3. get_sync_status (lines ~781-822)
"""

import re
import sys
from pathlib import Path


def simplify_stock_sync(file_path: str):
    """Simplify stock_sync.py exception handling"""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')

    print(f"Original: {len(lines)} lines")

    # Create backup
    backup_path = file_path + '.backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Backup: {backup_path}")

    # Process the 3 functions
    # We'll work backwards to avoid line number shifts

    # 1. get_sync_status (simplest - no nested try)
    lines = simplify_get_sync_status(lines)

    # 2. sync_batch_stocks (has nested try)
    lines = simplify_sync_batch_stocks(lines)

    # 3. sync_single_stock (has nested try)
    lines = simplify_sync_single_stock(lines)

    # Write back
    new_content = '\n'.join(lines)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"Modified: {len(lines)} lines")
    print(f"Reduction: ~{len(content.split(chr(10))) - len(lines)} lines")
    print("OK: File simplified successfully")


def simplify_sync_single_stock(lines):
    """Simplify sync_single_stock function"""
    # Find the function
    func_start = None
    try_line = None
    except_line = None
    func_end = None

    for i, line in enumerate(lines):
        if '@router.post("/single")' in line:
            # Find async def line
            for j in range(i, min(i+10, len(lines))):
                if 'async def sync_single_stock' in lines[j]:
                    func_start = j
                    break

        if func_start and try_line is None:
            # Look for try: after function docstring
            if line.strip() == 'try:':
                indent = len(line) - len(line.lstrip())
                if indent == 4:  # Function-level try
                    try_line = i

        if try_line and except_line is None:
            # Look for except Exception as e:
            if 'except Exception as e:' in line:
                indent = len(line) - len(line.lstrip())
                if indent == 4:  # Same level as try
                    except_line = i

        if except_line and func_end is None:
            # Find the end (next line at function level or end of function)
            if line.strip() and not line.strip().startswith('#'):
                indent = len(line) - len(line.lstrip())
                if indent == 0 and i > except_line:
                    # Check if it's a new function or decorator
                    if line.strip().startswith('@') or line.strip().startswith('async def') or line.strip().startswith('def '):
                        func_end = i
                        break

    if func_end is None:
        func_end = len(lines) - 1

    print(f"  sync_single_stock: try@{try_line}, except@{except_line}, end@{func_end}")

    if try_line is None or except_line is None:
        print("  Warning: Could not find try/except")
        return lines

    # Remove try line and except block, reduce indentation of body
    result = lines[:try_line]  # Before try

    # Add try body with reduced indentation
    try_body = lines[try_line + 1:except_line]
    for line in try_body:
        if line.strip():
            # Reduce indentation by 4 spaces
            original_indent = len(line) - len(line.lstrip())
            if original_indent >= 8:  # Was inside try
                new_indent = original_indent - 4
                result.append(' ' * new_indent + line.lstrip())
            else:
                result.append(line)
        else:
            result.append(line)

    # Skip except line (lines[except_line])
    # Add rest of function (after except block)
    # Find where except block ends (next line at function level)
    except_end = except_line + 1
    for i in range(except_line + 1, min(func_end, len(lines))):
        if lines[i].strip():
            indent = len(lines[i]) - len(lines[i].lstrip())
            if indent <= 4:  # Function level or less
                except_end = i
                break
        except_end = i

    result.extend(lines[except_end:])

    return result


def simplify_sync_batch_stocks(lines):
    """Simplify sync_batch_stocks function"""
    # Similar logic
    func_start = None
    try_line = None
    except_line = None
    func_end = None

    for i, line in enumerate(lines):
        if '@router.post("/batch")' in line:
            for j in range(i, min(i+10, len(lines))):
                if 'async def sync_batch_stocks' in lines[j]:
                    func_start = j
                    break

        if func_start and try_line is None:
            if line.strip() == 'try:':
                indent = len(line) - len(line.lstrip())
                if indent == 4:
                    # Make sure it's after batch function
                    if i > func_start:
                        try_line = i

        if try_line and except_line is None:
            if 'except Exception as e:' in line:
                indent = len(line) - len(line.lstrip())
                if indent == 4 and i > try_line:
                    except_line = i

    # Find function end
    if except_line:
        for i in range(except_line + 5, len(lines)):
            if lines[i].strip().startswith('@router.get'):
                func_end = i
                break

    if func_end is None:
        func_end = len(lines) - 1

    print(f"  sync_batch_stocks: try@{try_line}, except@{except_line}, end@{func_end}")

    if try_line is None or except_line is None:
        print("  Warning: Could not find try/except")
        return lines

    # Same simplification logic
    result = lines[:try_line]

    try_body = lines[try_line + 1:except_line]
    for line in try_body:
        if line.strip():
            original_indent = len(line) - len(line.lstrip())
            if original_indent >= 8:
                new_indent = original_indent - 4
                result.append(' ' * new_indent + line.lstrip())
            else:
                result.append(line)
        else:
            result.append(line)

    # Find except block end
    except_end = except_line + 1
    for i in range(except_line + 1, min(func_end, len(lines))):
        if lines[i].strip():
            indent = len(lines[i]) - len(lines[i].lstrip())
            if indent <= 4:
                except_end = i
                break
        except_end = i

    result.extend(lines[except_end:])

    return result


def simplify_get_sync_status(lines):
    """Simplify get_sync_status function (no nested try)"""
    func_start = None
    try_line = None
    except_line = None

    for i, line in enumerate(lines):
        if '@router.get("/status/{symbol}")' in line:
            for j in range(i, min(i+10, len(lines))):
                if 'async def get_sync_status' in lines[j]:
                    func_start = j
                    break

        if func_start and try_line is None:
            if line.strip() == 'try:':
                indent = len(line) - len(line.lstrip())
                if indent == 4 and i > func_start:
                    try_line = i

        if try_line and except_line is None:
            if 'except Exception as e:' in line:
                indent = len(line) - len(line.lstrip())
                if indent == 4 and i > try_line:
                    except_line = i

    print(f"  get_sync_status: try@{try_line}, except@{except_line}")

    if try_line is None or except_line is None:
        print("  Warning: Could not find try/except")
        return lines

    # Simplify: remove try line and except block, reduce body indent
    result = lines[:try_line]

    try_body = lines[try_line + 1:except_line]
    for line in try_body:
        if line.strip():
            original_indent = len(line) - len(line.lstrip())
            if original_indent >= 8:
                new_indent = original_indent - 4
                result.append(' ' * new_indent + line.lstrip())
            else:
                result.append(line)
        else:
            result.append(line)

    # Find end of except block (should be end of function)
    except_end = except_line + 1
    for i in range(except_line + 1, len(lines)):
        if lines[i].strip():
            indent = len(lines[i]) - len(lines[i].lstrip())
            if indent <= 4:
                except_end = i
                break
        except_end = i

    result.extend(lines[except_end:])

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python simplify_stock_sync.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    try:
        simplify_stock_sync(file_path)
        print("\nNext: Run import test")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
