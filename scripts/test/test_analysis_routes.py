# -*- coding: utf-8 -*-
"""
分析路由测试脚本

验证 app/routers/analysis 路由的所有端点功能
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)


async def test_routes():
    """测试 analysis 路由的所有端点"""
    print("=" * 50)
    print("[TEST] 开始测试 analysis 路由...")

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
        print(f"   {endpoint.path}")
        print(f"   方法: {endpoint.methods}")

    # 基本功能测试
    basic_tests_passed = True

    # 测试单股分析端点
    try:
        from fastapi.testclient import TestClient
        from app.routers.analysis.schemas import SingleAnalysisRequest

        with TestClient(app=router) as client:
            # 测试数据
            test_data = SingleAnalysisRequest(
                symbol="000001",
                parameters={
                    "market_type": "A股",
                    "research_depth": "快速"
                }
            )

            # 发送请求
            response = client.post("/single", json=test_data.dict())

            # 检查响应
            assert response.status_code == 200
            assert "success" in response.json()
            assert "data" in response.json()

            print("   [OK] POST /single - 端点测试通过")
    except Exception as e:
            print(f"   [ERROR] POST /single - 端点测试失败: {e}")
            basic_tests_passed = False

    # 测试批量分析端点
    try:
        from fastapi.testclient import TestClient
        from app.routers.analysis.schemas import BatchAnalysisRequest

        with TestClient(app=router) as client:
            # 测试数据
            test_data = BatchAnalysisRequest(
                title="批量测试",
                symbols=["000001", "000002"],
                parameters={
                    "market_type": "A股",
                    "research_depth": "快速"
                }
            )

            # 发送请求
            response = client.post("/batch", json=test_data.dict())

            # 检查响应
            assert response.status_code == 200
            assert "success" in response.json()
            assert "data" in response.json()

            print("   [OK] POST /batch - 端点测试通过")
    except Exception as e:
            print(f"   [ERROR] POST /batch - 端点测试失败: {e}")
            basic_tests_passed = False

    # 测试状态查询端点
    try:
        task_id = "test_task_123"

        with TestClient(app=router) as client:
            response = client.get(f"/tasks/{task_id}/status")

            # 检查响应
            assert response.status_code == 200
            assert "success" in response.json()
            assert "task_id" in response.json()

            print("   [OK] GET /tasks/{{id}}/status - 端点测试通过")
    except Exception as e:
            print(f"   [ERROR] GET /tasks/{{id}}/status - 端点测试失败: {e}")
            basic_tests_passed = False

    # 测试结果查询端点
    try:
        task_id = "test_task_456"

        with TestClient(app=router) as client:
            response = client.get(f"/tasks/{task_id}/result")

            # 检查响应
            assert response.status_code == 200
            assert "success" in response.json()
            assert "data" in response.json()

            print("   [OK] GET /tasks/{{id}}/result - 端点测试通过")
    except Exception as e:
            print(f"   [ERROR] GET /tasks/{{id}}/result - 端点测试失败: {e}")
            basic_tests_passed = False

    # 测试任务列表端点
    try:
        with TestClient(app=router) as client:
            response = client.get("/tasks")

            # 检查响应
            assert response.status_code == 200
            assert "success" in response.json()
            assert "tasks" in response.json()

            print("   [OK] GET /tasks - 端点测试通过")
    except Exception as e:
            print(f"   [ERROR] GET /tasks - 端点测试失败: {e}")
            basic_tests_passed = False

    # 测试测试路由
    try:
        from fastapi.testclient import TestClient
        from app.core.config import settings

        with TestClient(app=router, base_url="http://test") as client:
            # 测试根路径
            response = client.get("/")
            assert response.status_code == 200

            print("   [OK] 根路径测试通过")
    except Exception as e:
        print(f"   [ERROR] 根路径测试失败: {e}")

    # 汇总结果
    print("=" * 50)
    if basic_tests_passed:
        print("[SUCCESS] 所有基本功能测试通过！")
    else:
        print("[WARNING] 部分基本功能测试失败，需要修复")

    return basic_tests_passed


if __name__ == "__main__":
    asyncio.run(test_routes())
