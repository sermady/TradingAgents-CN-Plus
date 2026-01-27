# -*- coding: utf-8 -*-
"""
验证 Tushare 数据源 PEG 计算功能
"""
import sys
import os
import asyncio
import logging

# 添加项目根目录到 Python 路径
sys.path.append(os.getcwd())

import tradingagents
print(f"DEBUG: tradingagents location: {os.path.dirname(tradingagents.__file__)}")

from tradingagents.dataflows.providers.china.tushare import TushareProvider

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def validate_peg():
    """验证 PEG 字段是否存在且有效"""
    logger.info("开始验证 Tushare PEG 计算...")

    try:
        # 1. 初始化 TushareProvider
        provider = TushareProvider()
        logger.info(f"数据源初始化成功: {provider.provider_name}")

        # 检查是否已连接
        if not provider.is_available():
            logger.error("❌ Tushare 数据源不可用，请检查 Token 配置")
            return

        stock_code = "600519.SH" # 贵州茅台
        logger.info(f"正在获取 {stock_code} 的基础数据...")

        # 2. 获取股票基础数据
        if asyncio.iscoroutinefunction(provider.get_stock_basic_info):
            data = await provider.get_stock_basic_info(stock_code)
        else:
            data = provider.get_stock_basic_info(stock_code)

        if not data:
            logger.error(f"❌ 未能获取到 {stock_code} 的数据")
            return

        logger.info("数据获取成功")

        # 3. 检查 PEG 字段
        if hasattr(data, "model_dump"):
            data_dict = data.model_dump()
        elif hasattr(data, "dict"):
            data_dict = data.dict()
        else:
            data_dict = dict(data)

        peg = data_dict.get('peg')

        # 打印关键指标
        logger.info("-" * 40)
        logger.info(f"股票代码: {data_dict.get('code')}")
        logger.info(f"股票名称: {data_dict.get('name')}")
        logger.info(f"市盈率(PE): {data_dict.get('pe')}")
        logger.info(f"市盈率TTM(PE_TTM): {data_dict.get('pe_ttm')}")
        # 注意：q_profit_yoy 是原始数据字段，可能不在标准化后的输出中，除非我们特意加了
        # 但 PEG 是基于它计算的
        logger.info(f"PEG: {peg}")
        logger.info("-" * 40)

        # 4. 验证结果
        if peg is not None:
            logger.info(f"✅ PEG 验证通过: {peg}")
        else:
            logger.warning("⚠️ PEG 字段为 None")

    except Exception as e:
        logger.error(f"❌ 验证过程中发生错误: {str(e)}", exc_info=True)

if __name__ == "__main__":
    # Windows 环境下设置 event loop policy
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(validate_peg())
