# -*- coding: utf-8 -*-
"""
测试 Tushare 每小时批量同步的频率限制功能

运行方式:
    python scripts/test_rate_limit.py

功能说明:
    - 第一次运行：正常执行（设置频率限制标记）
    - 第二次运行：检测到频率限制，跳过执行
    - 验证 Redis 中的频率限制标记是否正确设置
"""

import asyncio
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, "E:\\WorkSpace\\TradingAgents-CN")


async def test_rate_limit():
    """测试频率限制功能"""
    print("=" * 70)
    print("测试 Tushare rt_k 频率限制功能")
    print("=" * 70)

    # 模拟当前时间（交易时段）
    from app.core.config import get_settings

    settings = get_settings()
    tz = ZoneInfo(settings.TIMEZONE)
    now = datetime.now(tz)

    print(f"\n当前时间: {now.isoformat()}")
    print(f"时区: {settings.TIMEZONE}")

    # 生成频率限制 Key
    current_hour_key = now.strftime("%Y%m%d_%H")
    rate_limit_key = f"tushare_rt_k_rate_limit:{current_hour_key}"

    print(f"\n频率限制 Key: {rate_limit_key}")

    # 检查 Redis 中的标记
    try:
        from app.core.database import get_redis_client

        redis = get_redis_client()

        # 检查是否已有标记
        existing = await redis.get(rate_limit_key)
        if existing:
            print(f"\n[WARNING] 检测到已有频率限制标记")
            print(
                f"上次调用时间: {existing.decode() if isinstance(existing, bytes) else existing}"
            )
            print(f"\n[OK] 频率限制检查正常工作 - 本小时已调用过，应当跳过")
        else:
            print(f"\n[OK] 未检测到频率限制标记")
            print(f"说明：这是本小时的首次调用，或频率限制标记已过期")

            # 设置测试标记
            await redis.setex(rate_limit_key, 3600, now.isoformat())
            print(f"\n[LOCK] 已设置测试频率限制标记（TTL: 3600秒）")

        # 验证标记是否设置成功
        verify = await redis.get(rate_limit_key)
        if verify:
            print(f"\n[OK] 验证成功：标记已正确设置")
            ttl = await redis.ttl(rate_limit_key)
            print(f"剩余 TTL: {ttl} 秒")
        else:
            print(f"\n[FAIL] 验证失败：标记未设置")

    except Exception as e:
        print(f"\n[ERROR] Redis 连接失败: {e}")
        print("请确保 Redis 服务已启动")
        return False

    # 测试完整的同步函数
    print("\n" + "=" * 70)
    print("测试完整的 run_tushare_hourly_bulk_sync() 函数")
    print("=" * 70)

    try:
        from app.worker.tushare_sync_service import run_tushare_hourly_bulk_sync

        result = await run_tushare_hourly_bulk_sync()

        print(f"\n执行结果:")
        print(f"  skipped: {result.get('skipped', False)}")
        print(f"  reason: {result.get('reason', 'N/A')}")

        if result.get("skipped"):
            if "频率限制" in result.get("reason", ""):
                print(f"\n[OK] 频率限制功能正常工作！")
                print(f"  - 本小时已调用过 rt_k 接口")
                print(f"  - 系统正确跳过以避免频率限制错误")
            elif "非交易" in result.get("reason", ""):
                print(f"\n[INFO] 当前不在交易时段，跳过执行（这是正常的）")
        else:
            print(f"\n[INFO] 同步成功执行")
            print(f"  - 总计: {result.get('total', 0)} 只股票")
            print(f"  - MongoDB: {result.get('mongo_success', 0)} 成功")

    except Exception as e:
        print(f"\n[ERROR] 同步函数执行失败: {e}")
        import traceback

        print(f"\n详细错误:\n{traceback.format_exc()}")
        return False

    print("\n" + "=" * 70)
    print("[DONE] 测试完成")
    print("=" * 70)
    return True


if __name__ == "__main__":
    # 检查是否在交易时段
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from app.core.config import get_settings

    settings = get_settings()
    tz = ZoneInfo(settings.TIMEZONE)
    now = datetime.now(tz)

    if now.weekday() > 4:
        print("[WARNING] 今天是周末，不在交易时段")
        print("提示：测试仍会继续执行，但会因为非交易时段而跳过")
        print()

    # 运行测试
    result = asyncio.run(test_rate_limit())
    sys.exit(0 if result else 1)
