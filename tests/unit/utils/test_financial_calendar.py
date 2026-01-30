"""
财务日历单元测试

测试 FinancialCalendar 类的各项功能：
1. 财报发布日期计算
2. 距离下次财报发布天数
3. 财报敏感期判断
4. 缓存TTL自动调整
"""

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from tradingagents.utils.financial_calendar import (
    FinancialCalendar,
    get_cache_config,
    get_cache_ttl,
    get_cache_storage,
)


class TestFinancialCalendar:
    """财务日历测试类"""

    def test_get_next_report_deadline_q1(self):
        """测试获取一季报截止日"""
        # 2026年1月30日，应该在4月30日发布一季报
        current_date = datetime(2026, 1, 30, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        deadline, quarter = FinancialCalendar.get_next_report_deadline(current_date)

        assert quarter == "Q1"
        assert deadline.month == 4
        assert deadline.day == 30
        assert deadline.hour == 16  # 16:00发布

    def test_get_next_report_deadline_q2(self):
        """测试获取半年报截止日"""
        # 2026年5月1日，应该在8月31日发布半年报
        current_date = datetime(2026, 5, 1, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        deadline, quarter = FinancialCalendar.get_next_report_deadline(current_date)

        assert quarter == "Q2"
        assert deadline.month == 8
        assert deadline.day == 31

    def test_get_next_report_deadline_q3(self):
        """测试获取三季报截止日"""
        # 2026年9月1日，应该在10月31日发布三季报
        current_date = datetime(2026, 9, 1, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        deadline, quarter = FinancialCalendar.get_next_report_deadline(current_date)

        assert quarter == "Q3"
        assert deadline.month == 10
        assert deadline.day == 31

    def test_get_next_report_deadline_q4(self):
        """测试获取年报截止日"""
        # 2026年11月1日，应该在次年4月30日发布年报
        current_date = datetime(2026, 11, 1, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        deadline, quarter = FinancialCalendar.get_next_report_deadline(current_date)

        assert quarter == "Q4"
        assert deadline.year == 2027
        assert deadline.month == 4
        assert deadline.day == 30

    def test_get_days_to_next_report(self):
        """测试距离下次财报发布天数"""
        # 2026年1月30日，距离4月30日还有90天
        current_date = datetime(2026, 1, 30, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        days = FinancialCalendar.get_days_to_next_report(current_date)

        assert days == 90  # 4月30日 - 1月30日 = 90天

    def test_is_report_period_near_true(self):
        """测试财报敏感期判断（在敏感期内）"""
        # 2026年4月28日，距离4月30日还有2天，应该在敏感期内
        current_date = datetime(2026, 4, 28, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        is_near = FinancialCalendar.is_report_period_near(current_date, days=3)

        assert is_near is True

    def test_is_report_period_near_false(self):
        """测试财报敏感期判断（不在敏感期内）"""
        # 2026年1月30日，距离4月30日还有90天，不在敏感期内
        current_date = datetime(2026, 1, 30, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        is_near = FinancialCalendar.is_report_period_near(current_date, days=3)

        assert is_near is False

    def test_is_report_release_day_true(self):
        """测试财报发布日判断（是发布日且已过16:00）"""
        # 2026年4月30日 17:00，是发布日且已过16:00
        current_date = datetime(2026, 4, 30, 17, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        is_release_day = FinancialCalendar.is_report_release_day(current_date)

        assert is_release_day is True

    def test_is_report_release_day_false_before_time(self):
        """测试财报发布日判断（是发布日但未过16:00）"""
        # 2026年4月30日 12:00，是发布日但未过16:00
        current_date = datetime(2026, 4, 30, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        is_release_day = FinancialCalendar.is_report_release_day(current_date)

        assert is_release_day is False

    def test_should_use_short_ttl_near_report(self):
        """测试是否应该使用短TTL（在财报敏感期）"""
        # 2026年4月28日，距离发布日还有2天，应该使用短TTL
        current_date = datetime(2026, 4, 28, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        should_short = FinancialCalendar.should_use_short_ttl(current_date)

        assert should_short is True

    def test_should_use_short_ttl_normal(self):
        """测试是否应该使用短TTL（不在财报敏感期）"""
        # 2026年1月30日，距离发布日还有90天，不应该使用短TTL
        current_date = datetime(2026, 1, 30, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        should_short = FinancialCalendar.should_use_short_ttl(current_date)

        assert should_short is False

    def test_get_adjusted_ttl_short(self):
        """测试获取调整后TTL（短TTL）"""
        # 2026年4月28日，距离发布日还有2天，应该返回1小时
        current_date = datetime(2026, 4, 28, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        adjusted_ttl = FinancialCalendar.get_adjusted_ttl(
            "financial",
            604800,
            current_date,  # 基础TTL 7天
        )

        assert adjusted_ttl == 3600  # 1小时

    def test_get_adjusted_ttl_normal(self):
        """测试获取调整后TTL（正常TTL）"""
        # 2026年1月30日，距离发布日还有90天，应该返回基础TTL
        current_date = datetime(2026, 1, 30, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        base_ttl = 604800  # 7天
        adjusted_ttl = FinancialCalendar.get_adjusted_ttl(
            "financial", base_ttl, current_date
        )

        assert adjusted_ttl == base_ttl  # 不变

    def test_get_adjusted_ttl_non_sensitive_type(self):
        """测试获取调整后TTL（非敏感类型）"""
        # 即使是财报发布日，非敏感类型也不调整
        current_date = datetime(2026, 4, 30, 17, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        base_ttl = 3600  # 1小时
        adjusted_ttl = FinancialCalendar.get_adjusted_ttl(
            "valuation",
            base_ttl,
            current_date,  # 估值指标不受财报影响
        )

        assert adjusted_ttl == base_ttl  # 不变

    def test_get_report_info(self):
        """测试获取财报信息"""
        current_date = datetime(2026, 1, 30, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        info = FinancialCalendar.get_report_info(current_date)

        assert "current_date" in info
        assert "next_report_date" in info
        assert "next_report_quarter" in info
        assert "days_to_next_report" in info
        assert "is_sensitive_period" in info
        assert "is_report_release_day" in info
        assert "should_use_short_ttl" in info

        assert info["next_report_quarter"] == "Q1"
        assert info["days_to_next_report"] == 90


class TestCacheConfig:
    """缓存配置测试类"""

    def test_get_cache_config_valuation(self):
        """测试获取估值指标缓存配置"""
        config = get_cache_config("valuation")

        assert config["base_ttl"] == 3600  # 1小时
        assert config["storage"] == "redis"
        assert config["affected_by_report_date"] is False

    def test_get_cache_config_financial(self):
        """测试获取财报数据缓存配置"""
        config = get_cache_config("financial")

        assert config["base_ttl"] == 604800  # 7天
        assert config["storage"] == "mongodb"
        assert config["affected_by_report_date"] is True

    def test_get_cache_config_dividend(self):
        """测试获取分红数据缓存配置"""
        config = get_cache_config("dividend")

        assert config["base_ttl"] == 2592000  # 30天
        assert config["storage"] == "mongodb"
        assert config["affected_by_report_date"] is False

    def test_get_cache_config_default(self):
        """测试获取默认缓存配置"""
        config = get_cache_config("unknown")

        assert config["base_ttl"] == 86400  # 1天（默认）
        assert config["storage"] == "mongodb"

    def test_get_cache_ttl_normal(self):
        """测试获取正常缓存TTL"""
        current_date = datetime(2026, 1, 30, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        ttl = get_cache_ttl("financial", current_date)

        assert ttl == 604800  # 7天

    def test_get_cache_ttl_sensitive(self):
        """测试获取敏感期缓存TTL"""
        current_date = datetime(2026, 4, 28, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        ttl = get_cache_ttl("financial", current_date)

        assert ttl == 3600  # 1小时

    def test_get_cache_ttl_non_sensitive(self):
        """测试获取非敏感类型缓存TTL（不受日期影响）"""
        current_date = datetime(2026, 4, 28, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        ttl = get_cache_ttl("valuation", current_date)

        assert ttl == 3600  # 1小时（不变）

    def test_get_cache_storage_redis(self):
        """测试获取Redis存储位置"""
        storage = get_cache_storage("valuation")
        assert storage == "redis"

    def test_get_cache_storage_mongodb(self):
        """测试获取MongoDB存储位置"""
        storage = get_cache_storage("financial")
        assert storage == "mongodb"


class TestEdgeCases:
    """边界情况测试类"""

    def test_report_deadline_exact_time(self):
        """测试恰好是财报发布时间"""
        # 2026年4月30日 16:00，恰好是发布时间
        current_date = datetime(2026, 4, 30, 16, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        deadline, quarter = FinancialCalendar.get_next_report_deadline(current_date)

        # 当前时间 >= 发布时间，应该找下一个财报
        assert quarter == "Q2"
        assert deadline.month == 8

    def test_report_deadline_one_minute_before(self):
        """测试财报发布时间前1分钟"""
        # 2026年4月30日 15:59，发布前1分钟
        current_date = datetime(
            2026, 4, 30, 15, 59, 0, tzinfo=ZoneInfo("Asia/Shanghai")
        )
        deadline, quarter = FinancialCalendar.get_next_report_deadline(current_date)

        # 当前时间 < 发布时间，应该还是Q1
        assert quarter == "Q1"
        assert deadline.month == 4

    def test_year_boundary(self):
        """测试跨年边界"""
        # 2026年12月31日，年报应该是次年4月30日
        current_date = datetime(
            2026, 12, 31, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai")
        )
        deadline, quarter = FinancialCalendar.get_next_report_deadline(current_date)

        assert quarter == "Q4"
        assert deadline.year == 2027
        assert deadline.month == 4

    def test_sensitive_days_boundary(self):
        """测试敏感天数边界"""
        # 2026年4月27日，距离4月30日还有3天（恰好是边界）
        current_date = datetime(2026, 4, 27, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        is_near = FinancialCalendar.is_report_period_near(current_date, days=3)

        # 恰好是3天，应该在敏感期内
        assert is_near is True

    def test_sensitive_days_one_day_after(self):
        """测试敏感天数边界后1天"""
        # 2026年4月26日，距离4月30日还有4天（超出边界1天）
        current_date = datetime(2026, 4, 26, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        is_near = FinancialCalendar.is_report_period_near(current_date, days=3)

        # 超出3天，不在敏感期内
        assert is_near is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
