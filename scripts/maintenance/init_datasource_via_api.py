# -*- coding: utf-8 -*-
"""
通过API初始化数据源配置的脚本
确保 akshare 和 baostock 在数据库中有正确的配置
"""

import requests
import sys
import os

# API配置
API_BASE_URL = "http://localhost:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "tradingagents123"


def get_token():
    """获取访问令牌"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/auth/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            headers={"Content-Type": "application/json"},
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("data", {}).get("access_token", "")
        else:
            print(f"❌ 登录失败: {response.text}")
            return ""
    except Exception as e:
        print(f"❌ 登录异常: {e}")
        return ""


def init_datasource_configs():
    """初始化数据源配置"""
    token = get_token()
    if not token:
        print("❌ 未获取到访问令牌,无法继续")
        return False

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 创建数据源配置
    data_source_configs = [
        {
            "name": "baostock",
            "type": "baostock",
            "display_name": "BaoStock (开源历史数据)",
            "description": "开源免费数据源，适合获取历史数据",
            "enabled": True,
            "priority": 1,
            "market_categories": ["a_shares"],
            "config_params": {
                "use_for_analysis": True,
                "use_for_realtime": False,
                "use_for_news": False,
            },
        },
        {
            "name": "akshare",
            "type": "akshare",
            "display_name": "AKShare (开源免费)",
            "description": "开源免费数据源,适合快速测试和开发",
            "enabled": True,
            "priority": 2,
            "market_categories": ["a_shares"],
            "config_params": {
                "use_for_analysis": True,
                "use_for_realtime": True,
                "use_for_news": True,
            },
        },
        {
            "name": "tushare",
            "type": "tushare",
            "display_name": "Tushare (认证数据源)",
            "description": "高质量付费数据源,适合正式分析",
            "enabled": True,
            "priority": 3,
            "market_categories": ["a_shares"],
            "config_params": {
                "use_for_analysis": True,
                "use_for_realtime": True,
                "use_for_news": True,
            },
        },
    ]

    system_config = {
        "version": "1.0.1",
        "is_active": True,
        "data_source_configs": data_source_configs,
    }

    # 检查现有配置
    print("\n=== 检查现有配置 ===")
    check_response = requests.get(
        f"{API_BASE_URL}/api/datasource-groupings", headers=headers
    )

    if check_response.status_code == 200:
        existing_groups = check_response.json()
        print(f"现有数据源分组: {len(existing_groups)} 个")
        for group in existing_groups:
            ds_name = group.get("data_source_name", "unknown")
            priority = group.get("priority", 0)
            enabled = group.get("enabled", False)
            print(f"  - {ds_name}: priority={priority}, enabled={enabled}")

    # 调用初始化API
    print("\n=== 开始初始化数据源配置 ===")
    init_response = requests.post(
        f"{API_BASE_URL}/api/admin/data-sources/init", headers=headers
    )

    if init_response.status_code == 200:
        result = init_response.json()
        print(f"\n✅ 初始化状态: {init_response.status_code}")
        print(f"响应内容: {str(result)[:200]}...")

        if init_response.status_code == 200:
            print("\n=== 验证配置是否写入成功 ===")
            verify_response = requests.get(
                f"{API_BASE_URL}/api/datasource-groupings", headers=headers
            )

            if verify_response.status_code == 200:
                groups = verify_response.json()
                akshare_exists = any(
                    g.get("data_source_name", "").lower() == "akshare" for g in groups
                )
                baostock_exists = any(
                    g.get("data_source_name", "").lower() == "baostock" for g in groups
                )

                print(f"\n验证结果:")
                print(f"  akshare 配置: {'✅ 存在' if akshare_exists else '❌ 缺失'}")
                print(f"  baostock 配置: {'✅ 存在' if baostock_exists else '❌ 缺失'}")

                if akshare_exists and baostock_exists:
                    print("\n✅ 数据源配置初始化成功！")
                    return True
                else:
                    print("\n⚠️ 数据源配置初始化部分成功，请检查日志获取详细信息")
                    return True
            else:
                print(f"\n❌ 验证失败: {verify_response.text}")
                return False
        else:
            print(f"\n❌ 初始化失败: {init_response.text}")
            return False
    else:
        print(
            f"\n❌ 初始化失败: HTTP {init_response.status_code} - {init_response.text}"
        )
        return False


if __name__ == "__main__":
    try:
        print("=== 数据源配置初始化工具 ===")
        success = init_datasource_configs()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
