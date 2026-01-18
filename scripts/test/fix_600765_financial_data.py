# -*- coding: utf-8 -*-
"""
自动修复600765财务数据问题
1. 测试Tushare连接
2. 更新数据库配置
3. 重新同步财务数据
4. 验证结果
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging

# 配置日志（ASCII编码避免Windows乱码）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

async def step1_test_tushare_connection():
    """步骤1: 测试Tushare连接"""
    logger.info("="*80)
    logger.info("Step 1: Testing Tushare Connection")
    logger.info("="*80)
    
    try:
        import tushare as ts
        import os
        
        token = os.getenv('TUSHARE_TOKEN')
        if not token or token.startswith('your_'):
            logger.error("FAIL: TUSHARE_TOKEN not configured or invalid")
            return False
        
        logger.info(f"OK: TUSHARE_TOKEN found (length: {len(token)})")
        
        # 设置token并测试连接
        ts.set_token(token)
        pro = ts.pro_api()
        
        # 测试API调用
        test_data = pro.stock_basic(list_status="L", limit=1)
        
        if test_data is not None and not test_data.empty:
            logger.info(f"OK: Tushare API connection successful")
            logger.info(f"    Test data: {len(test_data)} records")
            return True
        else:
            logger.error("FAIL: Tushare API returned empty data")
            return False
            
    except Exception as e:
        logger.error(f"FAIL: Tushare connection failed: {e}")
        return False

async def step2_enable_tushare_in_db(db):
    """步骤2: 启用Tushare数据源"""
    logger.info("")
    logger.info("="*80)
    logger.info("Step 2: Enable Tushare in Database Configuration")
    logger.info("="*80)
    
    try:
        # 获取当前配置
        config_collection = db.system_configs
        config = await config_collection.find_one({"is_active": True})
        
        if not config:
            logger.error("FAIL: No active config found")
            return False
        
        logger.info(f"OK: Found active config (version: {config.get('version')})")
        
        # 检查数据源配置
        data_source_configs = config.get('data_source_configs', [])
        logger.info(f"    Current data sources: {len(data_source_configs)}")
        
        # 更新Tushare配置为启用状态
        updated = False
        for ds in data_source_configs:
            if ds.get('type') == 'tushare':
                if not ds.get('enabled'):
                    ds['enabled'] = True
                    updated = True
                    logger.info("    -> Enabling Tushare data source")
                else:
                    logger.info("    -> Tushare already enabled")
                
                # 设置高优先级
                if ds.get('priority') != 2:
                    ds['priority'] = 2
                    updated = True
                    logger.info(f"    -> Setting Tushare priority to 2")
                break
        
        # 如果没有Tushare配置，添加它
        tushare_exists = any(ds.get('type') == 'tushare' for ds in data_source_configs)
        if not tushare_exists:
            import os
            token = os.getenv('TUSHARE_TOKEN', '')
            
            new_tushare_config = {
                'type': 'tushare',
                'enabled': True,
                'priority': 2,
                'api_key': token,
                'market_categories': ['a_shares'],
                'name': 'Tushare'
            }
            data_source_configs.append(new_tushare_config)
            updated = True
            logger.info("    -> Adding new Tushare data source configuration")
        
        if updated:
            # 更新配置
            result = await config_collection.update_one(
                {"_id": config['_id']},
                {"$set": {
                    "data_source_configs": data_source_configs,
                    "updated_at": datetime.utcnow()
                }}
            )
            logger.info("OK: Database configuration updated successfully")
            return True
        else:
            logger.info("OK: No updates needed")
            return True
            
    except Exception as e:
        logger.error(f"FAIL: Failed to update database config: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def step3_sync_financial_data(db, code="600765"):
    """步骤3: 同步财务数据"""
    logger.info("")
    logger.info("="*80)
    logger.info(f"Step 3: Sync Financial Data for {code}")
    logger.info("="*80)
    
    try:
        from tradingagents.dataflows.providers.china.tushare import TushareProvider
        
        # 初始化Tushare Provider
        provider = TushareProvider()
        
        # 测试连接
        if not await provider.connect():
            logger.error("FAIL: Failed to connect to Tushare")
            return False
        
        logger.info("OK: Tushare provider connected")
        
        # 获取财务数据
        financial_data = await provider.get_financial_data(code)
        
        if financial_data:
            logger.info("OK: Financial data retrieved from Tushare")
            
            # 检查数据完整性
            key_fields = ['pe', 'pb', 'roe', 'net_profit', 'revenue']
            missing_fields = []
            present_fields = []
            
            for field in key_fields:
                if field in financial_data and financial_data[field] is not None:
                    present_fields.append(field)
                else:
                    missing_fields.append(field)
            
            logger.info(f"    Present fields: {', '.join(present_fields)}")
            if missing_fields:
                logger.warning(f"    Missing fields: {', '.join(missing_fields)}")
            
            # 保存到数据库
            await db.stock_financial_data.update_one(
                {"code": code},
                {"$set": financial_data},
                upsert=True
            )
            logger.info("OK: Financial data saved to database")
            return True
        else:
            logger.error("FAIL: No financial data returned from Tushare")
            return False
            
    except Exception as e:
        logger.error(f"FAIL: Failed to sync financial data: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def step4_verify_data(db, code="600765"):
    """步骤4: 验证数据"""
    logger.info("")
    logger.info("="*80)
    logger.info(f"Step 4: Verify Financial Data for {code}")
    logger.info("="*80)
    
    try:
        # 查询数据
        doc = await db.stock_financial_data.find_one({"code": code})
        
        if not doc:
            logger.error(f"FAIL: No financial data found for {code}")
            return False
        
        logger.info("OK: Financial data found in database")
        
        # 检查关键字段
        key_fields = ['pe', 'pb', 'roe', 'net_profit', 'revenue', 'total_assets']
        all_present = True
        
        for field in key_fields:
            value = doc.get(field)
            if value is not None and str(value) != 'nan':
                logger.info(f"    {field}: {value}")
            else:
                logger.warning(f"    {field}: MISSING")
                all_present = False
        
        if all_present:
            logger.info("OK: All key financial fields are present!")
            return True
        else:
            logger.warning("WARNING: Some financial fields are missing")
            return False
            
    except Exception as e:
        logger.error(f"FAIL: Failed to verify data: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def main():
    """主函数"""
    logger.info("Starting Automated 600765 Financial Data Fix")
    logger.info("="*80)
    logger.info("")
    
    # 连接数据库
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db 
