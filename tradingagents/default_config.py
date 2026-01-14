import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_dir": os.path.join(os.path.expanduser("~"), "Documents", "TradingAgents", "data"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings
    "llm_provider": "openai",
    "deep_think_llm": "gpt-4o",  # 修复: o4-mini 不是有效的 OpenAI 模型
    "quick_think_llm": "gpt-4o-mini",
    "backend_url": "https://api.openai.com/v1",
    # Debate and discussion settings
    # 牛熊辩论轮次: 3轮 = Bull发言3次 + Bear发言3次 = 6次交锋
    "max_debate_rounds": 3,
    # 风险讨论轮次: 2轮 = (Risky+Safe+Neutral) x 2 = 6次发言
    "max_risk_discuss_rounds": 2,
    "max_recur_limit": 100,
    # Tool settings - 从环境变量读取，提供默认值
    "online_tools": os.getenv("ONLINE_TOOLS_ENABLED", "false").lower() == "true",
    "online_news": os.getenv("ONLINE_NEWS_ENABLED", "true").lower() == "true",

    # ========== 实时行情配置 ==========
    # 实时行情功能开关（环境变量可覆盖）
    "realtime_data_enabled": os.getenv("REALTIME_DATA_ENABLED", "true").lower() == "true",
    # 实时行情详细配置
    "realtime_data": {
        "enabled": True,                    # 是否启用实时行情
        "auto_detect_trading_hours": True,  # 自动检测交易时段
        "preferred_source": "akshare",      # 首选数据源：akshare/tushare
        "fallback_to_close": True,          # 非交易时段回退到收盘价
        "cache_ttl_seconds": 60,            # 实时数据缓存时间（秒）
    },
    # 默认分析日期配置
    "default_analysis_date": "today",       # today/yesterday/specific_date

    # ========== 统一配置：工具调用和重试 ==========
    # 各分析师的工具调用限制
    "analyst_tool_call_limits": {
        "fundamentals": 1,  # 基本面分析师：一次工具调用即可获取所有数据
        "market": 3,        # 市场分析师：最多3次工具调用
        "news": 3,          # 新闻分析师：最多3次工具调用
        "social_media": 3,  # 社交媒体分析师：最多3次工具调用
    },
    # LLM重试配置
    "max_llm_retries": 3,        # LLM调用最大重试次数
    "retry_base_delay": 1.0,     # 重试基础延时（秒）
    # 历史记忆检索配置
    "memory_n_matches": 5,       # 检索历史记忆的数量

    # Note: Database and cache configuration is now managed by .env file and config.database_manager
    # No database/cache settings in default config to avoid configuration conflicts
}
