# -*- coding: utf-8 -*-
"""
Exception Handling Simplifier - Text Pattern Matching

Simplifies exception handling in router files by removing generic try-except blocks
that only log and re-raise HTTPException, while preserving business-specific handlers.

Usage:
    python scripts/maintenance/simplify_exception_handling_v2.py <file_path>
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple


def find_try_blocks(file_path: str) -> List[Dict]:
    """Find all top-level try-except blocks in the file

    Returns list of dict with keys:
    - start: line number (1-based)
    - end: line number (1-based)
    - function_name: name of containing function
    - has_nested: whether there are nested try blocks
    - is_simplifiable: whether this try block can be simplified
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    results = []
    current_function = None
    try_stack = []  # Stack of (line_num, indent) tuples

    for i, line in enumerate(lines, 1):
        # Track function definitions
        if re.match(r'^\s*(async\s+)?def\s+\w+', line):
            match = re.search(r'(?:async\s+)?def\s+(\w+)', line)
            if match:
                current_function = match.group(1)

        # Detect try blocks
        stripped = line.strip()
        if stripped.startswith('try:'):
            indent = len(line) - len(line.lstrip())
            try_stack.append((i, indent))

        # Detect except blocks at function level
        elif stripped.startswith('except') and try_stack:
            # Check if this except matches the last try's indentation
            try_line, try_indent = try_stack[-1]
            except_indent = len(line) - len(line.lstrip())

            if except_indent == try_indent:
                # Found matching try-except block
                # Find the end of the except block
                end_line = find_except_block_end(lines, i, except_indent)

                # Check if this try block contains nested try blocks
                has_nested = check_nested_try(lines, try_line, end_line, try_indent)

                # Check if simplifiable
                is_simplifiable = is_simplifiable_try_except(
                    lines, try_line, i, end_line, try_indent
                )

                results.append({
                    'start': try_line,
                    'end': end_line,
                    'function_name': current_function,
                    'has_nested': has_nested,
                    'is_simplifiable': is_simplifiable
                })

                try_stack.pop()

    return results


def find_except_block_end(lines: List[str], except_line: int, indent: int) -> int:
    """Find the end line of an except block"""
    i = except_line
    while i < len(lines):
        line = lines[i]
        if line.strip() == '':
            i += 1
            continue

        line_indent = len(line) - len(line.lstrip())
        # If we find a line at or above the except indentation, block ended
        if line_indent <= indent and i > except_line:
            return i
        i += 1
    return len(lines)


def check_nested_try(lines: List[str], start: int, end: int, outer_indent: int) -> bool:
    """Check if there are nested try blocks within the given range"""
    for i in range(start, min(end, len(lines))):
        line = lines[i]
        if 'try:' in line:
            indent = len(line) - len(line.lstrip())
            # Check if this try is nested (greater indentation)
            if indent > outer_indent:
                return True
    return False


def is_simplifiable_try_except(
    lines: List[str],
    try_line: int,
    except_line: int,
    end_line: int,
    indent: int
) -> bool:
    """Check if a try-except block is simplifiable

    Simplifiable if:
    1. Only catches Exception (or no specific exception)
    2. Except body only has logger.error and raise HTTPException
    """

    # Check exception type
    except_line_content = lines[except_line - 1].strip()
    if not except_line_content.startswith('except Exception') and not except_line_content == 'except:':
        return False

    # Check except body
    body_start = except_line
    body_lines = []
    for i in range(body_start, min(end_line, len(lines))):
        line = lines[i]
        if line.strip() == '':
            continue
        line_indent = len(line) - len(line.lstrip())
        if line_indent <= indent:
            break
        body_lines.append(line)

    # Check if body only contains logger.error and raise HTTPException
    has_logger_error = False
    has_raise_http = False

    for line in body_lines:
        stripped = line.strip()
        # Check for logger.error
        if 'logger.error' in stripped and not stripped.startswith('#'):
            has_logger_error = True
        # Check for raise HTTPException
        if 'raise HTTPException' in stripped or 'raise HTTPException' in line:
            has_raise_http = True

    return has_logger_error and has_raise_http


def simplify_file(file_path: str) -> bool:
    """Simplify exception handling in the file"""
    try_blocks = find_try_blocks(file_path)

    simplifiable = [tb for tb in try_blocks if tb['is_simplifiable']]
    preservable = [tb for tb in try_blocks if not tb['is_simplifiable']]

    if not simplifiable:
        print(f"OK: No simplifiable try blocks found")
        return False

    print(f"\nAnalyzing {file_path}:")
    print(f"  Simplifiable try blocks: {len(simplifiable)}")
    print(f"  Preservable try blocks: {len(preservable)}")

    for tb in simplifiable:
        print(f"  - Lines {tb['start']}-{tb['end']}: {tb['function_name']}")
        if tb['has_nested']:
            print(f"    (Has nested try, special handling)")

    # Read file
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Create backup
    backup_path = file_path + '.backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"\nBackup created: {backup_path}")

    # Process from end to start (to avoid line number shifts)
    modified_lines = lines.copy()
    for tb in reversed(simplifiable):
        start = tb['start'] - 1  # Convert to 0-based
        except_line = find_except_line(modified_lines, start, tb['end'])
        end = tb['end'] - 1

        if tb['has_nested']:
            modified_lines = remove_outer_try_preserve_nested(
                modified_lines, start, except_line, end
            )
        else:
            modified_lines = remove_simple_try(
                modified_lines, start, except_line, end
            )

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(modified_lines)

    print(f"OK: Modified file: {file_path}")
    return True


def find_except_line(lines: List[str], try_start: int, try_end: int) -> int:
    """Find the except line for a given try"""
    try_indent = len(lines[try_start]) - len(lines[try_start].lstrip())

    for i in range(try_start + 1, min(try_end, len(lines))):
        line = lines[i]
        if 'except' in line and 'Exception' in line:
            except_indent = len(line) - len(line.lstrip())
            if except_indent == try_indent:
                return i
    return -1


def remove_outer_try_preserve_nested(
    lines: List[str], start: int, except_line: int, end: int
) -> List[str]:
    """Remove outer try-except, reduce indentation but preserve relative structure

    Strategy:
    1. Remove try line (start)
    2. Remove except line (except_line)
    3. Reduce try body indentation by 4 spaces (nested tries maintain relative indent)
    """
    result = []

    # Copy everything before try
    result.extend(lines[:start])

    # Copy try body with reduced indentation
    base_indent = len(lines[start]) - len(lines[start].lstrip()) + 4

    for line in lines[start + 1:except_line]:
        if line.strip():  # Non-empty line
            original_indent = len(line) - len(line.lstrip())
            if original_indent >= base_indent:
                # Reduce indentation by 4 spaces
                new_indent = original_indent - 4
                result.append(' ' * new_indent + line.lstrip())
            else:
                # Keep as-is (shouldn't happen)
                result.append(line)
        else:
            # Empty line
            result.append(line)

    # Skip except line, copy everything after
    result.extend(lines[except_line + 1:])

    return result


def remove_simple_try(
    lines: List[str], start: int, except_line: int, end: int
) -> List[str]:
    """Remove simple try-except block (no nesting), reduce indentation of body"""
    result = []

    # Copy everything before try
    result.extend(lines[:start])

    # Copy try body with reduced indentation
    base_indent = len(lines[start]) - len(lines[start].lstrip()) + 4

    for line in lines[start + 1:except_line]:
        if line.strip():
            original_indent = len(line) - len(line.lstrip())
            if original_indent >= base_indent:
                new_indent = original_indent - 4
                result.append(' ' * new_indent + line.lstrip())
            else:
                result.append(line)
        else:
            result.append(line)

    # Skip except line, copy everything after
    result.extend(lines[except_line + 1:])

    return result


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python simplify_exception_handling_v2.py <file_path>")
        print("\nExample:")
        print("  python simplify_exception_handling_v2.py app/routers/stock_sync.py")
        sys.exit(1)

    file_path = sys.argv[1]

    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    try:
        success = simplify_file(file_path)
        if success:
            print("\nOK: Processing completed")
            print("\nNext steps:")
            print("  1. Check the modified file")
            print("  2. Run import test: python -c \"from app.routers.stock_sync import router; print('OK')\"")
            print("  3. If issues, restore backup: cp file.py.backup file.py")
        else:
            print("\nNo changes needed")
            sys.exit(0)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
