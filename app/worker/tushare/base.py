# -*- coding: utf-8 -*-
"""
Tushare同步服务基础类
提供通用的工具函数和辅助方法
"""

from datetime import datetime, timedelta
from typing import Dict, Any
import logging

from app.core.database import get_mongo_db
from app.core.config import settings
from app.core.rate_limiter import get_tushare_rate_limiter
from app.services.stock_data_service import get_stock_data_service
from app.services.base_sync_service import BaseSyncService
from app.utils.timezone import now_tz
from tradingagents.dataflows.providers.china.tushare import TushareProvider

logger = logging.getLogger(__name__)

# UTC+8 时区
UTC_8 = timedelta(hours=8)


def get_utc8_now():
    """
    获取 UTC+8 当前时间（naive datetime）

    注意：返回 naive datetime（不带时区信息），MongoDB 会按原样存储本地时间值
    这样前端可以直接添加 +08:00 后缀显示
    """
    return now_tz().replace(tzinfo=None)


class TushareSyncBase(BaseSyncService):
    """
    Tushare同步服务基础类
    提供通用方法和工具函数
    """

    @property
    def data_source(self) -> str:
        """数据源标识符"""
        return "tushare"

    def __init__(self):
        super().__init__()
        self.provider = TushareProvider()
        self.stock_service = get_stock_data_service()
        self.db = get_mongo_db()
        self.settings = settings

        # 同步配置
        self.batch_size = 100  # 批量处理大小
        self.rate_limit_delay = 0.1  # API调用间隔(秒) - 已弃用，使用rate_limiter
        self.max_retries = 3  # 最大重试次数

        # 速率限制器（从环境变量读取配置）
        tushare_tier = getattr(
            settings, "TUSHARE_TIER", "standard"
        )  # free/basic/standard/premium/vip
        safety_margin = float(
            getattr(settings, "TUSHARE_RATE_LIMIT_SAFETY_MARGIN", "0.8")
        )
        self.rate_limiter = get_tushare_rate_limiter(
            tier=tushare_tier, safety_margin=safety_margin
        )

    async def initialize(self):
        """初始化同步服务"""
        success = await self.provider.connect()
        if not success:
            raise RuntimeError("❌ Tushare连接失败，无法启动同步服务")

        # 初始化历史数据服务
        self.historical_service = await self.historical_data_service()

        # 初始化新闻数据服务
        self.news_service = await self.news_data_service()

        logger.info("✅ Tushare同步服务初始化完成")

    async def historical_data_service(self):
        """延迟初始化历史数据服务"""
        from app.services.historical_data_service import get_historical_data_service
        if self.historical_service is None:
            self.historical_service = await get_historical_data_service()
        return self.historical_service

    async def news_data_service(self):
        """延迟初始化新闻数据服务"""
        from app.services.news import get_news_data_service
        if self.news_service is None:
            self.news_service = await get_news_data_service()
        return self.news_service

    def is_rate_limit_error(self, error_msg: str) -> bool:
        """检测是否为 API 限流错误"""
        rate_limit_keywords = [
            "每分钟最多访问",
            "每分钟最多",
            "rate limit",
            "too many requests",
            "访问频率",
            "请求过于频繁",
        ]
        error_msg_lower = error_msg.lower()
        return any(keyword in error_msg_lower for keyword in rate_limit_keywords)

    def is_trading_time(self) -> bool:
        """
        判断当前是否在交易时间
        A股交易时间：
        - 周一到周五（排除节假日）
        - 上午：9:30-11:30
        - 下午：13:00-15:00

        注意：此方法不检查节假日，仅检查时间段
        """
        from datetime import datetime
        import pytz

        # 使用上海时区
        tz = pytz.timezone("Asia/Shanghai")
        now = datetime.now(tz)

        # 检查是否是周末
        from tradingagents.utils.trading_hours import is_weekend
        if is_weekend():
            return False

        # 检查时间段
        current_time = now.time()

        # 上午交易时间：9:30-11:30
        morning_start = datetime.strptime("09:30", "%H:%M").time()
        morning_end = datetime.strptime("11:30", "%H:%M").time()

        # 下午交易时间：13:00-15:00
        afternoon_start = datetime.strptime("13:00", "%H:%M").time()
        afternoon_end = datetime.strptime("15:00", "%H:%M").time()

        # 判断是否在交易时间段内
        is_morning = morning_start <= current_time <= morning_end
        is_afternoon = afternoon_start <= current_time <= afternoon_end

        return is_morning or is_afternoon

    async def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        try:
            # 统计各集合的数据量
            basic_info_count = await self.db.stock_basic_info.count_documents({})
            quotes_count = await self.db.market_quotes.count_documents({})

            # 获取最新更新时间
            latest_basic = await self.db.stock_basic_info.find_one(
                {}, sort=[("updated_at", -1)]
            )
            latest_quotes = await self.db.market_quotes.find_one(
                {}, sort=[("updated_at", -1)]
            )

            return {
                "provider_connected": self.provider.is_available(),
                "collections": {
                    "stock_basic_info": {
                        "count": basic_info_count,
                        "latest_update": latest_basic.get("updated_at")
                        if (latest_basic and isinstance(latest_basic, dict))
                        else None,
                    },
                    "market_quotes": {
                        "count": quotes_count,
                        "latest_update": latest_quotes.get("updated_at")
                        if (latest_quotes and isinstance(latest_quotes, dict))
                        else None,
                    },
                },
                "status_time": datetime.utcnow(),
            }

        except Exception as e:
            logger.error(f"❌ 获取同步状态失败: {e}")
            return {"error": str(e)}
