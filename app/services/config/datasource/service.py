# -*- coding: utf-8 -*-
"""
数据源配置服务

提供数据源配置管理和测试功能
"""

import logging
import time
from typing import Dict, Any

from app.models.config import DataSourceConfig
from app.services.crud import BaseCRUDService
from ..base_config_service import BaseConfigService
from .testers import DataSourceTesterMixin

logger = logging.getLogger(__name__)


class DataSourceConfigService(
    BaseConfigService, BaseCRUDService, DataSourceTesterMixin
):
    """数据源配置服务"""

    def __init__(self, db_manager=None):
        BaseConfigService.__init__(self, db_manager)
        BaseCRUDService.__init__(self)

    @property
    def collection_name(self) -> str:
        """MongoDB 集合名称"""
        return "data_source_configs"

    async def test_data_source_config(
        self, ds_config: DataSourceConfig
    ) -> Dict[str, Any]:
        """测试数据源配置 - 真实调用API进行验证"""
        start_time = time.time()
        try:
            ds_type = (
                ds_config.type.value
                if hasattr(ds_config.type, "value")
                else str(ds_config.type)
            )

            logger.info(
                f"🧪 [TEST] Testing data source config: {ds_config.name} ({ds_type})"
            )

            # 优先使用配置中的 API Key，如果没有或被截断，则从数据库获取
            api_key = ds_config.api_key

            logger.info(
                f"🔍 [TEST] Received API Key from config: {repr(api_key)} (type: {type(api_key).__name__}, length: {len(api_key) if api_key else 0})"
            )

            # 根据不同的数据源类型进行测试
            if ds_type == "tushare":
                return await self._test_tushare(ds_config, api_key, start_time)
            elif ds_type == "akshare":
                return await self._test_akshare(ds_config, start_time)
            elif ds_type == "baostock":
                return await self._test_baostock(ds_config, start_time)
            elif ds_type == "yahoo_finance":
                return await self._test_yahoo_finance(ds_config, start_time)
            elif ds_type == "alpha_vantage":
                return await self._test_alpha_vantage(ds_config, api_key, start_time)
            else:
                return await self._test_generic_data_source(
                    ds_config, ds_type, api_key, start_time
                )

        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"❌ 测试数据源配置失败: {e}")
            return {
                "success": False,
                "message": f"连接失败: {str(e)}",
                "response_time": response_time,
                "details": None,
            }
