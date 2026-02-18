# -*- coding: utf-8 -*-
"""分析执行服务核心模块

整合所有混入类，提供统一的分析执行服务接口
"""

import asyncio
import concurrent.futures
import logging
from typing import TYPE_CHECKING, Optional

from app.services.analysis.execution.config_builder import ConfigBuilderMixin
from app.services.analysis.execution.progress_manager import ProgressManagerMixin
from app.services.analysis.execution.result_builder import ResultBuilderMixin
from app.services.memory_state_manager import get_memory_state_manager
from app.services.progress_log_handler import (
    register_analysis_tracker,
    unregister_analysis_tracker,
)

if TYPE_CHECKING:
    from app.services.redis_progress_tracker import RedisProgressTracker

logger = logging.getLogger(__name__)


class AnalysisExecutionService(
    ConfigBuilderMixin, ProgressManagerMixin, ResultBuilderMixin
):
    """分析执行服务

    整合配置构建、进度管理、结果构建等功能，提供完整的分析执行能力
    """

    def __init__(self):
        # 初始化各混入类
        ProgressManagerMixin.__init__(self)
        self.memory_manager = get_memory_state_manager()
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=3)

    async def execute_analysis_background(self, task_id: str, user_id: str, request):
        """在后台执行分析任务

        Args:
            task_id: 任务ID
            user_id: 用户ID
            request: 分析请求对象
        """
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
        """验证股票代码

        Args:
            task_id: 任务ID
            request: 分析请求对象
            stock_code: 股票代码

        Returns:
            验证是否通过
        """
        from app.models.analysis import AnalysisStatus
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

    async def _execute_analysis_sync(
        self,
        task_id: str,
        user_id: str,
        request,
        progress_tracker: Optional["RedisProgressTracker"] = None,
    ):
        """同步执行分析（在共享线程池中运行）

        Args:
            task_id: 任务ID
            user_id: 用户ID
            request: 分析请求对象
            progress_tracker: 进度跟踪器

        Returns:
            分析结果字典
        """
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
        progress_tracker: Optional["RedisProgressTracker"] = None,
    ):
        """同步执行分析的具体实现

        Args:
            task_id: 任务ID
            user_id: 用户ID
            request: 分析请求对象
            progress_tracker: 进度跟踪器

        Returns:
            分析结果字典
        """
        from datetime import datetime

        from tradingagents.utils.logging_init import get_logger, init_logging

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
