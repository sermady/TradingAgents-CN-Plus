# -*- coding: utf-8 -*-
"""
Progress Manager 单元测试

测试进度管理服务的核心功能：
- 创建进度跟踪器
- 更新进度
- 获取进度信息
- 完成分析
- 销毁跟踪器
- 清理旧跟踪器
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from app.services.progress_manager import ProgressManager


# ==============================================================================
# 测试进度管理器初始化
# ==============================================================================


@pytest.mark.unit
def test_progress_manager_init():
    """测试进度管理器初始化"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

        manager = ProgressManager()

        assert manager._trackers == {}
        assert manager._redis_client is not None


# ==============================================================================
# 测试创建进度跟踪器
# ==============================================================================


@pytest.mark.unit
def test_create_tracker():
    """测试创建进度跟踪器"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

    with patch("app.services.progress_manager.RedisProgressTracker") as MockTracker:
        mock_tracker = Mock()
        MockTracker.return_value = mock_tracker

        manager = ProgressManager()

        # 创建跟踪器
        task_id = "task_123"
        tracker = manager.create_tracker(
            task_id=task_id,
            analysts=["market", "fundamentals"],
            research_depth="comprehensive",
            llm_provider="dashscope",
        )

        assert tracker is not None
        assert manager._trackers[task_id] == tracker
        MockTracker.assert_called_once()


@pytest.mark.unit
def test_create_tracker_duplicate():
    """测试创建重复跟踪器"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

    with patch("app.services.progress_manager.RedisProgressTracker") as MockTracker:
        mock_tracker = Mock()
        MockTracker.return_value = mock_tracker

        manager = ProgressManager()

        # 第一次创建
        task_id = "task_123"
        tracker1 = manager.create_tracker(
            task_id=task_id,
            analysts=["market"],
            research_depth="quick",
            llm_provider="openai",
        )

        assert manager._trackers[task_id] == tracker1

        # 第二次创建相同task_id
        tracker2 = manager.create_tracker(
            task_id=task_id,
            analysts=["market", "fundamentals"],
            research_depth="comprehensive",
            llm_provider="dashscope",
        )

        # 应该返回已存在的跟踪器
        assert tracker2 == tracker1
        # MockTracker应该只调用一次
        assert MockTracker.call_count == 1


# ==============================================================================
# 测试获取进度跟踪器
# ==============================================================================


@pytest.mark.unit
def test_get_tracker_exists():
    """测试获取已存在的跟踪器"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

    manager = ProgressManager()

    # 创建跟踪器
    task_id = "task_123"
    with patch("app.services.progress_manager.RedisProgressTracker") as MockTracker:
        mock_tracker = Mock()
        MockTracker.return_value = mock_tracker
        manager.create_tracker(task_id, ["market"], "comprehensive", "openai")

    # 获取跟踪器
    tracker = manager.get_tracker(task_id)

    assert tracker is not None
    assert manager._trackers.get(task_id) == tracker


@pytest.mark.unit
def test_get_tracker_not_exists():
    """测试获取不存在的跟踪器"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

    manager = ProgressManager()

    # 获取不存在的跟踪器
    tracker = manager.get_tracker("nonexistent_task")

    assert tracker is None


# ==============================================================================
# 测试更新进度
# ==============================================================================


@pytest.mark.unit
def test_update_progress():
    """测试更新进度"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

    manager = ProgressManager()

    # 创建跟踪器
    task_id = "task_123"
    mock_tracker = Mock()
    manager._trackers[task_id] = mock_tracker

    # 更新进度
    manager.update_progress(task_id, "正在分析市场数据...")

    # 验证跟踪器方法被调用
    mock_tracker.update_progress.assert_called_once_with(message="正在分析市场数据...")


@pytest.mark.unit
def test_update_progress_not_exists():
    """测试更新不存在的任务进度"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

    manager = ProgressManager()

    # 更新不存在的任务进度
    manager.update_progress("nonexistent_task", "测试消息")

    # 应该不抛出异常
    assert "nonexistent_task" not in manager._trackers


# ==============================================================================
# 测试完成分析
# ==============================================================================


@pytest.mark.unit
def test_complete_analysis_success():
    """测试成功完成分析"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

    manager = ProgressManager()

    # 创建跟踪器
    task_id = "task_123"
    mock_tracker = Mock()
    manager._trackers[task_id] = mock_tracker

    # 完成分析（成功）
    manager.complete_analysis(task_id, success=True, reason="分析完成")

    # 验证跟踪器方法被调用
    mock_tracker.complete.assert_called_once_with(success=True, reason="分析完成")


@pytest.mark.unit
def test_complete_analysis_failure():
    """测试分析失败"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

    manager = ProgressManager()

    # 创建跟踪器
    task_id = "task_123"
    mock_tracker = Mock()
    manager._trackers[task_id] = mock_tracker

    # 完成分析（失败）
    manager.complete_analysis(task_id, success=False, reason="数据源错误")

    # 验证跟踪器方法被调用
    mock_tracker.complete.assert_called_once_with(success=False, reason="数据源错误")


@pytest.mark.unit
def test_complete_analysis_not_exists():
    """测试完成不存在的分析"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

    manager = ProgressManager()

    # 完成不存在的任务
    manager.complete_analysis("nonexistent_task")

    # 应该不抛出异常
    assert "nonexistent_task" not in manager._trackers


# ==============================================================================
# 测试销毁跟踪器
# ==============================================================================


@pytest.mark.unit
def test_destroy_tracker():
    """测试销毁跟踪器"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

    manager = ProgressManager()

    # 创建跟踪器
    task_id = "task_123"
    mock_tracker = Mock()
    manager._trackers[task_id] = mock_tracker

    # 销毁跟踪器
    manager.destroy_tracker(task_id)

    # 验证跟踪器从缓存中移除
    assert task_id not in manager._trackers
    # 验证跟踪器方法被调用
    mock_tracker.destroy.assert_called_once()


@pytest.mark.unit
def test_destroy_tracker_not_exists():
    """测试销毁不存在的跟踪器"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

    manager = ProgressManager()

    # 销毁不存在的跟踪器
    manager.destroy_tracker("nonexistent_task")

    # 应该不抛出异常
    assert "nonexistent_task" not in manager._trackers


# ==============================================================================
# 测试清理旧跟踪器
# ==============================================================================


@pytest.mark.unit
def test_cleanup_old_trackers():
    """测试清理旧跟踪器"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

    manager = ProgressManager()

    # 创建多个跟踪器
    task_ids = [f"task_{i}" for i in range(10)]
    for task_id in task_ids:
        mock_tracker = Mock()
        manager._trackers[task_id] = mock_tracker

    # 清理24小时前的跟踪器
    manager.cleanup_old_trackers(max_age_hours=24)

    # 验证每个跟踪器都被检查
    for task_id in task_ids:
        mock_tracker = manager._trackers.get(task_id)
        if mock_tracker:
            mock_tracker.is_expired.assert_called_once_with(max_age_hours=24)


# ==============================================================================
# 测试跟踪器管理
# ==============================================================================


@pytest.mark.unit
def test_multiple_trackers():
    """测试管理多个跟踪器"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

    with patch("app.services.progress_manager.RedisProgressTracker") as MockTracker:
        MockTracker.return_value = Mock()

        manager = ProgressManager()

        # 创建多个跟踪器
        task_ids = [f"task_{i}" for i in range(5)]
        for task_id in task_ids:
            manager.create_tracker(
                task_id=task_id,
                analysts=["market"],
                research_depth="quick",
                llm_provider="openai",
            )

        # 验证所有跟踪器都被创建
        assert len(manager._trackers) == 5
        for task_id in task_ids:
            assert task_id in manager._trackers


@pytest.mark.unit
def test_tracker_isolation():
    """测试跟踪器之间的隔离"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

    with patch("app.services.progress_manager.RedisProgressTracker") as MockTracker:
        mock_tracker1 = Mock()
        mock_tracker2 = Mock()
        MockTracker.side_effect = [mock_tracker1, mock_tracker2]

        manager = ProgressManager()

        # 创建两个跟踪器
        task_id_1 = "task_1"
        task_id_2 = "task_2"

        tracker1 = manager.create_tracker(
            task_id=task_id_1,
            analysts=["market"],
            research_depth="quick",
            llm_provider="openai",
        )

        tracker2 = manager.create_tracker(
            task_id=task_id_2,
            analysts=["fundamentals"],
            research_depth="comprehensive",
            llm_provider="dashscope",
        )

        # 验证两个跟踪器是独立的
        assert tracker1 != tracker2
        assert manager._trackers[task_id_1] != manager._trackers[task_id_2]

        # 更新一个跟踪器不应该影响另一个
        manager.update_progress(task_id_1, "任务1的进度")
        # tracker2的update_progress不应该被调用
        assert mock_tracker2.update_progress.call_count == 0


# ==============================================================================
# 测试边界条件
# ==============================================================================


@pytest.mark.unit
def test_empty_task_id():
    """测试空任务ID"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

        manager = ProgressManager()

        # 空任务ID
        tracker = manager.get_tracker("")

        assert tracker is None


@pytest.mark.unit
def test_empty_message():
    """测试空消息"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

        manager = ProgressManager()

        # 创建跟踪器
        task_id = "task_123"
        mock_tracker = Mock()
        manager._trackers[task_id] = mock_tracker

        # 更新空消息
        manager.update_progress(task_id, "")

        # 应该被处理
        mock_tracker.update_progress.assert_called_once_with(message="")


@pytest.mark.unit
def test_max_age_zero():
    """测试最大年龄为0"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

        manager = ProgressManager()

        # 创建跟踪器
        task_id = "task_123"
        mock_tracker = Mock()
        manager._trackers[task_id] = mock_tracker

        # 最大年龄为0（所有跟踪器都应该被清理）
        manager.cleanup_old_trackers(max_age_hours=0)

        mock_tracker.is_expired.assert_called_once_with(max_age_hours=0)


# ==============================================================================
# 测试错误处理
# ==============================================================================


@pytest.mark.unit
def test_error_handling_in_create():
    """测试创建跟踪器时的错误处理"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

    with patch("app.services.progress_manager.RedisProgressTracker") as MockTracker:
        # 模拟创建错误
        MockTracker.side_effect = Exception("创建跟踪器失败")

        manager = ProgressManager()

        # 应该抛出异常
        try:
            manager.create_tracker(
                task_id="task_123",
                analysts=["market"],
                research_depth="quick",
                llm_provider="openai",
            )
        except Exception as e:
            assert "创建跟踪器失败" in str(e)


@pytest.mark.unit
def test_error_handling_in_update():
    """测试更新进度时的错误处理"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

        manager = ProgressManager()

        # 创建跟踪器
        task_id = "task_123"
        mock_tracker = Mock()
        mock_tracker.update_progress.side_effect = Exception("更新失败")
        manager._trackers[task_id] = mock_tracker

        # 应该抛出异常
        try:
            manager.update_progress(task_id, "测试消息")
        except Exception as e:
            assert "更新失败" in str(e)


@pytest.mark.unit
def test_error_handling_in_complete():
    """测试完成分析时的错误处理"""
    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

        manager = ProgressManager()

        # 创建跟踪器
        task_id = "task_123"
        mock_tracker = Mock()
        mock_tracker.complete.side_effect = Exception("完成失败")
        manager._trackers[task_id] = mock_tracker

        # 应该抛出异常
        try:
            manager.complete_analysis(task_id, success=True, reason="完成")
        except Exception as e:
            assert "完成失败" in str(e)


# ==============================================================================
# 测试性能
# ==============================================================================


@pytest.mark.unit
@pytest.mark.slow
def test_performance_multiple_trackers():
    """测试管理多个跟踪器的性能"""
    import time

    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

    with patch("app.services.progress_manager.RedisProgressTracker") as MockTracker:
        mock_tracker = Mock()
        MockTracker.return_value = mock_tracker

        manager = ProgressManager()

        # 性能测试：创建和更新100个跟踪器
        start = time.time()
        task_ids = [f"task_{i:05d}" for i in range(100)]
        for task_id in task_ids:
            manager.create_tracker(
                task_id=task_id,
                analysts=["market", "fundamentals"],
                research_depth="comprehensive",
                llm_provider="dashscope",
            )
            manager.update_progress(task_id, f"分析进度 {task_id}")
        end = time.time()

        elapsed = end - start

        # 验证所有跟踪器都被创建
        assert len(manager._trackers) == 100

        # 性能应该在合理时间内（例如< 2秒）
        assert elapsed < 2


@pytest.mark.unit
@pytest.mark.slow
def test_performance_cleanup():
    """测试清理旧跟踪器的性能"""
    import time

    with patch("app.services.progress_manager.get_redis_client") as mock_get_redis:
        mock_redis = Mock()
        mock_get_redis.return_value = mock_redis

        manager = ProgressManager()

        # 创建大量跟踪器
        task_ids = [f"task_{i:05d}" for i in range(1000)]
        for task_id in task_ids:
            mock_tracker = Mock()
            manager._trackers[task_id] = mock_tracker

        # 性能测试：清理旧跟踪器
        start = time.time()
        manager.cleanup_old_trackers(max_age_hours=24)
        end = time.time()

        elapsed = end - start

        # 验证所有跟踪器都被检查
        assert len(manager._trackers) == 1000

        # 性能应该在合理时间内（例如< 1秒）
        assert elapsed < 1
