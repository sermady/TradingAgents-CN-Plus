"""
财务日历工具 - 财报发布日期管理和缓存策略优化

功能：
1. 管理财报发布截止日（一季报、半年报、三季报、年报）
2. 计算距离下次财报发布的天数
3. 根据财报发布日期动态调整缓存TTL
4. 判断当前是否处于财报发布敏感期

使用场景：
- 在财报发布前3天缩短缓存时间，确保及时获取新财报
- 在财报发布日（16:00后）强制刷新缓存
- 其他时间使用正常缓存策略
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from zoneinfo import ZoneInfo


class FinancialCalendar:
    """
    财务日历管理器

    管理A股财报发布时间表：
    - Q1 一季报：4月30日截止
    - Q2 半年报：8月31日截止
    - Q3 三季报：10月31日截止
    - Q4 年报：次年4月30日截止
    """

    # 财报发布截止日（月份, 日期）
    REPORT_DEADLINES = {
        "Q1": (4, 30),  # 一季报
        "Q2": (8, 31),  # 半年报
        "Q3": (10, 31),  # 三季报
        "Q4": (4, 30),  # 年报（次年）
    }

    # 默认时区：中国时区
    DEFAULT_TIMEZONE = "Asia/Shanghai"

    # 财报发布敏感天数（默认3天）
    DEFAULT_SENSITIVE_DAYS = 3

    # 财报发布时间（收盘后，16:00）
    REPORT_RELEASE_HOUR = 16

    @classmethod
    def get_current_date(cls, timezone: Optional[str] = None) -> datetime:
        """
        获取当前日期时间（指定时区）

        Args:
            timezone: 时区名称，默认为中国时区

        Returns:
            datetime: 当前日期时间
        """
        tz = ZoneInfo(timezone or cls.DEFAULT_TIMEZONE)
        return datetime.now(tz)

    @classmethod
    def get_next_report_deadline(
        cls, current_date: Optional[datetime] = None
    ) -> Tuple[datetime, str]:
        """
        获取下一次财报发布截止日

        Args:
            current_date: 当前日期，默认为今天

        Returns:
            Tuple[datetime, str]: (截止日日期, 季度名称)
        """
        if current_date is None:
            current_date = cls.get_current_date()

        # 确保使用aware datetime进行比较
        if current_date.tzinfo is None:
            current_date = current_date.replace(tzinfo=ZoneInfo(cls.DEFAULT_TIMEZONE))

        year = current_date.year

        # 定义本年度的财报截止日（使用aware datetime）
        tz = ZoneInfo(cls.DEFAULT_TIMEZONE)
        deadlines = [
            (
                datetime(year, 4, 30, cls.REPORT_RELEASE_HOUR, 0, 0, tzinfo=tz),
                "Q1",
            ),  # 一季报
            (
                datetime(year, 8, 31, cls.REPORT_RELEASE_HOUR, 0, 0, tzinfo=tz),
                "Q2",
            ),  # 半年报
            (
                datetime(year, 10, 31, cls.REPORT_RELEASE_HOUR, 0, 0, tzinfo=tz),
                "Q3",
            ),  # 三季报
            (
                datetime(year + 1, 4, 30, cls.REPORT_RELEASE_HOUR, 0, 0, tzinfo=tz),
                "Q4",
            ),  # 年报（次年）
        ]

        # 找到下一个未到期的财报截止日
        for deadline, quarter in deadlines:
            if current_date < deadline:
                return deadline, quarter

        # 如果本年度所有财报都已发布，返回下一年的一季报
        return datetime(year + 1, 4, 30, cls.REPORT_RELEASE_HOUR, 0, 0, tzinfo=tz), "Q1"

    @classmethod
    def get_days_to_next_report(cls, current_date: Optional[datetime] = None) -> int:
        """
        计算距离下次财报发布还有多少天

        Args:
            current_date: 当前日期，默认为今天

        Returns:
            int: 距离下次财报发布的天数（0表示今天发布）
        """
        if current_date is None:
            current_date = cls.get_current_date()

        next_deadline, _ = cls.get_next_report_deadline(current_date)

        # 计算天数差（不考虑时间，只看日期）
        # 使用相同的时区信息进行计算
        if current_date.tzinfo is None:
            current_date = current_date.replace(tzinfo=ZoneInfo(cls.DEFAULT_TIMEZONE))

        current_date_only = current_date.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        deadline_date_only = next_deadline.replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        delta = deadline_date_only - current_date_only
        return max(0, delta.days)

    @classmethod
    def is_report_period_near(
        cls, current_date: Optional[datetime] = None, days: int = DEFAULT_SENSITIVE_DAYS
    ) -> bool:
        """
        判断当前是否处于财报发布敏感期

        Args:
            current_date: 当前日期，默认为今天
            days: 敏感天数（默认3天）

        Returns:
            bool: 是否在财报发布前N天内
        """
        days_to_report = cls.get_days_to_next_report(current_date)
        return 0 <= days_to_report <= days

    @classmethod
    def is_report_release_day(
        cls, current_date: Optional[datetime] = None, after_market_close: bool = True
    ) -> bool:
        """
        判断今天是否是财报发布日

        Args:
            current_date: 当前日期，默认为今天
            after_market_close: 是否只在收盘后（16:00）返回True

        Returns:
            bool: 今天是否是财报发布日
        """
        if current_date is None:
            current_date = cls.get_current_date()

        days_to_report = cls.get_days_to_next_report(current_date)

        # 如果不是发布日，返回False
        if days_to_report != 0:
            return False

        # 如果需要检查是否在收盘后
        if after_market_close:
            return current_date.hour >= cls.REPORT_RELEASE_HOUR

        return True

    @classmethod
    def should_use_short_ttl(
        cls,
        current_date: Optional[datetime] = None,
        sensitive_days: int = DEFAULT_SENSITIVE_DAYS,
    ) -> bool:
        """
        判断是否应该使用短缓存TTL

        在以下情况使用短TTL（1小时）：
        1. 财报发布前N天内
        2. 财报发布日当天（16:00后）

        Args:
            current_date: 当前日期，默认为今天
            sensitive_days: 敏感天数

        Returns:
            bool: 是否应该使用短TTL
        """
        if current_date is None:
            current_date = cls.get_current_date()

        # 检查是否在财报发布前N天内
        if cls.is_report_period_near(current_date, sensitive_days):
            return True

        # 检查是否是财报发布日（且已过16:00）
        if cls.is_report_release_day(current_date, after_market_close=True):
            return True

        return False

    @classmethod
    def get_adjusted_ttl(
        cls,
        data_category: str,
        base_ttl: int,
        current_date: Optional[datetime] = None,
        sensitive_days: int = DEFAULT_SENSITIVE_DAYS,
    ) -> int:
        """
        根据财报发布日期调整缓存TTL

        Args:
            data_category: 数据类别（valuation/financial/dividend）
            base_ttl: 基础TTL（秒）
            current_date: 当前日期，默认为今天
            sensitive_days: 敏感天数

        Returns:
            int: 调整后的TTL（秒）
        """
        if current_date is None:
            current_date = cls.get_current_date()

        # 只有财务数据受财报发布日期影响
        if data_category not in ["financial", "fundamental"]:
            return base_ttl

        # 检查是否应该使用短TTL
        if cls.should_use_short_ttl(current_date, sensitive_days):
            return 3600  # 1小时

        return base_ttl

    @classmethod
    def get_report_info(cls, current_date: Optional[datetime] = None) -> dict:
        """
        获取当前财报信息

        Args:
            current_date: 当前日期，默认为今天

        Returns:
            dict: 包含财报信息的字典
        """
        if current_date is None:
            current_date = cls.get_current_date()

        next_deadline, quarter = cls.get_next_report_deadline(current_date)
        days_to_report = cls.get_days_to_next_report(current_date)

        return {
            "current_date": current_date.strftime("%Y-%m-%d %H:%M:%S"),
            "next_report_date": next_deadline.strftime("%Y-%m-%d"),
            "next_report_quarter": quarter,
            "days_to_next_report": days_to_report,
            "is_sensitive_period": cls.is_report_period_near(current_date),
            "is_report_release_day": cls.is_report_release_day(current_date),
            "should_use_short_ttl": cls.should_use_short_ttl(current_date),
        }


# 预定义的缓存TTL配置（根据数据类型分级）
CACHE_TTL_CONFIG = {
    # ===== L1: 实时估值指标（1小时）=====
    "valuation": {
        "base_ttl": 3600,  # 1小时
        "storage": "redis",
        "description": "估值指标（PE、PB、PS、总市值）",
    },
    "daily_basic": {
        "base_ttl": 3600,  # 1小时
        "storage": "redis",
        "description": "每日指标",
    },
    "realtime_quote": {
        "base_ttl": 300,  # 5分钟
        "storage": "redis",
        "description": "实时行情",
    },
    # ===== L2: 季度财报数据（7天，财报日调整为1小时）=====
    "financial": {
        "base_ttl": 604800,  # 7天
        "storage": "mongodb",
        "description": "财报数据（营收、利润、ROE等）",
        "affected_by_report_date": True,
        "sensitive_ttl": 3600,  # 财报敏感期使用1小时
    },
    "financial_indicators": {
        "base_ttl": 604800,  # 7天
        "storage": "mongodb",
        "description": "财务指标（ROE、EPS等）",
        "affected_by_report_date": True,
        "sensitive_ttl": 3600,
    },
    "income_statement": {
        "base_ttl": 604800,  # 7天
        "storage": "mongodb",
        "description": "利润表",
        "affected_by_report_date": True,
        "sensitive_ttl": 3600,
    },
    "balance_sheet": {
        "base_ttl": 604800,  # 7天
        "storage": "mongodb",
        "description": "资产负债表",
        "affected_by_report_date": True,
        "sensitive_ttl": 3600,
    },
    "cashflow_statement": {
        "base_ttl": 604800,  # 7天
        "storage": "mongodb",
        "description": "现金流量表",
        "affected_by_report_date": True,
        "sensitive_ttl": 3600,
    },
    "fundamental": {
        "base_ttl": 604800,  # 7天（默认）
        "storage": "mongodb",
        "description": "基本面数据",
        "affected_by_report_date": True,
        "sensitive_ttl": 3600,
    },
    # ===== L3: 长期基本面（30天）=====
    "dividend": {
        "base_ttl": 2592000,  # 30天
        "storage": "mongodb",
        "description": "分红数据",
        "affected_by_report_date": False,
    },
    "company_info": {
        "base_ttl": 2592000,  # 30天
        "storage": "mongodb",
        "description": "公司基本信息",
        "affected_by_report_date": False,
    },
    "stock_basic": {
        "base_ttl": 2592000,  # 30天
        "storage": "mongodb",
        "description": "股票基础信息",
        "affected_by_report_date": False,
    },
}


def get_cache_config(data_category: str) -> dict:
    """
    获取指定数据类别的缓存配置

    Args:
        data_category: 数据类别

    Returns:
        dict: 缓存配置
    """
    return CACHE_TTL_CONFIG.get(
        data_category,
        {
            "base_ttl": 86400,  # 默认1天
            "storage": "mongodb",
            "description": "通用数据",
            "affected_by_report_date": False,
        },
    )


def get_cache_ttl(data_category: str, current_date: Optional[datetime] = None) -> int:
    """
    获取指定数据类别的缓存TTL（自动考虑财报发布日期）

    Args:
        data_category: 数据类别
        current_date: 当前日期，默认为今天

    Returns:
        int: 缓存TTL（秒）
    """
    config = get_cache_config(data_category)
    base_ttl = config["base_ttl"]

    # 如果受财报发布日期影响，进行调整
    if config.get("affected_by_report_date", False):
        return FinancialCalendar.get_adjusted_ttl(data_category, base_ttl, current_date)

    return base_ttl


def get_cache_storage(data_category: str) -> str:
    """
    获取指定数据类别的存储位置

    Args:
        data_category: 数据类别

    Returns:
        str: 存储位置（redis/mongodb）
    """
    config = get_cache_config(data_category)
    return config.get("storage", "mongodb")


# 向后兼容：保留原有的常量定义
FINANCIAL_REPORT_DEADLINES = FinancialCalendar.REPORT_DEADLINES
DEFAULT_SENSITIVE_DAYS = FinancialCalendar.DEFAULT_SENSITIVE_DAYS
REPORT_RELEASE_HOUR = FinancialCalendar.REPORT_RELEASE_HOUR
