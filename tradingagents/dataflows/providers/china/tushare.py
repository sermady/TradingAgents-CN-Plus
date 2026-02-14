# -*- coding: utf-8 -*-
"""
统一的Tushare数据提供器

该文件为了向后兼容，从子模块导入所有功能。
实际实现已拆分到 tushare/ 目录下的各个子模块。

拆分后的模块结构：
- tushare/__init__.py: 模块入口，组合完整类
- tushare/cache_manager.py: 批量行情缓存管理
- tushare/base_provider.py: TushareProvider 基类（Token管理、连接）
- tushare/basic_data.py: 股票基础信息
- tushare/historical_data.py: 历史行情数据
- tushare/realtime_data.py: 实时行情数据
- tushare/financial_data.py: 财务数据
- tushare/news_data.py: 新闻数据
"""

# 导入tushare库状态
try:
    import tushare as ts

    TUSHARE_AVAILABLE = True
except ImportError:
    TUSHARE_AVAILABLE = False
    ts = None

# 从子模块导入所有公共接口
from .tushare.cache_manager import (
    BATCH_QUOTES_CACHE,
    BATCH_CACHE_TTL_SECONDS,
    _get_batch_cache_lock,
    _is_batch_cache_valid,
    _get_cached_batch_quotes,
    _set_cached_batch_quotes,
    _invalidate_batch_cache,
)

from .tushare.base_provider import BaseTushareProvider

from .tushare.basic_data import BasicDataMixin
from .tushare.historical_data import HistoricalDataMixin
from .tushare.realtime_data import RealtimeDataMixin
from .tushare.financial_data import FinancialDataMixin
from .tushare.news_data import NewsDataMixin


# 组合完整的 TushareProvider 类
class TushareProvider(
    BasicDataMixin,
    HistoricalDataMixin,
    RealtimeDataMixin,
    FinancialDataMixin,
    NewsDataMixin,
    BaseTushareProvider,
):
    """
    统一的Tushare数据提供器
    合并app层和tradingagents层的所有优势功能
    """

    def __init__(self):
        # 调用 MRO 中的第一个父类的 __init__
        super().__init__()


# 全局提供器实例（向后兼容）
_tushare_provider = None
_tushare_provider_initialized = False


def get_tushare_provider() -> "TushareProvider":
    """获取全局Tushare提供器实例"""
    global _tushare_provider, _tushare_provider_initialized
    if _tushare_provider is None:
        _tushare_provider = TushareProvider()
        # 使用同步连接方法，避免异步上下文问题
        if not _tushare_provider_initialized:
            try:
                # 直接使用同步连接方法
                _tushare_provider.connect_sync()
                _tushare_provider_initialized = True
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(f"⚠️ Tushare自动连接失败: {e}")
    return _tushare_provider


def get_realtime_quote(symbol: str) -> dict | None:
    """
    获取单只股票的实时行情（同步版本，供 data_source_manager 调用）

    使用 Tushare 的 daily 接口获取最新日线数据，
    因为 rt_k 接口是批量接口，单只股票调用浪费配额。

    Args:
        symbol: 股票代码（6位数字，如 '000001'）

    Returns:
        dict: 标准化的实时行情数据
        None: 获取失败时返回
    """
    from datetime import datetime, timedelta
    import logging

    logger = logging.getLogger(__name__)

    try:
        provider = get_tushare_provider()
        if not provider.is_available():
            logger.warning("⚠️ Tushare 提供器不可用，无法获取实时行情")
            return None

        # 标准化股票代码为 Tushare 格式
        ts_code = provider._normalize_ts_code(symbol)

        # 获取最近3天的日线数据（考虑周末和节假日）
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=5)).strftime("%Y%m%d")

        df = provider.api.daily(
            ts_code=ts_code, start_date=start_date, end_date=end_date
        )

        if df is None or df.empty:
            logger.warning(f"⚠️ Tushare daily 接口返回空数据: {symbol}")
            return None

        # 取最新一天的数据
        row = df.iloc[0]

        # 安全获取数值
        def safe_float(val, default=0.0):
            try:
                if val is None or (isinstance(val, float) and val != val):  # NaN check
                    return default
                return float(val)
            except (ValueError, TypeError):
                return default

        # 标准化输出格式
        result = {
            "symbol": symbol,
            "name": "",  # daily 接口不包含名称
            "price": safe_float(row.get("close")),
            "change": safe_float(row.get("change")),
            "change_pct": safe_float(row.get("pct_chg")),
            "open": safe_float(row.get("open")),
            "high": safe_float(row.get("high")),
            "low": safe_float(row.get("low")),
            "pre_close": safe_float(row.get("pre_close")),
            # Tushare daily 返回的成交量单位是手，直接使用原始单位
            "volume": safe_float(row.get("vol")),
            "volume_unit": "lots",  # 明确标注单位为手
            # Tushare daily 返回的成交额单位是千元，转换为元
            "amount": safe_float(row.get("amount")) * 1000,
            "trade_date": str(row.get("trade_date", "")),
            "timestamp": datetime.now().isoformat(),
            "source": "tushare_daily",
        }

        logger.debug(f"✅ Tushare 获取实时行情成功: {symbol} 价格={result['price']}")
        return result

    except Exception as e:
        logger.error(f"❌ Tushare 获取实时行情失败 {symbol}: {e}")
        return None


# 导出公共接口
__all__ = [
    # 主类
    "TushareProvider",
    "BaseTushareProvider",
    # Mixin类
    "BasicDataMixin",
    "HistoricalDataMixin",
    "RealtimeDataMixin",
    "FinancialDataMixin",
    "NewsDataMixin",
    # 缓存管理
    "BATCH_QUOTES_CACHE",
    "BATCH_CACHE_TTL_SECONDS",
    "_get_batch_cache_lock",
    "_is_batch_cache_valid",
    "_get_cached_batch_quotes",
    "_set_cached_batch_quotes",
    "_invalidate_batch_cache",
    # 全局实例函数
    "get_tushare_provider",
    "get_realtime_quote",
    # 库状态
    "TUSHARE_AVAILABLE",
    "ts",
]
