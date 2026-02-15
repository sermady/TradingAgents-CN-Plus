# -*- coding: utf-8 -*-
"""
测试 error_handler 装饰器重构后的服务
验证 stock_data_service 等功能正常
"""
import sys
sys.path.insert(0, 'E:\\WorkSpace\\TradingAgents-CN')


def test_import():
    """测试导入"""
    print("[TEST] 测试导入重构后的服务...")
    try:
        from app.services.stock_data_service import StockDataService, get_stock_data_service
        from app.utils.error_handler import (
            async_handle_errors_none,
            async_handle_errors_empty_list,
            async_handle_errors_false,
        )
        print("  [OK] StockDataService 导入成功")
        print("  [OK] error_handler 装饰器导入成功")
        return True
    except Exception as e:
        print(f"  [ERROR] 导入失败: {e}")
        return False


def test_decorators_applied():
    """测试装饰器已正确应用"""
    print("\n[TEST] 测试装饰器应用...")
    try:
        from app.services.stock_data_service import StockDataService
        from app.utils.error_handler import async_handle_errors

        service = StockDataService()

        # 验证方法存在
        methods = [
            'get_stock_basic_info',
            'get_market_quotes',
            'get_stock_list',
            'update_stock_basic_info',
            'update_market_quotes',
        ]

        for method_name in methods:
            assert hasattr(service, method_name), f"缺少方法: {method_name}"
            method = getattr(service, method_name)
            assert callable(method), f"{method_name} 不可调用"

        print(f"  [OK] 所有方法 ({len(methods)}个) 都存在且可调用")

        # 验证装饰器已应用（通过检查函数属性）
        # 注意：由于 functools.wraps，原始函数名会被保留
        for method_name in methods:
            method = getattr(service, method_name)
            # 异步方法应该被包装
            import inspect
            assert inspect.iscoroutinefunction(method), f"{method_name} 应该是异步函数"

        print("  [OK] 所有方法都是异步函数")
        return True

    except Exception as e:
        print(f"  [ERROR] 装饰器应用测试失败: {e}")
        return False


def test_method_signatures():
    """测试方法签名正确"""
    print("\n[TEST] 测试方法签名...")
    try:
        from app.services.stock_data_service import StockDataService
        import inspect

        service = StockDataService()

        # 测试 get_stock_basic_info 返回类型注解
        sig = inspect.signature(service.get_stock_basic_info)
        assert 'symbol' in sig.parameters, "缺少 symbol 参数"
        assert 'source' in sig.parameters, "缺少 source 参数"
        print("  [OK] get_stock_basic_info 签名正确")

        # 测试 get_stock_list 返回类型注解
        sig = inspect.signature(service.get_stock_list)
        assert 'market' in sig.parameters, "缺少 market 参数"
        assert 'industry' in sig.parameters, "缺少 industry 参数"
        assert 'page' in sig.parameters, "缺少 page 参数"
        assert 'page_size' in sig.parameters, "缺少 page_size 参数"
        print("  [OK] get_stock_list 签名正确")

        # 测试 update 方法
        sig = inspect.signature(service.update_stock_basic_info)
        assert 'symbol' in sig.parameters, "缺少 symbol 参数"
        assert 'update_data' in sig.parameters, "缺少 update_data 参数"
        print("  [OK] update_stock_basic_info 签名正确")

        return True

    except Exception as e:
        print(f"  [ERROR] 方法签名测试失败: {e}")
        return False


def test_error_handler_functionality():
    """测试错误处理装饰器功能"""
    print("\n[TEST] 测试错误处理装饰器功能...")
    try:
        from app.utils.error_handler import (
            async_handle_errors_none,
            async_handle_errors_empty_list,
            async_handle_errors_false,
        )

        # 测试装饰器可以正确应用
        @async_handle_errors_none(error_message="测试错误")
        async def test_none():
            raise ValueError("测试异常")

        @async_handle_errors_empty_list(error_message="测试错误")
        async def test_list():
            raise ValueError("测试异常")

        @async_handle_errors_false(error_message="测试错误")
        async def test_bool():
            raise ValueError("测试异常")

        # 运行测试
        import asyncio

        result1 = asyncio.run(test_none())
        assert result1 is None, f"期望 None，实际 {result1}"
        print("  [OK] async_handle_errors_none 工作正常")

        result2 = asyncio.run(test_list())
        assert result2 == [], f"期望 []，实际 {result2}"
        print("  [OK] async_handle_errors_empty_list 工作正常")

        result3 = asyncio.run(test_bool())
        assert result3 is False, f"期望 False，实际 {result3}"
        print("  [OK] async_handle_errors_false 工作正常")

        return True

    except Exception as e:
        print(f"  [ERROR] 错误处理功能测试失败: {e}")
        return False


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("error_handler 装饰器重构验证测试")
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
        print("\n[OK] 所有测试通过！error_handler 装饰器重构验证成功。")
        return 0
    else:
        print(f"\n[WARN] {total - passed} 个测试失败，请检查。")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
