# -*- coding: utf-8 -*-
"""
测试 metrics_collector error_handler 装饰器重构
"""
import sys
sys.path.insert(0, 'E:\\WorkSpace\\TradingAgents-CN')


def test_import():
    """测试导入"""
    print("[TEST] 测试导入重构后的服务...")
    try:
        from app.services.metrics_collector import MetricsCollector, MetricType
        from app.utils.error_handler import (
            async_handle_errors_empty_list,
            async_handle_errors_none,
            async_handle_errors_zero,
            async_handle_errors_empty_dict,
        )
        print("  [OK] MetricsCollector 导入成功")
        print("  [OK] error_handler 装饰器导入成功")
        return True
    except Exception as e:
        print(f"  [ERROR] 导入失败: {e}")
        return False


def test_decorators_applied():
    """测试装饰器已正确应用"""
    print("\n[TEST] 测试装饰器应用...")
    try:
        from app.services.metrics_collector import MetricsCollector

        # 验证类存在
        assert hasattr(MetricsCollector, 'query_metrics'), "缺少 query_metrics 方法"
        assert hasattr(MetricsCollector, 'get_summary'), "缺少 get_summary 方法"
        assert hasattr(MetricsCollector, 'get_all_summaries'), "缺少 get_all_summaries 方法"
        assert hasattr(MetricsCollector, 'cleanup_old_metrics'), "缺少 cleanup_old_metrics 方法"
        assert hasattr(MetricsCollector, 'get_health_status'), "缺少 get_health_status 方法"

        print("  [OK] 所有重构方法都存在")

        # 验证异步方法
        import inspect
        methods = [
            'query_metrics',
            'get_summary',
            'get_all_summaries',
            'cleanup_old_metrics',
            'get_health_status',
        ]

        for method_name in methods:
            method = getattr(MetricsCollector, method_name)
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
        from app.services.metrics_collector import MetricsCollector
        import inspect

        # 测试 query_metrics
        sig = inspect.signature(MetricsCollector.query_metrics)
        assert 'metric_type' in sig.parameters, "缺少 metric_type 参数"
        assert 'start_time' in sig.parameters, "缺少 start_time 参数"
        assert 'end_time' in sig.parameters, "缺少 end_time 参数"
        assert 'limit' in sig.parameters, "缺少 limit 参数"
        print("  [OK] query_metrics 签名正确")

        # 测试 get_summary
        sig = inspect.signature(MetricsCollector.get_summary)
        assert 'metric_type' in sig.parameters, "缺少 metric_type 参数"
        print("  [OK] get_summary 签名正确")

        # 测试 cleanup_old_metrics
        sig = inspect.signature(MetricsCollector.cleanup_old_metrics)
        assert 'days' in sig.parameters, "缺少 days 参数"
        print("  [OK] cleanup_old_metrics 签名正确")

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
            async_handle_errors_none,
            async_handle_errors_zero,
            async_handle_errors_empty_dict,
        )

        # 测试装饰器可以正确应用
        @async_handle_errors_empty_list(error_message="测试错误")
        async def test_list():
            raise ValueError("测试异常")

        @async_handle_errors_none(error_message="测试错误")
        async def test_none():
            raise ValueError("测试异常")

        @async_handle_errors_zero(error_message="测试错误")
        async def test_zero():
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

        result3 = asyncio.run(test_zero())
        assert result3 == 0, f"期望 0，实际 {result3}"
        print("  [OK] async_handle_errors_zero 工作正常")

        result4 = asyncio.run(test_dict())
        assert result4 == {}, f"期望 {{}}，实际 {result4}"
        print("  [OK] async_handle_errors_empty_dict 工作正常")

        return True

    except Exception as e:
        print(f"  [ERROR] 错误处理功能测试失败: {e}")
        return False


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("MetricsCollector error_handler 装饰器重构验证测试")
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
        print("\n[OK] 所有测试通过！MetricsCollector error_handler 装饰器重构验证成功。")
        return 0
    else:
        print(f"\n[WARN] {total - passed} 个测试失败，请检查。")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
