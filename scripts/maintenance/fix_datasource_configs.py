# -*- coding: utf-8 -*-
"""
直接修复数据源配置的脚本
直接在数据库中添加 akshare 和 baostock 的配置
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def fix_datasource_configs():
    """修复数据源配置"""
    from app.core.config import settings
    from pymongo import MongoClient
    from datetime import datetime

    try:
        # 连接数据库
        client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[settings.MONGO_DB]
        print("✅ 成功连接数据库")

        # 检查当前配置
        sys_config = db.system_configs.find_one({"is_active": True})
        if not sys_config:
            print("\n未找到激活的配置，创建新配置")
            sys_config = {
                "version": "1.0.0",
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "data_source_configs": [],
            }

        data_source_configs = sys_config.get("data_source_configs", [])
        print(f"\n=== 当前数据源配置 (共{len(data_source_configs)}个) ===")
        for idx, ds in enumerate(data_source_configs, 1):
            print(
                f"{idx}. {ds.get('name', 'unknown')} - priority={ds.get('priority', 0)}, enabled={ds.get('enabled', False)}"
            )

        # 检查是否需要添加 akshare 和 baostock
        ds_names = [ds.get("name", "").lower() for ds in data_source_configs]
        has_akshare = "akshare" in ds_names
        has_baostock = "baostock" in ds_names

        print(f"\n=== 数据源检查 ===")
        print(f"AKShare存在: {has_akshare}")
        print(f"BaoStock存在: {has_baostock}")

        missing_configs = []

        if not has_akshare:
            print("\n➕ 添加 AKShare 配置...")
            missing_configs.append(
                {
                    "name": "akshare",
                    "type": "akshare",
                    "display_name": "AKShare (开源免费)",
                    "description": "开源免费数据源，适合快速测试和学习",
                    "enabled": True,
                    "priority": 2,
                    "market_categories": ["a_shares"],
                    "config_params": {
                        "use_for_analysis": True,
                        "use_for_realtime": True,
                        "use_for_news": True,
                    },
                }
            )

        if not has_baostock:
            print("\n➕ 添加 BaoStock 配置...")
            missing_configs.append(
                {
                    "name": "baostock",
                    "type": "baostock",
                    "display_name": "BaoStock (开源历史)",
                    "description": "开源免费数据源，适合获取历史数据",
                    "enabled": True,
                    "priority": 1,
                    "market_categories": ["a_shares"],
                    "config_params": {
                        "use_for_analysis": True,
                        "use_for_realtime": False,
                        "use_for_news": False,
                    },
                }
            )

        if missing_configs:
            print(f"\n=== 将添加 {len(missing_configs)} 个数据源配置 ===")
            data_source_configs.extend(missing_configs)

            # 更新配置
            result = db.system_configs.update_one(
                {"is_active": True},
                {
                    "$set": {
                        "updated_at": datetime.utcnow(),
                        "data_source_configs": data_source_configs,
                    }
                },
            )

            print(f"\n✅ 成功更新系统配置")

            # 检查数据源分组配置
            print("\n=== 检查 datasource_groupings ===")
            ds_groupings = list(db.datasource_groupings.find().limit(10))
            print(f"datasource_groupings 文档数: {len(ds_groupings)}")
            for group in ds_groupings:
                print(
                    f" - {group.get('data_source_name')}, 优先级: {group.get('priority')}, 启用: {group.get('enabled')}"
                )

            # 更新或插入数据源分组配置
            added_groups = 0
            for ds_config in missing_configs:
                ds_name = ds_config["name"]
                ds_type = ds_config["type"]
                priority = ds_config["priority"]
                market_category = "a_shares"

                # 检查是否已存在配置
                existing = db.datasource_groupings.find_one(
                    {"data_source_name": ds_name, "market_category_id": market_category}
                )

                if existing:
                    # 更新现有配置
                    db.datasource_groupings.update_one(
                        {
                            "data_source_name": ds_name,
                            "market_category_id": market_category,
                        },
                        {
                            "$set": {
                                "priority": priority,
                                "enabled": True,
                                "updated_at": datetime.utcnow(),
                            }
                        },
                    )
                    print(f"\n✅ 更新 {ds_name} 在 A股市场的配置")
                    added_groups += 1
                else:
                    # 插入新配置
                    db.datasource_groupings.insert_one(
                        {
                            "data_source_name": ds_name,
                            "market_category_id": market_category,
                            "priority": priority,
                            "enabled": True,
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow(),
                        }
                    )
                    print(f"\n✅ 创建 {ds_name} 在 A股市场的配置")
                    added_groups += 1

            print(f"\n✅ 数据源配置和分组配置已更新 (添加了{added_groups}个分组配置)")

        else:
            print("\n✅ 数据源配置已完整，无需更新")

        # 验证结果
        print("\n=== 验证配置 ===")
        sys_config = db.system_configs.find_one({"is_active": True})
        ds_configs = sys_config.get("data_source_configs", [])

        print(f"系统配置版本: {sys_config.get('version')}")
        print(f"数据源总数: {len(ds_configs)}")
        print("\n数据源列表:")
        for ds in ds_configs:
            print(f"  - {ds.get('display_name')} (优先级: {ds.get('priority')})")
            if ds.get("enabled"):
                print(f"    ✅ 已启用")
            else:
                print(f"    ❌ 已禁用")

        # 检查 datasource_groupings
        print("\n数据源分组配置:")
        groupings = list(
            db.datasource_groupings.find({"market_category_id": "a_shares"})
        )
        for group in groupings:
            print(
                f"  - {group.get('data_source_name')}: 优先级 {group.get('priority')}, 启用 {group.get('enabled')}"
            )

        client.close()
        print("\n✅ 数据源配置修复完成")
        return True

    except Exception as e:
        print(f"❌ 数据源配置修复失败: {e}")
        import traceback

        print(f"堆栈跟踪:\n{traceback.format_exc()}")
        return False


if __name__ == "__main__":
    asyncio.run(fix_datasource_configs())
