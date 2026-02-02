#!/usr/bin/env python3
"""
同步 605589 (圣泉集团) 的每股指标数据到 MongoDB
从 Tushare 获取最新数据并更新 stock_basic_info 集合
"""

import asyncio
import sys
from datetime import datetime
from pymongo import MongoClient

# 添加项目路径
sys.path.insert(0, r"E:\WorkSpace\TradingAgents-CN")

from tradingagents.dataflows.providers.china.tushare import TushareProvider


async def sync_per_share_metrics():
    """同步每股指标数据"""
    symbol = "605589"

    print(f"开始同步 {symbol} (圣泉集团) 的每股指标数据...")
    print("=" * 70)

    # 创建Tushare提供器并获取数据
    provider = TushareProvider()

    try:
        # 获取股票基本信息（包含每股指标）
        stock_basic_result = await provider.get_stock_basic_info(symbol)

        if not stock_basic_result:
            print("❌ 从Tushare获取数据失败")
            return False

        # 处理返回值（可能是字典或列表）
        if isinstance(stock_basic_result, list):
            stock_basic = stock_basic_result[0] if stock_basic_result else None
        else:
            stock_basic = stock_basic_result

        if not stock_basic:
            print("❌ 无法解析Tushare返回数据")
            return False

        print("\n【从Tushare获取的数据】")
        per_share_fields = [
            "eps",
            "bps",
            "ocfps",
            "capital_rese_ps",
            "undist_profit_ps",
        ]
        for field in per_share_fields:
            value = stock_basic.get(field)
            print(f"  {field}: {value}")

        # 连接MongoDB
        client = MongoClient(
            "mongodb://admin:tradingagents123@localhost:27017/tradingagents?authSource=admin"
        )
        db = client["tradingagents"]

        # 准备更新数据
        update_data = {
            "eps": stock_basic.get("eps"),
            "bps": stock_basic.get("bps"),
            "ocfps": stock_basic.get("ocfps"),
            "capital_rese_ps": stock_basic.get("capital_rese_ps"),
            "undist_profit_ps": stock_basic.get("undist_profit_ps"),
            "updated_at": datetime.now(),
            "per_share_metrics_synced": True,
        }

        # 更新 stock_basic_info 集合
        result = db.stock_basic_info.update_one({"code": symbol}, {"$set": update_data})

        print(f"\n【MongoDB 更新结果】")
        print(f"  匹配文档数: {result.matched_count}")
        print(f"  修改文档数: {result.modified_count}")

        if result.matched_count > 0:
            print(f"\n✅ 成功更新 {symbol} 的每股指标数据到 MongoDB")

            # 验证更新
            doc = db.stock_basic_info.find_one({"code": symbol})
            print("\n【验证更新后的数据】")
            for field in per_share_fields:
                value = doc.get(field)
                print(f"  {field}: {value}")

            client.close()
            return True
        else:
            print(f"\n❌ 未找到 {symbol} 的文档")
            client.close()
            return False

    except Exception as e:
        print(f"❌ 同步失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(sync_per_share_metrics())
    sys.exit(0 if success else 1)
