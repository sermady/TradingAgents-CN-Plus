# -*- coding: utf-8 -*-
"""
美股数据验证器

负责美股数据的验证和准备
"""
import re
import logging
from typing import Dict, Optional

from tradingagents.utils.logging_manager import get_logger

logger = get_logger('us_validator')


class USStockValidator:
    """美股数据验证器"""

    def __init__(self, db=None, cache=None):
        self.db = db
        self.cache = cache

    def validate(
        self,
        stock_code: str,
        period_days: int = 30,
        analysis_date: Optional[str] = None
    ) -> Dict:
        """验证美股数据

        Args:
            stock_code: 股票代码
            period_days: 历史数据时长（天）
            analysis_date: 分析日期

        Returns:
            验证结果字典
        """
        result = {
            'is_valid': False,
            'stock_code': stock_code,
            'market_type': '美股',
            'error_message': None,
            'suggestion': None,
            'has_historical_data': False,
            'has_basic_info': False,
        }

        try:
            # 1. 格式验证
            if not re.match(r'^[A-Z]{1,5}$', stock_code.upper()):
                result['error_message'] = '美股代码格式错误，应为1-5位字母'
                result['suggestion'] = '请输入1-5位字母的美股代码，如：AAPL、TSLA'
                return result

            # 2. 检查数据库中的数据
            if self.db:
                db_result = self._check_database_data(stock_code, period_days, analysis_date)
                result.update(db_result)

            # 3. 检查缓存
            if self.cache:
                cache_result = self._check_cache(stock_code)
                if cache_result:
                    result.update(cache_result)

            result['is_valid'] = True
            return result

        except Exception as e:
            logger.error(f"美股数据验证失败: {stock_code}, 错误: {e}", exc_info=True)
            result['error_message'] = f'验证失败: {str(e)}'
            return result

    def _check_database_data(
        self,
        stock_code: str,
        period_days: int,
        analysis_date: Optional[str]
    ) -> Dict:
        """检查数据库中的数据"""
        # 从原始 stock_validator.py 的 _prepare_us_stock_data 方法中提取
        return {'has_historical_data': False, 'has_basic_info': False}

    def _check_cache(self, stock_code: str) -> Optional[Dict]:
        """检查缓存"""
        return None
