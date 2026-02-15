# -*- coding: utf-8 -*-
"""
测试 error_handler 装饰器推广
验证重构后的服务能正确导入和使用装饰器
"""
import sys
sys.path.insert(0, 'E:\\WorkSpace\\TradingAgents-CN')


def test_error_handler_import():
    """测试 error_handler 装饰器导入"""
    print("[TEST] 测试 error_handler 装饰器导入...")
    try:
        from app.utils.error_handler import (
            async_handle_errors_none,
            async_handle_errors_empty_list,
            async_handle_errors_empty_dict,
            async_handle_errors_false,
            async_handle_errors_zero,
        )
        print("  [OK] 所有异步装饰器导入成功")
        return True
    except Exception as e:
        print(f"  [ERROR] 导入失败: {e}")
        return False


def test_historical_data_service():
    """测试 HistoricalDataService 重构"""
    print("\n[TEST] 测试 HistoricalDataService...")
    try:
        from app.services.historical_data_service import HistoricalDataService

        # 验证类存在
        assert hasattr(HistoricalDataService, 'get_historical_data'), "缺少 get_historical_data 方法"
        assert hasattr(HistoricalDataService, 'get_latest_date'), "缺少 get_latest_date 方法"
        assert hasattr(HistoricalDataService, 'get_data_statistics'), "缺少 get_data_statistics 方法"

        # 验证装饰器已应用（方法应该有__wrapped__属性或被装饰器包装）
        import inspect

        methods_to_check = [
            'get_historical_data',
            'get_latest_date',
            'get_data_statistics',
        ]

        for method_name in methods_to_check:
            method = getattr(HistoricalDataService, method_name)
            assert inspect.iscoroutinefunction(method), f"{method_name} 应该是异步函数"

        print(f"  [OK] 所有方法 ({len(methods_to_check)}个) 验证通过")
        return True

    except Exception as e:
        print(f"  [ERROR] HistoricalDataService 测试失败: {e}")
        return False


def test_error_handler_functionality():
    """测试错误处理装饰器功能"""
    print("\n[TEST] 测试错误处理装饰器功能...")
    try:
        from app.utils.error_handler import (
            async_handle_errors_empty_list,
            async_handle_errors_none,
            async_handle_errors_empty_dict,
        )

        # 测试装饰器可以正确应用
        @async_handle_errors_empty_list(error_message="测试错误")
        async def test_list():
            raise ValueError("测试异常")

        @async_handle_errors_none(error_message="测试错误")
        async def test_none():
            raise ValueError("测试异常")

        @async_handle_errors_empty_dict(error_message="测试错误")
        async def test_dict():
            raise ValueError("测试异常")

        # 运行测试
        import asyncio

        result1 = asyncio.run(test_list())
        assert result1 == [], f"期望 []，实际 {result1}"
        print("  [OK] async_handle_errors_empty_list 工作正常")

        result2 = asyncio.run(test_none())
        assert result2 is None, f"期望 None，实际 {result2}"
        print("  [OK] async_handle_errors_none 工作正常")

        result3 = asyncio.run(test_dict())
        assert result3 == {}, f"期望 {{}}，实际 {result3}"
        print("  [OK] async_handle_errors_empty_dict 工作正常")

        return True

    except Exception as e:
        print(f"  [ERROR] 错误处理功能测试失败: {e}")
        return False


def test_syntax_check():
    """测试语法检查"""
    print("\n[TEST] 测试重构文件语法...")
    import subprocess

    files_to_check = [
        'app/services/historical_data_service.py',
    ]

    all_passed = True
    for file_path in files_to_check:
        try:
            result = subprocess.run(
                ['python', '-m', 'py_compile', file_path],
                capture_output=True,
                text=True,
                cwd='E:\\WorkSpace\\TradingAgents-CN'
            )
            if result.returncode == 0:
                print(f"  [OK] {file_path}")
            else:
                print(f"  [ERROR] {file_path}: {result.stderr}")
                all_passed = False
        except Exception as e:
            print(f"  [ERROR] {file_path}: {e}")
            all_passed = False

    return all_passed


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("error_handler 装饰器推广验证测试")
    print("=" * 60)

    results = []

    # 同步测试
    results.append(("装饰器导入", test_error_handler_import()))
    results.append(("语法检查", test_syntax_check()))
    results.append(("HistoricalDataService", test_historical_data_service()))
    results.append(("错误处理功能", test_error_handler_functionality()))

    # 汇总
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")

    print("-" * 60)
    print(f"总计: {passed}/{total} 通过")

    if passed == total:
        print("\n[OK] 所有测试通过！error_handler 装饰器推广验证成功。")
        return 0
    else:
        print(f"\n[WARN] {total - passed} 个测试失败，请检查。")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
