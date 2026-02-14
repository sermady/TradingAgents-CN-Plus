# -*- coding: utf-8 -*-
"""
代码审查脚本 - 检查未提交的修改
"""
import subprocess
import re
from pathlib import Path
from typing import List, Tuple

# 安全问题模式
SECURITY_PATTERNS = {
    'CRITICAL': [
        (r'password\s*=\s*["\'].*["\']', '硬编码密码'),
        (r'api_key\s*=\s*["\'].*["\']', '硬编码API密钥'),
        (r'secret\s*=\s*["\'].*["\']', '硬编码密钥'),
        (r'token\s*=\s*["\'].*["\']', '硬编码令牌'),
        (r'eval\s*\(', '使用eval()'),
        (r'exec\s*\(', '使用exec()'),
        (r'os\.system\s*\(', '使用os.system()'),
        (r'subprocess\.call\s*\(', '使用subprocess.call()'),
    ],
    'HIGH': [
        (r'--.*\$.*--', 'SQL注入风险 - shell命令'),
        (r'f["\'].*\{.*\}.*["\'].*execute', 'SQL注入风险 - f-string'),
        (r'\.format\s*\([^)]*\$\s*\)', 'SQL注入风险 - .format()'),
        (r'open\(.*\.\.', '路径遍历风险'),
        (r'<.*>', 'XSS风险 - HTML注入'),
    ],
}

# 代码质量问题
QUALITY_PATTERNS = {
    'HIGH': [
        (r'console\.log', 'console.log语句'),
        (r'print\s*\([^)]*\)', 'print语句（应使用logger）'),
        (r'#\s*TODO', 'TODO注释'),
        (r'#\s*FIXME', 'FIXME注释'),
        (r'#\s*HACK', 'HACK注释'),
        (r'#\s*XXX', 'XXX注释'),
    ],
    'MEDIUM': [
        (r'😀|😂|🤣|⚠|✅|❌|📊|🚀|🔧|⏭️|⏸|ℹ️|📋|🔄|⚡|📈|🔍|🔥|💰',
         'Emoji字符'),
    ],
}


def check_file_security(file_path: Path, content: str) -> List[Tuple[str, str, int, str]]:
    """
    检查文件安全问题

    Returns:
        [(severity, issue, line_no, description)]
    """
    issues = []
    lines = content.split('\n')

    for severity, patterns in SECURITY_PATTERNS.items():
        for pattern, description in patterns:
            for line_no, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append((severity, description, line_no, line.strip()))
                    # 对于CRITICAL问题，只报告一次
                    if severity == 'CRITICAL':
                        break

    return issues


def check_file_quality(file_path: Path, content: str) -> List[Tuple[str, str, int, str]]:
    """
    检查代码质量问题

    Returns:
        [(severity, issue, line_no, description)]
    """
    issues = []
    lines = content.split('\n')

    for severity, patterns in QUALITY_PATTERNS.items():
        for pattern, description in patterns:
            for line_no, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append((severity, description, line_no, line.strip()))

    return issues


def review_changes():
    """主审查函数"""
    print("=" * 80)
    print("代码审查报告")
    print("=" * 80)

    # 获取修改的文件列表（仅审查本次修复涉及的文件）
    files_to_review = [
        'app/core/config_bridge.py',
        'app/services/data_sources/base.py',
        'app/services/data_sources/constants.py',
        'app/services/data_sources/akshare_adapter.py',
        'app/services/data_sources/baostock_adapter.py',
        'app/services/data_sources/manager.py',
        'app/services/data_sources/tushare_adapter.py',
        'app/services/data_sources/local_backup.py',
        'scripts/maintenance/remove_emoji.py',
    ]

    all_issues = []
    total_files = 0
    files_with_issues = 0

    for file_path_str in files_to_review:
        file_path = Path(file_path_str)
        if not file_path.exists():
            continue

        total_files += 1
        print(f"\n[检查] {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 安全检查
            security_issues = check_file_security(file_path, content)
            # 质量检查
            quality_issues = check_file_quality(file_path, content)

            if security_issues or quality_issues:
                files_with_issues += 1
                print(f"  发现 {len(security_issues) + len(quality_issues)} 个问题")

                for severity, issue, line_no, line in security_issues + quality_issues:
                    all_issues.append((file_path_str, severity, issue, line_no, line))
                    print(f"    [{severity}] Line {line_no}: {issue}")
                    print(f"           {line[:80]}")
            else:
                print(f"  [OK] 无问题")

        except Exception as e:
            print(f"  [ERROR] 检查失败: {e}")

    # 总结
    print("\n" + "=" * 80)
    print("审查总结")
    print("=" * 80)
    print(f"检查文件数: {total_files}")
    print(f"有问题文件数: {files_with_issues}")
    print(f"总问题数: {len(all_issues)}")

    # 按严重性分组
    critical_issues = [i for i in all_issues if i[1] == 'CRITICAL']
    high_issues = [i for i in all_issues if i[1] == 'HIGH']
    medium_issues = [i for i in all_issues if i[1] == 'MEDIUM']

    print(f"\n[CRITICAL] {len(critical_issues)} 个")
    print(f"[HIGH] {len(high_issues)} 个")
    print(f"[MEDIUM] {len(medium_issues)} 个")

    # 决策
    if critical_issues:
        print("\n" + "!" * 80)
        print("❌ 审查未通过：发现CRITICAL级别安全问题")
        print("必须修复后才能提交！")
        print("!" * 80)
        return False

    if high_issues:
        print("\n" + "!" * 80)
        print("⚠️  审查未通过：发现HIGH级别问题")
        print("建议修复后再提交！")
        print("!" * 80)
        return False

    print("\n" + "=" * 80)
    print("✅ 审查通过：无CRITICAL或HIGH级别问题")
    print("=" * 80)
    return True


if __name__ == "__main__":
    import sys
    success = review_changes()
    sys.exit(0 if success else 1)
