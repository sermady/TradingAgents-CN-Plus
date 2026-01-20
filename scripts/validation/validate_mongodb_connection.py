# -*- coding: utf-8 -*-
"""
MongoDB 连接验证脚本

用于验证 MongoDB 连接配置的正确性,包括:
- 连接测试(无认证、admin数据库、目标数据库)
- 环境变量验证
- Docker网络检查
- 连接字符串验证

使用方法:
    python scripts/validation/validate_mongodb_connection.py

返回值:
    0 - 所有测试通过
    1 - 至少有一个测试失败
"""

import os
import sys
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure


def test_connection_no_auth(mongodb_host, mongodb_port):
    """测试1: 不使用认证连接"""
    print("📊 测试 1: 不使用认证连接")
    print("-" * 80)
    try:
        uri = f"mongodb://{mongodb_host}:{mongodb_port}/"
        print(f"连接字符串: {uri}")
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        print("✅ 连接成功(无认证)")
        print(f"   服务器版本: {client.server_info()['version']}")
        client.close()
        return True
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False
    finally:
        print()


def test_connection_admin(
    mongodb_username, mongodb_password, mongodb_host, mongodb_port, mongodb_database
):
    """测试2: 使用认证连接到 admin 数据库"""
    print("📊 测试 2: 使用认证连接到 admin 数据库")
    print("-" * 80)
    try:
        uri = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_host}:{mongodb_port}/admin"
        print(
            f"连接字符串: mongodb://{mongodb_username}:***@{mongodb_host}:{mongodb_port}/admin"
        )
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        print("✅ 连接成功(admin 数据库)")

        # 列出所有数据库
        dbs = client.list_database_names()
        print(f"   可用数据库: {dbs}")
        client.close()
        return True
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False
    finally:
        print()


def test_connection_target(
    mongodb_username,
    mongodb_password,
    mongodb_host,
    mongodb_port,
    mongodb_database,
    mongodb_auth_source,
):
    """测试3: 使用认证连接到目标数据库"""
    print("📊 测试 3: 使用认证连接到目标数据库")
    print("-" * 80)
    try:
        uri = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_host}:{mongodb_port}/{mongodb_database}?authSource={mongodb_auth_source}"
        print(
            f"连接字符串: mongodb://{mongodb_username}:***@{mongodb_host}:{mongodb_port}/{mongodb_database}?authSource={mongodb_auth_source}"
        )
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        print("✅ 连接成功(目标数据库)")

        # 测试数据库操作
        db = client[mongodb_database]
        collections = db.list_collection_names()
        print(f"   数据库: {mongodb_database}")
        print(f"   集合数量: {len(collections)}")
        if collections:
            print(f"   集合列表: {collections[:5]}...")
        client.close()
        return True
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        print()


def test_connection_string(
    mongodb_username, mongodb_password, mongodb_database, connection_string
):
    """测试4: 使用 MONGODB_CONNECTION_STRING 环境变量"""
    print("📊 测试 4: 使用 MONGODB_CONNECTION_STRING 环境变量")
    print("-" * 80)
    if not connection_string:
        print("⚠️  未设置 MONGODB_CONNECTION_STRING 环境变量")
        print()
        return True  # 如果没有设置connection_string,不算失败
    try:
        # 隐藏密码
        safe_uri = (
            connection_string.replace(mongodb_password, "***")
            if mongodb_password in connection_string
            else connection_string
        )
        print(f"连接字符串: {safe_uri}")
        client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        print("✅ 连接成功(MONGODB_CONNECTION_STRING)")

        # 测试数据库操作
        db = client[mongodb_database]
        collections = db.list_collection_names()
        print(f"   数据库: {mongodb_database}")
        print(f"   集合数量: {len(collections)}")
        client.close()
        return True
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        print()


def test_docker_network(mongodb_host, mongodb_port):
    """测试5: 检查 Docker 网络连接"""
    print("📊 测试 5: 检查 Docker 网络连接")
    print("-" * 80)
    import socket

    try:
        # 尝试解析主机名
        ip = socket.gethostbyname(mongodb_host)
        print(f"✅ 主机名解析成功: {mongodb_host} -> {ip}")

        # 尝试连接端口
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((mongodb_host, mongodb_port))
        sock.close()

        if result == 0:
            print(f"✅ 端口连接成功: {mongodb_host}:{mongodb_port}")
            return True
        else:
            print(f"❌ 端口连接失败: {mongodb_host}:{mongodb_port}")
            return False
    except Exception as e:
        print(f"❌ 网络检查失败: {e}")
        return False
    finally:
        print()


def main():
    """主函数"""
    print("=" * 80)
    print("🔍 MongoDB 连接验证")
    print("=" * 80)
    print()

    # 从环境变量读取配置
    mongodb_host = os.getenv("MONGODB_HOST", "localhost")
    mongodb_port = int(os.getenv("MONGODB_PORT", "27017"))
    mongodb_username = os.getenv("MONGODB_USERNAME", "admin")
    mongodb_password = os.getenv("MONGODB_PASSWORD", "tradingagents123")
    mongodb_database = os.getenv("MONGODB_DATABASE", "tradingagents")
    mongodb_auth_source = os.getenv("MONGODB_AUTH_SOURCE", "admin")
    connection_string = os.getenv("MONGODB_CONNECTION_STRING")

    print("📋 当前配置:")
    print(f"   MONGODB_HOST: {mongodb_host}")
    print(f"   MONGODB_PORT: {mongodb_port}")
    print(f"   MONGODB_USERNAME: {mongodb_username}")
    print(f"   MONGODB_PASSWORD: {'*' * len(mongodb_password)}")
    print(f"   MONGODB_DATABASE: {mongodb_database}")
    print(f"   MONGODB_AUTH_SOURCE: {mongodb_auth_source}")
    print()

    # 运行所有测试
    results = []
    results.append(("无认证连接", test_connection_no_auth(mongodb_host, mongodb_port)))
    results.append(
        (
            "Admin数据库认证",
            test_connection_admin(
                mongodb_username,
                mongodb_password,
                mongodb_host,
                mongodb_port,
                mongodb_database,
            ),
        )
    )
    results.append(
        (
            "目标数据库认证",
            test_connection_target(
                mongodb_username,
                mongodb_password,
                mongodb_host,
                mongodb_port,
                mongodb_database,
                mongodb_auth_source,
            ),
        )
    )
    results.append(
        (
            "连接字符串",
            test_connection_string(
                mongodb_username, mongodb_password, mongodb_database, connection_string
            ),
        )
    )
    results.append(("Docker网络", test_docker_network(mongodb_host, mongodb_port)))

    # 打印总结
    print("=" * 80)
    print("📝 测试总结")
    print("=" * 80)
    print()
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
    print()

    # 检查是否有失败
    failed_tests = [name for name, passed in results if not passed]
    if failed_tests:
        print(f"❌ {len(failed_tests)} 个测试失败")
        print()
        print("如果测试失败,请检查:")
        print("1. MongoDB 容器是否正在运行")
        print("   docker ps | grep mongo")
        print()
        print("2. MongoDB 容器日志")
        print("   docker logs <mongodb_container_name>")
        print()
        print("3. Docker 网络配置")
        print("   docker network inspect <network_name>")
        print()
        print("4. 应用容器是否在同一网络")
        print("   docker inspect <app_container_name> | grep NetworkMode")
        print()
        print("5. MongoDB 用户是否已创建")
        print("   docker exec -it <mongodb_container_name> mongosh")
        print("   use admin")
        print("   db.auth('admin', 'tradingagents123')")
        print("   show users")
        print()
        print("6. 检查 .env 文件中的配置")
        print("   cat .env | grep MONGODB")
        return 1
    else:
        print("✅ 所有测试通过")
        return 0


if __name__ == "__main__":
    sys.exit(main())
