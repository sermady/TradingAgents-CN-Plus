# -*- coding: utf-8 -*-
"""
分析路由简化测试脚本

只测试不需要认证的端点
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)


async def test_routes():
    """测试 analysis 路由的公开端点"""
    print("=" * 50)
    print("[TEST] 开始测试 analysis 路由（公开端点）...")

    # 导入必要的模块
    try:
        from app.routers.analysis.routes import router
        print("[OK] 成功导入 app.routers.analysis.routes.router")
    except Exception as e:
        print(f"[ERROR] 导入失败: {e}")
        return False

    # 检查端点列表
    endpoints = [route for route in router.routes]
    print(f"[INFO] 发现 {len(endpoints)} 个端点")
    for endpoint in endpoints:
        print(f"   路径: {endpoint.path}")
        print(f"   方法: {endpoint.methods}")

    # 基本功能测试
    basic_tests_passed = True

    # 测试测试路由（不需要认证）
    try:
        from fastapi.testclient import TestClient

        with TestClient(app=router, base_url="http://test") as client:
            # 测试 /test-route
            response = client.get("/test-route")

            # 检查响应
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert data["message"] == "测试路由工作正常"

            print("   [OK] GET /test-route - 端点测试通过")
    except Exception as e:
        print(f"   [ERROR] GET /test-route - 端点测试失败: {e}")
        basic_tests_passed = False

    # 测试路由器是否正确注册
    try:
        # 验证路由器配置
        assert router.prefix == "", "路由前缀应为空字符串"
        assert router.tags is None or len(router.tags) == 0, "路由标签应为空"
        print("   [OK] 路由器配置验证通过")
    except Exception as e:
        print(f"   [ERROR] 路由器配置验证失败: {e}")
        basic_tests_passed = False

    # 汇总结果
    print("=" * 50)
    if basic_tests_passed:
        print("[SUCCESS] 所有基本功能测试通过！")
    else:
        print("[WARNING] 部分基本功能测试失败，需要修复")

    return basic_tests_passed


if __name__ == "__main__":
    asyncio.run(test_routes())
