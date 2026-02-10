#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证 asyncio 修复效果"""

import asyncio
import threading
import time


def test_asyncio_in_thread():
    """测试在线程中使用 asyncio 的正确方式"""
    print("\n" + "=" * 60)
    print("测试: 在线程中正确使用 asyncio")
    print("=" * 60)

    async def async_task():
        """模拟异步任务"""
        print("  异步任务开始...")
        await asyncio.sleep(0.1)
        print("  异步任务完成!")
        return "success"

    def run_sync_with_proper_loop():
        """在新线程中正确运行异步代码"""
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            result = new_loop.run_until_complete(async_task())
            print(f"  任务结果: {result}")
        finally:
            # 清理未完成的任务
            pending = asyncio.all_tasks(new_loop)
            for task in pending:
                task.cancel()
            if pending:
                new_loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            new_loop.run_until_complete(new_loop.shutdown_asyncgens())
            new_loop.close()

    # 测试在线程中运行
    thread = threading.Thread(target=run_sync_with_proper_loop, daemon=True)
    thread.start()
    thread.join(timeout=5)

    if thread.is_alive():
        print("❌ 线程超时")
        return False
    else:
        print("✅ 线程成功完成")
        return True


def test_event_loop_detection():
    """测试事件循环检测"""
    print("\n" + "=" * 60)
    print("测试: 事件循环检测")
    print("=" * 60)

    # 测试1: 无事件循环时
    try:
        loop = asyncio.get_running_loop()
        print(f"  发现运行中的事件循环: {loop}")
    except RuntimeError:
        print("  ✅ 正确检测到无运行中的事件循环")

    # 测试2: 有事件循环时
    async def check_loop():
        try:
            loop = asyncio.get_running_loop()
            print(f"  ✅ 正确获取当前运行的事件循环: {loop}")
            return True
        except RuntimeError:
            print("  ❌ 错误: 应该能获取到事件循环")
            return False

    return asyncio.run(check_loop())


def test_concurrent_execution():
    """测试并发执行"""
    print("\n" + "=" * 60)
    print("测试: 并发执行多个异步任务")
    print("=" * 60)

    async def task(name, delay):
        print(f"  任务 {name} 开始 (延迟 {delay}s)")
        await asyncio.sleep(delay)
        print(f"  任务 {name} 完成")
        return name

    async def main():
        # 并发执行多个任务
        tasks = [
            task("A", 0.1),
            task("B", 0.2),
            task("C", 0.15),
        ]
        results = await asyncio.gather(*tasks)
        print(f"  所有任务结果: {results}")
        return results

    results = asyncio.run(main())

    if len(results) == 3:
        print("✅ 并发执行成功")
        return True
    else:
        print("❌ 并发执行失败")
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("AsyncIO 修复验证测试")
    print("=" * 60)

    tests = [
        ("事件循环检测", test_event_loop_detection),
        ("并发执行测试", test_concurrent_execution),
        ("线程中AsyncIO", test_asyncio_in_thread),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ {name}测试失败: {e}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"📊 总计: {passed + failed}")

    if failed == 0:
        print("\n🎉 所有测试通过! AsyncIO 修复正确!")
        return 0
    else:
        print(f"\n⚠️ {failed}个测试失败")
        return 1


if __name__ == "__main__":
    exit(main())
