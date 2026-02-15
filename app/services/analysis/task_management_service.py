# -*- coding: utf-8 -*-
"""任务管理服务

提取自 simple_analysis_service.py 中的任务管理相关逻辑：
- create_analysis_task
- get_task_status
- list_user_tasks
- list_all_tasks
- cleanup_zombie_tasks
- get_zombie_tasks
- _update_task_status
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from bson import ObjectId

from app.core.database import get_mongo_db
from app.models.analysis import AnalysisStatus
from app.models.user import PyObjectId
from app.services.memory_state_manager import get_memory_state_manager, TaskStatus
from app.services.redis_progress_tracker import get_progress_by_id
from app.utils.error_handler import (
    async_handle_errors,
    async_handle_errors_empty_list,
    async_handle_errors_none,
)

logger = logging.getLogger(__name__)

# 状态映射常量
STATUS_MAPPING = {
    "processing": "running",
    "pending": "pending",
    "completed": "completed",
    "failed": "failed",
    "cancelled": "cancelled",
}


class TaskManagementService:
    """任务管理服务"""

    def __init__(self):
        self.memory_manager = get_memory_state_manager()

    @async_handle_errors_none(error_message="创建分析任务失败")
    async def create_analysis_task(
        self, user_id: str, request
    ) -> Dict[str, Any]:
        """创建分析任务（立即返回，不执行分析）"""
        import uuid

        # 生成任务ID
        task_id = str(uuid.uuid4())

        # 使用 get_symbol() 方法获取股票代码
        stock_code = request.get_symbol()
        if not stock_code:
            raise ValueError("股票代码不能为空")

        logger.info(f"📝 创建分析任务: {task_id} - {stock_code}")

        # 在内存中创建任务状态
        from app.services.analysis.base_analysis_service import BaseAnalysisService

        base_service = BaseAnalysisService()
        task_state = await self.memory_manager.create_task(
            task_id=task_id,
            user_id=user_id,
            stock_code=stock_code,
            parameters=request.parameters.model_dump() if request.parameters else {},
            stock_name=base_service._resolve_stock_name(stock_code),
        )

        logger.info(f"✅ 任务状态已创建: {task_state.task_id}")

        # 验证任务是否可以查询到
        verify_task = await self.memory_manager.get_task(task_id)
        if verify_task:
            logger.info(f"✅ 任务创建验证成功: {verify_task.task_id}")
        else:
            logger.error(f"❌ 任务创建验证失败: 无法查询到刚创建的任务 {task_id}")

        # 写入数据库任务文档的初始记录
        await self._create_task_in_db(task_id, user_id, stock_code, base_service)

        return {
            "task_id": task_id,
            "status": "pending",
            "message": "任务已创建，等待执行",
        }

    async def _create_task_in_db(
        self, task_id: str, user_id: str, stock_code: str, base_service
    ):
        """在数据库中创建任务记录"""
        try:
            db = get_mongo_db()
            name = base_service._resolve_stock_name(stock_code)

            result = await db.analysis_tasks.update_one(
                {"task_id": task_id},
                {
                    "$setOnInsert": {
                        "task_id": task_id,
                        "user_id": user_id,
                        "stock_code": stock_code,
                        "stock_symbol": stock_code,
                        "stock_name": name,
                        "status": "pending",
                        "progress": 0,
                        "created_at": datetime.utcnow(),
                    }
                },
                upsert=True,
            )

            if result.upserted_id or result.matched_count > 0:
                logger.info(f"✅ 任务已保存到MongoDB: {task_id}")
            else:
                logger.warning(
                    f"⚠️ MongoDB保存结果异常: matched={result.matched_count}, upserted={result.upserted_id}"
                )
        except Exception as e:
            logger.error(f"❌ 创建任务时写入MongoDB失败: {e}")
            import traceback

            logger.error(f"❌ MongoDB保存详细错误: {traceback.format_exc()}")

    @async_handle_errors_none(error_message="获取任务状态失败")
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        logger.info(f"🔍 查询任务状态: {task_id}")

        # 强制使用全局内存管理器实例
        global_memory_manager = get_memory_state_manager()

        # 获取统计信息
        stats = await global_memory_manager.get_statistics()
        logger.info(f"📊 内存中任务统计: {stats}")

        result = await global_memory_manager.get_task_dict(task_id)
        if result:
            logger.info(f"✅ 找到任务: {task_id} - 状态: {result.get('status')}")

            # 优先从Redis获取详细进度信息
            redis_progress = get_progress_by_id(task_id)
            if redis_progress:
                result = self._merge_redis_progress(result, redis_progress)

        return result

    def _merge_redis_progress(
        self, result: Dict[str, Any], redis_progress: Dict[str, Any]
    ) -> Dict[str, Any]:
        """合并Redis进度数据"""
        # 从 steps 数组中提取当前步骤的名称和描述
        current_step_index = redis_progress.get("current_step", 0)
        steps = redis_progress.get("steps", [])
        current_step_name = redis_progress.get("current_step_name", "")
        current_step_description = redis_progress.get("current_step_description", "")

        # 如果 Redis 中的名称/描述为空，从 steps 数组中提取
        if not current_step_name and steps and 0 <= current_step_index < len(steps):
            current_step_info = steps[current_step_index]
            current_step_name = current_step_info.get("name", "")
            current_step_description = current_step_info.get("description", "")

        result.update(
            {
                "progress": redis_progress.get(
                    "progress_percentage", result.get("progress", 0)
                ),
                "current_step": current_step_index,
                "current_step_name": current_step_name,
                "current_step_description": current_step_description,
                "message": redis_progress.get("last_message", result.get("message", "")),
                "elapsed_time": redis_progress.get("elapsed_time", 0),
                "remaining_time": redis_progress.get("remaining_time", 0),
                "estimated_total_time": redis_progress.get(
                    "estimated_total_time", result.get("estimated_duration", 300)
                ),
                "steps": steps,
                "start_time": result.get("start_time"),
                "last_update": redis_progress.get("last_update", result.get("start_time")),
            }
        )
        return result

    @async_handle_errors_empty_list(error_message="获取任务列表失败")
    async def list_all_tasks(
        self, status: Optional[str] = None, limit: int = 20, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取所有任务列表（不限用户）"""
        task_status = self._parse_status(status)

        # 1) 从内存读取所有任务
        tasks_in_mem = await self.memory_manager.list_all_tasks(
            status=task_status, limit=limit * 2, offset=0
        )
        logger.info(f"📋 [Tasks] 内存返回数量: {len(tasks_in_mem)}")

        # 2) 从 MongoDB 读取任务
        db = get_mongo_db()
        collection = db["analysis_tasks"]

        query = {}
        if task_status:
            query["status"] = task_status.value

        count = await collection.count_documents(query)
        cursor = collection.find(query).sort("start_time", -1).limit(limit * 2)
        tasks_from_db = []
        async for doc in cursor:
            doc.pop("_id", None)
            tasks_from_db.append(doc)

        # 3) 合并任务（内存优先）
        merged_tasks = self._merge_tasks(tasks_from_db, tasks_in_mem)

        # 分页
        results = merged_tasks[offset : offset + limit]

        # 为结果补齐股票名称
        from app.services.analysis.base_analysis_service import BaseAnalysisService

        base_service = BaseAnalysisService()
        results = base_service._enrich_stock_names(results)

        logger.info(
            f"📋 [Tasks] 合并后返回数量: {len(results)} (内存: {len(tasks_in_mem)}, MongoDB: {count})"
        )
        return results

    @async_handle_errors_empty_list(error_message="获取用户任务列表失败")
    async def list_user_tasks(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """获取用户任务列表"""
        task_status = self._parse_status(status)

        # 1) 从内存读取任务
        tasks_in_mem = await self.memory_manager.list_user_tasks(
            user_id=user_id,
            status=task_status,
            limit=limit * 2,
            offset=0,
        )
        logger.info(f"📋 [Tasks] 内存返回数量: {len(tasks_in_mem)}")

        # 2) 从 MongoDB 读取历史任务
        mongo_tasks = await self._fetch_user_tasks_from_db(user_id, task_status, limit)

        # 3) 合并内存和 MongoDB 数据
        merged_tasks = self._merge_user_tasks(tasks_in_mem, mongo_tasks)

        # 统一处理时区信息
        self._normalize_timezone(merged_tasks)

        # 分页
        results = merged_tasks[offset : offset + limit]

        # 为结果补齐股票名称
        from app.services.analysis.base_analysis_service import BaseAnalysisService

        base_service = BaseAnalysisService()
        results = base_service._enrich_stock_names(results)

        logger.info(f"📋 [Tasks] 合并后返回数量: {len(results)}")
        return results

    def _parse_status(self, status: Optional[str]) -> Optional[TaskStatus]:
        """解析状态字符串"""
        if not status:
            return None
        try:
            mapped_status = STATUS_MAPPING.get(status, status)
            return TaskStatus(mapped_status)
        except ValueError:
            logger.warning(f"⚠️ [Tasks] 无效的状态值: {status}")
            return None

    def _merge_tasks(
        self, db_tasks: List[Dict], mem_tasks: List[Dict]
    ) -> List[Dict[str, Any]]:
        """合并数据库和内存中的任务"""
        task_dict = {}

        # 先添加 MongoDB 中的任务
        for task in db_tasks:
            task_id = task.get("task_id")
            if task_id:
                task_dict[task_id] = task

        # 再添加内存中的任务（覆盖 MongoDB 中的同名任务）
        for task in mem_tasks:
            task_id = task.get("task_id")
            if task_id:
                task_dict[task_id] = task

        # 转换为列表并按时间排序
        merged_tasks = list(task_dict.values())
        merged_tasks.sort(key=lambda x: x.get("start_time", ""), reverse=True)
        return merged_tasks

    async def _fetch_user_tasks_from_db(
        self, user_id: str, task_status: Optional[TaskStatus], limit: int
    ) -> List[Dict[str, Any]]:
        """从数据库获取用户任务"""
        mongo_tasks: List[Dict[str, Any]] = []

        try:
            db = get_mongo_db()

            # user_id 可能是字符串或 ObjectId，做兼容
            uid_candidates = self._build_uid_candidates(user_id)

            # 兼容 user_id 与 user 两种字段名
            base_condition = {"$in": uid_candidates}
            or_conditions = [
                {"user_id": base_condition},
                {"user": base_condition},
            ]
            query = {"$or": or_conditions}

            if task_status:
                query["status"] = task_status.value

            cursor = (
                db.analysis_tasks.find(query)
                .sort("created_at", -1)
                .limit(limit * 2)
            )

            async for doc in cursor:
                mongo_tasks.append(self._normalize_task_doc(doc))

        except Exception as e:
            logger.error(f"❌ MongoDB 查询任务列表失败: {e}", exc_info=True)

        return mongo_tasks

    def _build_uid_candidates(self, user_id: str) -> List[Any]:
        """构建用户ID候选列表"""
        uid_candidates = [user_id]

        if str(user_id) == "admin":
            try:
                admin_oid_str = "507f1f77bcf86cd799439011"
                uid_candidates.append(ObjectId(admin_oid_str))
                uid_candidates.append(admin_oid_str)
            except Exception as e:
                logger.warning(f"⚠️ [Tasks] admin用户ObjectId创建失败: {e}")
        else:
            try:
                uid_candidates.append(ObjectId(user_id))
            except Exception:
                pass

        return uid_candidates

    def _normalize_task_doc(self, doc: Dict) -> Dict[str, Any]:
        """标准化任务文档"""
        user_field_val = doc.get("user_id", doc.get("user"))
        stock_code_value = (
            doc.get("symbol") or doc.get("stock_code") or doc.get("stock_symbol")
        )

        item = {
            "task_id": doc.get("task_id"),
            "user_id": str(user_field_val) if user_field_val is not None else None,
            "symbol": stock_code_value,
            "stock_code": stock_code_value,
            "stock_symbol": stock_code_value,
            "stock_name": doc.get("stock_name"),
            "status": str(doc.get("status", "pending")),
            "progress": int(doc.get("progress", 0) or 0),
            "message": doc.get("message", ""),
            "current_step": doc.get("current_step", ""),
            "start_time": doc.get("started_at") or doc.get("created_at"),
            "end_time": doc.get("completed_at"),
            "parameters": doc.get("parameters", {}),
            "execution_time": doc.get("execution_time"),
            "tokens_used": doc.get("tokens_used"),
            "result_data": doc.get("result"),
        }

        # 时间格式转为 ISO 字符串
        for k in ("start_time", "end_time"):
            if item.get(k) and hasattr(item[k], "isoformat"):
                dt = item[k]
                if dt.tzinfo is None:
                    china_tz = timezone(timedelta(hours=8))
                    dt = dt.replace(tzinfo=china_tz)
                item[k] = dt.isoformat()

        return item

    def _merge_user_tasks(
        self, mem_tasks: List[Dict], mongo_tasks: List[Dict]
    ) -> List[Dict[str, Any]]:
        """合并用户任务（内存 + MongoDB）"""
        task_dict = {}

        # 先添加内存中的任务
        for task in mem_tasks:
            task_id = task.get("task_id")
            if task_id:
                task_dict[task_id] = task

        # 再添加 MongoDB 中的任务
        for task in mongo_tasks:
            task_id = task.get("task_id")
            if not task_id:
                continue

            if task_id in task_dict:
                # 如果是 processing/running 状态，使用 MongoDB 中的进度数据
                if task.get("status") in ["processing", "running"]:
                    mem_task = task_dict[task_id]
                    mem_task["progress"] = task.get("progress", mem_task.get("progress", 0))
                    mem_task["message"] = task.get("message", mem_task.get("message", ""))
                    mem_task["current_step"] = task.get(
                        "current_step", mem_task.get("current_step", "")
                    )
            else:
                task_dict[task_id] = task

        # 转换为列表并按时间排序
        merged_tasks = list(task_dict.values())
        merged_tasks.sort(key=lambda x: x.get("start_time", ""), reverse=True)
        return merged_tasks

    def _normalize_timezone(self, tasks: List[Dict]):
        """统一处理时区信息"""
        china_tz = timezone(timedelta(hours=8))

        for task in tasks:
            for time_field in (
                "start_time",
                "end_time",
                "created_at",
                "started_at",
                "completed_at",
            ):
                value = task.get(time_field)
                if value:
                    if hasattr(value, "isoformat"):
                        if value.tzinfo is None:
                            value = value.replace(tzinfo=china_tz)
                        task[time_field] = value.isoformat()
                    elif (
                        isinstance(value, str)
                        and value
                        and not value.endswith(("Z", "+08:00", "+00:00"))
                    ):
                        if "T" in value or " " in value:
                            task[time_field] = value.replace(" ", "T") + "+08:00"

    @async_handle_errors(
        default_return={"success": False, "error": "清理失败", "total_cleaned": 0},
        error_message="清理僵尸任务失败",
    )
    async def cleanup_zombie_tasks(self, max_running_hours: int = 2) -> Dict[str, Any]:
        """清理僵尸任务"""
        # 1) 清理内存中的僵尸任务
        memory_cleaned = await self.memory_manager.cleanup_zombie_tasks(
            max_running_hours
        )

        # 2) 清理 MongoDB 中的僵尸任务
        db = get_mongo_db()
        cutoff_time = datetime.utcnow() - timedelta(hours=max_running_hours)

        zombie_filter = {
            "status": {"$in": ["processing", "running", "pending"]},
            "$or": [
                {"started_at": {"$lt": cutoff_time}},
                {"created_at": {"$lt": cutoff_time, "started_at": None}},
            ],
        }

        update_result = await db.analysis_tasks.update_many(
            zombie_filter,
            {
                "$set": {
                    "status": "failed",
                    "last_error": f"任务超时（运行时间超过 {max_running_hours} 小时）",
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        mongo_cleaned = update_result.modified_count

        logger.info(
            f"🧹 僵尸任务清理完成: 内存={memory_cleaned}, MongoDB={mongo_cleaned}"
        )

        return {
            "success": True,
            "memory_cleaned": memory_cleaned,
            "mongo_cleaned": mongo_cleaned,
            "total_cleaned": memory_cleaned + mongo_cleaned,
            "max_running_hours": max_running_hours,
        }

    @async_handle_errors_empty_list(error_message="查询僵尸任务失败")
    async def get_zombie_tasks(self, max_running_hours: int = 2) -> List[Dict[str, Any]]:
        """获取僵尸任务列表（不执行清理，仅查询）"""
        db = get_mongo_db()
        cutoff_time = datetime.utcnow() - timedelta(hours=max_running_hours)

        zombie_filter = {
            "status": {"$in": ["processing", "running", "pending"]},
            "$or": [
                {"started_at": {"$lt": cutoff_time}},
                {"created_at": {"$lt": cutoff_time, "started_at": None}},
            ],
        }

        cursor = db.analysis_tasks.find(zombie_filter).sort("created_at", -1)
        zombie_tasks = []

        async for doc in cursor:
            task = {
                "task_id": doc.get("task_id"),
                "user_id": str(doc.get("user_id", doc.get("user"))),
                "stock_code": doc.get("stock_code"),
                "stock_name": doc.get("stock_name"),
                "status": doc.get("status"),
                "created_at": doc.get("created_at").isoformat()
                if doc.get("created_at")
                else None,
                "started_at": doc.get("started_at").isoformat()
                if doc.get("started_at")
                else None,
                "running_hours": None,
            }

            # 计算运行时长
            start_time = doc.get("started_at") or doc.get("created_at")
            if start_time:
                running_seconds = (datetime.utcnow() - start_time).total_seconds()
                task["running_hours"] = round(running_seconds / 3600, 2)

            zombie_tasks.append(task)

        logger.info(f"📋 查询到 {len(zombie_tasks)} 个僵尸任务")
        return zombie_tasks

    @async_handle_errors_none(error_message="更新任务状态失败")
    async def update_task_status(
        self,
        task_id: str,
        status: AnalysisStatus,
        progress: int,
        error_message: str = None,
    ):
        """更新任务状态"""
        db = get_mongo_db()
        update_data = {
            "status": status,
            "progress": progress,
            "updated_at": datetime.utcnow(),
        }

        if status == AnalysisStatus.PROCESSING and progress == 10:
            update_data["started_at"] = datetime.utcnow()
        elif status == AnalysisStatus.COMPLETED:
            update_data["completed_at"] = datetime.utcnow()
        elif status == AnalysisStatus.FAILED:
            update_data["last_error"] = error_message
            update_data["completed_at"] = datetime.utcnow()

        await db.analysis_tasks.update_one(
            {"task_id": task_id}, {"$set": update_data}
        )

        logger.debug(f"📊 任务状态已更新: {task_id} -> {status} ({progress}%)")
