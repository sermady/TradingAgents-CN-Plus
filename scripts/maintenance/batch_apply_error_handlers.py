# -*- coding: utf-8 -*-
"""
error_handler装饰器批量应用工具

自动识别并应用error_handler装饰器到服务文件
"""
import os
import re
from pathlib import Path


# 需要优化的服务文件列表（按优先级）
HIGH_PRIORITY_FILES = [
    "app/services/alert_manager.py",
    "app/services/favorites_service.py",
    "app/services/auth_service.py",
]

MEDIUM_PRIORITY_FILES = [
    "app/services/quotes_service.py",
    "app/services/foreign_stock_service.py",
    "app/services/config_provider.py",
]

# 常见的错误处理模式
ERROR_PATTERNS = [
    # logger.error(f"❌ 操作失败: {e}")
    # return None
    (r'logger\.error\(f"[^"]*❌[^"]*\{e\}"', r'except Exception as e:\s*return None'),

    # logger.error(f"❌ 操作失败: {e}")
    # return False
    (r'logger\.error\(f"[^"]*❌[^"]*\{e\}"', r'except Exception as e:\s*return False'),

    # logger.error(f"❌ 查询失败: {e}")
    # return []
    (r'logger\.error\(f"[^"]*❌[^"]*查询失败[^"]*\{e\}"', r'except Exception as e:\s*return \[\]'),
]


def count_error_patterns(file_path: Path) -> dict:
    """统计文件中的错误处理模式数量"""
    try:
        content = file_path.read_text(encoding='utf-8')

        pattern_counts = {}
        for i, pattern in enumerate(ERROR_PATTERNS, 1):
            matches = len(re.findall(pattern, content))
            pattern_counts[f'pattern_{i}'] = matches

        total_errors = sum(pattern_counts.values())

        return {
            'file': str(file_path),
            'lines': len(content.split('\n')),
            'pattern_counts': pattern_counts,
            'total_errors': total_errors,
            'optimizable': total_errors > 3,  # 超过3个错误处理模式
        }
    except Exception as e:
        print(f"❌ 分析文件失败 {file_path}: {e}")
        return {'file': str(file_path), 'error': str(e)}


def analyze_services_directory():
    """分析app/services目录，识别优化目标"""
    services_dir = Path("app/services")

    if not services_dir.exists():
        print("❌ app/services目录不存在")
        return []

    # 获取所有.py文件
    py_files = list(services_dir.glob("*.py"))

    # 排除特殊文件
    exclude_files = {
        "__init__.py",
        "alert_manager_v2.py",  # 我们刚创建的优化版
    }

    target_files = [f for f in py_files if f.name not in exclude_files and f.is_file()]

    print(f"\n📊 分析app/services目录:")
    print(f"   总Python文件数: {len(target_files)}")

    # 分析每个文件
    analysis_results = []
    for file_path in target_files[:20]:  # 先分析前20个文件
        result = count_error_patterns(file_path)
        if result.get('optimizable', False):
            analysis_results.append(result)

    # 按优化价值排序
    analysis_results.sort(key=lambda x: x['total_errors'], reverse=True)

    print(f"\n🎯 高价值优化目标（错误处理模式 >3）:")
    for result in analysis_results[:10]:
        print(f"   {result['file']}:")
        print(f"      行数: {result['lines']}")
        print(f"      错误处理: {result['total_errors']}处")

    return analysis_results


def generate_optimization_plan(analysis_results: list) -> dict:
    """生成优化计划"""
    total_files = len(analysis_results)
    total_errors = sum(r['total_errors'] for r in analysis_results)
    avg_reduction = 30  # 估算每个文件平均减少30行

    plan = {
        'total_files': total_files,
        'total_errors': total_errors,
        'estimated_reduction': total_files * avg_reduction,
        'high_priority': [r['file'] for r in analysis_results if r['total_errors'] > 10],
        'medium_priority': [r['file'] for r in analysis_results if 5 < r['total_errors'] <= 10],
    }

    print(f"\n📋 优化计划:")
    print(f"   目标文件数: {total_files}")
    print(f"   错误处理总数: {total_errors}")
    print(f"   预计减少代码: ~{plan['estimated_reduction']}行")
    print(f"   高优先级: {len(plan['high_priority'])}个文件")
    print(f"   中优先级: {len(plan['medium_priority'])}个文件")

    return plan


def main():
    """主函数"""
    print("="*70)
    print("error_handler装饰器批量应用工具")
    print("="*70)

    # 分析app/services目录
    analysis_results = analyze_services_directory()

    if not analysis_results:
        print("\n⚠️ 未找到可优化的文件")
        return

    # 生成优化计划
    plan = generate_optimization_plan(analysis_results)

    # 输出推荐优化顺序
    print(f"\n✅ 推荐优化顺序（按错误处理密度排序）:")
    print()

    high_priority = plan['high_priority'][:5]
    for i, file_path in enumerate(high_priority, 1):
        print(f"  {i}. {file_path}")

    print(f"\n📝 下一步:")
    print(f"   1. 对高优先级文件应用error_handler装饰器")
    print(f"   2. 每个文件优化后运行测试验证")
    print(f"   3. 确保功能正常后继续下一个")
    print(f"   4. 完成后更新进度报告")
    print()
    print("="*70)


if __name__ == "__main__":
    main()
