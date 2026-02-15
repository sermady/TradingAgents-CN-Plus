# -*- coding: utf-8 -*-
"""
内部消息数据服务
提供统一的内部消息存储、查询和管理功能
"""
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging
from pymongo import ReplaceOne
from pymongo.errors import BulkWriteError
from bson import ObjectId

from app.core.database import get_database

logger = logging.getLogger(__name__)


def convert_objectid_to_str(data: Union[Dict, List[Dict]]) -> Union[Dict, List[Dict]]:
    """
    转换 MongoDB ObjectId 为字符串，避免 JSON 序列化错误

    Args:
        data: 单个文档或文档列表

    Returns:
        转换后的数据
    """
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and '_id' in item:
                item['_id'] = str(item['_id'])
        return data
    elif isinstance(data, dict):
        if '_id' in data:
            data['_id'] = str(data['_id'])
        return data
    return data


@dataclass
class InternalMessageQueryParams:
    """内部消息查询参数"""
    symbol: Optional[str] = None
    symbols: Optional[List[str]] = None
    message_type: Optional[str] = None  # research_report/insider_info/analyst_note/meeting_minutes/internal_analysis
    category: Optional[str] = None  # fundamental_analysis/technical_analysis/market_sentiment/risk_assessment
    source_type: Optional[str] = None  # internal_research/insider/analyst/meeting/system_analysis
    department: Optional[str] = None
    author: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    importance: Optional[str] = None
    access_level: Optional[str] = None  # public/internal/restricted/confidential
    min_confidence: Optional[float] = None
    rating: Optional[str] = None  # strong_buy/buy/hold/sell/strong_sell
    keywords: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    limit: int = 50
    skip: int = 0
    sort_by: str = "created_time"
    sort_order: int = -1  # -1 for desc, 1 for asc


@dataclass
class InternalMessageStats:
    """内部消息统计信息"""
    total_count: int = 0
    message_types: Dict[str, int] = field(default_factory=dict)
    categories: Dict[str, int] = field(default_factory=dict)
    departments: Dict[str, int] = field(default_factory=dict)
    importance_levels: Dict[str, int] = field(default_factory=dict)
    ratings: Dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    recent_count: int = 0  # 最近24小时


class InternalMessageService:
    """内部消息数据服务"""
    
    def __init__(self):
        self.db = None
        self.collection = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def initialize(self):
        """初始化服务"""
        try:
            self.db = get_database()
            self.collection = self.db.internal_messages
            self.logger.info("✅ 内部消息数据服务初始化成功")
        except Exception as e:
            self.logger.error(f"❌ 内部消息数据服务初始化失败: {e}")
            raise
    
    async def _get_collection(self):
        """获取集合实例"""
        if self.collection is None:
            await self.initialize()
        return self.collection
    
    async def save_internal_messages(
        self, 
        messages: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        批量保存内部消息
        
        Args:
            messages: 内部消息列表
            
        Returns:
            保存统计信息
        """
        if not messages:
            return {"saved": 0, "failed": 0}
        
        try:
            collection = await self._get_collection()
            
            # 准备批量操作
            operations = []
            for message in messages:
                # 添加时间戳
                message["created_at"] = datetime.utcnow()
                message["updated_at"] = datetime.utcnow()
                
                # 使用message_id作为唯一标识
                filter_dict = {
                    "message_id": message.get("message_id")
                }
                
                operations.append(ReplaceOne(filter_dict, message, upsert=True))
            
            # 执行批量操作
            result = await collection.bulk_write(operations, ordered=False)
            
            saved_count = result.upserted_count + result.modified_count
            self.logger.info(f"✅ 内部消息批量保存完成: {saved_count}/{len(messages)}")
            
            return {
                "saved": saved_count,
                "failed": len(messages) - saved_count,
                "upserted": result.upserted_count,
                "modified": result.modified_count
            }
            
        except BulkWriteError as e:
            self.logger.error(f"❌ 内部消息批量保存部分失败: {e.details}")
            return {
                "saved": e.details.get("nUpserted", 0) + e.details.get("nModified", 0),
                "failed": len(e.details.get("writeErrors", [])),
                "errors": e.details.get("writeErrors", [])
            }
        except Exception as e:
            self.logger.error(f"❌ 内部消息保存失败: {e}")
            return {"saved": 0, "failed": len(messages), "error": str(e)}
    
    async def query_internal_messages(
        self, 
        params: InternalMessageQueryParams
    ) -> List[Dict[str, Any]]:
        """
        查询内部消息
        
        Args:
            params: 查询参数
            
        Returns:
            内部消息列表
        """
        try:
            collection = await self._get_collection()
            
            # 构建查询条件
            query = {}
            
            if params.symbol:
                query["symbol"] = params.symbol
            elif params.symbols:
                query["symbol"] = {"$in": params.symbols}
            
            if params.message_type:
                query["message_type"] = params.message_type
            
            if params.category:
                query["category"] = params.category
            
            if params.source_type:
                query["source.type"] = params.source_type
            
            if params.department:
                query["source.department"] = params.department
            
            if params.author:
                query["source.author"] = params.author
            
            if params.start_time or params.end_time:
                time_query = {}
                if params.start_time:
                    time_query["$gte"] = params.start_time
                if params.end_time:
                    time_query["$lte"] = params.end_time
                query["created_time"] = time_query
            
            if params.importance:
                query["importance"] = params.importance
            
            if params.access_level:
                query["access_level"] = params.access_level
            
            if params.min_confidence:
                query["confidence_level"] = {"$gte": params.min_confidence}
            
            if params.rating:
                query["related_data.rating"] = params.rating
            
            if params.keywords:
                query["keywords"] = {"$in": params.keywords}
            
            if params.tags:
                query["tags"] = {"$in": params.tags}
            
            # 执行查询
            cursor = collection.find(query)
            
            # 排序
            cursor = cursor.sort(params.sort_by, params.sort_order)
            
            # 分页
            cursor = cursor.skip(params.skip).limit(params.limit)
            
            # 获取结果
            messages = await cursor.to_list(length=params.limit)

            # 🔧 转换 ObjectId 为字符串，避免 JSON 序列化错误
            messages = convert_objectid_to_str(messages)

            self.logger.debug(f"📊 查询到 {len(messages)} 条内部消息")
            return messages
            
        except Exception as e:
            self.logger.error(f"❌ 内部消息查询失败: {e}")
            return []
    
    async def get_latest_messages(
        self, 
        symbol: str = None, 
        message_type: str = None,
        access_level: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取最新内部消息"""
        params = InternalMessageQueryParams(
            symbol=symbol,
            message_type=message_type,
            access_level=access_level,
            limit=limit,
            sort_by="created_time",
            sort_order=-1
        )
        return await self.query_internal_messages(params)
    
    async def search_messages(
        self,
        query: str,
        symbol: str = None,
        access_level: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """全文搜索内部消息"""
        from app.utils.search_utils import execute_text_search

        collection = await self._get_collection()

        # 构建额外过滤条件
        extra_filters = {}
        if access_level:
            extra_filters["access_level"] = access_level

        return await execute_text_search(
            collection=collection,
            query=query,
            symbol=symbol,
            limit=limit,
            extra_filters=extra_filters if extra_filters else None
        )
    
    async def get_research_reports(
        self, 
        symbol: str = None,
        department: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取研究报告"""
        params = InternalMessageQueryParams(
            symbol=symbol,
            message_type="research_report",
            department=department,
            limit=limit,
            sort_by="created_time",
            sort_order=-1
        )
        return await self.query_internal_messages(params)
    
    async def get_analyst_notes(
        self, 
        symbol: str = None,
        author: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """获取分析师笔记"""
        params = InternalMessageQueryParams(
            symbol=symbol,
            message_type="analyst_note",
            author=author,
            limit=limit,
            sort_by="created_time",
            sort_order=-1
        )
        return await self.query_internal_messages(params)
    
    async def get_internal_statistics(
        self, 
        symbol: str = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> InternalMessageStats:
        """获取内部消息统计信息"""
        try:
            collection = await self._get_collection()
            
            # 构建匹配条件
            match_stage = {}
            if symbol:
                match_stage["symbol"] = symbol
            if start_time or end_time:
                time_query = {}
                if start_time:
                    time_query["$gte"] = start_time
                if end_time:
                    time_query["$lte"] = end_time
                match_stage["created_time"] = time_query
            
            # 聚合管道
            pipeline = []
            if match_stage:
                pipeline.append({"$match": match_stage})
            
            pipeline.extend([
                {
                    "$group": {
                        "_id": None,
                        "total_count": {"$sum": 1},
                        "avg_confidence": {"$avg": "$confidence_level"},
                        "message_types": {"$push": "$message_type"},
                        "categories": {"$push": "$category"},
                        "departments": {"$push": "$source.department"},
                        "importance_levels": {"$push": "$importance"},
                        "ratings": {"$push": "$related_data.rating"}
                    }
                }
            ])
            
            # 执行聚合
            result = await collection.aggregate(pipeline).to_list(length=1)
            
            if result:
                stats_data = result[0]
                
                # 统计各类别数量
                def count_items(items):
                    counts = {}
                    for item in items:
                        if item:
                            counts[item] = counts.get(item, 0) + 1
                    return counts
                
                return InternalMessageStats(
                    total_count=stats_data.get("total_count", 0),
                    message_types=count_items(stats_data.get("message_types", [])),
                    categories=count_items(stats_data.get("categories", [])),
                    departments=count_items(stats_data.get("departments", [])),
                    importance_levels=count_items(stats_data.get("importance_levels", [])),
                    ratings=count_items(stats_data.get("ratings", [])),
                    avg_confidence=stats_data.get("avg_confidence", 0.0)
                )
            else:
                return InternalMessageStats()
                
        except Exception as e:
            self.logger.error(f"❌ 内部消息统计失败: {e}")
            return InternalMessageStats()


# 全局服务实例
_internal_message_service = None

async def get_internal_message_service() -> InternalMessageService:
    """获取内部消息数据服务实例"""
    global _internal_message_service
    if _internal_message_service is None:
        _internal_message_service = InternalMessageService()
        await _internal_message_service.initialize()
    return _internal_message_service
