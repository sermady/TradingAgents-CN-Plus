# -*- coding: utf-8 -*-
"""搜索工具模块

提供通用的 MongoDB 全文搜索功能
"""

from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


async def execute_text_search(
    collection,
    query: str,
    limit: int = 50,
    symbol: Optional[str] = None,
    extra_filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """执行 MongoDB 全文搜索

    通用的全文搜索函数，支持股票代码过滤和额外条件过滤。
    使用 MongoDB 的 $text 索引进行相关度排序。

    Args:
        collection: MongoDB 集合对象
        query: 搜索关键词
        limit: 返回结果数量限制，默认50
        symbol: 可选的股票代码过滤
        extra_filters: 可选的额外过滤条件，如 {"platform": "twitter"} 或 {"access_level": "public"}

    Returns:
        List[Dict]: 搜索结果列表，按相关度排序

    Example:
        # 搜索社媒消息
        results = await execute_text_search(
            collection=social_collection,
            query="比特币",
            symbol="BTC",
            extra_filters={"platform": "twitter"}
        )

        # 搜索内部消息
        results = await execute_text_search(
            collection=internal_collection,
            query="财报",
            extra_filters={"access_level": "internal"}
        )
    """
    try:
        # 构建搜索条件
        search_query = {
            "$text": {"$search": query}
        }

        # 添加股票代码过滤
        if symbol:
            search_query["symbol"] = symbol

        # 添加额外过滤条件
        if extra_filters:
            search_query.update(extra_filters)

        # 执行搜索，包含相关度分数
        cursor = collection.find(
            search_query,
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})])

        # 获取结果
        messages = await cursor.limit(limit).to_list(length=limit)

        logger.debug(f"🔍 全文搜索找到 {len(messages)} 条相关消息")
        return messages

    except Exception as e:
        logger.error(f"❌ 全文搜索失败: {e}")
        return []
