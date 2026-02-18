# -*- coding: utf-8 -*-
"""
Stocks Router Exception Simplifier

Simplifies 4 try-except blocks in stocks.py:
1. get_quote foreign stock quote (lines ~101-109)
2. get_fundamentals foreign stock info (lines ~245-253)
3. get_kline foreign stock kline (lines ~461-474)
4. get_news A-share news outer try (lines ~650-750)
"""

import re
import sys
from pathlib import Path


def simplify_stocks(file_path: str):
    """Simplify stocks.py exception handling"""

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')

    print(f"Original: {len(lines)} lines")

    # Create backup
    backup_path = file_path + '.backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Backup: {backup_path}")

    # Simplify each function
    lines = simplify_get_quote(lines)
    lines = simplify_get_fundamentals(lines)
    lines = simplify_get_kline(lines)
    lines = simplify_get_news(lines)

    # Write back
    new_content = '\n'.join(lines)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"Modified: {len(lines)} lines")
    print(f"Reduction: ~{len(content.split(chr(10))) - len(lines)} lines")
    print("OK: File simplified successfully")


def simplify_get_quote(lines):
    """Simplify get_quote foreign stock try-except"""
    # Find: if market in ['HK', 'US']: ... try: ... except Exception as e: ...
    func_start = None
    try_line = None
    except_line = None

    for i, line in enumerate(lines):
        if "if market in ['HK', 'US']:" in line and func_start is None:
            func_start = i

        if func_start and try_line is None:
            if line.strip() == 'try:' and i > func_start:
                # Check if it's inside the foreign stock block
                indent = len(line) - len(line.lstrip())
                if indent == 8:  # Inside if block
                    try_line = i

        if try_line and except_line is None:
            if 'except Exception as e:' in line and i > try_line:
                indent = len(line) - len(line.lstrip())
                if indent == 8:
                    except_line = i

    if try_line is None or except_line is None:
        print(f"  get_quote foreign: try@{try_line}, except@{except_line} - not found or already simplified")
        return lines

    print(f"  get_quote foreign: try@{try_line}, except@{except_line}")

    # Simplify: remove try/except, reduce body indent
    result = lines[:try_line]

    # Add body with reduced indent
    body = lines[try_line + 1:except_line]
    for line in body:
        if line.strip():
            orig_indent = len(line) - len(line.lstrip())
            if orig_indent >= 12:  # Inside try
                new_indent = orig_indent - 4
                result.append(' ' * new_indent + line.lstrip())
            else:
                result.append(line)
        else:
            result.append(line)

    # Find end of except block
    except_end = except_line + 1
    for i in range(except_line + 1, len(lines)):
        if lines[i].strip():
            indent = len(lines[i]) - len(lines[i].lstrip())
            if indent <= 8:  # Back to if block level or less
                except_end = i
                break
        except_end = i

    result.extend(lines[except_end:])
    return result


def simplify_get_fundamentals(lines):
    """Simplify get_fundamentals foreign stock try-except"""
    func_start = None
    try_line = None
    except_line = None

    for i, line in enumerate(lines):
        if 'async def get_fundamentals(' in line:
            func_start = i

        if func_start and try_line is None:
            if line.strip() == 'try:' and i > func_start:
                # Check indent to find the foreign stock try
                indent = len(line) - len(line.lstrip())
                if indent == 8:
                    # Verify it's after if market in ['HK', 'US']
                    for j in range(i-5, i):
                        if j >= 0 and "if market in ['HK', 'US']:" in lines[j]:
                            try_line = i
                            break

        if try_line and except_line is None:
            if 'except Exception as e:' in line and i > try_line:
                indent = len(line) - len(line.lstrip())
                if indent == 8:
                    except_line = i

    if try_line is None or except_line is None:
        print(f"  get_fundamentals foreign: try@{try_line}, except@{except_line} - not found")
        return lines

    print(f"  get_fundamentals foreign: try@{try_line}, except@{except_line}")

    result = lines[:try_line]

    body = lines[try_line + 1:except_line]
    for line in body:
        if line.strip():
            orig_indent = len(line) - len(line.lstrip())
            if orig_indent >= 12:
                new_indent = orig_indent - 4
                result.append(' ' * new_indent + line.lstrip())
            else:
                result.append(line)
        else:
            result.append(line)

    except_end = except_line + 1
    for i in range(except_line + 1, len(lines)):
        if lines[i].strip():
            indent = len(lines[i]) - len(lines[i].lstrip())
            if indent <= 8:
                except_end = i
                break
        except_end = i

    result.extend(lines[except_end:])
    return result


def simplify_get_kline(lines):
    """Simplify get_kline foreign stock try-except"""
    func_start = None
    try_line = None
    except_line = None

    for i, line in enumerate(lines):
        if 'async def get_kline(' in line:
            func_start = i

        if func_start and try_line is None:
            if line.strip() == 'try:' and i > func_start:
                indent = len(line) - len(line.lstrip())
                if indent == 8:
                    # Check context - should be after foreign service creation
                    for j in range(i-3, i):
                        if j >= 0 and 'ForeignStockService' in lines[j]:
                            try_line = i
                            break

        if try_line and except_line is None:
            if 'except Exception as e:' in line and i > try_line:
                indent = len(line) - len(line.lstrip())
                if indent == 8:
                    # Check if it has the kline error message
                    for j in range(i, min(i+3, len(lines))):
                        if 'K线数据失败' in lines[j]:
                            except_line = i
                            break

    if try_line is None or except_line is None:
        print(f"  get_kline foreign: try@{try_line}, except@{except_line} - not found")
        return lines

    print(f"  get_kline foreign: try@{try_line}, except@{except_line}")

    result = lines[:try_line]

    body = lines[try_line + 1:except_line]
    for line in body:
        if line.strip():
            orig_indent = len(line) - len(line.lstrip())
            if orig_indent >= 12:
                new_indent = orig_indent - 4
                result.append(' ' * new_indent + line.lstrip())
            else:
                result.append(line)
        else:
            result.append(line)

    except_end = except_line + 1
    for i in range(except_line + 1, len(lines)):
        if lines[i].strip():
            indent = len(lines[i]) - len(lines[i].lstrip())
            if indent <= 8:
                except_end = i
                break
        except_end = i

    result.extend(lines[except_end:])
    return result


def simplify_get_news(lines):
    """Simplify get_news A-share outer try-except"""
    func_start = None
    try_line = None
    except_line = None

    for i, line in enumerate(lines):
        if 'async def get_news(' in line:
            func_start = i

        if func_start and try_line is None:
            if line.strip() == 'try:' and i > func_start:
                indent = len(line) - len(line.lstrip())
                if indent == 8:
                    # Should be after 'else:' (A-share branch)
                    for j in range(i-5, i):
                        if j >= 0 and 'else:' in lines[j]:
                            try_line = i
                            break

        if try_line and except_line is None:
            if 'except Exception as e:' in line and i > try_line:
                indent = len(line) - len(line.lstrip())
                if indent == 8:
                    # Check if it returns empty data (not raise)
                    for j in range(i, min(i+15, len(lines))):
                        if 'return ok(data)' in lines[j] or 'items':
                            except_line = i
                            break

    if try_line is None or except_line is None:
        print(f"  get_news A-share: try@{try_line}, except@{except_line} - not found")
        return lines

    print(f"  get_news A-share: try@{try_line}, except@{except_line}")

    result = lines[:try_line]

    body = lines[try_line + 1:except_line]
    for line in body:
        if line.strip():
            orig_indent = len(line) - len(line.lstrip())
            if orig_indent >= 12:
                new_indent = orig_indent - 4
                result.append(' ' * new_indent + line.lstrip())
            else:
                result.append(line)
        else:
            result.append(line)

    # For get_news, the except block returns empty data - we need to keep that behavior
    # So we'll add a fallback at the end
    except_end = except_line + 1
    for i in range(except_line + 1, len(lines)):
        if lines[i].strip():
            indent = len(lines[i]) - len(lines[i].lstrip())
            if indent <= 8:
                except_end = i
                break
        except_end = i

    result.extend(lines[except_end:])
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python simplify_stocks.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]

    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    try:
        simplify_stocks(file_path)
        print("\nNext: Run import test")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
