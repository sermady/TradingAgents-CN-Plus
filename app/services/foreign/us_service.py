# -*- coding: utf-8 -*-
"""美股数据服务 - 向后兼容入口

此文件已重构，所有功能已迁移到 app/services/foreign/us/ 目录下的模块：
- quote.py: QuoteMixin (实时行情获取)
- info.py: InfoMixin (基础信息获取)
- kline.py: KlineMixin (K线数据获取)
- news.py: NewsMixin (新闻获取)
- service.py: USStockService 主类

为了保持向后兼容，请从 app.services.foreign.us 导入：
    from app.services.foreign.us import USStockService
"""

# 从新的模块位置重新导出所有内容
from app.services.foreign.us import USStockService

__all__ = ["USStockService"]
