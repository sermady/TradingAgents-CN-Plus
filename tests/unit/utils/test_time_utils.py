# -*- coding: utf-8 -*-
"""
时间工具模块测试
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import patch
import sys
import os

# 添加项目根目录到路径
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


class TestTimeUtils:
    """测试时间工具函数"""

    def test_get_current_date(self):
        """测试获取当前日期"""
        from tradingagents.utils.time_utils import get_current_date

        result = get_current_date()
        assert isinstance(result, date)
        assert result == date.today()

    def test_get_current_datetime(self):
        """测试获取当前日期时间"""
        from tradingagents.utils.time_utils import get_current_datetime

        result = get_current_datetime()
        assert isinstance(result, datetime)

    def test_get_current_date_str_default(self):
        """测试获取默认格式日期字符串"""
        from tradingagents.utils.time_utils import get_current_date_str

        result = get_current_date_str()
        # 默认格式: 2026年01月25日
        assert isinstance(result, str)
        assert "年" in result
        assert "月" in result
        assert "日" in result

    def test_get_current_date_str_custom_format(self):
        """测试自定义格式日期字符串"""
        from tradingagents.utils.time_utils import get_current_date_str

        result = get_current_date_str("%Y-%m-%d")
        assert isinstance(result, str)
        assert "-" in result

    def test_get_current_datetime_str_default(self):
        """测试获取默认格式日期时间字符串"""
        from tradingagents.utils.time_utils import get_current_datetime_str

        result = get_current_datetime_str()
        assert isinstance(result, str)
        assert "年" in result
        assert "月" in result

    def test_get_current_datetime_str_custom_format(self):
        """测试自定义格式日期时间字符串"""
        from tradingagents.utils.time_utils import get_current_datetime_str

        result = get_current_datetime_str("%Y-%m-%d %H:%M:%S")
        assert isinstance(result, str)
        assert "-" in result
        assert ":" in result

    def test_get_chinese_date(self):
        """测试获取中文日期"""
        from tradingagents.utils.time_utils import get_chinese_date

        result = get_chinese_date()
        assert isinstance(result, str)
        assert "年" in result
        assert "月" in result
        assert "日" in result

    def test_get_chinese_weekday(self):
        """测试获取中文星期几"""
        from tradingagents.utils.time_utils import get_chinese_weekday

        result = get_chinese_weekday()
        assert isinstance(result, str)
        assert result in ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    def test_get_iso_date(self):
        """测试获取ISO格式日期"""
        from tradingagents.utils.time_utils import get_iso_date

        result = get_iso_date()
        assert isinstance(result, str)
        assert "-" in result
        # 格式: 2026-01-25
        parts = result.split("-")
        assert len(parts) == 3

    def test_get_chinese_datetime(self):
        """测试获取中文日期时间"""
        from tradingagents.utils.time_utils import get_chinese_datetime

        result = get_chinese_datetime()
        assert isinstance(result, str)
        assert "年" in result
        assert "月" in result
        assert "日" in result

    def test_get_now(self):
        """测试获取当前时间（now函数）"""
        from tradingagents.utils.time_utils import get_now

        result = get_now()
        assert isinstance(result, datetime)

    def test_get_today_str(self):
        """测试获取今日字符串"""
        from tradingagents.utils.time_utils import get_today_str

        result = get_today_str()
        assert isinstance(result, str)

    def test_get_days_ago_str(self):
        """测试获取N天前日期字符串"""
        from tradingagents.utils.time_utils import get_days_ago_str

        result = get_days_ago_str(7)
        assert isinstance(result, str)

    def test_get_days_later_str(self):
        """测试获取N天后日期字符串"""
        from tradingagents.utils.time_utils import get_days_later_str

        result = get_days_later_str(7)
        assert isinstance(result, str)

    def test_get_timestamp(self):
        """测试获取时间戳"""
        from tradingagents.utils.time_utils import get_timestamp

        result = get_timestamp()
        assert isinstance(result, datetime)

    def test_get_iso_timestamp(self):
        """测试获取ISO格式时间戳"""
        from tradingagents.utils.time_utils import get_iso_timestamp

        result = get_iso_timestamp()
        assert isinstance(result, str)

    def test_format_datetime(self):
        """测试日期时间格式化"""
        from tradingagents.utils.time_utils import format_datetime

        test_datetime = datetime(2026, 1, 25, 14, 30, 45)
        result = format_datetime(test_datetime)
        assert isinstance(result, str)

    def test_parse_datetime(self):
        """测试日期时间解析"""
        from tradingagents.utils.time_utils import parse_datetime

        result = parse_datetime("2026-01-25")
        assert isinstance(result, datetime)
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 25


class TestTimerClass:
    """测试Timer类"""

    def test_timer_context_manager(self):
        """测试Timer上下文管理器"""
        from tradingagents.utils.time_utils import Timer

        with Timer() as timer:
            # 模拟一些操作
            _ = sum(range(100))

        assert timer.duration >= 0


class TestCacheTimeClass:
    """测试CacheTime类"""

    def test_cache_time_init(self):
        """测试CacheTime初始化"""
        from tradingagents.utils.time_utils import CacheTime

        cache = CacheTime()
        assert cache._cache_time is None

    def test_cache_time_update(self):
        """测试CacheTime更新"""
        from tradingagents.utils.time_utils import CacheTime

        cache = CacheTime()
        cache.update()

        # 刚更新，不应该过期
        assert cache._cache_time is not None
        assert not cache.is_expired(60)

    def test_cache_time_is_expired(self):
        """测试CacheTime过期判断"""
        from tradingagents.utils.time_utils import CacheTime

        cache = CacheTime()
        # 未更新的cache应该返回过期
        assert cache.is_expired(0)

    def test_cache_time_get_age_seconds(self):
        """测试CacheTime获取年龄"""
        from tradingagents.utils.time_utils import CacheTime

        cache = CacheTime()
        cache.update()

        age = cache.get_age_seconds()
        assert age >= 0


class TestTimeUtilsMock:
    """使用mock测试时间工具"""

    @patch("tradingagents.utils.time_utils.date")
    def test_get_current_date_mock(self, mock_date):
        """测试获取当前日期（使用mock）"""
        from tradingagents.utils.time_utils import get_current_date

        mock_date.today.return_value = date(2026, 1, 25)
        result = get_current_date()
        assert result == date(2026, 1, 25)

    @patch("tradingagents.utils.time_utils.datetime")
    def test_get_current_datetime_mock(self, mock_datetime):
        """测试获取当前日期时间（使用mock）"""
        from tradingagents.utils.time_utils import get_current_datetime

        mock_datetime.now.return_value = datetime(2026, 1, 25, 14, 30, 45)
        result = get_current_datetime()
        assert result == datetime(2026, 1, 25, 14, 30, 45)
