# -*- coding: utf-8 -*-
"""
数据源配置初始化脚本
确保 akshare 和 baostock 在数据库中有正确的配置
"""

import asyncio
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())


async def init_datasource_configs():
    """初始化数据源配置"""
    # 先尝试直接导入
    try:
        from app.core.database import get_mongo_db
        from datetime import datetime
    except ModuleNotFoundError:
        # 从容器内部运行
        import os

        sys.path.insert(0, "/app")
        from app.core.database import get_mongo_db
        from datetime import datetime

    try:
        db = get_mongo_db()
        print("✅ 成功连接数据库")

        # 检查是否已有激活配置
        existing_config = await db.system_configs.find_one({"is_active": True})

        if existing_config:
            print("\n=== 已有激活的配置 ===")
            config = existing_config.get("data_source_configs", [])
            for ds in config:
                print(
                    f"  - {ds.get('name')}: priority={ds.get('priority')}, enabled={ds.get('enabled')}"
                )
            print("\n检查配置是否包含 akshare 和 baostock...")
            has_akshare = any(ds.get("name", "").lower() == "akshare" for ds in config)
            has_baostock = any(
                ds.get("name", "").lower() == "baostock" for ds in config
            )

            if has_akshare and has_baostock:
                print("✅ 数据库中已存在所有数据源配置")
                return True
            elif has_akshare or has_baost:
                print("⚠️ 数据库中缺少部分数据源配置，将补充缺失的配置")
            else:
                print("⚠️ 数据库中没有数据源配置，将创建完整配置")
        else:
            print("⚠️ 数据库中没有激活配置，将创建新配置")

        # 创建数据源配置
        data_source_configs = [
            {
                "name": "tushare",
                "type": "tushare",
                "display_name": "TuShare (认证数据源)",
                "description": "高质量付费数据源，适合正式分析",
                "enabled": True,
                "priority": 3,
                "market_categories": ["a_shares"],
                "config_params": {
                    "use_for_analysis": True,
                    "use_for_realtime": True,
                    "use_for_news": True,
                },
            },
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
            },
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
        ]

        # 创建系统配置文档
        system_config = {
            "version": "1.0.0",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "data_source_configs": data_source_configs,
        }

        # 插入或更新系统配置
        result = await db.system_configs.update_one(
            {"is_active": True}, {"$set": system_config, "upsert": True}
        )

        print(f"\n✅ {'创建' if result.upserted_id else '更新'}了系统配置")
        print("\n=== 创建的数据源配置 ===")
        for ds in data_source_configs:
            print(f"  📊 {ds['display_name']}")
            print(f"     类型: {ds['type']}")
            print(f"     优先级: {ds['priority']}")
            print(f"     支持的市场: {', '.join(ds['market_categories'])}")
            print(f"     状态: {'启用' if ds['enabled'] else '禁用'}")
            if ds.get("config_params"):
                print(f"     配置: {ds['config_params']}")

        print("\n💡 优先级说明:")
        print("   - 数字越大优先级越高")
        print("   - Baostock (优先级1): 开源历史数据，作为最后兜底")
        print("   - AKShare (优先级2): 开源实时数据，适合快速测试")
        print("   - TuShare (优先级3): 付费数据源，高质量分析")

        print("\n✅ 数据源配置初始化完成")
        return True

    except Exception as e:
        print(f"❌ 初始化数据源配置失败: {e}")
        import traceback

        print(f"堆栈跟踪:\n{traceback.format_exc()}")
        return False


if __name__ == "__main__":
    asyncio.run(init_datasource_configs())
