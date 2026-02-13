#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TradingAgents 演示脚本 - 使用阿里百炼大模型
这个脚本展示了如何使用阿里百炼大模型运行 TradingAgents 框架
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("default")

try:
    from dotenv import load_dotenv

    # 加载 .env 文件
    load_dotenv()
except ImportError:
    pass  # 如果 dotenv 未安装，继续执行

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG


def main():
    """主函数"""
    import os as _os

    logger.info(f"🚀 TradingAgents 演示 - 阿里百炼版本")
    logger.info(f"=")

    # 检查API密钥
    dashscope_key = _os.getenv("DASHSCOPE_API_KEY")
    finnhub_key = _os.getenv("FINNHUB_API_KEY")

    if not dashscope_key:
        logger.error(f"❌ 错误: 未找到 DASHSCOPE_API_KEY 环境变量")
        logger.info(f"请设置您的阿里百炼 API 密钥:")
        logger.info(f"  Windows: set DASHSCOPE_API_KEY=your_api_key")
        logger.info(f"  Linux/Mac: export DASHSCOPE_API_KEY=your_api_key")
        logger.info(f"  或创建 .env 文件")
        print()
        logger.info(f"🔗 获取API密钥:")
        logger.info(f"  1. 访问 https://dashscope.aliyun.com/")
        logger.info(f"  2. 注册/登录阿里云账号")
        logger.info(f"  3. 开通百炼服务")
        logger.info(f"  4. 在控制台获取API密钥")
        return

    if not finnhub_key:
        logger.error(f"❌ 错误: 未找到 FINNHUB_API_KEY 环境变量")
        logger.info(f"请设置您的 FinnHub API 密钥:")
        logger.info(f"  Windows: set FINNHUB_API_KEY=your_api_key")
        logger.info(f"  Linux/Mac: export FINNHUB_API_KEY=your_api_key")
        logger.info(f"  或创建 .env 文件")
        print()
        logger.info(f"🔗 获取API密钥:")
        logger.info(f"  访问 https://finnhub.io/ 注册免费账户")
        return

    logger.info(f"✅ 阿里百炼 API 密钥: {dashscope_key[:10]}...")
    logger.info(f"✅ FinnHub API 密钥: {finnhub_key[:10]}...")
    print()

    # 创建阿里百炼配置
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = "dashscope"
    config["backend_url"] = "https://dashscope.aliyuncs.com/api/v1"
    config["deep_think_llm"] = "qwen-plus-latest"  # 使用通义千问Plus进行深度思考
    config["quick_think_llm"] = "qwen-turbo"  # 使用通义千问Turbo进行快速任务
    config["max_debate_rounds"] = 1  # 减少辩论轮次以降低成本
    config["online_tools"] = True

    logger.info(f"📊 配置信息:")
    logger.info(f"  LLM 提供商: {config['llm_provider']}")
    logger.info(f"  深度思考模型: {config['deep_think_llm']} (通义千问Plus)")
    logger.info(f"  快速思考模型: {config['quick_think_llm']} (通义千问Turbo)")
    logger.info(f"  最大辩论轮次: {config['max_debate_rounds']}")
    logger.info(f"  在线工具: {config['online_tools']}")
    print()

    try:
        logger.info(f"🤖 正在初始化 TradingAgents...")
        ta = TradingAgentsGraph(debug=True, config=config)
        logger.info(f"✅ TradingAgents 初始化成功!")
        print()

        # 分析股票
        stock_symbol = "AAPL"  # 苹果公司
        analysis_date = "2024-05-10"

        # 设置中文输出提示
        _os.environ["TRADINGAGENTS_LANGUAGE"] = "zh-CN"

        logger.info(f"📈 开始分析股票: {stock_symbol}")
        logger.info(f"📅 分析日期: {analysis_date}")
        logger.info(f"⏳ 正在进行多智能体分析，请稍候...")
        logger.info(f"🧠 使用阿里百炼大模型进行智能分析...")
        print()

        # 执行分析
        state, decision = ta.propagate(stock_symbol, analysis_date)

        logger.info(f"🎯 分析结果:")
        logger.info(f"=")
        print(decision)
        print()

        logger.info(f"✅ 分析完成!")
        logger.info(f"💡 提示: 您可以修改 stock_symbol 和 analysis_date 来分析其他股票")
        print()
        logger.info(f"🌟 阿里百炼大模型特色:")
        logger.info(f"  - 中文理解能力强")
        logger.info(f"  - 金融领域知识丰富")
        logger.info(f"  - 推理能力出色")
        logger.info(f"  - 成本相对较低")

    except Exception as e:
        logger.error(f"❌ 运行时错误: {str(e)}")
        print()
        # 显示详细的错误信息
        import traceback

        logger.error(f"🔍 详细错误信息:")
        traceback.print_exc()
        print()
        logger.info(f"🔧 可能的解决方案:")
        logger.info(f"1. 检查阿里百炼API密钥是否正确")
        logger.info(f"2. 确认已开通百炼服务并有足够额度")
        logger.info(f"3. 检查网络连接")
        logger.error(f"4. 查看详细错误信息进行调试")
        print()
        logger.info(f"📞 如需帮助:")
        logger.info(f"  - 阿里百炼官方文档: https://help.aliyun.com/zh/dashscope/")
        logger.info(f"  - 控制台: https://dashscope.console.aliyun.com/")


if __name__ == "__main__":
    main()
