# -*- coding: utf-8 -*-
"""
移除代码中的Emoji，替换为文本标记
"""
import re
import sys
from pathlib import Path

# Windows环境下强制使用UTF-8编码输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Emoji替换映射
EMOJI_REPLACEMENTS = {
    "✅": "[OK]",
    "❌": "[ERROR]",
    "⚠️": "[WARN]",
    "⚠": "[WARN]",
    "📊": "[DATA]",
    "🚀": "[START]",
    "🔧": "[TOOL]",
    "⏭️": "[SKIP]",
    "⏭": "[SKIP]",
    "⏸️": "[SKIP]",
    "ℹ️": "[INFO]",
    "ℹ": "[INFO]",
    "📋": "[LIST]",
    "🔄": "[REFRESH]",
    "⚡": "[FAST]",
    "📈": "[CHART]",
    "🔍": "[DEBUG]",
    "🔥": "[HOT]",
    "💰": "[MONEY]",
}


def remove_emoji_from_file(file_path: Path) -> int:
    """
    从文件中移除Emoji

    Args:
        file_path: 文件路径

    Returns:
        替换数量
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        replacement_count = 0

        # 替换所有Emoji
        for emoji, replacement in EMOJI_REPLACEMENTS.items():
            if emoji in content:
                count = content.count(emoji)
                content = content.replace(emoji, replacement)
                replacement_count += count
                print(f"  {file_path.name}: {emoji} -> {replacement} ({count}处)")

        # 只有内容发生变化时才写入
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return replacement_count
        return 0

    except Exception as e:
        print(f"[ERROR] 处理文件失败 {file_path}: {e}")
        return 0


def main():
    """主函数"""
    print("[START] 开始移除Emoji...")

    # 需要处理的文件
    target_files = [
        "app/services/data_sources/akshare_adapter.py",
        "app/services/data_sources/baostock_adapter.py",
        "app/services/data_sources/manager.py",
        "app/services/data_sources/local_backup.py",
    ]

    project_root = Path(__file__).parent.parent.parent
    total_replacements = 0

    for file_path_str in target_files:
        file_path = project_root / file_path_str
        if file_path.exists():
            count = remove_emoji_from_file(file_path)
            total_replacements += count
        else:
            print(f"[WARN] 文件不存在: {file_path}")

    print(f"[OK] Emoji移除完成，共替换 {total_replacements} 处")


if __name__ == "__main__":
    main()
