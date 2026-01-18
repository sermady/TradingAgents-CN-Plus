# -*- coding: utf-8 -*-
"""
诊断600765财务数据缺失问题
"""
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_database_financial_data(code):
    """检查数据库中的财务数据"""
    logger.info(f"\n{'='*80}")
    logger.info(f"检查 {code} 的数据库财务数据")
    logger.info(f"{'='*80}\n")
    
    try:
        from app.core.database import get_mongo_db
        import pymongo
        
        # 连接数据库
        logger.info("连接MongoDB...")
        db = get_mongo_db()
        
        # 查询财务数据
        collection = db.stock_financial_data
        cursor = collection.find({"code": code}).sort("report_date", -1).limit(10)
        
        records = list(cursor)
        logger.info(f"找到 {len(records)} 条财务数据记录")
        
        if records:
            logger.info(f"\n最新的财务数据:")
            for i, record in enumerate(records[:3]):
                logger.info(f"\n记录 {i+1}:")
                logger.info(f"  报告期: {record.get('report_period')}")
                logger.info(f"  报告日期: {record.get('report_date')}")
                logger.info(f"  数据源: {record.get('data_source')}")
                logger.info(f"  市值: {record.get('market_cap')}")
                logger.info(f"  PE: {record.get('pe')}")
                logger.info(f"  PB: {record.get('pb')}")
                logger.info(f"  ROE: {record.get('roe')}")
                logger.info(f"  总资产: {record.get('total_assets')}")
                logger.info(f"  净利润: {record.get('net_profit')}")
                logger.info(f"  营业收入: {record.get('revenue')}")
                
                # 检查关键字段是否为空
                missing_fields = []
                key_fields = ['pe', 'pb', 'roe', 'market_cap', 'net_profit', 'revenue', 'total_assets']
                for field in key_fields:
                    if not record.get(field):
                        missing_fields.append(field)
                
                if missing_fields:
                    logger.warning(f"  ⚠️ 缺失字段: {', '.join(missing_fields)}")
                else:
                    logger.info(f"  ✅ 所有关键字段都存在")
        else:
            logger.warning(f"❌ 数据库中没有 {code} 的财务数据")
        
        return len(records) > 0
        
    except Exception as e:
        logger.error(f"❌ 检查数据库失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def check_analysis_results(code):
    """检查分析结果中的基本面报告"""
    logger.info(f"\n{'='*80}")
    logger.info(f"检查 {code} 的分析结果")
    logger.info(f"{'='*80}\n")
    
    try:
        from app.core.database import get_mongo_db
        
        db = get_mongo_db()
        collection = db.analysis_reports
        
        # 查询最新的分析报告
        cursor = collection.find({"stock_code": code}).sort("analysis_date", -1).limit(1)
        report = cursor.next() if cursor.alive else None
        
        if report:
            logger.info(f"找到分析报告，分析ID: {report.get('analysis_id')}")
            logger.info(f"分析时间: {report.get('analysis_date')}")
            
            # 检查reports字段
            reports = report.get('reports', [])
            logger.info(f"包含 {len(reports)} 个分析师报告")
            
            # 查找基本面分析师报告
            fundamentals_report = None
            for r in reports:
                if r.get('analyst') == '基本面分析师':
                    fundamentals_report = r
                    break
            
            if fundamentals_report:
                logger.info(f"\n基本面分析师报告:")
                logger.info(f"  状态: {fundamentals_report.get('status')}")
                logger.info(f"  报告长度: {len(fundamentals_report.get('content', ''))}")
                content = fundamentals_report.get('content', '')
                
                # 检查报告中是否提到"缺失"
                if "缺失" in content or "数据缺失" in content:
                    logger.warning(f"  ⚠️ 报告中提到'数据缺失'")
                    # 查找相关段落
                    for line in content.split('\n'):
                        if "缺失" in line or "数据" in line:
                            logger.info(f"    {line}")
                else:
                    logger.info(f"  ✅ 报告中未提及数据缺失")
                    
                # 保存报告到文件
                output_file = f"temp/600765_fundamentals_report.txt"
                os.makedirs("temp", exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"\n完整报告已保存到: {output_file}")
            else:
                logger.warning(f"❌ 未找到基本面分析师报告")
        else:
            logger.warning(f"❌ 数据库中没有 {code} 的分析报告")
        
        return report is not None
        
    except Exception as e:
        logger.error(f"❌ 检查分析结果失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_fundamentals_tool(code):
    """测试基本面数据获取工具"""
    logger.info(f"\n{'='*80}")
    logger.info(f"测试 {code} 的基本面数据获取工具")
    logger.info(f"{'='*80}\n")
    
    try:
        from tradingagents.dataflows.interface import get_stock_fundamentals_tushare
        from datetime import datetime, timedelta
        
        # 计算日期范围（获取最近10天数据）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        logger.info(f"调用基本面数据获取: {code}, {start_str} ~ {end_str}")
        
        # 调用工具
        result = get_stock_fundamentals_tushare(
            ticker=code,
            start_date=start_str,
            end_date=end_str
        )
        
        logger.info(f"\n获取结果:")
        logger.info(f"  类型: {type(result)}")
        logger.info(f"  长度: {len(result) if isinstance(result, str) else 'N/A'}")
        
        # 检查结果内容
        if isinstance(result, str):
            logger.info(f"\n结果预览（前500字符）:")
            logger.info(result[:500])
            
            # 检查关键字段
            key_fields = ['PE:', 'PB:', 'ROE:', '市值:', '净利润:', '营业收入:']
            missing_fields = []
            for field in key_fields:
                if field not in result:
                    missing_fields.append(field)
            
            if missing_fields:
                logger.warning(f"  ⚠️ 缺失字段: {', '.join(missing_fields)}")
            else:
                logger.info(f"  ✅ 所有关键字段都存在")
                
            # 保存完整结果
            output_file = f"temp/600765_fundamentals_data.txt"
            os.makedirs("temp", exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result)
            logger.info(f"\n完整数据已保存到: {output_file}")
        else:
            logger.warning(f"❌ 结果不是字符串类型")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 测试基本面工具失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    code = "600765"
    
    print("\n" + "="*80)
    print(f"600765财务数据缺失问题诊断")
    print("="*80)
    
    # 1. 检查数据库财务数据
    has_financial_data = check_database_financial_data(code)
    
    # 2. 测试基本面数据获取工具
    test_fundamentals_tool(code)
    
    # 3. 检查分析结果
    has_analysis_report = check_analysis_results(code)
    
    # 总结
    print("\n" + "="*80)
    print("诊断总结")
    print("="*80)
    print(f"数据库中有财务数据: {'✅ 是' if has_financial_data else '❌ 否'}")
    print(f"有分析报告: {'✅ 是' if has_analysis_report else '❌ 否'}")
    
    if not has_financial_data:
        print("\n💡 建议:")
        print("  1. 检查财务数据同步任务是否正常运行")
        print("  2. 检查.env中的财务数据同步配置")
        print("  3. 手动触发财务数据同步")
    else:
        print("\n💡 建议:")
        print("  1. 查看temp/600765_fundamentals_report.txt了解LLM如何看待数据")
        print("  2. 查看temp/600765_fundamentals_data.txt了解获取到的数据")
