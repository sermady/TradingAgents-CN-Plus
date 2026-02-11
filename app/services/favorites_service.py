# -*- coding: utf-8 -*-
"""
自选股服务
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

from app.core.database import get_mongo_db
from app.models.user import FavoriteStock
from app.services.quotes_service import get_quotes_service

logger = logging.getLogger("webapi")


class FavoritesService:
    """自选股服务类"""

    def __init__(self):
        self.db = None

    async def _get_db(self):
        """获取数据库连接"""
        if self.db is None:
            self.db = get_mongo_db()
        return self.db

    def _is_valid_object_id(self, user_id: str) -> bool:
        """
        检查是否是有效的ObjectId格式
        注意：这里只检查格式，不代表数据库中实际存储的是ObjectId类型
        为了兼容性，我们统一使用 user_favorites 集合存储自选股
        """
        # 强制返回 False，统一使用 user_favorites 集合
        return False

    def _format_favorite(self, favorite: Dict[str, Any]) -> Dict[str, Any]:
        """格式化收藏条目（仅基础信息，不包含实时行情）。
        行情将在 get_user_favorites 中批量富集。
        """
        added_at = favorite.get("added_at")
        if isinstance(added_at, datetime):
            added_at = added_at.isoformat()
        return {
            "stock_code": favorite.get("stock_code"),
            "stock_name": favorite.get("stock_name"),
            "market": favorite.get("market", "A股"),
            "added_at": added_at,
            "tags": favorite.get("tags", []),
            "notes": favorite.get("notes", ""),
            "alert_price_high": favorite.get("alert_price_high"),
            "alert_price_low": favorite.get("alert_price_low"),
            # 行情占位，稍后填充
            "current_price": None,
            "change_percent": None,
            "volume": None,
        }

    def _infer_exchange_from_code(self, code: str) -> str:
        """根据股票代码推断交易所。

        A股代码规则：
        - 600/601/603/605/688/689 开头：上海证券交易所
        - 000/001/002/003/300/301/303 开头：深圳证券交易所
        - 430/83/87/88 开头：北京证券交易所
        """
        if not code:
            return "-"

        code = str(code).zfill(6)

        # 上海证券交易所
        if code.startswith(("600", "601", "603", "605", "688", "689")):
            return "上海证券交易所"

        # 深圳证券交易所
        if code.startswith(("000", "001", "002", "003", "300", "301", "303")):
            return "深圳证券交易所"

        # 北京证券交易所
        if code.startswith(("430", "83", "87", "88")):
            return "北京证券交易所"

        return "-"

    def _infer_board_from_code(self, code: str) -> str:
        """根据股票代码推断板块。

        A股代码规则：
        - 600/601/603/605/000/001 开头：主板
        - 002/003 开头：中小板（现为主板）
        - 300/301/303 开头：创业板
        - 688/689 开头：科创板
        - 430/83/87/88 开头：北交所
        """
        if not code:
            return "-"

        code = str(code).zfill(6)

        # 科创板
        if code.startswith(("688", "689")):
            return "科创板"

        # 创业板
        if code.startswith(("300", "301", "303")):
            return "创业板"

        # 北交所
        if code.startswith(("430", "83", "87", "88")):
            return "北交所"

        # 主板（包括原中小板）
        if code.startswith(("600", "601", "603", "605", "000", "001", "002", "003")):
            return "主板"

        return "-"

    async def get_user_favorites(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户自选股列表，并批量拉取实时行情进行富集（兼容字符串ID与ObjectId）。"""
        logger.info(f"🔍 get_user_favorites 被调用，user_id={user_id}")
        db = await self._get_db()

        favorites: List[Dict[str, Any]] = []
        if self._is_valid_object_id(user_id):
            # 先尝试使用 ObjectId 查询
            user = await db.users.find_one({"_id": ObjectId(user_id)})
            # 如果 ObjectId 查询失败，尝试使用字符串查询
            if user is None:
                user = await db.users.find_one({"_id": user_id})
            favorites = (user or {}).get("favorite_stocks", [])
        else:
            doc = await db.user_favorites.find_one({"user_id": user_id})
            favorites = (doc or {}).get("favorites", [])

        # 先格式化基础字段
        items = [self._format_favorite(fav) for fav in favorites]

        # 批量获取股票基础信息（板块等）
        codes = [it.get("stock_code") for it in items if it.get("stock_code")]
        # [类型安全] 确保codes是list类型（支持list/set等可迭代类型）
        if not isinstance(codes, list):
            codes = list(codes)
        logger.info(f"🔍 获取自选股基础信息，股票代码: {codes}")
        if codes:
            try:
                # 🔥 获取数据源优先级配置
                from app.core.unified_config_service import get_config_manager

                config = get_config_manager()
                data_source_configs = config.get_data_source_configs()

                # 提取启用的数据源，按优先级排序
                # 🔥 data_source_configs 是字典列表，不是对象列表
                enabled_sources = [
                    ds.get("type", "").lower()
                    for ds in data_source_configs
                    if ds.get("enabled")
                    and ds.get("type", "").lower() in ["tushare", "akshare", "baostock"]
                ]

                if not enabled_sources:
                    enabled_sources = ["tushare", "akshare", "baostock"]

                # 从 stock_basic_info 获取板块信息（按数据源优先级依次查询）
                basic_info_coll = db["stock_basic_info"]
                # [分页] 限制返回数量，防止内存溢出（用户自选股通常<500只）
                max_codes = min(len(codes), 500)

                # 🔥 按优先级依次查询各数据源，直到找到所有股票的信息
                basic_map = {}
                remaining_codes = codes[:max_codes].copy()

                for source in enabled_sources:
                    if not remaining_codes:
                        break

                    cursor = basic_info_coll.find(
                        {
                            "code": {"$in": remaining_codes},
                            "source": source,
                        },
                        {"code": 1, "sse": 1, "market": 1, "_id": 0},
                    ).limit(max_codes)
                    docs = await cursor.to_list(length=max_codes)

                    for doc in docs:
                        code = str(doc.get("code")).zfill(6)
                        if code not in basic_map:
                            basic_map[code] = doc
                            if code in remaining_codes:
                                remaining_codes.remove(code)

                # 填充板块和交易所信息
                logger.info(f"🔍 开始填充板块和交易所信息，共 {len(items)} 只股票")
                for it in items:
                    code = it.get("stock_code")
                    basic = basic_map.get(code)
                    if basic:
                        # market 字段表示板块（主板、创业板、科创板等）
                        it["board"] = basic.get("market", "-")
                        # sse 字段表示交易所（上海证券交易所、深圳证券交易所等）
                        it["exchange"] = basic.get("sse", "-")
                        logger.debug(
                            f"✅ 从数据库获取 {code}: board={it['board']}, exchange={it['exchange']}"
                        )
                    else:
                        # 🔥 从股票代码推断交易所和板块
                        it["exchange"] = self._infer_exchange_from_code(code)
                        it["board"] = self._infer_board_from_code(code)
                        logger.info(
                            f"🔥 从代码推断 {code}: board={it['board']}, exchange={it['exchange']}"
                        )
            except Exception as e:
                logger.error(f"❌ 获取板块交易所信息失败: {e}")
                # 查询失败时设置默认值
                for it in items:
                    it["board"] = "-"
                    it["exchange"] = "-"

        # 批量获取行情（优先使用入库的 market_quotes，30秒更新）
        if codes:
            try:
                coll = db["market_quotes"]
                # 兼容 AKShare (price/change_percent) 和 Tushare (close/pct_chg)
                # [分页] 限制查询数量，防止内存溢出
                max_quotes = min(len(codes), 500)
                cursor = coll.find(
                    {"code": {"$in": codes[:max_quotes]}},
                    {
                        "code": 1,
                        "close": 1,
                        "price": 1,
                        "pct_chg": 1,
                        "change_percent": 1,
                        "amount": 1,
                    },
                ).limit(max_quotes)
                docs = await cursor.to_list(length=max_quotes)
                quotes_map = {str(d.get("code")).zfill(6): d for d in (docs or [])}
                for it in items:
                    code = it.get("stock_code")
                    q = quotes_map.get(code)
                    if q:
                        # 🔥 兼容 AKShare (price/change_percent) 和 Tushare (close/pct_chg)
                        # 使用 is not None 避免 0 值被误判为 falsy
                        close = q.get("close")
                        it["current_price"] = (
                            close if close is not None else q.get("price")
                        )
                        pct_chg = q.get("pct_chg")
                        it["change_percent"] = (
                            pct_chg if pct_chg is not None else q.get("change_percent")
                        )
                # 兜底：对未命中的代码使用在线源补齐（可选）
                missing = [c for c in codes if c not in quotes_map]
                if missing:
                    try:
                        quotes_online = await get_quotes_service().get_quotes(missing)
                        for it in items:
                            code = it.get("stock_code")
                            if it.get("current_price") is None:
                                q2 = (
                                    quotes_online.get(code, {}) if quotes_online else {}
                                )
                                # 🔥 兼容 AKShare (price/change_percent) 和 Tushare (close/pct_chg)
                                # 使用 is not None 避免 0 值被误判为 falsy
                                close2 = q2.get("close")
                                it["current_price"] = (
                                    close2 if close2 is not None else q2.get("price")
                                )
                                pct_chg2 = q2.get("pct_chg")
                                it["change_percent"] = (
                                    pct_chg2
                                    if pct_chg2 is not None
                                    else q2.get("change_percent")
                                )
                    except Exception as e:
                        logger.warning(f"⚠️ 在线源补齐行情失败: {e}")
            except Exception as e:
                # 查询失败时保持占位 None，避免影响基础功能
                logger.warning(f"⚠️ 获取行情失败: {e}")

        return items

    async def add_favorite(
        self,
        user_id: str,
        stock_code: str,
        stock_name: str,
        market: str = "A股",
        tags: List[str] = None,
        notes: str = "",
        alert_price_high: Optional[float] = None,
        alert_price_low: Optional[float] = None,
    ) -> bool:
        """添加股票到自选股（兼容字符串ID与ObjectId）"""
        import logging

        logger = logging.getLogger("webapi")

        try:
            logger.info(
                f"🔧 [add_favorite] 开始添加自选股: user_id={user_id}, stock_code={stock_code}"
            )

            db = await self._get_db()
            logger.info(f"🔧 [add_favorite] 数据库连接获取成功")

            favorite_stock = {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "market": market,
                "added_at": datetime.utcnow(),
                "tags": tags or [],
                "notes": notes,
                "alert_price_high": alert_price_high,
                "alert_price_low": alert_price_low,
            }

            logger.info(f"🔧 [add_favorite] 自选股数据构建完成: {favorite_stock}")

            is_oid = self._is_valid_object_id(user_id)
            logger.info(
                f"🔧 [add_favorite] 用户ID类型检查: is_valid_object_id={is_oid}"
            )

            if is_oid:
                logger.info(f"🔧 [add_favorite] 使用 ObjectId 方式添加到 users 集合")

                # 先尝试使用 ObjectId 查询
                result = await db.users.update_one(
                    {"_id": ObjectId(user_id)},
                    {
                        "$push": {"favorite_stocks": favorite_stock},
                        "$setOnInsert": {"favorite_stocks": []},
                    },
                )
                logger.info(
                    f"🔧 [add_favorite] ObjectId查询结果: matched_count={result.matched_count}, modified_count={result.modified_count}"
                )

                # 如果 ObjectId 查询失败，尝试使用字符串查询
                if result.matched_count == 0:
                    logger.info(
                        f"🔧 [add_favorite] ObjectId查询失败，尝试使用字符串ID查询"
                    )
                    result = await db.users.update_one(
                        {"_id": user_id}, {"$push": {"favorite_stocks": favorite_stock}}
                    )
                    logger.info(
                        f"🔧 [add_favorite] 字符串ID查询结果: matched_count={result.matched_count}, modified_count={result.modified_count}"
                    )

                success = result.matched_count > 0
                logger.info(f"🔧 [add_favorite] 返回结果: {success}")
                return success
            else:
                logger.info(
                    f"🔧 [add_favorite] 使用字符串ID方式添加到 user_favorites 集合"
                )
                result = await db.user_favorites.update_one(
                    {"user_id": user_id},
                    {
                        "$setOnInsert": {
                            "user_id": user_id,
                            "created_at": datetime.utcnow(),
                        },
                        "$push": {"favorites": favorite_stock},
                        "$set": {"updated_at": datetime.utcnow()},
                    },
                    upsert=True,
                )
                logger.info(
                    f"🔧 [add_favorite] 更新结果: matched_count={result.matched_count}, modified_count={result.modified_count}, upserted_id={result.upserted_id}"
                )
                logger.info(f"🔧 [add_favorite] 返回结果: True")
                return True
        except Exception as e:
            logger.error(
                f"❌ [add_favorite] 添加自选股异常: {type(e).__name__}: {str(e)}",
                exc_info=True,
            )
            raise

    async def remove_favorite(self, user_id: str, stock_code: str) -> bool:
        """从自选股中移除股票（兼容字符串ID与ObjectId）"""
        db = await self._get_db()

        if self._is_valid_object_id(user_id):
            # 先尝试使用 ObjectId 查询
            result = await db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$pull": {"favorite_stocks": {"stock_code": stock_code}}},
            )
            # 如果 ObjectId 查询失败，尝试使用字符串查询
            if result.matched_count == 0:
                result = await db.users.update_one(
                    {"_id": user_id},
                    {"$pull": {"favorite_stocks": {"stock_code": stock_code}}},
                )
            return result.modified_count > 0
        else:
            result = await db.user_favorites.update_one(
                {"user_id": user_id},
                {
                    "$pull": {"favorites": {"stock_code": stock_code}},
                    "$set": {"updated_at": datetime.utcnow()},
                },
            )
            return result.modified_count > 0

    async def update_favorite(
        self,
        user_id: str,
        stock_code: str,
        tags: Optional[List[str]] = None,
        notes: Optional[str] = None,
        alert_price_high: Optional[float] = None,
        alert_price_low: Optional[float] = None,
    ) -> bool:
        """更新自选股信息（兼容字符串ID与ObjectId）"""
        db = await self._get_db()

        # 统一构建更新字段（根据不同集合的字段路径设置前缀）
        is_oid = self._is_valid_object_id(user_id)
        prefix = "favorite_stocks.$." if is_oid else "favorites.$."
        update_fields: Dict[str, Any] = {}
        if tags is not None:
            update_fields[prefix + "tags"] = tags
        if notes is not None:
            update_fields[prefix + "notes"] = notes
        if alert_price_high is not None:
            update_fields[prefix + "alert_price_high"] = alert_price_high
        if alert_price_low is not None:
            update_fields[prefix + "alert_price_low"] = alert_price_low

        if not update_fields:
            return True

        if is_oid:
            result = await db.users.update_one(
                {"_id": ObjectId(user_id), "favorite_stocks.stock_code": stock_code},
                {"$set": update_fields},
            )
            return result.modified_count > 0
        else:
            result = await db.user_favorites.update_one(
                {"user_id": user_id, "favorites.stock_code": stock_code},
                {"$set": {**update_fields, "updated_at": datetime.utcnow()}},
            )
            return result.modified_count > 0

    async def is_favorite(self, user_id: str, stock_code: str) -> bool:
        """检查股票是否在自选股中（兼容字符串ID与ObjectId）"""
        import logging

        logger = logging.getLogger("webapi")

        try:
            logger.info(
                f"🔧 [is_favorite] 检查自选股: user_id={user_id}, stock_code={stock_code}"
            )

            db = await self._get_db()

            is_oid = self._is_valid_object_id(user_id)
            logger.info(f"🔧 [is_favorite] 用户ID类型: is_valid_object_id={is_oid}")

            if is_oid:
                # 先尝试使用 ObjectId 查询
                user = await db.users.find_one(
                    {"_id": ObjectId(user_id), "favorite_stocks.stock_code": stock_code}
                )

                # 如果 ObjectId 查询失败，尝试使用字符串查询
                if user is None:
                    logger.info(
                        f"🔧 [is_favorite] ObjectId查询未找到，尝试使用字符串ID查询"
                    )
                    user = await db.users.find_one(
                        {"_id": user_id, "favorite_stocks.stock_code": stock_code}
                    )

                result = user is not None
                logger.info(f"🔧 [is_favorite] 查询结果: {result}")
                return result
            else:
                doc = await db.user_favorites.find_one(
                    {"user_id": user_id, "favorites.stock_code": stock_code}
                )
                result = doc is not None
                logger.info(f"🔧 [is_favorite] 字符串ID查询结果: {result}")
                return result
        except Exception as e:
            logger.error(
                f"❌ [is_favorite] 检查自选股异常: {type(e).__name__}: {str(e)}",
                exc_info=True,
            )
            raise

    async def get_user_tags(self, user_id: str) -> List[str]:
        """获取用户使用的所有标签（兼容字符串ID与ObjectId）"""
        db = await self._get_db()

        if self._is_valid_object_id(user_id):
            pipeline = [
                {"$match": {"_id": ObjectId(user_id)}},
                {"$unwind": "$favorite_stocks"},
                {"$unwind": "$favorite_stocks.tags"},
                {"$group": {"_id": "$favorite_stocks.tags"}},
                {"$sort": {"_id": 1}},
            ]
            result = await db.users.aggregate(pipeline).to_list(None)
        else:
            pipeline = [
                {"$match": {"user_id": user_id}},
                {"$unwind": "$favorites"},
                {"$unwind": "$favorites.tags"},
                {"$group": {"_id": "$favorites.tags"}},
                {"$sort": {"_id": 1}},
            ]
            result = await db.user_favorites.aggregate(pipeline).to_list(None)

        return [item["_id"] for item in result if item.get("_id")]

    def _get_mock_price(self, stock_code: str) -> float:
        """获取模拟股价"""
        # 基于股票代码生成模拟价格
        base_price = hash(stock_code) % 100 + 10
        return round(base_price + (hash(stock_code) % 1000) / 100, 2)

    def _get_mock_change(self, stock_code: str) -> float:
        """获取模拟涨跌幅"""
        # 基于股票代码生成模拟涨跌幅
        change = (hash(stock_code) % 2000 - 1000) / 100
        return round(change, 2)

    def _get_mock_volume(self, stock_code: str) -> int:
        """获取模拟成交量"""
        # 基于股票代码生成模拟成交量
        return (hash(stock_code) % 10000 + 1000) * 100


# 创建全局实例
favorites_service = FavoritesService()
