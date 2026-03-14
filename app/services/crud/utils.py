# -*- coding: utf-8 -*-
"""CRUD 服务工具函数

提供通用的辅助方法，如 ID 转换、时间戳管理等。
"""

from typing import Optional, Dict, Any
from datetime import datetime
from bson import ObjectId


def to_object_id(id: str) -> Optional[ObjectId]:
    """将字符串转为 ObjectId

    Args:
        id: 字符串 ID

    Returns:
        Optional[ObjectId]: ObjectId 对象，无效格式返回 None
    """
    try:
        if isinstance(id, ObjectId):
            return id
        if isinstance(id, str) and ObjectId.is_valid(id):
            return ObjectId(id)
        return None
    except Exception:
        return None


def build_id_query(id: str) -> Dict[str, Any]:
    """构建兼容 ObjectId 和字符串的 ID 查询条件

    如果 id 是有效的 ObjectId 格式，使用 ObjectId 查询；
    否则使用字符串查询。

    Args:
        id: 文档 ID

    Returns:
        Dict: MongoDB 查询条件
    """
    oid = to_object_id(id)
    if oid:
        return {"_id": oid}
    return {"_id": id}


def add_timestamps(data: Dict[str, Any], is_update: bool = False) -> Dict[str, Any]:
    """添加时间戳字段

    Args:
        data: 原始数据
        is_update: 是否为更新操作

    Returns:
        Dict: 添加了时间戳的数据
    """
    now = datetime.utcnow()

    if is_update:
        data["updated_at"] = now
    else:
        if "created_at" not in data:
            data["created_at"] = now
        data["updated_at"] = now

    return data
