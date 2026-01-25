# -*- coding: utf-8 -*-
"""
Analysis Service 单元测试

测试分析服务的核心功能：
- 用户ID转换
- TradingGraph缓存
- 单股分析提交
- 批量分析提交
- 任务执行
- 进度跟踪
- Token使用记录
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime
from bson import ObjectId

from app.services.analysis_service import AnalysisService
from app.models.analysis import (
    AnalysisParameters,
    AnalysisTask,
    AnalysisResult,
    AnalysisStatus,
    BatchStatus,
    SingleAnalysisRequest,
    BatchAnalysisRequest,
)
from app.models.user import PyObjectId


# ==============================================================================
# 测试分析服务初始化
# ==============================================================================


@pytest.mark.unit
def test_analysis_service_init():
    """测试分析服务初始化"""
    with patch("app.services.analysis_service.get_redis_client"):
        with patch("app.services.analysis_service.UsageStatisticsService"):
            with patch("app.services.analysis_service.get_progress_manager"):
                with patch("app.services.analysis_service.get_billing_service"):
                    service = AnalysisService()

                    assert service.queue_service is not None
                    assert service.usage_service is not None
                    assert service.progress_manager is not None
                    assert service.billing_service is not None
                    assert service._trading_graph_cache == {}
                    assert service._progress_trackers == {}


# ==============================================================================
# 测试用户ID转换
# ==============================================================================


@pytest.mark.unit
def test_convert_user_id_valid_string():
    """测试有效字符串用户ID转换"""
    with patch("app.services.analysis_service.get_redis_client"):
        with patch("app.services.analysis_service.UsageStatisticsService"):
            with patch("app.services.analysis_service.get_progress_manager"):
                with patch("app.services.analysis_service.get_billing_service"):
                    service = AnalysisService()

                    # 测试有效的ObjectId字符串
                    valid_id = "507f1f77bcf86cd799439011"
                    result = service._convert_user_id(valid_id)

                    # PyObjectId是Annotated类型，不能直接用isinstance
                    # 改为检查字符串表示
                    assert str(result) == valid_id


@pytest.mark.unit
def test_convert_user_id_admin():
    """测试admin用户ID转换"""
    with patch("app.services.analysis_service.get_redis_client"):
        with patch("app.services.analysis_service.UsageStatisticsService"):
            with patch("app.services.analysis_service.get_progress_manager"):
                with patch("app.services.analysis_service.get_billing_service"):
                    with patch(
                        "app.services.analysis_service.settings"
                    ) as mock_settings:
                        mock_settings.ADMIN_USER_ID = "507f1f77bcf86cd799439011"

                        service = AnalysisService()

                        result = service._convert_user_id("admin")

                        # 检查字符串表示
                        assert str(result) == "507f1f77bcf86cd799439011"


@pytest.mark.unit
def test_convert_user_id_invalid_string():
    """测试无效字符串用户ID转换"""
    with patch("app.services.analysis_service.get_redis_client"):
        with patch("app.services.analysis_service.UsageStatisticsService"):
            with patch("app.services.analysis_service.get_progress_manager"):
                with patch("app.services.analysis_service.get_billing_service"):
                    service = AnalysisService()

                    # 测试无效的ObjectId字符串
                    invalid_id = "invalid_id_string"
                    result = service._convert_user_id(invalid_id)

                    # 应该生成新的ObjectId
                    assert str(result) != invalid_id


@pytest.mark.unit
def test_convert_user_id_none():
    """测试None用户ID转换"""
    with patch("app.services.analysis_service.get_redis_client"):
        with patch("app.services.analysis_service.UsageStatisticsService"):
            with patch("app.services.analysis_service.get_progress_manager"):
                with patch("app.services.analysis_service.get_billing_service"):
                    service = AnalysisService()

                    result = service._convert_user_id(None)

                    assert isinstance(result, PyObjectId)


# ==============================================================================
# 测试TradingGraph缓存
# ==============================================================================


@pytest.mark.unit
def test_get_trading_graph_cache():
    """测试TradingGraph缓存功能"""
    with patch("app.services.analysis_service.get_redis_client"):
        with patch("app.services.analysis_service.UsageStatisticsService"):
            with patch("app.services.analysis_service.get_progress_manager"):
                with patch("app.services.analysis_service.get_billing_service"):
                    with patch(
                        "app.services.analysis_service.TradingAgentsGraph"
                    ) as MockGraph:
                        # 每次调用返回新的Mock实例
                        MockGraph.side_effect = [Mock(), Mock()]

                        service = AnalysisService()

                        config1 = {
                            "llm_provider": "openai",
                            "model": "gpt-4",
                            "selected_analysts": ["market", "fundamentals"],
                            "debug": False,
                        }

                        # 第一次调用应该创建新的实例
                        graph1 = service._get_trading_graph(config1)
                        assert MockGraph.call_count == 1

                        # 第二次调用应该使用缓存的实例
                        graph2 = service._get_trading_graph(config1)
                        assert MockGraph.call_count == 1  # 没有增加
                        assert graph1 is graph2  # 同一个实例

                        # 不同配置应该创建新实例
                        config2 = {**config1, "model": "gpt-3.5"}
                        graph3 = service._get_trading_graph(config2)
                        assert MockGraph.call_count == 2
                        assert graph1 is not graph3


@pytest.mark.unit
def test_get_trading_graph_default_config():
    """测试使用默认配置创建TradingGraph"""
    with patch("app.services.analysis_service.get_redis_client"):
        with patch("app.services.analysis_service.UsageStatisticsService"):
            with patch("app.services.analysis_service.get_progress_manager"):
                with patch("app.services.analysis_service.get_billing_service"):
                    with patch(
                        "app.services.analysis_service.TradingAgentsGraph"
                    ) as MockGraph:
                        MockGraph.return_value = Mock()

                        service = AnalysisService()

                        # 最小配置
                        minimal_config = {}
                        graph = service._get_trading_graph(minimal_config)

                        # 验证调用参数
                        call_args = MockGraph.call_args
                        assert call_args is not None

                        # 验证默认参数
                        kwargs = call_args[1] if len(call_args) > 1 else {}
                        assert "selected_analysts" in kwargs
                        assert "debug" in kwargs
                        assert "config" in kwargs


# ==============================================================================
# 测试单股分析提交
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_single_analysis_success():
    """测试成功提交单股分析"""
    with patch("app.services.analysis_service.get_redis_client"):
        with patch(
            "app.services.analysis_service.UsageStatisticsService"
        ) as MockUsageService:
            mock_usage = AsyncMock()
            mock_usage.get_user_concurrent_tasks.return_value = 0
            MockUsageService.return_value = mock_usage

            with patch(
                "app.services.analysis_service.get_progress_manager"
            ) as MockProgressManager:
                mock_progress_manager = AsyncMock()
                mock_progress_manager.create_analysis.return_value = "task_123"
                MockProgressManager.return_value = mock_progress_manager

                with patch(
                    "app.services.analysis_service.get_billing_service"
                ) as MockBillingService:
                    mock_billing = AsyncMock()
                    MockBillingService.return_value = mock_billing

                    with patch(
                        "app.services.analysis_service.QueueService"
                    ) as MockQueueService:
                        mock_queue = AsyncMock()
                        mock_queue.can_submit.return_value = True
                        mock_queue.submit_task.return_value = True
                        MockQueueService.return_value = mock_queue

                        service = AnalysisService()

                        request = SingleAnalysisRequest(
                            stock_code="000001",
                            analysis_type="comprehensive",
                            depth_level=3,
                        )

                        result = await service.submit_single_analysis(
                            user_id="507f1f77bcf86cd799439011", request=request
                        )

                        # 验证结果
                        assert result is not None
                        assert result.task_id == "task_123"
                        assert result.status == AnalysisStatus.QUEUED

                        # 验证调用
                        mock_usage.get_user_concurrent_tasks.assert_called_once()
                        mock_progress_manager.create_analysis.assert_called_once()
                        mock_queue.submit_task.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_single_analysis_concurrent_limit():
    """测试并发限制"""
    with patch("app.services.analysis_service.get_redis_client"):
        with patch(
            "app.services.analysis_service.UsageStatisticsService"
        ) as MockUsageService:
            mock_usage = AsyncMock()
            mock_usage.get_user_concurrent_tasks.return_value = 10  # 超过限制
            MockUsageService.return_value = mock_usage

            with patch("app.services.analysis_service.get_progress_manager"):
                with patch("app.services.analysis_service.get_billing_service"):
                    with patch("app.services.analysis_service.QueueService"):
                        service = AnalysisService()

                        request = SingleAnalysisRequest(
                            stock_code="000001",
                            analysis_type="comprehensive",
                            depth_level=3,
                        )

                        # 应该抛出异常或返回错误
                        with pytest.raises(Exception) as exc_info:
                            await service.submit_single_analysis(
                                user_id="507f1f77bcf86cd799439011", request=request
                            )

                        assert "concurrent" in str(exc_info.value).lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_single_analysis_invalid_stock():
    """测试无效股票代码"""
    with patch("app.services.analysis_service.get_redis_client"):
        with patch("app.services.analysis_service.UsageStatisticsService"):
            with patch("app.services.analysis_service.get_progress_manager"):
                with patch("app.services.analysis_service.get_billing_service"):
                    with patch("app.services.analysis_service.QueueService"):
                        service = AnalysisService()

                        # 无效的股票代码
                        request = SingleAnalysisRequest(
                            stock_code="",  # 空代码
                            analysis_type="comprehensive",
                            depth_level=3,
                        )

                        # 应该抛出验证错误
                        with pytest.raises(ValueError):
                            await service.submit_single_analysis(
                                user_id="507f1f77bcf86cd799439011", request=request
                            )


# ==============================================================================
# 测试批量分析提交
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_batch_analysis_success():
    """测试成功提交批量分析"""
    with patch("app.services.analysis_service.get_redis_client"):
        with patch(
            "app.services.analysis_service.UsageStatisticsService"
        ) as MockUsageService:
            mock_usage = AsyncMock()
            mock_usage.get_user_concurrent_tasks.return_value = 0
            MockUsageService.return_value = mock_usage

            with patch(
                "app.services.analysis_service.get_progress_manager"
            ) as MockProgressManager:
                mock_progress_manager = AsyncMock()
                mock_progress_manager.create_batch_analysis.return_value = "batch_123"
                MockProgressManager.return_value = mock_progress_manager

            with patch("app.services.analysis_service.get_billing_service"):
                with patch(
                    "app.services.analysis_service.QueueService"
                ) as MockQueueService:
                    mock_queue = AsyncMock()
                    mock_queue.can_submit.return_value = True
                    mock_queue.submit_task.return_value = True
                    MockQueueService.return_value = mock_queue

                service = AnalysisService()

                request = BatchAnalysisRequest(
                    stock_codes=["000001", "600519", "000002"],
                    analysis_type="comprehensive",
                    depth_level=3,
                    enable_parallel=True,
                )

                result = await service.submit_batch_analysis(
                    user_id="507f1f77bcf86cd799439011", request=request
                )

                # 验证结果
                assert result is not None
                assert result.batch_id == "batch_123"
                assert result.status == BatchStatus.QUEUED
                assert len(result.task_ids) == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_submit_batch_analysis_too_many_stocks():
    """测试批量分析股票数量过多"""
    with patch("app.services.analysis_service.get_redis_client"):
        with patch("app.services.analysis_service.UsageStatisticsService"):
            with patch("app.services.analysis_service.get_progress_manager"):
                with patch("app.services.analysis_service.get_billing_service"):
                    with patch("app.services.analysis_service.QueueService"):
                        service = AnalysisService()

                        # 超过限制的股票数量
                        too_many_stocks = [
                            f"00000{i}" for i in range(1, 51)
                        ]  # 50只股票
                        request = BatchAnalysisRequest(
                            stock_codes=too_many_stocks,
                            analysis_type="comprehensive",
                            depth_level=3,
                        )

                        # 应该抛出异常
                        with pytest.raises(ValueError):
                            await service.submit_batch_analysis(
                                user_id="507f1f77bcf86cd799439011", request=request
                            )


# ==============================================================================
# 测试任务状态更新
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_task_status():
    """测试任务状态更新"""
    with patch("app.services.analysis_service.get_redis_client"):
        with patch("app.services.analysis_service.UsageStatisticsService"):
            with patch("app.services.analysis_service.get_progress_manager"):
                with patch("app.services.analysis_service.get_billing_service"):
                    with patch("app.services.analysis_service.QueueService"):
                        service = AnalysisService()

                        task_id = "task_123"
                        new_status = AnalysisStatus.RUNNING
                        progress = 0.5
                        message = "分析进行中..."

                        # Mock数据库操作
                        with patch.object(
                            service, "_update_task_status_with_tracker"
                        ) as mock_update:
                            mock_update.return_value = True

                            await service._update_task_status(
                                task_id=task_id,
                                status=new_status,
                                progress=progress,
                                message=message,
                            )

                            # 验证调用
                            mock_update.assert_called_once_with(
                                task_id, new_status, progress, message
                            )


# ==============================================================================
# 测试Token使用记录
# ==============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_record_token_usage():
    """测试Token使用记录"""
    with patch("app.services.analysis_service.get_redis_client"):
        with patch(
            "app.services.analysis_service.UsageStatisticsService"
        ) as MockUsageService:
            mock_usage = AsyncMock()
            mock_usage.record_token_usage.return_value = True
            MockUsageService.return_value = mock_usage

            service = AnalysisService()

            user_id = "507f1f77bcf86cd799439011"
            task_id = "task_123"
            model = "gpt-4"
            tokens = {
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "total_tokens": 300,
            }

            await service._record_token_usage(
                user_id=user_id, task_id=task_id, model=model, tokens=tokens
            )

            # 验证调用
            mock_usage.record_token_usage.assert_called_once_with(
                user_id=user_id,
                model=model,
                prompt_tokens=tokens["prompt_tokens"],
                completion_tokens=tokens["completion_tokens"],
                task_id=task_id,
            )


# ==============================================================================
# 测试错误处理
# ==============================================================================


@pytest.mark.unit
def test_error_handling_in_convert_user_id():
    """测试用户ID转换中的错误处理"""
    with patch("app.services.analysis_service.get_redis_client"):
        with patch("app.services.analysis_service.UsageStatisticsService"):
            with patch("app.services.analysis_service.get_progress_manager"):
                with patch("app.services.analysis_service.get_billing_service"):
                    service = AnalysisService()

                    # 测试各种无效输入（除了None，因为类型检查会在传入前失败）
                    invalid_inputs = ["", "invalid", "12345", {"id": "test"}]

                    for invalid_input in invalid_inputs:
                        # 应该不会抛出异常，而是生成新的ObjectId
                        result = service._convert_user_id(invalid_input)
                        # 检查生成了ObjectId
                        assert len(str(result)) == 24  # ObjectId字符串长度


@pytest.mark.unit
@pytest.mark.asyncio
async def test_error_handling_in_submit_analysis():
    """测试提交分析时的错误处理"""
    with patch("app.services.analysis_service.get_redis_client"):
        with patch("app.services.analysis_service.UsageStatisticsService"):
            with patch(
                "app.services.analysis_service.get_progress_manager"
            ) as MockProgressManager:
                # 模拟错误
                mock_progress_manager = AsyncMock()
                mock_progress_manager.create_analysis.side_effect = Exception(
                    "Database error"
                )
                MockProgressManager.return_value = mock_progress_manager

            with patch("app.services.analysis_service.get_billing_service"):
                with patch("app.services.analysis_service.QueueService"):
                    service = AnalysisService()

                    request = SingleAnalysisRequest(
                        stock_code="000001",
                        analysis_type="comprehensive",
                        depth_level=3,
                    )

                    # 应该抛出异常
                    with pytest.raises(Exception):
                        await service.submit_single_analysis(
                            user_id="507f1f77bcf86cd799439011", request=request
                        )


# ==============================================================================
# 测试边界条件
# ==============================================================================


@pytest.mark.unit
def test_trading_graph_cache_with_different_configs():
    """测试不同配置的缓存行为"""
    with patch("app.services.analysis_service.get_redis_client"):
        with patch("app.services.analysis_service.UsageStatisticsService"):
            with patch("app.services.analysis_service.get_progress_manager"):
                with patch("app.services.analysis_service.get_billing_service"):
                    with patch(
                        "app.services.analysis_service.TradingAgentsGraph"
                    ) as MockGraph:
                        MockGraph.return_value = Mock()

                        service = AnalysisService()

                        configs = [
                            {"model": "gpt-4"},
                            {"model": "gpt-4", "temperature": 0.5},
                            {"model": "gpt-4", "temperature": 0.7},
                            {"model": "gpt-3.5"},
                        ]

                        graphs = []
                        for config in configs:
                            graph = service._get_trading_graph(config)
                            graphs.append(graph)

                        # 每个不同的配置应该创建新的实例
                        assert MockGraph.call_count == 4

                        # 相同配置应该复用
                        graph_again = service._get_trading_graph(configs[0])
                        assert MockGraph.call_count == 4  # 没有增加
                        assert graph_again is graphs[0]


# ==============================================================================
# 测试性能
# ==============================================================================


@pytest.mark.unit
@pytest.mark.slow
def test_trading_graph_cache_performance():
    """测试TradingGraph缓存性能"""
    import time

    with patch("app.services.analysis_service.get_redis_client"):
        with patch("app.services.analysis_service.UsageStatisticsService"):
            with patch("app.services.analysis_service.get_progress_manager"):
                with patch("app.services.analysis_service.get_billing_service"):
                    with patch(
                        "app.services.analysis_service.TradingAgentsGraph"
                    ) as MockGraph:
                        MockGraph.return_value = Mock()

                        service = AnalysisService()

                        config = {"model": "gpt-4"}

                        # 第一次调用（创建）
                        start = time.time()
                        service._get_trading_graph(config)
                        create_time = time.time() - start

                        # 第二次调用（缓存）
                        start = time.time()
                        service._get_trading_graph(config)
                        cache_time = time.time() - start

                        # 缓存调用应该快得多
                        assert cache_time < create_time


# ==============================================================================
# 测试数据验证
# ==============================================================================


@pytest.mark.unit
def test_validate_analysis_parameters():
    """测试分析参数验证"""
    with patch("app.services.analysis_service.get_redis_client"):
        with patch("app.services.analysis_service.UsageStatisticsService"):
            with patch("app.services.analysis_service.get_progress_manager"):
                with patch("app.services.analysis_service.get_billing_service"):
                    service = AnalysisService()

                    # 有效参数
                    valid_params = {
                        "stock_code": "000001",
                        "analysis_type": "comprehensive",
                        "depth_level": 3,
                    }

                    # 无效参数
                    invalid_params = {
                        "stock_code": "",  # 空代码
                        "analysis_type": "invalid_type",  # 无效类型
                        "depth_level": 10,  # 超出范围
                    }

                    # 这里应该有参数验证逻辑
                    # 由于服务中可能没有显式的验证方法，我们测试使用这些参数时的行为
                    # 如果有专门的验证方法，应该测试它
