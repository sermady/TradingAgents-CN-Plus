# -*- coding: utf-8 -*-
"""分析执行服务

提取自 simple_analysis_service.py 中的分析执行核心逻辑：
- execute_analysis_background
- _execute_analysis_sync
- _run_analysis_sync
- 进度更新和回调
- 结果处理和格式化
"""

import asyncio
import concurrent.futures
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional

from app.models.analysis import AnalysisStatus, AnalysisParameters
from app.services.memory_state_manager import get_memory_state_manager, TaskStatus
from app.services.redis_progress_tracker import RedisProgressTracker
from app.services.progress_log_handler import (
    register_analysis_tracker,
    unregister_analysis_tracker,
)
from app.utils.error_handler import (
    handle_errors,
    async_handle_errors,
    async_handle_errors_none,
)
from app.utils.report_extractor import ReportExtractor

logger = logging.getLogger(__name__)

# 节点进度映射表
NODE_PROGRESS_MAP = {
    # 分析师阶段 (10% → 45%)
    "📊 市场分析师": 27.5,
    "💼 基本面分析师": 45,
    "📰 新闻分析师": 27.5,
    "💬 社交媒体分析师": 27.5,
    # 研究辩论阶段 (45% → 70%)
    "🐂 看涨研究员": 51.25,
    "🐻 看跌研究员": 57.5,
    "👔 研究经理": 70,
    # 交易员阶段 (70% → 78%)
    "💼 交易员决策": 78,
    # 风险评估阶段 (78% → 93%)
    "🔥 激进风险评估": 81.75,
    "🛡️ 保守风险评估": 85.5,
    "⚖️ 中性风险评估": 89.25,
    "🎯 风险经理": 93,
    # 最终阶段 (93% → 100%)
    "📊 生成报告": 97,
}


class AnalysisExecutionService:
    """分析执行服务"""

    def __init__(self):
        self.memory_manager = get_memory_state_manager()
        self._progress_trackers: Dict[str, RedisProgressTracker] = {}
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=3)

    async def execute_analysis_background(self, task_id: str, user_id: str, request):
        """在后台执行分析任务"""
        stock_code = request.get_symbol()
        progress_tracker = None

        try:
            logger.info(f"🚀 开始后台执行分析任务: {task_id}")

            # 验证股票代码
            if not await self._validate_stock_code(task_id, request, stock_code):
                return

            # 创建进度跟踪器
            progress_tracker = await self._create_progress_tracker(task_id, request)
            self._progress_trackers[task_id] = progress_tracker
            register_analysis_tracker(task_id, progress_tracker)

            # 初始化进度
            await self._initialize_progress(task_id, progress_tracker)

            # 执行实际的分析
            result = await self._execute_analysis_sync(
                task_id, user_id, request, progress_tracker
            )

            # 标记进度跟踪器完成
            await asyncio.to_thread(progress_tracker.mark_completed)

            # 执行风控验证
            result = await self._run_risk_validation(task_id, result)

            # 保存分析结果
            await self._save_results(task_id, result)

            # 更新状态为完成
            await self._mark_task_completed(task_id, result)

            # 创建通知
            await self._create_completion_notification(user_id, request, result)

            logger.info(f"✅ 后台分析任务完成: {task_id}")

        except Exception as e:
            await self._handle_execution_error(task_id, request, e, progress_tracker)
        finally:
            # 清理
            if task_id in self._progress_trackers:
                del self._progress_trackers[task_id]
            unregister_analysis_tracker(task_id)

    async def _validate_stock_code(
        self, task_id: str, request, stock_code: str
    ) -> bool:
        """验证股票代码"""
        from tradingagents.utils.stock_validator import prepare_stock_data_async

        market_type = request.parameters.market_type if request.parameters else "A股"
        analysis_date = self._format_analysis_date(
            request.parameters.analysis_date if request.parameters else None
        )

        validation_result = await prepare_stock_data_async(
            stock_code=stock_code,
            market_type=market_type,
            period_days=30,
            analysis_date=analysis_date,
        )

        if not validation_result.is_valid:
            error_msg = f"❌ 股票代码验证失败: {validation_result.error_message}"
            logger.error(error_msg)

            user_friendly_error = (
                f"❌ 股票代码无效\n\n"
                f"{validation_result.error_message}\n\n"
                f"💡 {validation_result.suggestion}"
            )

            await self.memory_manager.update_task_status(
                task_id=task_id,
                status=AnalysisStatus.FAILED,
                progress=0,
                error_message=user_friendly_error,
            )
            return False

        logger.info(f"✅ 股票代码验证通过: {stock_code}")
        return True

    def _format_analysis_date(self, analysis_date) -> str:
        """格式化分析日期"""
        if not analysis_date:
            return datetime.now().strftime("%Y-%m-%d")

        if isinstance(analysis_date, datetime):
            return analysis_date.strftime("%Y-%m-%d")
        elif isinstance(analysis_date, str):
            try:
                parsed_date = datetime.strptime(analysis_date, "%Y-%m-%d")
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                return datetime.now().strftime("%Y-%m-%d")
        return datetime.now().strftime("%Y-%m-%d")

    async def _create_progress_tracker(
        self, task_id: str, request
    ) -> RedisProgressTracker:
        """创建Redis进度跟踪器"""
        parameters = request.parameters or AnalysisParameters()

        def create_tracker():
            return RedisProgressTracker(
                task_id=task_id,
                analysts=parameters.selected_analysts or ["market", "fundamentals"],
                research_depth=parameters.research_depth or "标准",
                llm_provider="dashscope",
            )

        return await asyncio.to_thread(create_tracker)

    async def _initialize_progress(
        self, task_id: str, progress_tracker: RedisProgressTracker
    ):
        """初始化任务进度"""
        await asyncio.to_thread(
            progress_tracker.update_progress,
            {"progress_percentage": 10, "last_message": "🚀 开始股票分析"},
        )

        await self.memory_manager.update_task_status(
            task_id=task_id,
            status=TaskStatus.RUNNING,
            progress=10,
            message="分析开始...",
            current_step="initialization",
        )

        # 更新MongoDB状态
        from app.services.analysis.task_management_service import TaskManagementService

        task_service = TaskManagementService()
        await task_service.update_task_status(task_id, AnalysisStatus.PROCESSING, 10)

    async def _execute_analysis_sync(
        self,
        task_id: str,
        user_id: str,
        request,
        progress_tracker: Optional[RedisProgressTracker] = None,
    ) -> Dict[str, Any]:
        """同步执行分析（在共享线程池中运行）"""
        loop = asyncio.get_event_loop()
        logger.info(
            f"🚀 [线程池] 提交分析任务到共享线程池: {task_id} - {request.stock_code}"
        )

        result = await loop.run_in_executor(
            self._thread_pool,
            self._run_analysis_sync,
            task_id,
            user_id,
            request,
            progress_tracker,
        )
        logger.info(f"✅ [线程池] 分析任务执行完成: {task_id}")
        return result

    def _run_analysis_sync(
        self,
        task_id: str,
        user_id: str,
        request,
        progress_tracker: Optional[RedisProgressTracker] = None,
    ) -> Dict[str, Any]:
        """同步执行分析的具体实现"""
        from tradingagents.utils.logging_init import init_logging, get_logger

        init_logging()
        thread_logger = get_logger("analysis_thread")
        thread_logger.info(
            f"🔄 [线程池] 开始执行分析: {task_id} - {request.stock_code}"
        )

        try:
            # 配置阶段
            self._update_progress_sync(
                task_id, 7, "⚙️ 配置分析参数", "configuration", progress_tracker
            )

            # 获取模型配置
            config = self._build_analysis_config(request)

            # 初始化分析引擎
            self._update_progress_sync(
                task_id,
                9,
                "🚀 初始化AI分析引擎",
                "engine_initialization",
                progress_tracker,
            )

            from app.services.analysis.base_analysis_service import BaseAnalysisService

            base_service = BaseAnalysisService()
            trading_graph = base_service._get_trading_graph(config)

            # 准备分析数据
            start_time = datetime.now()
            analysis_date = self._get_analysis_date(request)

            # 获取交易日范围
            from tradingagents.utils.trading_date_manager import (
                get_trading_date_manager,
            )

            date_mgr = get_trading_date_manager()
            data_start_date, data_end_date = date_mgr.get_trading_date_range(
                analysis_date, lookback_days=10
            )

            logger.info(f"📅 分析目标日期: {analysis_date}")
            logger.info(f"📅 数据查询范围: {data_start_date} 至 {data_end_date}")

            # 开始分析
            self._update_progress_sync(
                task_id,
                10,
                "🤖 开始多智能体协作分析",
                "agent_analysis",
                progress_tracker,
            )

            # 启动进度模拟线程
            progress_thread = self._start_progress_simulation(request, progress_tracker)

            # 定义进度回调函数
            callback = self._create_progress_callback(task_id, progress_tracker)

            # 执行实际分析
            state, decision = trading_graph.propagate(
                request.stock_code,
                analysis_date,
                progress_callback=callback,
                task_id=task_id,
            )

            logger.info(f"✅ trading_graph.propagate 执行完成")

            # 处理结果
            if progress_tracker:
                progress_tracker.update_progress("📊 处理分析结果")
            self._update_progress_sync(
                task_id, 90, "处理分析结果...", "result_processing", progress_tracker
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            # 构建结果
            result = self._build_analysis_result(
                request, state, decision, execution_time, analysis_date
            )

            logger.info(f"✅ [线程池] 分析完成: {task_id} - 耗时{execution_time:.2f}秒")
            return result

        except Exception as e:
            logger.error(f"❌ [线程池] 分析执行失败: {task_id} - {e}")
            raise

    def _update_progress_sync(
        self,
        task_id: str,
        progress: int,
        message: str,
        step: str,
        progress_tracker: Optional[RedisProgressTracker] = None,
    ):
        """在线程池中同步更新进度"""
        try:
            if progress_tracker:
                progress_tracker.update_progress(
                    {"progress_percentage": progress, "last_message": message}
                )

            # 更新内存中的任务状态
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    self.memory_manager.update_task_status(
                        task_id=task_id,
                        status=TaskStatus.RUNNING,
                        progress=progress,
                        message=message,
                        current_step=step,
                    )
                )
            finally:
                loop.close()

            # 更新 MongoDB
            from pymongo import MongoClient
            from app.core.config import settings

            sync_client = MongoClient(settings.MONGO_URI)
            sync_db = sync_client[settings.MONGO_DB]

            sync_db.analysis_tasks.update_one(
                {"task_id": task_id},
                {
                    "$set": {
                        "progress": progress,
                        "current_step": step,
                        "message": message,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
            sync_client.close()

        except Exception as e:
            logger.warning(f"⚠️ 进度更新失败: {e}")

    def _build_analysis_config(self, request) -> Dict[str, Any]:
        """构建分析配置"""
        from app.services.analysis.model_provider_service import (
            create_analysis_config,
            ModelProviderService,
        )
        from app.services.model_capability_service import get_model_capability_service

        capability_service = get_model_capability_service()
        research_depth = (
            request.parameters.research_depth if request.parameters else "标准"
        )

        # 获取模型
        if (
            request.parameters
            and hasattr(request.parameters, "quick_analysis_model")
            and hasattr(request.parameters, "deep_analysis_model")
            and request.parameters.quick_analysis_model
            and request.parameters.deep_analysis_model
        ):
            quick_model = request.parameters.quick_analysis_model
            deep_model = request.parameters.deep_analysis_model
            logger.info(
                f"📝 [分析服务] 用户指定模型: quick={quick_model}, deep={deep_model}"
            )

            # 验证模型
            validation = capability_service.validate_model_pair(
                quick_model, deep_model, research_depth
            )
            if not validation["valid"]:
                for warning in validation["warnings"]:
                    logger.warning(warning)
                quick_model, deep_model = capability_service.recommend_models_for_depth(
                    research_depth
                )
                logger.info(f"✅ 已切换: quick={quick_model}, deep={deep_model}")
        else:
            quick_model, deep_model = capability_service.recommend_models_for_depth(
                research_depth
            )
            logger.info(f"🤖 自动推荐模型: quick={quick_model}, deep={deep_model}")

        # 获取提供商信息
        quick_provider_info = (
            ModelProviderService.get_provider_and_url(quick_model) or {}
        )
        deep_provider_info = ModelProviderService.get_provider_and_url(deep_model) or {}

        # 创建配置
        config = create_analysis_config(
            research_depth=research_depth,
            selected_analysts=request.parameters.selected_analysts
            if request.parameters
            else ["market", "fundamentals"],
            quick_model=quick_model,
            deep_model=deep_model,
            llm_provider=quick_provider_info.get("provider", "openai"),
            market_type=request.parameters.market_type if request.parameters else "A股",
        )

        # 添加混合模式配置
        config["quick_provider"] = quick_provider_info.get("provider", "openai")
        config["deep_provider"] = deep_provider_info.get("provider", "openai")
        config["quick_backend_url"] = quick_provider_info.get("backend_url", "")
        config["deep_backend_url"] = deep_provider_info.get("backend_url", "")

        return config

    def _get_analysis_date(self, request) -> str:
        """获取分析日期"""
        if (
            request.parameters
            and hasattr(request.parameters, "analysis_date")
            and request.parameters.analysis_date
        ):
            if isinstance(request.parameters.analysis_date, datetime):
                return request.parameters.analysis_date.strftime("%Y-%m-%d")
            elif isinstance(request.parameters.analysis_date, str):
                return request.parameters.analysis_date
        return datetime.now().strftime("%Y-%m-%d")

    def _start_progress_simulation(
        self, request, progress_tracker: Optional[RedisProgressTracker]
    ) -> threading.Thread:
        """启动进度模拟线程"""

        def simulate_progress():
            try:
                if not progress_tracker:
                    return

                analysts = (
                    request.parameters.selected_analysts
                    if request.parameters
                    else ["market", "fundamentals"]
                )

                # 模拟分析师执行
                for i, analyst in enumerate(analysts):
                    time.sleep(15)
                    if analyst == "market":
                        progress_tracker.update_progress("📊 市场分析师正在分析")
                    elif analyst == "fundamentals":
                        progress_tracker.update_progress("💼 基本面分析师正在分析")
                    elif analyst == "news":
                        progress_tracker.update_progress("📰 新闻分析师正在分析")
                    elif analyst == "social":
                        progress_tracker.update_progress("💬 社交媒体分析师正在分析")

                # 研究团队阶段
                time.sleep(10)
                progress_tracker.update_progress("🐂 看涨研究员构建论据")

                time.sleep(8)
                progress_tracker.update_progress("🐻 看跌研究员识别风险")

                # 辩论阶段
                research_depth = (
                    request.parameters.research_depth if request.parameters else "标准"
                )
                debate_rounds = {
                    "快速": 1,
                    "基础": 1,
                    "标准": 1,
                    "深度": 2,
                    "全面": 3,
                }.get(research_depth, 1)

                for round_num in range(debate_rounds):
                    time.sleep(12)
                    progress_tracker.update_progress(f"🎯 研究辩论 第{round_num + 1}轮")

                time.sleep(8)
                progress_tracker.update_progress("👔 研究经理形成共识")

                # 交易员阶段
                time.sleep(10)
                progress_tracker.update_progress("💼 交易员制定策略")

                # 风险管理阶段
                time.sleep(8)
                progress_tracker.update_progress("🔥 激进风险评估")

                time.sleep(6)
                progress_tracker.update_progress("🛡️ 保守风险评估")

                time.sleep(6)
                progress_tracker.update_progress("⚖️ 中性风险评估")

                time.sleep(8)
                progress_tracker.update_progress("🎯 风险经理制定策略")

                # 最终阶段
                time.sleep(5)
                progress_tracker.update_progress("📡 信号处理")

            except Exception as e:
                logger.warning(f"⚠️ 进度模拟失败: {e}")

        progress_thread = threading.Thread(target=simulate_progress, daemon=True)
        progress_thread.start()
        return progress_thread

    def _create_progress_callback(self, task_id: str, progress_tracker):
        """创建进度回调函数"""

        def callback(message: str):
            try:
                logger.info(f"🎯🎯🎯 [Graph进度回调被调用] message={message}")
                if not progress_tracker:
                    return

                progress_pct = NODE_PROGRESS_MAP.get(message)
                if progress_pct is not None:
                    current_progress = progress_tracker.progress_data.get(
                        "progress_percentage", 0
                    )

                    if int(progress_pct) > current_progress:
                        progress_tracker.update_progress(
                            {
                                "progress_percentage": int(progress_pct),
                                "last_message": message,
                            }
                        )
                        logger.info(
                            f"📊 [Graph进度] 进度已更新: {current_progress}% → {int(progress_pct)}% - {message}"
                        )

                        # 同时更新内存和 MongoDB
                        self._sync_progress_to_db(task_id, int(progress_pct), message)
                    else:
                        progress_tracker.update_progress({"last_message": message})
                else:
                    logger.warning(f"⚠️ [Graph进度] 未知节点: {message}")
                    progress_tracker.update_progress({"last_message": message})

            except Exception as e:
                logger.error(f"❌ Graph进度回调失败: {e}", exc_info=True)

        return callback

    def _sync_progress_to_db(self, task_id: str, progress: int, message: str):
        """同步进度到数据库"""
        try:
            import asyncio
            from pymongo import MongoClient
            from app.core.config import settings

            # 创建同步 MongoDB 客户端
            sync_client = MongoClient(settings.MONGO_URI)
            sync_db = sync_client[settings.MONGO_DB]

            sync_db.analysis_tasks.update_one(
                {"task_id": task_id},
                {
                    "$set": {
                        "progress": progress,
                        "current_step": message,
                        "message": message,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
            sync_client.close()

            # 异步更新内存
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    self.memory_manager.update_task_status(
                        task_id=task_id,
                        status=TaskStatus.RUNNING,
                        progress=progress,
                        message=message,
                        current_step=message,
                    )
                )
            finally:
                loop.close()

        except Exception as e:
            logger.warning(f"⚠️ [Graph进度] 同步更新失败: {e}")

    def _build_analysis_result(
        self, request, state, decision, execution_time: float, analysis_date: str
    ) -> Dict[str, Any]:
        """构建分析结果"""
        import uuid

        # 提取reports
        try:
            extraction_result = ReportExtractor.extract_all_content(state)
            reports = extraction_result.get("reports", {})
        except Exception as e:
            logger.warning(f"⚠️ 提取reports时出错: {e}")
            reports = self._extract_reports_fallback(decision)

        # 格式化decision
        formatted_decision = self._format_decision(decision)

        # 生成summary和recommendation
        summary = self._generate_summary(reports, state)
        recommendation = self._generate_recommendation(formatted_decision)

        # 获取模型信息
        model_info = (
            decision.get("model_info", "Unknown")
            if isinstance(decision, dict)
            else "Unknown"
        )

        return {
            "analysis_id": str(uuid.uuid4()),
            "stock_code": request.stock_code,
            "stock_symbol": request.stock_code,
            "analysis_date": analysis_date,
            "summary": summary,
            "recommendation": recommendation,
            "confidence_score": formatted_decision.get("confidence", 0.0),
            "risk_level": "中等",
            "key_points": [],
            "detailed_analysis": decision,
            "execution_time": execution_time,
            "tokens_used": decision.get("tokens_used", 0)
            if isinstance(decision, dict)
            else 0,
            "state": state,
            "analysts": request.parameters.selected_analysts
            if request.parameters
            else [],
            "research_depth": request.parameters.research_depth
            if request.parameters
            else "快速",
            "reports": reports,
            "decision": formatted_decision,
            "model_info": model_info,
            "performance_metrics": state.get("performance_metrics", {})
            if isinstance(state, dict)
            else {},
        }

    def _extract_reports_fallback(self, decision) -> Dict[str, str]:
        """降级提取报告"""
        reports = {}
        try:
            if isinstance(decision, dict):
                for key, value in decision.items():
                    if isinstance(value, str) and len(value) > 50:
                        reports[key] = value
                logger.info(f"📊 降级：从decision中提取到 {len(reports)} 个报告")
        except Exception as e:
            logger.warning(f"⚠️ 降级提取也失败: {e}")
        return reports

    def _format_decision(self, decision) -> Dict[str, Any]:
        """格式化decision数据"""
        try:
            if isinstance(decision, dict):
                # 处理目标价格
                target_price = self._parse_target_price(decision.get("target_price"))

                # 将英文投资建议转换为中文
                action_translation = {
                    "BUY": "买入",
                    "SELL": "卖出",
                    "HOLD": "持有",
                    "buy": "买入",
                    "sell": "卖出",
                    "hold": "持有",
                }
                action = decision.get("action", "持有")
                chinese_action = action_translation.get(action, action)

                return {
                    "action": chinese_action,
                    "confidence": decision.get("confidence", 0.5),
                    "risk_score": decision.get("risk_score", 0.3),
                    "target_price": target_price,
                    "reasoning": decision.get("reasoning", "暂无分析推理"),
                }
        except Exception as e:
            logger.error(f"❌ 格式化decision失败: {e}")

        return {
            "action": "持有",
            "confidence": 0.5,
            "risk_score": 0.3,
            "target_price": None,
            "reasoning": "暂无分析推理",
        }

    def _parse_target_price(self, target_price) -> Optional[float]:
        """解析目标价格"""
        if target_price is None or target_price == "N/A":
            return None

        try:
            if isinstance(target_price, str):
                clean_price = (
                    target_price.replace("$", "")
                    .replace("¥", "")
                    .replace("￥", "")
                    .strip()
                )
                return (
                    float(clean_price)
                    if clean_price and clean_price != "None"
                    else None
                )
            elif isinstance(target_price, (int, float)):
                return float(target_price)
        except (ValueError, TypeError):
            pass
        return None

    def _generate_summary(self, reports: Dict[str, str], state) -> str:
        """生成摘要"""
        summary = ""

        # 1. 优先从reports中的final_trade_decision提取
        if isinstance(reports, dict) and "final_trade_decision" in reports:
            final_decision_content = reports["final_trade_decision"]
            if (
                isinstance(final_decision_content, str)
                and len(final_decision_content) > 50
            ):
                summary = (
                    final_decision_content[:200]
                    .replace("#", "")
                    .replace("*", "")
                    .strip()
                )
                if len(final_decision_content) > 200:
                    summary += "..."
                return summary

        # 2. 从state中提取
        if not summary and isinstance(state, dict):
            final_decision = state.get("final_trade_decision", "")
            if isinstance(final_decision, str) and len(final_decision) > 50:
                summary = final_decision[:200].replace("#", "").replace("*", "").strip()
                if len(final_decision) > 200:
                    summary += "..."
                return summary

        # 3. 从其他报告中提取
        if not summary and isinstance(reports, dict):
            for report_name, content in reports.items():
                if isinstance(content, str) and len(content) > 100:
                    summary = content[:200].replace("#", "").replace("*", "").strip()
                    if len(content) > 200:
                        summary += "..."
                    return summary

        # 4. 最后的备用方案
        if not summary:
            summary = "分析已完成，请查看详细报告。"

        return summary

    def _generate_recommendation(self, formatted_decision: Dict[str, Any]) -> str:
        """生成投资建议"""
        if not isinstance(formatted_decision, dict):
            return "请参考详细分析报告做出投资决策。"

        action = formatted_decision.get("action", "持有")
        target_price = formatted_decision.get("target_price")
        reasoning = formatted_decision.get("reasoning", "")

        recommendation = f"投资建议：{action}。"
        if target_price:
            recommendation += f"目标价格：{target_price}元。"
        if reasoning:
            recommendation += f"决策依据：{reasoning}"

        return recommendation

    async def _run_risk_validation(
        self, task_id: str, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行风控验证"""
        try:
            from app.services.execution_risk_gateway import (
                get_execution_risk_gateway,
            )

            logger.info(f"🔒 开始执行风控验证: {task_id}")
            risk_gateway = get_execution_risk_gateway()
            risk_validation = risk_gateway.validate_from_analysis_result(result)

            result["risk_validation"] = risk_validation.to_dict()

            if risk_validation.blocked:
                logger.warning(f"🚫 交易决策被风控拦截: {task_id}")
                result["warnings"] = result.get("warnings", []) + [
                    f"风控拦截: {risk_validation.summary}"
                ]
            elif not risk_validation.passed:
                logger.warning(f"⚠️ 交易决策存在风险警告: {task_id}")
                result["warnings"] = result.get("warnings", []) + [
                    f"风险提示: {risk_validation.summary}"
                ]
            else:
                logger.info(f"✅ 风控验证通过: {task_id}")

        except Exception as risk_error:
            logger.error(f"❌ 风控验证失败(继续保存结果): {task_id} - {risk_error}")

        return result

    async def _save_results(self, task_id: str, result: Dict[str, Any]):
        """保存分析结果"""
        try:
            logger.info(f"💾 开始保存分析结果: {task_id}")
            from app.services.analysis.report_generation_service import (
                ReportGenerationService,
            )

            report_service = ReportGenerationService()
            await report_service.save_analysis_results_complete(task_id, result)
            logger.info(f"✅ 分析结果保存完成: {task_id}")
        except Exception as save_error:
            logger.error(f"❌ 保存分析结果失败: {task_id} - {save_error}")

    async def _mark_task_completed(self, task_id: str, result: Dict[str, Any]):
        """标记任务完成"""
        await self.memory_manager.update_task_status(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            message="分析完成",
            current_step="completed",
            result_data=result,
        )

        from app.services.analysis.task_management_service import TaskManagementService

        task_service = TaskManagementService()
        await task_service.update_task_status(task_id, AnalysisStatus.COMPLETED, 100)

    async def _create_completion_notification(
        self, user_id: str, request, result: Dict[str, Any]
    ):
        """创建分析完成通知"""
        try:
            from app.services.notifications_service import get_notifications_service
            from app.models.notification import NotificationCreate

            svc = get_notifications_service()
            summary = str(result.get("summary", ""))[:120]
            await svc.create_and_publish(
                payload=NotificationCreate(
                    user_id=str(user_id),
                    type="analysis",
                    title=f"{request.stock_code} 分析完成",
                    content=summary,
                    link=f"/stocks/{request.stock_code}",
                    source="analysis",
                )
            )
        except Exception as notif_err:
            logger.warning(f"⚠️ 创建通知失败(忽略): {notif_err}")

    async def _handle_execution_error(
        self,
        task_id: str,
        request,
        error: Exception,
        progress_tracker: Optional[RedisProgressTracker] = None,
    ):
        """处理执行错误"""
        logger.error(f"❌ 后台分析任务失败: {task_id} - {error}")

        # 收集上下文信息
        error_context = {}
        if hasattr(request, "parameters") and request.parameters:
            if hasattr(request.parameters, "quick_model"):
                error_context["model"] = request.parameters.quick_model
            if hasattr(request.parameters, "deep_model"):
                error_context["model"] = request.parameters.deep_model

        # 格式化错误
        from app.utils.error_formatter import ErrorFormatter

        formatted_error = ErrorFormatter.format_error(str(error), error_context)
        user_friendly_error = (
            f"{formatted_error['title']}\n\n"
            f"{formatted_error['message']}\n\n"
            f"💡 {formatted_error['suggestion']}"
        )

        # 标记进度跟踪器失败
        if progress_tracker:
            progress_tracker.mark_failed(user_friendly_error)

        # 更新状态为失败
        await self.memory_manager.update_task_status(
            task_id=task_id,
            status=TaskStatus.FAILED,
            progress=0,
            message="分析失败",
            current_step="failed",
            error_message=user_friendly_error,
        )

        from app.services.analysis.task_management_service import TaskManagementService

        task_service = TaskManagementService()
        await task_service.update_task_status(
            task_id, AnalysisStatus.FAILED, 0, user_friendly_error
        )
