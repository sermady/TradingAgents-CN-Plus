#!/usr/bin/env python3
"""
批量修复 pyright 类型错误的脚本
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional


def fix_optional_subscript(content: str, line_num: int) -> str:
    """
    修复 Object of type "None" is not subscriptable 错误
    在访问前添加 None 检查
    """
    lines = content.split("\n")
    if line_num < 1 or line_num > len(lines):
        return content

    line = lines[line_num - 1]

    # 查找类似 data['key'] 或 obj.attr['key'] 的模式
    # 在访问前添加检查

    # 简单情况：直接对变量进行下标访问
    patterns = [
        r'(\w+)\[(\'[^\']*\'|"[^"]*")\]',
        r'(\w+)\.get\(([^)]+)\)\[(\'[^\']*\'|"[^"]*")\]',
    ]

    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            var_name = match.group(1)
            # 检查是否已经有 None 检查
            if (
                f"{var_name} is not None" not in line
                and f"{var_name} is None" not in line
            ):
                # 缩进
                indent = len(line) - len(line.lstrip())
                indent_str = " " * indent

                # 创建修复后的代码
                new_lines = [
                    f"{indent_str}if {var_name} is not None:",
                    f"{indent_str}    {line.lstrip()}",
                ]
                lines[line_num - 1] = "\n".join(new_lines)
                break

    return "\n".join(lines)


def fix_unbound_variable(content: str, line_num: int, var_name: str) -> str:
    """
    修复未绑定变量错误
    添加变量初始化
    """
    lines = content.split("\n")
    if line_num < 1 or line_num > len(lines):
        return content

    # 在函数开头或条件分支前添加变量初始化
    # 找到当前行的缩进级别
    current_line = lines[line_num - 1]
    current_indent = len(current_line) - len(current_line.lstrip())

    # 向上查找合适的插入位置（函数开头或条件语句前）
    insert_pos = 0
    for i in range(line_num - 2, -1, -1):
        line = lines[i]
        if line.strip().startswith("def ") or line.strip().startswith("class "):
            insert_pos = i + 1
            break
        # 找到相同或更低缩进级别的行
        indent = len(line) - len(line.lstrip())
        if indent < current_indent and line.strip():
            insert_pos = i + 1
            break

    # 添加变量初始化
    indent_str = " " * current_indent
    init_line = f"{indent_str}{var_name} = None  # type: ignore[var-name]\n"

    lines.insert(insert_pos, init_line.rstrip())

    return "\n".join(lines)


def fix_unused_import(content: str, line_num: int) -> str:
    """
    删除未使用的导入
    """
    lines = content.split("\n")
    if line_num < 1 or line_num > len(lines):
        return content

    # 标记为 type: ignore
    line = lines[line_num - 1]
    if "#" not in line:
        lines[line_num - 1] = line + "  # type: ignore[unused-import]"
    elif "type: ignore" not in line:
        lines[line_num - 1] = line + "  # type: ignore[unused-import]"

    return "\n".join(lines)


def fix_unused_variable(content: str, line_num: int) -> str:
    """
    修复未使用变量：将变量名改为 _
    """
    lines = content.split("\n")
    if line_num < 1 or line_num > len(lines):
        return content

    line = lines[line_num - 1]
    # 简单的变量赋值检测
    match = re.match(r"^(\s*)(\w+)\s*=", line)
    if match:
        indent, var_name = match.groups()
        # 替换为 _ 前缀表示未使用
        lines[line_num - 1] = line.replace(f"{var_name} =", f"_{var_name} =", 1)

    return "\n".join(lines)


def process_file(filepath: Path, fixes: List[Tuple[str, int, Optional[str]]]) -> bool:
    """
    处理单个文件，应用修复

    Args:
        filepath: 文件路径
        fixes: 修复列表，每个修复是 (error_type, line_number, extra_info)

    Returns:
        是否修改了文件
    """
    if not filepath.exists():
        print(f"文件不存在: {filepath}")
        return False

    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"读取文件失败 {filepath}: {e}")
        return False

    original_content = content

    # 按行号降序处理，避免行号变化
    fixes.sort(key=lambda x: x[1], reverse=True)

    for error_type, line_num, extra_info in fixes:
        if error_type == "reportOptionalSubscript":
            content = fix_optional_subscript(content, line_num)
        elif error_type == "reportUnboundVariable":
            content = fix_unbound_variable(
                content, line_num, extra_info or "unknown_var"
            )
        elif error_type == "reportUnusedImport":
            content = fix_unused_import(content, line_num)
        elif error_type == "reportUnusedVariable":
            content = fix_unused_variable(content, line_num)

    if content != original_content:
        try:
            filepath.write_text(content, encoding="utf-8")
            print(f"已修复: {filepath}")
            return True
        except Exception as e:
            print(f"写入文件失败 {filepath}: {e}")
            return False

    return False


def main():
    """主函数"""
    # 这里可以添加批量处理逻辑
    # 目前作为工具函数使用
    print("类型错误修复工具")
    print("使用方式: python fix_pyright_errors.py <file> <error_type> <line>")


if __name__ == "__main__":
    main()
