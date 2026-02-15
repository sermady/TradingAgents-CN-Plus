# -*- coding: utf-8 -*-
"""
基础接口定义

包含共享的常量、类型定义和工具函数
"""

from typing import Annotated, Dict
import os
from datetime import datetime

# 导入日志模块
try:
    from tradingagents.utils.logging_manager import get_logger

    logger = get_logger("agents")
except ImportError:
    import logging

    logger = logging.getLogger("agents")


# 导入配置管理器
# 初始化默认函数
def _default_get_config():
    return {}


def _default_set_config(config):
    pass


get_config = _default_get_config
set_config = _default_set_config
DATA_DIR = "./data"

try:
    from tradingagents.config.config_manager import config_manager

    DATA_DIR = config_manager.get_data_dir()

    def _get_config_impl():
        """获取配置（兼容性包装）"""
        return config_manager.load_settings()

    def _set_config_impl(config):
        """设置配置（兼容性包装）"""
        config_manager.save_settings(config)

    get_config = _get_config_impl
    set_config = _set_config_impl
except ImportError:
    pass


# 数据源可用性标志
YFIN_AVAILABLE = False
STOCKSTATS_AVAILABLE = False
StockstatsUtils = None
YF_AVAILABLE = False
yf = None
HK_STOCK_AVAILABLE = False
AKSHARE_HK_AVAILABLE = False

# 尝试导入yfinance相关模块
try:
    from ..providers.us.yfinance import *

    YFIN_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ yfinance工具不可用")

try:
    from ..technical.stockstats import *

    STOCKSTATS_AVAILABLE = True
    from ..technical.stockstats import StockstatsUtils
except ImportError:
    logger.warning("⚠️ stockstats工具不可用")
    StockstatsUtils = None

try:
    import yfinance as yf

    YF_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ yfinance库不可用")
    yf = None

# 导入港股工具
try:
    from ..providers.hk.hk_stock import get_hk_stock_data, get_hk_stock_info

    HK_STOCK_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ 港股工具不可用: {e}")
    HK_STOCK_AVAILABLE = False

# 导入AKShare港股工具
try:
    from ..providers.hk.improved_hk import (
        get_hk_stock_data_akshare,
        get_hk_stock_info_akshare,
    )

    AKSHARE_HK_AVAILABLE = True
except (ImportError, AttributeError) as e:
    logger.warning(f"⚠️ AKShare港股工具不可用: {e}")
    AKSHARE_HK_AVAILABLE = False

    def get_hk_stock_data_akshare(*args, **kwargs):
        return None

    def get_hk_stock_info_akshare(*args, **kwargs):
        return None
