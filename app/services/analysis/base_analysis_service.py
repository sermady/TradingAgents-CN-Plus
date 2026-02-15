# -*- coding: utf-8 -*-
"""分析服务基类

提取自 simple_analysis_service.py 中的通用功能：
- 股票名称解析和缓存
- 用户ID转换
- TradingGraph 实例获取
- 通用工具方法
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from bson import ObjectId

from app.models.user import PyObjectId
from app.utils.error_handler import handle_errors, async_handle_errors

logger = logging.getLogger(__name__)

# 股票基础信息获取（用于补充显示名称）
try:
    from tradingagents.dataflows.data_source_manager import get_data_source_manager

    _data_source_manager = get_data_source_manager()

    def _get_stock_info_safe(stock_code: str):
        """获取股票基础信息的安全封装"""
        return _data_source_manager.get_stock_basic_info(stock_code)
except Exception:
    _get_stock_info_safe = None


class BaseAnalysisService:
    """分析服务基类"""

    def __init__(self):
        # 简单的股票名称缓存，减少重复查询
        self._stock_name_cache: Dict[str, str] = {}

    def _resolve_stock_name(self, code: Optional[str]) -> str:
        """解析股票名称（带缓存）"""
        if not code:
            return ""

        # 命中缓存
        if code in self._stock_name_cache:
            return self._stock_name_cache[code]

        name = None
        try:
            if _get_stock_info_safe:
                info = _get_stock_info_safe(code)
                if isinstance(info, dict):
                    name = info.get("name")
        except Exception as e:
            logger.warning(f"⚠️ 获取股票名称失败: {code} - {e}")

        if not name:
            name = f"股票{code}"

        # 写缓存
        self._stock_name_cache[code] = name
        return name

    def _enrich_stock_names(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """为任务列表补齐股票名称(就地更新)"""
        try:
            for t in tasks:
                code = t.get("stock_code") or t.get("stock_symbol")
                name = t.get("stock_name")
                if not name and code:
                    t["stock_name"] = self._resolve_stock_name(code)
        except Exception as e:
            logger.warning(f"⚠️ 补齐股票名称时出现异常: {e}")
        return tasks

    def _convert_user_id(self, user_id: str) -> PyObjectId:
        """将字符串用户ID转换为PyObjectId"""
        try:
            logger.info(f"🔄 开始转换用户ID: {user_id} (类型: {type(user_id)})")

            # 如果是admin用户，使用固定的ObjectId
            if user_id == "admin":
                admin_object_id = ObjectId("507f1f77bcf86cd799439011")
                logger.info(f"🔄 转换admin用户ID: {user_id} -> {admin_object_id}")
                return PyObjectId(admin_object_id)
            else:
                # 尝试将字符串转换为ObjectId
                object_id = ObjectId(user_id)
                logger.info(f"🔄 转换用户ID: {user_id} -> {object_id}")
                return PyObjectId(object_id)
        except Exception as e:
            logger.error(f"❌ 用户ID转换失败: {user_id} -> {e}")
            # 如果转换失败，生成一个新的ObjectId
            new_object_id = ObjectId()
            logger.warning(f"⚠️ 生成新的用户ID: {new_object_id}")
            return PyObjectId(new_object_id)

    def _get_trading_graph(self, config: Dict[str, Any]):
        """获取或创建TradingAgents实例

        注意：为了避免并发执行时的数据混淆，每次都创建新实例
        虽然这会增加一些初始化开销，但可以确保线程安全
        """
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        logger.info(f"🔧 创建新的TradingAgents实例（并发安全模式）...")

        trading_graph = TradingAgentsGraph(
            selected_analysts=config.get(
                "selected_analysts", ["market", "fundamentals"]
            ),
            debug=config.get("debug", False),
            config=config,
        )

        logger.info(f"✅ TradingAgents实例创建成功（实例ID: {id(trading_graph)}）")
        return trading_graph

    @staticmethod
    def _format_error_for_user(error: Exception, context: Dict[str, Any] = None) -> str:
        """格式化错误信息为用户友好的提示"""
        from app.utils.error_formatter import ErrorFormatter

        error_context = context or {}
        formatted_error = ErrorFormatter.format_error(str(error), error_context)

        return (
            f"{formatted_error['title']}\n\n"
            f"{formatted_error['message']}\n\n"
            f"💡 {formatted_error['suggestion']}"
        )
