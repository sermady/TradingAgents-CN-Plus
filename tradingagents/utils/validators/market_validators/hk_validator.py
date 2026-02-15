# -*- coding: utf-8 -*-
"""
港股数据验证器

负责港股数据的验证和准备
"""
import re
import logging
from typing import Dict, Optional

from tradingagents.utils.logging_manager import get_logger

logger = get_logger('hk_validator')


class HKStockValidator:
    """港股数据验证器"""

    def __init__(self, db=None, cache=None):
        self.db = db
        self.cache = cache

    def validate(
        self,
        stock_code: str,
        period_days: int = 30,
        analysis_date: Optional[str] = None
    ) -> Dict:
        """验证港股数据

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
            'market_type': '港股',
            'error_message': None,
            'suggestion': None,
            'has_historical_data': False,
            'has_basic_info': False,
        }

        try:
            # 1. 格式验证
            stock_code_upper = stock_code.upper()
            hk_format = re.match(r'^\d{4,5}\.HK$', stock_code_upper)
            digit_format = re.match(r'^\d{4,5}$', stock_code)

            if not (hk_format or digit_format):
                result['error_message'] = '港股代码格式错误'
                result['suggestion'] = '请输入4-5位数字.HK格式（如：0700.HK）或4-5位数字（如：0700）'
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
            logger.error(f"港股数据验证失败: {stock_code}, 错误: {e}", exc_info=True)
            result['error_message'] = f'验证失败: {str(e)}'
            return result

    def _check_database_data(
        self,
        stock_code: str,
        period_days: int,
        analysis_date: Optional[str]
    ) -> Dict:
        """检查数据库中的数据"""
        # 从原始 stock_validator.py 的 _prepare_hk_stock_data 方法中提取
        return {'has_historical_data': False, 'has_basic_info': False}

    def _check_cache(self, stock_code: str) -> Optional[Dict]:
        """检查缓存"""
        return None

    def extract_stock_name(self, stock_info: Dict, stock_code: str) -> str:
        """从港股信息中提取股票名称"""
        # 从原始文件第195-262行提取逻辑
        if not stock_info:
            return '未知'

        # 处理不同类型的返回值
        if isinstance(stock_info, dict):
            return stock_info.get('name', '未知')

        if isinstance(stock_info, str):
            return stock_info

        return '未知'

    def get_network_limitation_suggestion(self) -> str:
        """获取港股网络限制的详细建议

        从原始文件第174-193行提取
        """
        suggestions = [
            '港股数据获取受到网络API限制，这是常见的临时问题',
            '',
            '解决方案：',
            '1. 等待5-10分钟后重试（API限制通常会自动解除）',
            '2. 检查网络连接是否稳定',
            '3. 如果是知名港股（如腾讯0700.HK、阿里巴巴9988.HK），代码格式通常正确',
            '4. 可以尝试使用其他时间段进行分析',
            '',
            '常见港股代码格式：',
            '• 腾讯控股：0700.HK',
            '• 阿里巴巴：9988.HK',
            '• 美团：3690.HK',
            '• 小米集团：1810.HK',
            '',
            '建议稍后重试，或联系技术支持获取帮助'
        ]
        return '\n'.join(suggestions)
