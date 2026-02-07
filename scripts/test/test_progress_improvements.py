# -*- coding: utf-8 -*-
"""
测试进度管理改进功能

借鉴上游 TradingAgents 项目设计思想的实现验证:
1. 统一状态转换逻辑
2. 标准化分析师顺序
3. 消息去重机制
"""

import pytest
import asyncio
from unittest.mock import Mock, patch


class TestAnalystOrderConstants:
    """测试分析师顺序常量"""

    def test_analyst_order_defined(self):
        """测试 ANALYST_ORDER 常量已定义"""
        from app.services.progress.constants import ANALYST_ORDER

        assert ANALYST_ORDER == ['market', 'social', 'news', 'fundamentals', 'china']

    def test_analyst_display_names(self):
        """测试分析师显示名称映射"""
        from app.services.progress.constants import ANALYST_DISPLAY_NAMES

        assert ANALYST_DISPLAY_NAMES['market'] == '市场分析师'
        assert ANALYST_DISPLAY_NAMES['social'] == '社交媒体分析师'
        assert ANALYST_DISPLAY_NAMES['news'] == '新闻分析师'
        assert ANALYST_DISPLAY_NAMES['fundamentals'] == '基本面分析师'
        assert ANALYST_DISPLAY_NAMES['china'] == '中国市场分析师'

    def test_analyst_report_map(self):
        """测试分析师报告字段映射"""
        from app.services.progress.constants import ANALYST_REPORT_MAP

        assert ANALYST_REPORT_MAP['market'] == 'market_report'
        assert ANALYST_REPORT_MAP['social'] == 'sentiment_report'
        assert ANALYST_REPORT_MAP['news'] == 'news_report'
        assert ANALYST_REPORT_MAP['fundamentals'] == 'fundamentals_report'
        assert ANALYST_REPORT_MAP['china'] == 'china_market_report'

    def test_analyst_status_constants(self):
        """测试状态常量"""
        from app.services.progress.constants import AnalystStatus

        assert AnalystStatus.PENDING == 'pending'
        assert AnalystStatus.IN_PROGRESS == 'in_progress'
        assert AnalystStatus.COMPLETED == 'completed'
        assert AnalystStatus.FAILED == 'failed'


class TestProgressManagerImprovements:
    """测试进度管理器改进"""

    @pytest.fixture
    def mock_tracker(self):
        """模拟进度跟踪器"""
        tracker = Mock()
        tracker.update_agent_status = Mock()
        return tracker

    @pytest.fixture
    def progress_manager(self, mock_tracker):
        """模拟进度管理器"""
        with patch('app.services.progress_manager.get_redis_client') as mock_redis:
            mock_redis.return_value = Mock()
            from app.services.progress_manager import ProgressManager
            manager = ProgressManager()
            manager._trackers['test_task'] = mock_tracker
            yield manager

    def test_normalize_analyst_order(self, progress_manager):
        """测试分析师顺序标准化"""
        manager = progress_manager

        # 测试乱序输入
        selected = ['china', 'market', 'fundamentals']
        ordered = manager.normalize_analyst_order(selected)

        # 验证按标准顺序排列
        assert ordered == ['market', 'fundamentals', 'china']

    def test_normalize_analyst_order_with_undefined(self, progress_manager):
        """测试包含未定义分析师类型的标准化"""
        manager = progress_manager

        # 包含未定义的分析师类型
        selected = ['market', 'undefined_analyst', 'news']
        ordered = manager.normalize_analyst_order(selected)

        # 标准类型按顺序，未定义类型在后
        assert ordered[0] == 'market'
        assert ordered[1] == 'news'
        assert 'undefined_analyst' in ordered

    def test_update_analyst_statuses_all_pending(self, progress_manager):
        """测试所有分析师等待状态"""
        from app.services.progress_manager import AnalystStatus

        manager = progress_manager

        # 没有任何报告
        reports = {}
        selected = ['market', 'news']

        status_map = manager.update_analyst_statuses('test_task', reports, selected)

        # 第一个应该是执行中，其余等待
        assert status_map['market'] == AnalystStatus.IN_PROGRESS
        assert status_map['news'] == AnalystStatus.PENDING

    def test_update_analyst_statuses_partial_complete(self, progress_manager):
        """测试部分分析师完成状态"""
        from app.services.progress_manager import AnalystStatus

        manager = progress_manager

        # market 已完成，其他未完成
        reports = {'market_report': 'market analysis content'}
        selected = ['market', 'news', 'fundamentals']

        status_map = manager.update_analyst_statuses('test_task', reports, selected)

        assert status_map['market'] == AnalystStatus.COMPLETED
        assert status_map['news'] == AnalystStatus.IN_PROGRESS
        assert status_map['fundamentals'] == AnalystStatus.PENDING

    def test_update_analyst_statuses_all_complete(self, progress_manager):
        """测试所有分析师完成状态"""
        from app.services.progress_manager import AnalystStatus

        manager = progress_manager

        # 所有报告都完成
        reports = {
            'market_report': 'content',
            'sentiment_report': 'content',
            'news_report': 'content',
        }
        selected = ['market', 'social', 'news']

        status_map = manager.update_analyst_statuses('test_task', reports, selected)

        # 全部完成
        assert all(s == AnalystStatus.COMPLETED for s in status_map.values())

    def test_get_next_pending_analyst(self, progress_manager):
        """测试获取下一个等待中的分析师"""
        from app.services.progress_manager import AnalystStatus

        manager = progress_manager

        status_map = {
            'market': AnalystStatus.COMPLETED,
            'social': AnalystStatus.IN_PROGRESS,
            'news': AnalystStatus.PENDING,
            'fundamentals': AnalystStatus.PENDING,
        }
        selected = ['market', 'social', 'news', 'fundamentals']

        next_pending = manager.get_next_pending_analyst(status_map, selected)

        # 下一个等待的是 news
        assert next_pending == 'news'


class TestMessageDedupCache:
    """测试消息去重缓存"""

    @pytest.mark.asyncio
    async def test_is_duplicate_new_message(self):
        """测试新消息不是重复"""
        from app.services.websocket_manager import MessageDedupCache

        cache = MessageDedupCache(max_size=10, window=60)
        message = {
            'task_id': 'task_1',
            'type': 'progress',
            'step_name': 'market_analysis',
            'progress': 50
        }

        is_dup = await cache.is_duplicate(message)
        assert is_dup is False

    @pytest.mark.asyncio
    async def test_is_duplicate_same_message(self):
        """测试相同消息被识别为重复"""
        from app.services.websocket_manager import MessageDedupCache

        cache = MessageDedupCache(max_size=10, window=60)
        message = {
            'task_id': 'task_1',
            'type': 'progress',
            'step_name': 'market_analysis',
            'progress': 50
        }

        # 第一次不是重复
        is_dup = await cache.is_duplicate(message)
        assert is_dup is False

        # 第二次是重复
        is_dup = await cache.is_duplicate(message)
        assert is_dup is True

    @pytest.mark.asyncio
    async def test_is_duplicate_different_messages(self):
        """测试不同消息不是重复"""
        from app.services.websocket_manager import MessageDedupCache

        cache = MessageDedupCache(max_size=10, window=60)

        message1 = {
            'task_id': 'task_1',
            'type': 'progress',
            'step_name': 'market_analysis',
            'progress': 50
        }
        message2 = {
            'task_id': 'task_1',
            'type': 'progress',
            'step_name': 'market_analysis',
            'progress': 60  # 不同的进度
        }

        is_dup1 = await cache.is_duplicate(message1)
        is_dup2 = await cache.is_duplicate(message2)

        assert is_dup1 is False
        assert is_dup2 is False  # 进度不同，不是重复

    @pytest.mark.asyncio
    async def test_cache_cleanup(self):
        """测试缓存过期清理"""
        from app.services.websocket_manager import MessageDedupCache

        # 使用非常短的时间窗口
        cache = MessageDedupCache(max_size=10, window=0.01)

        message = {
            'task_id': 'task_1',
            'type': 'progress',
            'step_name': 'market_analysis',
            'progress': 50
        }

        # 添加消息
        await cache.is_duplicate(message)

        # 等待过期
        await asyncio.sleep(0.02)

        # 过期后应该不是重复（因为已被清理）
        is_dup = await cache.is_duplicate(message)
        assert is_dup is False

    @pytest.mark.asyncio
    async def test_cache_size_limit(self):
        """测试缓存大小限制"""
        from app.services.websocket_manager import MessageDedupCache

        cache = MessageDedupCache(max_size=3, window=60)

        # 添加超过限制的消息
        for i in range(5):
            message = {
                'task_id': f'task_{i}',
                'type': 'progress',
                'step_name': 'analysis',
                'progress': i * 10
            }
            await cache.is_duplicate(message)

        # 缓存应该只保留最近的3个
        assert len(cache._cache) <= 3


class TestRedisProgressTrackerImprovements:
    """测试 RedisProgressTracker 改进"""

    @patch('app.services.progress.tracker.os.makedirs')
    @patch('app.services.progress.tracker.os.getenv')
    def test_update_agent_status(self, mock_getenv, mock_makedirs):
        """测试更新代理状态"""
        mock_getenv.return_value = 'false'  # Redis未启用

        from app.services.progress.tracker import RedisProgressTracker

        tracker = RedisProgressTracker(
            task_id='test_task',
            analysts=['market', 'news'],
            research_depth='标准',
            llm_provider='dashscope'
        )

        # 更新代理状态
        tracker.update_agent_status('市场分析师', 'in_progress')

        # 验证状态已保存
        assert 'agent_status' in tracker.progress_data
        assert tracker.progress_data['agent_status']['市场分析师']['status'] == 'in_progress'

    @patch('app.services.progress.tracker.os.makedirs')
    @patch('app.services.progress.tracker.os.getenv')
    def test_get_agent_status(self, mock_getenv, mock_makedirs):
        """测试获取代理状态"""
        mock_getenv.return_value = 'false'

        from app.services.progress.tracker import RedisProgressTracker

        tracker = RedisProgressTracker(
            task_id='test_task',
            analysts=['market'],
            research_depth='标准',
            llm_provider='dashscope'
        )

        # 先更新状态
        tracker.update_agent_status('市场分析师', 'completed')

        # 获取状态
        status = tracker.get_agent_status('市场分析师')
        assert status == 'completed'

        # 获取不存在的状态
        status = tracker.get_agent_status('不存在分析师')
        assert status is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
