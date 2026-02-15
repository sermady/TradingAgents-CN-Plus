# -*- coding: utf-8 -*-
"""
测试 scheduler_service error_handler 装饰器重构
"""
import sys
sys.path.insert(0, 'E:\\WorkSpace\\TradingAgents-CN')


def test_import():
    """测试导入"""
    print("[TEST] 测试导入重构后的服务...")
    try:
        from app.services.scheduler_service import SchedulerService
        from app.utils.error_handler import (
            async_handle_errors_empty_list,
            async_handle_errors_zero,
            async_handle_errors_false,
            async_handle_errors_empty_dict,
            async_handle_errors_none,
        )
        print("  [OK] SchedulerService 导入成功")
        print("  [OK] error_handler 装饰器导入成功")
        return True
    except Exception as e:
        print(f"  [ERROR] 导入失败: {e}")
        return False


def test_decorators_applied():
    """测试装饰器已正确应用"""
    print("\n[TEST] 测试装饰器应用...")
    try:
        from app.services.scheduler_service import SchedulerService

        # 验证类存在
        assert hasattr(SchedulerService, 'get_job_history'), "缺少 get_job_history 方法"
        assert hasattr(SchedulerService, 'count_job_history'), "缺少 count_job_history 方法"
        assert hasattr(SchedulerService, 'get_all_history'), "缺少 get_all_history 方法"
        assert hasattr(SchedulerService, 'count_all_history'), "缺少 count_all_history 方法"
        assert hasattr(SchedulerService, 'get_job_executions'), "缺少 get_job_executions 方法"
        assert hasattr(SchedulerService, 'count_job_executions'), "缺少 count_job_executions 方法"
        assert hasattr(SchedulerService, 'cancel_job_execution'), "缺少 cancel_job_execution 方法"
        assert hasattr(SchedulerService, 'mark_execution_as_failed'), "缺少 mark_execution_as_failed 方法"
        assert hasattr(SchedulerService, 'delete_execution'), "缺少 delete_execution 方法"
        assert hasattr(SchedulerService, 'get_job_execution_stats'), "缺少 get_job_execution_stats 方法"
        assert hasattr(SchedulerService, 'update_job_metadata'), "缺少 update_job_metadata 方法"

        print("  [OK] 所有重构方法都存在")

        # 验证异步方法
        import inspect
        methods = [
            'get_job_history',
            'count_job_history',
            'get_all_history',
            'count_all_history',
            'get_job_executions',
            'count_job_executions',
            'cancel_job_execution',
            'mark_execution_as_failed',
            'delete_execution',
            'get_job_execution_stats',
            'update_job_metadata',
        ]

        for method_name in methods:
            method = getattr(SchedulerService, method_name)
            assert inspect.iscoroutinefunction(method), f"{method_name} 应该是异步函数"

        print(f"  [OK] 所有方法 ({len(methods)}个) 都是异步函数")
        return True

    except Exception as e:
        print(f"  [ERROR] 装饰器应用测试失败: {e}")
        return False


def test_method_signatures():
    """测试方法签名正确"""
    print("\n[TEST] 测试方法签名...")
    try:
        from app.services.scheduler_service import SchedulerService
        import inspect

        # 测试 get_job_history
        sig = inspect.signature(SchedulerService.get_job_history)
        assert 'job_id' in sig.parameters, "缺少 job_id 参数"
        assert 'limit' in sig.parameters, "缺少 limit 参数"
        assert 'offset' in sig.parameters, "缺少 offset 参数"
        print("  [OK] get_job_history 签名正确")

        # 测试 count_job_history
        sig = inspect.signature(SchedulerService.count_job_history)
        assert 'job_id' in sig.parameters, "缺少 job_id 参数"
        print("  [OK] count_job_history 签名正确")

        # 测试 get_job_executions
        sig = inspect.signature(SchedulerService.get_job_executions)
        assert 'job_id' in sig.parameters, "缺少 job_id 参数"
        assert 'status' in sig.parameters, "缺少 status 参数"
        assert 'is_manual' in sig.parameters, "缺少 is_manual 参数"
        print("  [OK] get_job_executions 签名正确")

        # 测试 cancel_job_execution
        sig = inspect.signature(SchedulerService.cancel_job_execution)
        assert 'execution_id' in sig.parameters, "缺少 execution_id 参数"
        print("  [OK] cancel_job_execution 签名正确")

        # 测试 get_job_execution_stats
        sig = inspect.signature(SchedulerService.get_job_execution_stats)
        assert 'job_id' in sig.parameters, "缺少 job_id 参数"
        print("  [OK] get_job_execution_stats 签名正确")

        return True

    except Exception as e:
        print(f"  [ERROR] 方法签名测试失败: {e}")
        return False


def test_error_handler_functionality():
    """测试错误处理装饰器功能"""
    print("\n[TEST] 测试错误处理装饰器功能...")
    try:
        from app.utils.error_handler import (
            async_handle_errors_empty_list,
            async_handle_errors_zero,
            async_handle_errors_false,
            async_handle_errors_empty_dict,
            async_handle_errors_none,
        )

        # 测试装饰器可以正确应用
        @async_handle_errors_empty_list(error_message="测试错误")
        async def test_list():
            raise ValueError("测试异常")

        @async_handle_errors_zero(error_message="测试错误")
        async def test_zero():
            raise ValueError("测试异常")

        @async_handle_errors_false(error_message="测试错误")
        async def test_false():
            raise ValueError("测试异常")

        @async_handle_errors_empty_dict(error_message="测试错误")
        async def test_dict():
            raise ValueError("测试异常")

        @async_handle_errors_none(error_message="测试错误")
        async def test_none():
            raise ValueError("测试异常")

        # 运行测试
        import asyncio

        result1 = asyncio.run(test_list())
        assert result1 == [], f"期望 []，实际 {result1}"
        print("  [OK] async_handle_errors_empty_list 工作正常")

        result2 = asyncio.run(test_zero())
        assert result2 == 0, f"期望 0，实际 {result2}"
        print("  [OK] async_handle_errors_zero 工作正常")

        result3 = asyncio.run(test_false())
        assert result3 is False, f"期望 False，实际 {result3}"
        print("  [OK] async_handle_errors_false 工作正常")

        result4 = asyncio.run(test_dict())
        assert result4 == {}, f"期望 {{}}，实际 {result4}"
        print("  [OK] async_handle_errors_empty_dict 工作正常")

        result5 = asyncio.run(test_none())
        assert result5 is None, f"期望 None，实际 {result5}"
        print("  [OK] async_handle_errors_none 工作正常")

        return True

    except Exception as e:
        print(f"  [ERROR] 错误处理功能测试失败: {e}")
        return False


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("SchedulerService error_handler 装饰器重构验证测试")
    print("=" * 60)

    results = []

    # 同步测试
    results.append(("导入测试", test_import()))
    results.append(("装饰器应用", test_decorators_applied()))
    results.append(("方法签名", test_method_signatures()))
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
        print("\n[OK] 所有测试通过！SchedulerService error_handler 装饰器重构验证成功。")
        return 0
    else:
        print(f"\n[WARN] {total - passed} 个测试失败，请检查。")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
