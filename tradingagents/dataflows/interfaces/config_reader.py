# -*- coding: utf-8 -*-
"""
数据源配置读取模块

从数据库读取用户启用的数据源配置
"""

from .base_interface import logger


def _get_enabled_hk_data_sources() -> list:
    """
    从数据库读取用户启用的港股数据源配置

    Returns:
        list: 按优先级排序的数据源列表，如 ['akshare', 'yfinance']
    """
    try:
        # 尝试从数据库读取配置
        from app.core.database import get_mongo_db_sync

        db = get_mongo_db_sync()

        # 获取最新的激活配置
        config_data = db.system_configs.find_one(
            {"is_active": True}, sort=[("version", -1)]
        )

        if config_data and config_data.get("data_source_configs"):
            data_source_configs = config_data.get("data_source_configs", [])

            # 过滤出启用的港股数据源
            enabled_sources = []
            for ds in data_source_configs:
                if not ds.get("enabled", True):
                    continue

                # 检查是否支持港股市场（支持中英文标识）
                market_categories = ds.get("market_categories", [])
                if market_categories:
                    # 支持 '港股' 或 'hk_stocks'
                    if (
                        "港股" not in market_categories
                        and "hk_stocks" not in market_categories
                    ):
                        continue

                # 映射数据源类型
                ds_type = ds.get("type", "").lower()
                if ds_type in ["akshare", "yfinance", "finnhub"]:
                    enabled_sources.append(
                        {"type": ds_type, "priority": ds.get("priority", 0)}
                    )

            # 按优先级排序（数字越大优先级越高）
            enabled_sources.sort(key=lambda x: x["priority"], reverse=True)

            result = [s["type"] for s in enabled_sources]
            if result:
                logger.info(f"✅ [港股数据源] 从数据库读取: {result}")
                return result
            else:
                logger.warning(
                    f"⚠️ [港股数据源] 数据库中没有启用的港股数据源，使用默认顺序"
                )
        else:
            logger.warning("⚠️ [港股数据源] 数据库中没有配置，使用默认顺序")
    except Exception as e:
        logger.warning(f"⚠️ [港股数据源] 从数据库读取失败: {e}，使用默认顺序")

    # 回退到默认顺序
    return ["akshare", "yfinance"]


def _get_enabled_us_data_sources() -> list:
    """
    从数据库读取用户启用的美股数据源配置

    Returns:
        list: 按优先级排序的数据源列表，如 ['yfinance', 'finnhub']
    """
    try:
        # 尝试从数据库读取配置
        from app.core.database import get_mongo_db_sync

        db = get_mongo_db_sync()

        # 获取最新的激活配置
        config_data = db.system_configs.find_one(
            {"is_active": True}, sort=[("version", -1)]
        )

        if config_data and config_data.get("data_source_configs"):
            data_source_configs = config_data.get("data_source_configs", [])

            # 过滤出启用的美股数据源
            enabled_sources = []
            for ds in data_source_configs:
                if not ds.get("enabled", True):
                    continue

                # 检查是否支持美股市场（支持中英文标识）
                market_categories = ds.get("market_categories", [])
                if market_categories:
                    # 支持 '美股' 或 'us_stocks'
                    if (
                        "美股" not in market_categories
                        and "us_stocks" not in market_categories
                    ):
                        continue

                # 映射数据源类型
                ds_type = ds.get("type", "").lower()
                if ds_type in ["yfinance", "finnhub"]:
                    enabled_sources.append(
                        {"type": ds_type, "priority": ds.get("priority", 0)}
                    )

            # 按优先级排序（数字越大优先级越高）
            enabled_sources.sort(key=lambda x: x["priority"], reverse=True)

            result = [s["type"] for s in enabled_sources]
            if result:
                logger.info(f"✅ [美股数据源] 从数据库读取: {result}")
                return result
            else:
                logger.warning(
                    f"⚠️ [美股数据源] 数据库中没有启用的美股数据源，使用默认顺序"
                )
        else:
            logger.warning("⚠️ [美股数据源] 数据库中没有配置，使用默认顺序")
    except Exception as e:
        logger.warning(f"⚠️ [美股数据源] 从数据库读取失败: {e}，使用默认顺序")

    # 回退到默认顺序
    return ["yfinance", "finnhub"]
