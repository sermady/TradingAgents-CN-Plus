# -*- coding: utf-8 -*-
"""
数据库相关Fixtures
"""

import os
import pytest
from typing import Generator
from pymongo import MongoClient
from pymongo.database import Database


@pytest.fixture(scope="session")
def mongodb_client() -> Generator[MongoClient, None, None]:
    """
    测试MongoDB客户端
    使用session级别，所有测试共享一个客户端
    """
    # 构建连接字符串，支持认证
    mongodb_host = os.getenv("MONGODB_HOST", "localhost")
    mongodb_port = os.getenv("MONGODB_PORT", "27017")
    mongodb_user = os.getenv("MONGODB_USERNAME")
    mongodb_password = os.getenv("MONGODB_PASSWORD")
    mongodb_auth_source = os.getenv("MONGODB_AUTH_SOURCE", "admin")

    if mongodb_user and mongodb_password:
        # 使用认证
        conn_str = f"mongodb://{mongodb_user}:{mongodb_password}@{mongodb_host}:{mongodb_port}/?authSource={mongodb_auth_source}"
    else:
        # 无认证
        conn_str = f"mongodb://{mongodb_host}:{mongodb_port}/"

    client = MongoClient(conn_str, connectTimeoutMS=5000)
    # 测试连接
    try:
        client.admin.command("ping")
        yield client
    finally:
        client.close()


@pytest.fixture(scope="function")
def test_database(mongodb_client: MongoClient) -> Generator[Database, None, None]:
    """
    隔离的测试数据库
    每个测试函数使用独立的数据库，测试后自动清理
    """
    db_name = "tradingagents_test"
    db = mongodb_client[db_name]
    yield db
    # 测试后清空数据库（不删除数据库本身，只清空集合）
    # 处理数据库需要认证的情况
    try:
        for collection_name in db.list_collection_names():
            db.drop_collection(collection_name)
    except Exception:
        # 如果数据库不可用或需要认证，忽略清理错误
        pass


@pytest.fixture
def stock_collection(test_database: Database):
    """股票数据集合"""
    return test_database["stocks"]


@pytest.fixture
def user_collection(test_database: Database):
    """用户集合"""
    return test_database["users"]


@pytest.fixture
def analysis_collection(test_database: Database):
    """分析结果集合"""
    return test_database["analysis_results"]


@pytest.fixture
def report_collection(test_database: Database):
    """报告集合"""
    return test_database["reports"]


@pytest.fixture
def favorites_collection(test_database: Database):
    """自选股集合"""
    return test_database["favorites"]


@pytest.fixture
def screening_collection(test_database: Database):
    """筛选结果集合"""
    return test_database["screening_results"]


@pytest.fixture
def operation_logs_collection(test_database: Database):
    """操作日志集合"""
    return test_database["operation_logs"]


@pytest.fixture
def notifications_collection(test_database: Database):
    """通知集合"""
    return test_database["notifications"]


@pytest.fixture
def quotes_collection(test_database: Database):
    """实时行情集合"""
    return test_database["market_quotes"]


@pytest.fixture
def config_collection(test_database: Database):
    """配置集合"""
    return test_database["config"]


@pytest.fixture
def tags_collection(test_database: Database):
    """标签集合"""
    return test_database["tags"]
