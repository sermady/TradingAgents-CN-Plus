# -*- coding: utf-8 -*-
"""
统一接口工具模块 - 提供股票分析的统一入口（模块化版本）

原始文件已重命名为 unified_tools.py.backup
所有功能已拆分到 tools/ 目录下的独立模块
"""

# 重新导出所有工具函数，保持向后兼容
from tradingagents.agents.utils.toolkit.tools.data_tools import (
    get_stock_comprehensive_financials,
    get_stock_fundamentals_unified,
)
from tradingagents.agents.utils.toolkit.tools.market_tools import (
    get_stock_market_data_unified,
)
from tradingagents.agents.utils.toolkit.tools.analysis_tools import (
    get_stock_news_unified,
    get_stock_sentiment_unified,
)

__all__ = [
    # 数据工具
    'get_stock_comprehensive_financials',
    'get_stock_fundamentals_unified',
    # 市场工具
    'get_stock_market_data_unified',
    # 分析工具
    'get_stock_news_unified',
    'get_stock_sentiment_unified',
]
