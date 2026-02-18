# -*- coding: utf-8 -*-
"""
异常处理简化工具 - AST精确处理嵌套缩进

用于简化具有复杂嵌套try-except结构的路由文件。
只删除外层的通用异常处理（记录日志并重新抛出HTTPException），
保留内层的业务特定异常处理（优雅降级）。

使用方法:
    python scripts/maintenance/simplify_exception_handling.py <file_path>
"""

import ast
import sys
from pathlib import Path
from typing import List, Optional, Tuple


class TryExceptAnalyzer(ast.NodeVisitor):
    """分析try-except块，识别可简化的外层try块"""

    def __init__(self):
        self.simplifiable_tries = []  # 可简化的try块位置
        self.preservable_tries = []   # 需要保留的try块位置

    def visit_Try(self, node: ast.Try):
        """访问Try节点，分析是否可简化"""
        # 检查是否是函数体级别的try块
        is_function_level_try = False
        for parent in ast.walk(node):
            if isinstance(parent, ast.FunctionDef) and parent.body and isinstance(parent.body[0], ast.Try):
                if parent.body[0] == node:
                    is_function_level_try = True
                    break

        # 判断是否可以简化
        can_simplify = self._can_simplify_try_except(node)

        # 记录位置
        try_line = node.lineno
        try_end_line = self._get_node_end_line(node)

        if can_simplify and is_function_level_try:
            # 检查内层是否有需要保留的try块
            has_inner_try = self._has_nested_try(node)
            if has_inner_try:
                self.simplifiable_tries.append({
                    'start': try_line,
                    'end': try_end_line,
                    'has_nested': True,
                    'handler_name': self._get_function_name(node)
                })
            else:
                self.simplifiable_tries.append({
                    'start': try_line,
                    'end': try_end_line,
                    'has_nested': False,
                    'handler_name': self._get_function_name(node)
                })
        else:
            self.preservable_tries.append({
                'start': try_line,
                'end': try_end_line,
                'reason': 'business_logic' if not can_simplify else 'not_function_level'
            })

        self.generic_visit(node)

    def _can_simplify_try_except(self, node: ast.Try) -> bool:
        """判断try-except块是否可以简化

        可简化的条件：
        1. except只捕获Exception
        2. except体只有logger.error调用和raise HTTPException
        """
        if not node.handlers:
            return False

        # 检查所有except块
        for handler in node.handlers:
            # 检查异常类型
            if handler.type:
                # 如果不是捕获Exception，则不能简化
                if not isinstance(handler.type, ast.Name) or handler.type.id != 'Exception':
                    return False

            # 检查except体
            if not self._is_simple_exception_handler(handler.body):
                return False

        return True

    def _is_simple_exception_handler(self, body: List[ast.stmt]) -> bool:
        """检查except体是否只是简单的日志+HTTPException抛出

        简单模式：
        - logger.error(...)
        - raise HTTPException(...)
        """
        if len(body) > 2:
            return False

        has_logger_error = False
        has_raise_http = False

        for stmt in body:
            # 检查logger.error调用
            if isinstance(stmt, ast.Expr):
                if isinstance(stmt.value, ast.Call):
                    call = stmt.value
                    if isinstance(call.func, ast.Attribute):
                        if (isinstance(call.func.value, ast.Name) and
                            call.func.value.id == 'logger' and
                            call.func.attr == 'error'):
                            has_logger_error = True

            # 检查raise HTTPException
            if isinstance(stmt, ast.Raise):
                if isinstance(stmt.exc, ast.Call):
                    if isinstance(stmt.exc.func, ast.Name):
                        if 'HTTPException' in str(stmt.exc.func.id):
                            has_raise_http = True

        return has_logger_error and has_raise_http

    def _has_nested_try(self, node: ast.Try) -> bool:
        """检查try块内是否有嵌套的try块"""
        for child in ast.walk(node):
            if isinstance(child, ast.Try) and child != node:
                # 检查是否直接在body中（不包括handlers和finalbody）
                for stmt in node.body:
                    if stmt == child or (hasattr(stmt, 'body') and child in ast.walk(stmt)):
                        return True
        return False

    def _get_node_end_line(self, node: ast.AST) -> int:
        """获取节点结束行号"""
        max_line = node.lineno
        for child in ast.walk(node):
            if hasattr(child, 'lineno') and child.lineno > max_line:
                max_line = child.lineno
        return max_line

    def _get_function_name(self, node: ast.Try) -> Optional[str]:
        """获取包含try块的函数名"""
        for parent in ast.walk(ast.Module(body=[node])):
            if isinstance(parent, ast.FunctionDef):
                return parent.name
        return None


def analyze_file(file_path: str) -> Tuple[List[dict], List[dict]]:
    """分析文件，返回可简化和需要保留的try块"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    tree = ast.parse(content, filename=file_path)
    analyzer = TryExceptAnalyzer()
    analyzer.visit(tree)

    return analyzer.simplifiable_tries, analyzer.preservable_tries


def simplify_file_with_nested_try(file_path: str) -> bool:
    """简化包含嵌套try的文件

    策略：
    1. 识别可简化的外层try块
    2. 删除try行和except行
    3. 保持try体和内层try的缩进不变
    4. 添加注释说明全局处理器
    """
    simplifiable, preservable = analyze_file(file_path)

    if not simplifiable:
        print(f"OK: File {file_path} has no simplifiable try blocks")
        return False

    print(f"\nAnalyzing {file_path}:")
    print(f"  Simplifiable try blocks: {len(simplifiable)}")
    print(f"  Preservable try blocks: {len(preservable)}")

    for try_info in simplifiable:
        print(f"  - Lines {try_info['start']}-{try_info['end']}: {try_info['handler_name']}")
        if try_info['has_nested']:
            print(f"    (Has nested try, needs special handling)")

    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 处理每个可简化的try块（从后往前，避免行号偏移）
    modified_lines = lines.copy()
    for try_info in reversed(simplifiable):
        start = try_info['start'] - 1  # 转换为0-based
        end = try_info['end'] - 1

        if try_info['has_nested']:
            # 包含嵌套try：删除try行和except行，保持体不变
            modified_lines = _remove_outer_try_preserve_nested(
                modified_lines, start, end
            )
        else:
            # 无嵌套try：直接删除整个try-except块
            modified_lines = _remove_simple_try(
                modified_lines, start, end
            )

    # Write back
    backup_path = file_path + '.backup'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(modified_lines)

    print(f"\nOK: Modified file: {file_path}")
    print(f"  Backup: {backup_path}")
    return True


def _remove_outer_try_preserve_nested(lines: List[str], start: int, end: int) -> List[str]:
    """Remove outer try-except, preserve nested try indentation

    Strategy:
    1. Find try line (start)
    2. Find corresponding except line
    3. Delete try line
    4. Delete except line
    5. Keep try body indentation unchanged (nested try keeps original indent)
    """
    result = []
    i = 0
    try_indent = len(lines[start]) - len(lines[start].lstrip())

    # Find except line
    except_line_idx = None
    for j in range(start + 1, min(end + 1, len(lines))):
        line = lines[j]
        if line.strip().startswith('except'):
            # Check if indentation matches try
            except_indent = len(line) - len(line.lstrip())
            if except_indent == try_indent:
                except_line_idx = j
                break

    if except_line_idx is None:
        print(f"  Warning: Cannot find except line for try (line {start+1})")
        return lines

    # 复制try体之前的所有行
    result.extend(lines[:start])

    # 复制try体（跳过try行，保留内层try的缩进）
    result.extend(lines[start + 1:except_line_idx])

    # 跳过except行，复制后续内容
    result.extend(lines[except_line_idx + 1:])

    return result


def _remove_simple_try(lines: List[str], start: int, end: int) -> List[str]:
    """删除简单的try-except块（无嵌套）"""
    result = []
    try_indent = len(lines[start]) - len(lines[start].lstrip())

    # 找到except行
    except_line_idx = None
    for j in range(start + 1, min(end + 1, len(lines))):
        line = lines[j]
        if line.strip().startswith('except'):
            except_indent = len(line) - len(line.lstrip())
            if except_indent == try_indent:
                except_line_idx = j
                break

    if except_line_idx is None:
        return lines

    # 复制try体之前的所有行
    result.extend(lines[:start])

    # 复制try体（减少缩进）
    base_indent = try_indent + 4
    for line in lines[start + 1:except_line_idx]:
        if line.strip():  # 非空行
            original_indent = len(line) - len(line.lstrip())
            if original_indent >= base_indent:
                # 减少缩进
                new_indent = original_indent - 4
                result.append(' ' * new_indent + line.lstrip())
            else:
                result.append(line)
        else:
            result.append(line)

    # 跳过except行，复制后续内容
    result.extend(lines[except_line_idx + 1:])

    return result


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python simplify_exception_handling.py <file_path>")
        print("\nExample:")
        print("  python simplify_exception_handling.py app/routers/stock_sync.py")
        sys.exit(1)

    file_path = sys.argv[1]

    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    try:
        success = simplify_file_with_nested_try(file_path)
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
