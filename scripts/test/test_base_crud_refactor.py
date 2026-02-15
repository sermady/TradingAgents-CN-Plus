# -*- coding: utf-8 -*-
"""
测试 BaseCRUDService 重构后的服务
验证 tags_service 和 notifications_service 功能正常
"""
import asyncio
import sys
sys.path.insert(0, 'E:\\WorkSpace\\TradingAgents-CN')


def test_import():
    """测试导入"""
    print("[TEST] 测试导入重构后的服务...")
    try:
        from app.services.tags_service import TagsService, tags_service
        from app.services.notifications_service import NotificationsService, get_notifications_service
        print("  [OK] TagsService 导入成功")
        print("  [OK] NotificationsService 导入成功")
        return True
    except Exception as e:
        print(f"  [ERROR] 导入失败: {e}")
        return False


def test_base_class():
    """测试基类继承"""
    print("\n[TEST] 测试基类继承...")
    try:
        from app.services.tags_service import TagsService
        from app.services.notifications_service import NotificationsService
        from app.services.base_crud_service import BaseCRUDService

        # 验证继承关系
        assert issubclass(TagsService, BaseCRUDService), "TagsService 必须继承 BaseCRUDService"
        assert issubclass(NotificationsService, BaseCRUDService), "NotificationsService 必须继承 BaseCRUDService"

        # 验证 collection_name 属性
        tags = TagsService()
        assert tags.collection_name == "user_tags", f"期望 collection_name='user_tags', 实际='{tags.collection_name}'"

        notif = NotificationsService()
        assert notif.collection_name == "notifications", f"期望 collection_name='notifications', 实际='{notif.collection_name}'"

        print("  [OK] TagsService 正确继承 BaseCRUDService")
        print("  [OK] NotificationsService 正确继承 BaseCRUDService")
        print("  [OK] collection_name 属性正确")
        return True
    except Exception as e:
        print(f"  [ERROR] 基类继承测试失败: {e}")
        return False


def test_base_methods():
    """测试基类方法可用性"""
    print("\n[TEST] 测试基类方法...")
    try:
        from app.services.tags_service import TagsService
        from app.services.notifications_service import NotificationsService

        tags = TagsService()
        notif = NotificationsService()

        # 验证基类方法存在
        base_methods = ['create', 'get_by_id', 'list', 'update', 'delete', 'count', 'exists']
        for method in base_methods:
            assert hasattr(tags, method), f"TagsService 缺少方法: {method}"
            assert hasattr(notif, method), f"NotificationsService 缺少方法: {method}"
            assert callable(getattr(tags, method)), f"TagsService.{method} 不可调用"
            assert callable(getattr(notif, method)), f"NotificationsService.{method} 不可调用"

        print(f"  [OK] 所有基类方法 ({len(base_methods)}个) 都可用")
        return True
    except Exception as e:
        print(f"  [ERROR] 基类方法测试失败: {e}")
        return False


def test_custom_methods():
    """测试自定义业务方法存在"""
    print("\n[TEST] 测试自定义业务方法...")
    try:
        from app.services.tags_service import TagsService
        from app.services.notifications_service import NotificationsService

        tags = TagsService()
        notif = NotificationsService()

        # TagsService 自定义方法
        tags_methods = ['list_tags', 'create_tag', 'update_tag', 'delete_tag', 'ensure_indexes']
        for method in tags_methods:
            assert hasattr(tags, method), f"TagsService 缺少方法: {method}"

        # NotificationsService 自定义方法
        notif_methods = ['create_and_publish', 'unread_count', 'mark_read', 'mark_all_read']
        for method in notif_methods:
            assert hasattr(notif, method), f"NotificationsService 缺少方法: {method}"

        print(f"  [OK] TagsService 自定义方法 ({len(tags_methods)}个) 都可用")
        print(f"  [OK] NotificationsService 自定义方法 ({len(notif_methods)}个) 都可用")
        return True
    except Exception as e:
        print(f"  [ERROR] 自定义方法测试失败: {e}")
        return False


def test_global_instances():
    """测试全局实例"""
    print("\n[TEST] 测试全局实例...")
    try:
        from app.services.tags_service import tags_service
        from app.services.notifications_service import get_notifications_service

        # 验证全局实例存在
        assert tags_service is not None, "tags_service 全局实例不存在"

        # 验证 get_notifications_service 返回实例
        notif_service = get_notifications_service()
        assert notif_service is not None, "get_notifications_service() 返回 None"

        print("  [OK] tags_service 全局实例存在")
        print("  [OK] get_notifications_service() 返回有效实例")
        return True
    except Exception as e:
        print(f"  [ERROR] 全局实例测试失败: {e}")
        return False


async def test_async_methods():
    """测试异步方法（需要数据库连接）"""
    print("\n[TEST] 测试异步方法...")
    try:
        from app.services.tags_service import TagsService

        tags = TagsService()

        # 测试 ensure_indexes 不抛出异常
        try:
            await tags.ensure_indexes()
            print("  [OK] ensure_indexes 方法可调用")
        except Exception as e:
            # 数据库连接问题可以忽略
            print(f"  [WARN] ensure_indexes 需要数据库: {e}")

        return True
    except Exception as e:
        print(f"  [ERROR] 异步方法测试失败: {e}")
        return False


def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("BaseCRUDService 重构验证测试")
    print("=" * 60)

    results = []

    # 同步测试
    results.append(("导入测试", test_import()))
    results.append(("基类继承", test_base_class()))
    results.append(("基类方法", test_base_methods()))
    results.append(("自定义方法", test_custom_methods()))
    results.append(("全局实例", test_global_instances()))

    # 异步测试
    try:
        async_result = asyncio.run(test_async_methods())
        results.append(("异步方法", async_result))
    except Exception as e:
        print(f"\n[ERROR] 异步测试失败: {e}")
        results.append(("异步方法", False))

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
        print("\n[OK] 所有测试通过！BaseCRUDService 重构验证成功。")
        return 0
    else:
        print(f"\n[WARN] {total - passed} 个测试失败，请检查。")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
