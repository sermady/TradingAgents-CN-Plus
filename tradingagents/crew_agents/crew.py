# -*- coding: utf-8 -*-
"""
A股智能投资决策系统 - CrewAI多智能体协作核心
"""
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List, Dict, Any
import os
import sys
from datetime import datetime
import json
import time

# 强制UTF-8编码设置
import sys
import logging
if os.name == 'nt':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # 强制设置标准输出编码
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

# 抑制常见的包依赖警告
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='pkg_resources')
warnings.filterwarnings('ignore', category=DeprecationWarning, module='pkg_resources')
warnings.filterwarnings('ignore', category=UserWarning, message='.*pkg_resources.*')
warnings.filterwarnings('ignore', category=UserWarning, module='setuptools')
warnings.filterwarnings('ignore', category=DeprecationWarning, module='setuptools')

# 优化LiteLLM日志输出，减少冗余信息
os.environ['LITELLM_LOG'] = 'WARNING'
logging.getLogger('LiteLLM').setLevel(logging.WARNING)
logging.getLogger('litellm').setLevel(logging.WARNING)

if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# 禁用CrewAI遥测功能，解决网络连接错误
os.environ['OTEL_SDK_DISABLED'] = 'true'
os.environ['CREWAI_TELEMETRY_DISABLED'] = 'true'

# 统一日志配置
import logging as stdlib_logging
from loguru import logger

# 读取日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
# 使用路径配置管理器
try:
    from .config.path_config import get_path_str
    LOG_FILE = get_path_str("log_file") or os.getenv("LOG_FILE", "logs/a_share_investment_{time}.log")
except ImportError:
    LOG_FILE = os.getenv("LOG_FILE", "logs/a_share_investment_{time}.log")
LOG_ROTATION = os.getenv("LOG_ROTATION", "1 day")
LOG_RETENTION = os.getenv("LOG_RETENTION", "7 days")

# 配置loguru
logger.remove()
logger.add(sys.stderr, level=LOG_LEVEL, enqueue=True)
logger.add(LOG_FILE, rotation=LOG_ROTATION, retention=LOG_RETENTION, level=LOG_LEVEL)

# 配置标准logging模块以与loguru兼容
stdlib_logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 导入A股专用工具
from .tools.market_tools import (
    RealtimeQuoteTool, NorthBoundFlowTool, SectorFlowTool,
    LimitUpStocksTool, DragonTigerListTool
)

# 导入数据库驱动工具
from .tools.database_driven_tools import DatabaseDrivenMarketTool
# 导入高效缓存驱动工具
from .tools.cache_driven_tools import CacheDrivenMarketTool, data_preloader, agent_result_cache
# 导入腾讯实时市场工具
from .tools.tencent_market_tool import TencentMarketToolWrapper
# 导入智能协调器
from .coordination import smart_coordinator

# 导入复杂度管理器
from .config.complexity_manager import (
    complexity_manager, get_task_description, get_complexity_level, 
    get_expected_duration, get_timeout_seconds
)

# 导入MD报告生成器
try:
    from .utils.json_to_md_converter import AnalysisReportConverter
    MD_REPORT_AVAILABLE = True
except ImportError:
    logger.warning("[WARNING] MD报告转换器不可用，自动报告生成将被跳过")
    MD_REPORT_AVAILABLE = False

# 系统优化：使用CrewAI官方工具获得最佳性能
# 移除DEBUG日志，减少启动时冗余输出

# 🚀 Phase 1 性能优化：集成API调用池、单例管理、智能缓存和并发处理
try:
    from .performance import (
        initialize_performance_system, get_performance_stats,
        get_optimized_data_manager, get_smart_cache
    )
    
    # 尝试初始化性能优化系统
    try:
        perf_components = initialize_performance_system()
        optimized_data_manager = get_optimized_data_manager()
        smart_cache = get_smart_cache()
        
        PHASE1_OPTIMIZATION_AVAILABLE = True
        # 移除DEBUG日志，减少启动时冗余输出
        
    except Exception as init_error:
        logger.warning(f"[PHASE1_OPT] 性能优化系统初始化失败: {init_error}")
        optimized_data_manager = None
        smart_cache = None
        PHASE1_OPTIMIZATION_AVAILABLE = False
    
except ImportError as e:
    logger.warning(f"[PHASE1_OPT] 性能优化模块导入失败: {e}")
    optimized_data_manager = None
    smart_cache = None
    PHASE1_OPTIMIZATION_AVAILABLE = False
    
except Exception as e:
    logger.error(f"[PHASE1_OPT] 性能优化系统未知错误: {e}")
    optimized_data_manager = None
    smart_cache = None
    PHASE1_OPTIMIZATION_AVAILABLE = False
from .tools.financial_tools import (
    FinancialIndicatorsTool, CashFlowAnalysisTool, IndustryComparisonTool
)
from .tools.risk_tools import (
    VaRCalculatorTool, PledgeRiskTool, DelistingRiskTool
)
# 尝试导入异步工具和并行数据获取器（可选）
try:
    from .tools import ASYNC_TOOLS_AVAILABLE
    if ASYNC_TOOLS_AVAILABLE:
        from .tools.async_tools import (
            BatchDataFetchTool, SmartCacheTool, PerformanceMonitorTool
        )
    else:
        BatchDataFetchTool = None
        SmartCacheTool = None 
        PerformanceMonitorTool = None
except ImportError as e:
    BatchDataFetchTool = None
    SmartCacheTool = None
    PerformanceMonitorTool = None

# 导入并行数据获取系统
try:
    from .performance.parallel_data_fetcher import (
        get_parallel_fetcher, fetch_stock_analysis_data, DataType
    )
    PARALLEL_FETCHER_AVAILABLE = True
    # 移除DEBUG日志，减少启动时冗余输出
except ImportError as e:
    logger.warning(f"[PARALLEL] 并行数据获取系统导入失败: {e}")
    PARALLEL_FETCHER_AVAILABLE = False
from .tools.notification_tools import (
    WeChatWorkNotificationTool,
    DingTalkNotificationTool, RiskAlertTool, NotificationManagerTool
)
from .tools.historical_data_tool import HistoricalDataTool
from .tools.backtest_tools import BacktestTool

# 导入工具调用限制系统
try:
    from .utils.tool_call_limiter import get_tool_call_limiter, tool_call_wrapper
    from .tools.unified_data_collector import UnifiedDataCollectorTool, FastDataCollectorTool, AdvancedDataCollectorTool
    TOOL_LIMITER_AVAILABLE = True
    logger.info("[TOOL_LIMITER] 工具调用限制系统已导入")
except ImportError as e:
    logger.warning(f"[TOOL_LIMITER] 工具调用限制系统导入失败: {e}")
    TOOL_LIMITER_AVAILABLE = False

# 导入简化的LLM配置管理器
from .llm.simple_config_manager import (
    simple_llm_manager, get_current_llm,
    check_and_truncate_content, extract_key_information,
    create_message_fixing_llm
)

# 简化的配置验证 - 新的配置管理器自动处理所有验证
quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
if not quiet_mode:
    logger.info(f"[SIMPLE_CONFIG] 当前LLM配置: {simple_llm_manager.get_status()}")
else:
    # 静默模式下，在系统启动完成后统一显示配置信息
    _config_status = simple_llm_manager.get_status()
    _provider = _config_status.get('current_provider', 'unknown')
    _model = _config_status.get('current_model', 'unknown')
    print(f"\n[SUCCESS] AI模型: {_provider.title()}/{_model}")
    print(f"[SUCCESS] 数据源: Tushare + Redis缓存")
    print(f"[SUCCESS] 系统启动完成")

# 导入Agent日志系统
try:
    from .agent_logging.agent_logger import (
        AgentLogger, initialize_agent_logger, get_agent_logger,
        log_agent_execution
    )
    AGENT_LOGGING_AVAILABLE = True
    print("Agent日志系统已导入")
except ImportError as e:
    AGENT_LOGGING_AVAILABLE = False
    print(f"Agent日志系统导入失败: {e}")

# 导入状态管理系统
try:
    from .state import (
        InvestmentState, AnalysisStage, RiskLevel,
        create_investment_state, get_state_manager
    )
    from .state.crew_state_integration import StateAwareCrew
    STATE_MANAGEMENT_AVAILABLE = True
    print("状态管理系统已导入")
except ImportError as e:
    STATE_MANAGEMENT_AVAILABLE = False
    print(f"状态管理系统导入失败: {e}")

@CrewBase
class AShareInvestment():
    """A股智能投资决策团队"""

    # CrewAI期待的配置属性
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    def _get_stock_name(self, stock_code: str) -> str:
        """获取股票名称的工具方法"""
        try:
            import akshare as ak
            # 获取股票基本信息
            basic_info_df = ak.stock_individual_info_em(symbol=stock_code)
            if not basic_info_df.empty:
                # 转换为字典格式，查找股票名称
                for _, row in basic_info_df.iterrows():
                    item_name = str(row['item']).strip()
                    # 查找包含"名称"字样的项目
                    if '名称' in item_name or item_name == '股票简称':
                        stock_name = str(row['value']).strip()
                        if stock_name and stock_name != 'nan':
                            logger.info(f"[STOCK_NAME] 成功获取股票名称: {stock_code} -> {stock_name}")
                            return stock_name

                # 如果没找到名称字段，尝试查找第3行数据（通常是股票名称）
                if len(basic_info_df) >= 3:
                    stock_name = str(basic_info_df.iloc[2]['value']).strip()
                    if stock_name and stock_name != 'nan':
                        logger.info(f"[STOCK_NAME] 通过位置获取股票名称: {stock_code} -> {stock_name}")
                        return stock_name
        except Exception as e:
            logger.warning(f"[STOCK_NAME] 获取股票名称失败 {stock_code}: {e}")

        # 如果获取失败，返回默认格式
        logger.info(f"[STOCK_NAME] 使用默认格式: {stock_code}")
        return f"股票{stock_code}"

    # 在类级别初始化工具，确保@agent装饰器可以访问
    try:
        from .tools.unified_data_collector import UnifiedDataCollectorTool, FastDataCollectorTool
        from .tools.financial_tools import FinancialIndicatorsTool, CashFlowAnalysisTool, IndustryComparisonTool
        from .tools.technical_analysis_tools import TechnicalIndicatorsTool, PatternRecognitionTool
        from .tools.risk_tools import VaRCalculatorTool, PledgeRiskTool, DelistingRiskTool
        from .tools.notification_tools import WeChatWorkNotificationTool, DingTalkNotificationTool, RiskAlertTool, NotificationManagerTool
        from .tools.auxiliary_tools import IndustryComparisonTool as AuxIndustryComparisonTool

        # 统一数据收集工具
        unified_tools = [
            UnifiedDataCollectorTool(),
            FastDataCollectorTool()
        ]

        # 核心市场工具
        core_market_tools = [
            TencentMarketToolWrapper(),  # 使用腾讯API的实时市场数据工具
            NorthBoundFlowTool(),
            SectorFlowTool(),
            LimitUpStocksTool(),
            DragonTigerListTool()
        ]

        # 财务分析工具
        financial_tools = [
            FinancialIndicatorsTool(),
            CashFlowAnalysisTool(),
            IndustryComparisonTool()
        ]

        # 技术分析工具
        technical_tools = [
            TechnicalIndicatorsTool(),
            PatternRecognitionTool()
        ]

        # 风险管理工具
        risk_tools = [
            VaRCalculatorTool(),
            PledgeRiskTool(),
            DelistingRiskTool()
        ]

        # 通知工具
        notification_tools = [
            WeChatWorkNotificationTool(),
            DingTalkNotificationTool(),
            RiskAlertTool(),
            NotificationManagerTool()
        ]

        # 辅助工具
        auxiliary_tools = [
            AuxIndustryComparisonTool()
        ]

    except ImportError as e:
        # 如果导入失败，使用空列表避免AttributeError
        unified_tools = []
        core_market_tools = []
        financial_tools = []
        technical_tools = []
        risk_tools = []
        notification_tools = []
        auxiliary_tools = []
        print(f"⚠️ 工具初始化失败: {e}，使用空工具列表")

    def __init__(self):
        super().__init__()

        # 初始化工具调用限制器
        from .utils.tool_call_limiter import get_tool_call_limiter
        self.tool_limiter = get_tool_call_limiter()

        # 初始化Agent日志系统 (使用环境变量配置)
        self.logger = None
        if AGENT_LOGGING_AVAILABLE:
            try:
                # 读取日志配置环境变量
                enable_agent_logging = os.getenv('ENABLE_AGENT_LOGGING', 'true').lower() == 'true'
                enable_console_logging = os.getenv('ENABLE_CONSOLE_LOGGING', 'true').lower() == 'true'
                enable_file_logging = os.getenv('ENABLE_FILE_LOGGING', 'true').lower() == 'true'
                log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
                log_dir = os.getenv('LOG_DIR', 'logs')
                
                if enable_agent_logging:
                    self.logger = initialize_agent_logger(
                        log_dir=log_dir, 
                        enable_console=enable_console_logging,
                        enable_file_logging=enable_file_logging,
                        log_level=log_level
                    )
                    print(f"✅ Agent日志系统初始化成功 - 级别: {log_level}, 控制台: {enable_console_logging}, 文件: {enable_file_logging}, 目录: {log_dir}")
                else:
                    print("ℹ️ Agent日志系统已通过环境变量禁用")
            except Exception as e:
                print(f"⚠️ Agent日志系统初始化失败: {e}")
        
        # 读取CrewAI详细日志配置
        self.crewai_verbose = os.getenv('ENABLE_CREWAI_VERBOSE', 'true').lower() == 'true'
        # 禁用内存功能以避免ChromaDB错误
        # self.crewai_memory = os.getenv('CREWAI_MEMORY_ENABLED', 'true').lower() == 'true'
        self.crewai_memory = False  # 临时禁用内存功能以避免ChromaDB错误
        
        # 智能早停机制相关 - 强制启用以提高性能
        self._iteration_count = {}  # 每个Agent的迭代计数
        self._agent_outputs = {}    # 存储Agent输出用于质量检测
        self._early_stop_enabled = True  # 强制启用早停机制，提高性能
        if self.crewai_verbose:
            print("✅ CrewAI详细日志已启用")
        
        # 显示复杂度配置信息
        self._display_complexity_info()
        
        # 初始化状态管理系统
        self._init_state_management()
        
        # 初始化LLM
        self.llm = self._setup_llm()
        
        # 初始化高性能CrewAI官方工具
        self.market_tools = self._setup_market_tools()
        
        # 设置财务分析工具
        self.financial_tools = self._setup_financial_tools()
        
        self.risk_tools = [
            VaRCalculatorTool(),
            PledgeRiskTool(),
            DelistingRiskTool()
        ]
        
        # 异步工具（条件性）
        self.async_tools = []
        if BatchDataFetchTool is not None:
            try:
                self.async_tools.extend([
                    BatchDataFetchTool(),
                    SmartCacheTool(), 
                    PerformanceMonitorTool()
                ])
            except Exception as e:
                print(f"⚠️ 异步工具初始化失败: {e}，跳过异步工具")
        
        # 通知工具（条件性）
        self.notification_tools = []
        try:
            self.notification_tools.extend([
                WeChatWorkNotificationTool(),
                DingTalkNotificationTool(),
                RiskAlertTool(),
                NotificationManagerTool()
            ])
        except Exception as e:
            print(f"⚠️ 通知工具初始化失败: {e}，跳过通知工具")
        
        # 回测工具
        self.backtest_tools = [
            BacktestTool()
        ]
    
    def _display_complexity_info(self):
        """显示复杂度配置信息"""
        current_level = get_complexity_level()
        expected_duration = get_expected_duration()
        timeout = get_timeout_seconds()
        self.max_iter = complexity_manager.get_max_iterations()

        print(f"🎛️  Agent分析复杂度: {current_level.value.upper()}")
        print(f"⏱️  预期执行时间: {expected_duration}")
        print(f"🔄 最大迭代次数: {self.max_iter}")
        print(f"⏰ 超时限制: {timeout}秒")

    def _init_state_management(self):
        """初始化状态管理系统"""
        if STATE_MANAGEMENT_AVAILABLE:
            # 读取状态管理配置
            self.state_management_enabled = os.getenv('ENABLE_STATE_MANAGEMENT', 'true').lower() == 'true'
            self.state_persistence_enabled = os.getenv('ENABLE_STATE_PERSISTENCE', 'true').lower() == 'true'
            
            if self.state_management_enabled:
                self.current_state = None  # 当前分析状态
                self.state_manager = get_state_manager()
                print("✅ 状态管理系统初始化成功")
            else:
                self.current_state = None
                self.state_manager = None
                print("ℹ️ 状态管理系统已通过环境变量禁用")
        else:
            self.state_management_enabled = False
            self.current_state = None
            self.state_manager = None
            print("⚠️ 状态管理系统不可用")

    def _setup_llm(self):
        """设置LLM配置"""
        # 使用LLM配置管理器，返回LLM对象而非字符串
        from .llm.simple_config_manager import get_crewai_llm_object, simple_llm_manager
        
        # 检查是否为SMART模式
        if simple_llm_manager.is_smart_mode():
            quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
            if not quiet_mode:
                logger.info("[SMART_MODE] 检测到智能团队模式，将为不同角色使用优化模型")
            
            # 导入智能团队配置
            from .llm.smart_team_config import smart_team_config
            
            # 在SMART模式下，存储智能团队配置管理器
            self.smart_team_config = smart_team_config
            self.is_smart_mode = True
            
            # 返回默认LLM对象作为fallback
            return get_crewai_llm_object()
        else:
            # 统一模式
            self.smart_team_config = None
            self.is_smart_mode = False
            llm_object = get_crewai_llm_object()
            # logger.info(f"当前使用的AI模型: {llm_object}")  # 暂时注释掉，避免导入错误
            return llm_object
    
    def _get_agent_llm(self, role_name: str):
        """根据角色获取对应的LLM对象"""
        if self.is_smart_mode and self.smart_team_config:
            # SMART模式：根据角色获取专用模型
            from .llm.smart_team_config import AgentRole
            
            # 角色名称映射到AgentRole枚举
            role_mapping = {
                'market_monitor': AgentRole.MARKET_ANALYST,
                'financial_analyst': AgentRole.FUNDAMENTAL_ANALYST, 
                'technical_analyst': AgentRole.TECHNICAL_ANALYST,
                'risk_manager': AgentRole.RISK_MANAGER,
                'strategy_analyst': AgentRole.STRATEGY_ANALYST,
                'portfolio_manager': AgentRole.PORTFOLIO_MANAGER
            }
            
            # 角色中文名称映射
            role_chinese_names = {
                'market_monitor': '市场分析师',
                'financial_analyst': '基本面分析师',
                'technical_analyst': '技术分析师', 
                'risk_manager': '风险管理师',
                'strategy_analyst': '策略分析师',
                'portfolio_manager': '投资组合管理师'
            }
            
            role = role_mapping.get(role_name)
            if role:
                # 获取角色的模型配置信息
                config = self.smart_team_config.get_model_for_role(role)
                chinese_name = role_chinese_names.get(role_name, role_name)
                
                # 显示Agent创建信息
                quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
                if not quiet_mode:
                    print(f"[SMART_TEAM] 🤖 创建{chinese_name} -> 使用 {config['provider'].upper()}/{config['model']}")
                
                # 获取Smart模式的LLM并确保包装消息修复
                smart_llm = self.smart_team_config.get_crewai_llm_for_role(role)

                # 确保Smart模式的LLM也包装消息修复功能
                if not hasattr(smart_llm, '_is_message_fixed'):
                    smart_llm = create_message_fixing_llm(smart_llm)
                    smart_llm._is_message_fixed = True

                # 添加LLM响应增强功能 - 重新启用以解决LLM空响应问题
                if not hasattr(smart_llm, '_is_response_enhanced'):
                    smart_llm = self._enhance_llm_with_retry(smart_llm)
                    smart_llm._is_response_enhanced = True
                    quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
                    if not quiet_mode:
                        logger.debug(f"[MESSAGE_FIX] Smart模式Agent {chinese_name} LLM已包装消息修复")

                return smart_llm
            
        # 统一模式或未映射的角色：使用默认LLM
        llm_instance = self.llm

        # 确保LLM已包装消息修复功能
        if not hasattr(llm_instance, '_is_message_fixed'):
            llm_instance = create_message_fixing_llm(llm_instance)
            llm_instance._is_message_fixed = True
            quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
            if not quiet_mode:
                logger.debug(f"[MESSAGE_FIX] Agent {role_name} LLM已包装消息修复")

        # 添加LLM响应增强功能 - 重新启用以解决LLM空响应问题
        if not hasattr(llm_instance, '_is_response_enhanced'):
            llm_instance = self._enhance_llm_with_retry(llm_instance)
            llm_instance._is_response_enhanced = True
        #     quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
        #     if not quiet_mode:
        #         print(f"✅ {role_name} Agent已启用LLM响应增强")

        return llm_instance
    
    def _setup_market_tools(self):
        """设置高性能市场工具 - 使用缓存驱动工具获得极速性能"""
        logger.debug("[PERFORMANCE] 使用缓存驱动工具，极速响应，数据一致性最佳")
        return [
            TencentMarketToolWrapper(),  # 使用腾讯API的实时市场数据工具
            NorthBoundFlowTool(),
            SectorFlowTool(),
            LimitUpStocksTool(),
            DragonTigerListTool()
        ]
    
    def _setup_financial_tools(self):
        """设置财务分析工具 - 使用CrewAI官方工具"""
        logger.debug("[OPTIMIZED] 财务工具使用CrewAI官方组件，数据实时性最佳")
        return [
            FinancialIndicatorsTool(),
            CashFlowAnalysisTool(),
            IndustryComparisonTool()
        ]

    @agent
    def market_monitor(self) -> Agent:
        """市场监控专家Agent - 专注核心市场数据收集"""
        return Agent(
            config=self.agents_config['market_monitor'],
            tools=self.unified_tools,  # 使用统一数据收集工具，避免重复调用
            verbose=self.crewai_verbose,
            llm=self._get_agent_llm('market_monitor'),
            max_iter=2,  # 进一步限制最大迭代次数
            memory=self.crewai_memory
        )

    @agent
    def financial_analyst(self) -> Agent:
        """财务分析专家Agent - 专注基本面分析"""
        return Agent(
            config=self.agents_config['financial_analyst'],
            tools=self.financial_tools,  # 只使用财务分析工具
            verbose=self.crewai_verbose,
            llm=self._get_agent_llm('financial_analyst'),
            max_iter=4,  # 限制最大迭代次数
            memory=self.crewai_memory
        )

    @agent
    def technical_analyst(self) -> Agent:
        """技术分析专家Agent - 专注技术指标分析"""
        return Agent(
            config=self.agents_config['technical_analyst'],
            tools=self.technical_tools + self.core_market_tools[:1],  # 技术分析工具+实时行情
            verbose=self.crewai_verbose,
            llm=self._get_agent_llm('technical_analyst'),
            max_iter=4,  # 限制最大迭代次数
            memory=self.crewai_memory
        )

    @agent
    def risk_manager(self) -> Agent:
        """风险管理专家Agent - 专注风险评估与预警"""
        return Agent(
            config=self.agents_config['risk_manager'],
            tools=self.risk_tools + self.notification_tools,  # 风险工具 + 精简通知工具
            verbose=self.crewai_verbose,
            llm=self._get_agent_llm('risk_manager'),
            max_iter=3,  # 限制最大迭代次数
            memory=self.crewai_memory
        )

    @agent
    def strategy_analyst(self) -> Agent:
        """策略分析师Agent - 专注投资策略制定"""
        return Agent(
            config=self.agents_config['strategy_analyst'],
            tools=self.technical_tools + self.auxiliary_tools[:1],  # 技术工具 + 行业比较工具
            verbose=self.crewai_verbose,
            llm=self._get_agent_llm('strategy_analyst'),
            max_iter=5,  # 策略制定需要更多迭代
            memory=self.crewai_memory
        )

    @agent
    def portfolio_manager(self) -> Agent:
        """投资组合经理Agent - 综合决策与管理"""
        return Agent(
            config=self.agents_config['portfolio_manager'],
            tools=self.notification_tools + self.auxiliary_tools,  # 通知工具 + 辅助分析工具
            verbose=self.crewai_verbose,
            llm=self._get_agent_llm('portfolio_manager'),
            max_iter=3,  # 限制最大迭代次数
            memory=self.crewai_memory,
            allow_delegation=True
        )

    @agent  
    def portfolio_manager_hierarchical(self) -> Agent:
        """投资组合经理(层级模式专用 - 无工具)"""
        return Agent(
            config=self.agents_config['portfolio_manager'],
            tools=[],  # 层级模式下Manager Agent不能有工具
            verbose=self.crewai_verbose,
            llm=self._get_agent_llm('portfolio_manager'),
            max_iter=self.max_iter,
            memory=self.crewai_memory,
            allow_delegation=True
        )

    def get_agents(self) -> List[Agent]:
        """返回所有agents的列表"""
        return [
            self.market_monitor(),
            self.financial_analyst(), 
            self.technical_analyst(),
            self.risk_manager(),
            self.strategy_analyst(),
            self.portfolio_manager()
        ]

    @task
    def market_monitoring_task(self) -> Task:
        # 显示任务分配信息
        quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
        if not quiet_mode and self.is_smart_mode:
            print(f"[SMART_TEAM] 📊 市场分析师 -> 任务: 实时行情数据收集与市场动态监控")
        
        return Task(
            config=self.tasks_config['market_monitoring_task'],
            agent=self.market_monitor()
        )

    @task
    def financial_analysis_task(self) -> Task:
        # 显示任务分配信息
        quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
        if not quiet_mode and self.is_smart_mode:
            print(f"[SMART_TEAM] 💰 基本面分析师 -> 任务: 财务报表分析与价值评估")
        
        return Task(
            config=self.tasks_config['financial_analysis_task'],
            agent=self.financial_analyst()
        )

    @task
    def technical_analysis_task(self) -> Task:
        # 显示任务分配信息
        quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
        if not quiet_mode and self.is_smart_mode:
            print(f"[SMART_TEAM] 📈 技术分析师 -> 任务: 技术指标计算与趋势分析")
        
        return Task(
            config=self.tasks_config['technical_analysis_task'],
            agent=self.technical_analyst()
        )

    @task
    def risk_assessment_task(self) -> Task:
        # 显示任务分配信息
        quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
        if not quiet_mode and self.is_smart_mode:
            print(f"[SMART_TEAM] ⚠️ 风险管理师 -> 任务: 风险评估与预警分析")
        
        return Task(
            config=self.tasks_config['risk_assessment_task'],
            agent=self.risk_manager()
        )

    @task
    def strategy_analysis_task(self) -> Task:
        # 显示任务分配信息
        quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
        if not quiet_mode and self.is_smart_mode:
            print(f"[SMART_TEAM] 🎯 策略分析师 -> 任务: 投资策略制定与优化")
        
        return Task(
            config=self.tasks_config['strategy_formulation_task'],
            agent=self.strategy_analyst()
        )

    @task
    def portfolio_decision_task(self) -> Task:
        # 显示任务分配信息
        quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
        if not quiet_mode and self.is_smart_mode:
            print(f"[SMART_TEAM] 🎯 投资组合管理师 -> 任务: 整合分析结果与最终决策")
        
        # 确保输出目录存在 - 使用路径配置管理器
        try:
            from .config.path_config import get_path_str, ensure_dir
            output_dir = get_path_str("decisions_dir") or "results/decisions"
            ensure_dir("decisions_dir")
        except ImportError:
            output_dir = "results/decisions"
            os.makedirs(output_dir, exist_ok=True)
        
        # 简化输出文件名，移除模板变量
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f'final_investment_decision_{timestamp}.json'
        
        return Task(
            config=self.tasks_config['portfolio_decision_task'],
            agent=self.portfolio_manager(),
            output_file=os.path.join(output_dir, output_filename)
        )

    def get_tasks(self) -> List[Task]:
        """返回所有tasks的列表"""
        return [
            self.market_monitoring_task(),
            self.financial_analysis_task(), 
            self.technical_analysis_task(),
            self.risk_assessment_task(),
            self.strategy_analysis_task(),
            self.portfolio_decision_task()
        ]

    @crew
    def crew(self) -> Crew:
        """创建标准的顺序执行团队 - 激进性能优化版本"""
        return Crew(
            agents=self.get_agents(), # 获取agents列表
            tasks=self.get_tasks(),   # 获取tasks列表
            process=Process.sequential,
            verbose=self.crewai_verbose,  # 使用环境变量控制
            memory=self.crewai_memory,    # 使用环境变量控制内存跟踪
            cache=False,
            max_rpm=200,  # 提高请求速率限制
            max_execution_time=120,  # 强制设置2分钟超时
            planning=False,
            step_callback=self._log_step_execution if self.logger else None  # 添加步骤回调
        )

    def state_aware_crew(self, stock_code: str = None, stock_name: str = None):
        """创建状态感知的crew，集成投资状态管理"""
        if not STATE_MANAGEMENT_AVAILABLE or not self.state_management_enabled:
            logger.warning("[STATE] 状态管理不可用，返回标准crew")
            return self.crew()
        
        # 创建或获取投资状态
        if stock_code:
            if self.current_state is None or self.current_state.stock_code != stock_code:
                self.current_state = create_investment_state(stock_code, stock_name)
                logger.info(f"[STATE] 为股票{stock_code}创建新的投资状态")
        
        # 获取基础crew
        base_crew = self.crew()
        
        # 包装为状态感知crew
        state_aware_crew = StateAwareCrew(base_crew, self.current_state)
        
        logger.info("[STATE] 状态感知crew创建完成")
        return state_aware_crew

    def hierarchical_crew(self) -> Crew:
        """创建层级管理团队 (使用环境变量控制详细日志)"""
        # 获取所有agents，但排除manager agent
        all_agents = self.get_agents()
        manager = self.portfolio_manager()
        # 从agents列表中移除manager
        agents_without_manager = [agent for agent in all_agents if agent != manager]
        
        return Crew(
            agents=agents_without_manager,
            tasks=self.get_tasks(),
            process=Process.hierarchical,
            manager_agent=self.portfolio_manager_hierarchical(),  # 使用无工具的管理者
            verbose=self.crewai_verbose,  # 使用环境变量控制
            memory=self.crewai_memory,    # 使用环境变量控制内存跟踪
            cache=False,
            max_rpm=100,
            # max_execution_time=600,  # 移除10分钟超时限制
            planning=False,
            step_callback=self._log_step_execution if self.logger else None  # 添加步骤回调
        )

    def _check_output_quality(self, output: str) -> bool:
        """检查Agent输出质量，决定是否需要继续迭代"""
        if not output or len(output.strip()) < 50:
            return False  # 输出太短，质量不足
            
        # 检查是否包含关键信息标识
        quality_indicators = [
            '分析', '建议', '风险', '价格', '策略', 
            '数据', '指标', '结论', '评估', '决策'
        ]
        
        indicator_count = sum(1 for indicator in quality_indicators if indicator in output)
        if indicator_count < 3:
            return False  # 关键信息不足
            
        # 检查输出是否完整（包含具体数值或结论）
        has_numbers = any(c.isdigit() for c in output)
        has_conclusion = any(word in output for word in ['建议', '结论', '决策', '策略'])
        
        return has_numbers and has_conclusion

    def _log_step_execution(self, step_info):
        """CrewAI步骤执行回调 - 记录每一步的详细执行过程并实现智能早停"""
        if not self.logger:
            return
            
        try:
            # 获取步骤信息 - 改进agent名称获取逻辑
            agent_name = None
            
            # 尝试多种方式获取agent名称
            if hasattr(step_info, 'agent'):
                agent_obj = getattr(step_info, 'agent')
                if agent_obj:
                    if hasattr(agent_obj, 'role'):
                        agent_name = agent_obj.role
                    elif hasattr(agent_obj, 'name'):
                        agent_name = agent_obj.name
                    elif isinstance(agent_obj, str):
                        agent_name = agent_obj
                    else:
                        agent_name = str(agent_obj)
            
            # 如果还是没有获取到，尝试从task中获取
            if not agent_name and hasattr(step_info, 'task'):
                task_obj = getattr(step_info, 'task')
                if task_obj and hasattr(task_obj, 'agent'):
                    agent_task = task_obj.agent
                    if hasattr(agent_task, 'role'):
                        agent_name = agent_task.role
                    elif hasattr(agent_task, 'name'):
                        agent_name = agent_task.name
            
            # 使用更有意义的默认值
            if not agent_name:
                agent_name = 'System_Process'
            
            task_name = getattr(step_info, 'task', 'System_Task')
            if hasattr(task_name, 'description'):
                task_name = task_name.description[:50] + '...' if len(task_name.description) > 50 else task_name.description
            elif not isinstance(task_name, str):
                task_name = str(task_name)
                
            step_type = getattr(step_info, 'step_type', 'STEP')
            step_output = getattr(step_info, 'output', '')
            
            # 智能早停机制
            if self._early_stop_enabled and step_output:
                agent_key = f"{agent_name}_{task_name}"
                
                # 更新迭代计数
                if agent_key not in self._iteration_count:
                    self._iteration_count[agent_key] = 0
                self._iteration_count[agent_key] += 1
                
                # 存储输出用于质量检测
                if agent_key not in self._agent_outputs:
                    self._agent_outputs[agent_key] = []
                self._agent_outputs[agent_key].append(str(step_output))
                
                # 质量检测：如果输出质量足够好，标记为可以早停
                if self._check_output_quality(str(step_output)):
                    if self.logger:
                        self.logger.log_agent_progress(str(agent_name), "质量检测", 
                                                     "输出质量良好，建议早停")
            
            # 根据不同的步骤类型记录不同级别的日志
            if step_type in ['task_start', 'agent_start']:
                self.logger.log_agent_start(str(agent_name), str(task_name))
                
            elif step_type in ['task_complete', 'agent_complete']:
                self.logger.log_agent_complete(str(agent_name), str(task_name), 
                                             {'output': str(step_output)[:300]} if step_output else None)
                                             
            elif step_type in ['error', 'exception']:
                error_msg = getattr(step_info, 'error', str(step_output))
                self.logger.log_agent_error(str(agent_name), str(task_name), 
                                          Exception(str(error_msg)))
                                          
            else:
                # 一般进度更新
                self.logger.log_agent_progress(str(agent_name), str(task_name), 
                                             f"{step_type}: {str(step_output)[:200]}")
                                             
        except Exception as callback_error:
            print(f"[WARNING] 步骤回调日志记录失败: {callback_error}")

    def _preprocess_inputs(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """预处理输入，确保内容长度符合AI模型限制"""
        processed_inputs = {}
        
        for key, value in inputs.items():
            if isinstance(value, str):
                # 对字符串类型的值进行长度检查
                if len(value) > 25000:  # 为多个输入预留空间
                    processed_value = extract_key_information(value, 25000)
                    logger.warning(f"[INPUT] 输入项 {key} 长度过长，已智能压缩: {len(value)} -> {len(processed_value)}")
                    processed_inputs[key] = processed_value
                else:
                    processed_inputs[key] = value
            else:
                processed_inputs[key] = value
        
        # 计算总输入长度
        total_length = sum(len(str(v)) for v in processed_inputs.values())
        if total_length > 28000:  # 为prompt模板预留空间
            logger.warning(f"[INPUT] 总输入长度较大: {total_length} 字符，可能需要进一步优化")
        
        return processed_inputs
    
    def _check_problematic_stock(self, stock_code: str) -> bool:
        """检查是否为已知问题股票，提供快速失败机制"""
        problematic_stocks = {
            # 002815 (崇达技术) 已恢复正常，从问题列表中移除
            # 可以在这里添加真正的问题股票
        }
        
        if stock_code in problematic_stocks:
            reason = problematic_stocks[stock_code]
            logger.warning(f"[QUICK_FAIL] 检测到问题股票 {stock_code}: {reason}")
            return True
        
        return False
    
    def analyze_stock(self, stock_code: str, analysis_mode: str = "sequential") -> Dict[str, Any]:
        """分析股票的主要接口 - 集成智能协调器优化和数据预验证"""

        # 数据预验证 - 在分析开始前验证股票代码和分析请求
        try:
            from .validation.data_pre_validator import get_data_pre_validator
            pre_validator = get_data_pre_validator()

            # 映射分析模式到分析类型
            analysis_type_map = {
                "smart": "comprehensive",
                "cache_driven": "standard",
                "intelligent": "comprehensive",
                "sequential": "standard",
                "parallel": "quick"
            }
            analysis_type = analysis_type_map.get(analysis_mode, "standard")

            validation_result = pre_validator.validate_analysis_request(
                stock_code=stock_code,
                analysis_type=analysis_type
            )

            logger.info(f"[DATA_VALIDATOR] 股票 {stock_code} 预验证: {validation_result.validation_result.value} (置信度: {validation_result.confidence_score:.2f})")

            # 如果验证失败，直接返回错误
            if validation_result.validation_result.value == "失败":
                return {
                    'stock_code': stock_code,
                    'status': 'failed',
                    'error': 'validation_failed',
                    'message': f"股票 {stock_code} 数据预验证失败",
                    'issues': validation_result.issues,
                    'recommendations': validation_result.recommendations,
                    'validation_info': {
                        'data_quality': validation_result.data_quality.value,
                        'confidence_score': validation_result.confidence_score
                    },
                    'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
                }

            # 如果有警告，记录但继续执行
            if validation_result.warnings:
                logger.warning(f"[DATA_VALIDATOR] 股票 {stock_code} 验证警告: {'; '.join(validation_result.warnings[:2])}")

        except Exception as e:
            logger.warning(f"[DATA_VALIDATOR] 数据预验证失败，将继续分析: {e}")

        # 快速检查问题股票
        if self._check_problematic_stock(stock_code):
            return {
                'stock_code': stock_code,
                'status': 'failed',
                'error': 'problematic_stock',
                'message': f"股票 {stock_code} 为已知问题股票，建议使用其他有效股票代码",
                'suggestions': [
                    "使用000001 (平安银行)",
                    "使用600519 (贵州茅台)",
                    "使用000002 (万科A)",
                    "使用002415 (海康威视)"
                ],
                'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
            }

        # 优先使用智能协调器 (新的缓存驱动架构)
        if analysis_mode in ["smart", "cache_driven", "intelligent", "flow"] or analysis_mode == "sequential":
            logger.info(f"[SMART_COORDINATOR] 使用智能协调器分析股票: {stock_code}")
            try:
                import asyncio
                from .coordination import smart_coordinator

                # 根据不同的分析模式映射到smart_coordinator的模式
                smart_mode_mapping = {
                    "smart": "comprehensive",
                    "flow": "standard",  # flow模式使用standard以加快速度
                    "sequential": "comprehensive",
                    "cache_driven": "comprehensive",
                    "intelligent": "comprehensive"
                }
                smart_analysis_mode = smart_mode_mapping.get(analysis_mode, "comprehensive")

                # 使用更安全的事件循环处理方式
                import threading

                def run_async_in_thread(coro):
                    """在当前线程中运行异步代码"""
                    try:
                        # 尝试获取当前事件循环
                        loop = asyncio.get_running_loop()
                        # 如果有运行的事件循环，创建任务
                        if loop.is_running():
                            # 创建新的事件循环在新线程中运行
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(lambda: asyncio.run(coro))
                                return future.result()
                        else:
                            return loop.run_until_complete(coro)
                    except RuntimeError:
                        # 没有运行的事件循环
                        return asyncio.run(coro)

                # 运行智能协调器分析
                result = run_async_in_thread(smart_coordinator.smart_analysis_workflow(
                    stock_code=stock_code,
                    analysis_mode=smart_analysis_mode
                ))

                # 检查智能协调器结果
                if "error" not in result:
                    logger.info(f"[SMART_COORDINATOR] 智能协调器分析成功: {stock_code}")
                    # 格式化为标准返回格式
                    formatted_result = self._format_smart_coordinator_result(result, stock_code, analysis_mode)

                    # 记录分析完成
                    if self.logger:
                        self.logger.log_agent_complete("smart_coordinator", f"股票分析-{stock_code}",
                                                    formatted_result)

                    return formatted_result
                else:
                    logger.warning(f"[SMART_COORDINATOR] 智能协调器分析失败，降级到传统方式: {result.get('error')}")

            except Exception as e:
                logger.warning(f"[SMART_COORDINATOR] 智能协调器不可用，降级到传统分析: {e}")

        # 传统分析方式（作为备用）
        inputs = {
            'stock_code': stock_code,
            'current_date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
        }

        # 预处理输入以确保长度限制
        processed_inputs = self._preprocess_inputs(inputs)

        # 记录分析开始
        if self.logger:
            self.logger.log_agent_start("crew_coordinator", f"股票分析-{stock_code}", processed_inputs)

        try:
            if analysis_mode == "hierarchical":
                if self.logger:
                    self.logger.log_communication("crew_coordinator", "hierarchical_crew",
                                                      "启动层级分析", "使用层级管理模式")
                # 使用层级管理分析
                crew_result = self.hierarchical_crew().kickoff(inputs=processed_inputs)
                formatted_result = self._format_analysis_result(crew_result, stock_code, "hierarchical")
            else:
                if self.logger:
                    self.logger.log_communication("crew_coordinator", "sequential_crew",
                                                      "启动顺序分析", "使用状态感知模式")

                # 优先使用状态感知crew，降级到标准crew
                if STATE_MANAGEMENT_AVAILABLE and self.state_management_enabled:
                    logger.info(f"[STATE] 使用状态感知Crew分析股票: {stock_code}")
                    # 获取股票名称
                    stock_name = self._get_stock_name(stock_code)
                    logger.info(f"[STOCK_NAME] 获取到股票名称: {stock_name}")
                    state_aware_crew_instance = self.state_aware_crew(stock_code, stock_name)
                    crew_result = state_aware_crew_instance.kickoff(inputs=processed_inputs)
                else:
                    logger.info(f"[STANDARD] 使用标准Crew分析股票: {stock_code}")
                    crew_result = self.crew().kickoff(inputs=processed_inputs)

                formatted_result = self._format_analysis_result(crew_result, stock_code, "sequential")

            # 记录分析完成
            if self.logger:
                self.logger.log_agent_complete("crew_coordinator", f"股票分析-{stock_code}",
                                            formatted_result)

            return formatted_result
                
        except Exception as e:
            error_result = {
                "error": f"分析失败: {str(e)}",
                "stock_code": stock_code,
                "analysis_mode": analysis_mode,
                "timestamp": datetime.now().isoformat()
            }
            
            # 记录错误
            if self.logger:
                self.logger.log_agent_error("crew_coordinator", f"股票分析-{stock_code}", e)
            
            return error_result

    def analyze_stock_parallel(self, stock_code: str, analysis_mode: str = "sequential") -> Dict[str, Any]:
        """
        并行数据获取优化的股票分析接口
        预期减少60-70%的数据获取时间
        """
        # 快速检查问题股票
        if self._check_problematic_stock(stock_code):
            return {
                'stock_code': stock_code,
                'status': 'failed',
                'error': 'problematic_stock',
                'message': f"股票 {stock_code} 为已知问题股票，建议使用其他有效股票代码",
                'suggestions': [
                    "使用000001 (平安银行)",
                    "使用600519 (贵州茅台)",
                    "使用000002 (万科A)",
                    "使用002415 (海康威视)"
                ],
                'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S'),
                'analysis_mode': 'parallel_quick_fail'
            }
        
        if not PARALLEL_FETCHER_AVAILABLE:
            logger.warning("[PARALLEL] 并行数据获取不可用，降级到标准分析")
            return self.analyze_stock(stock_code, analysis_mode)
        
        logger.info(f"[PARALLEL] 开始并行优化分析: {stock_code}")
        start_time = time.time()
        
        inputs = {
            'stock_code': stock_code,
            'current_date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
        }
        
        try:
            # 并行预取数据
            logger.info("[PARALLEL] 开始并行数据预取...")
            parallel_data = fetch_stock_analysis_data(stock_code, include_advanced=True)
            
            # 统计并行获取结果
            successful_fetches = sum(1 for result in parallel_data.values() if result.success)
            cache_hits = sum(1 for result in parallel_data.values() if result.cache_hit)
            total_fetches = len(parallel_data)
            
            logger.info(f"[PARALLEL] 数据预取完成: {successful_fetches}/{total_fetches} 成功, "
                       f"{cache_hits} 缓存命中")
            
            # 将预取的数据添加到inputs中供Agent使用
            inputs['parallel_data'] = parallel_data
            inputs['parallel_stats'] = {
                'successful_fetches': successful_fetches,
                'cache_hits': cache_hits,
                'total_fetches': total_fetches
            }
            
            # 预处理输入以确保长度限制
            processed_inputs = self._preprocess_inputs(inputs)
            
            # 执行标准分析流程（但Agent可以使用预取的数据）
            if analysis_mode == "hierarchical":
                crew_result = self.hierarchical_crew().kickoff(inputs=processed_inputs)
                formatted_result = self._format_analysis_result(crew_result, stock_code, "hierarchical_parallel")
            else:
                if STATE_MANAGEMENT_AVAILABLE and self.state_management_enabled:
                    state_aware_crew_instance = self.state_aware_crew(stock_code)
                    crew_result = state_aware_crew_instance.kickoff(inputs=processed_inputs)
                else:
                    crew_result = self.crew().kickoff(inputs=processed_inputs)
                
                formatted_result = self._format_analysis_result(crew_result, stock_code, "sequential_parallel")
            
            # 添加性能统计
            total_time = time.time() - start_time
            formatted_result['parallel_performance'] = {
                'total_time': total_time,
                'data_fetch_stats': inputs['parallel_stats'],
                'performance_improvement': 'enabled'
            }
            
            logger.info(f"[PARALLEL] 并行优化分析完成: 耗时 {total_time:.2f}s")
            
            return formatted_result
            
        except Exception as e:
            logger.error(f"[PARALLEL] 并行分析失败，降级到标准分析: {e}")
            return self.analyze_stock(stock_code, analysis_mode)

    def _format_analysis_result(self, result: Any, stock_code: str, mode: str) -> Dict[str, Any]:
        """格式化分析结果"""
        
        formatted_result = {
            "stock_code": stock_code,
            "analysis_mode": mode,
            "analysis_time": datetime.now().isoformat(),
            "raw_result": str(result),
            "status": "completed"
        }
        
        # 尝试解析JSON结果
        try:
            if hasattr(result, 'json_dict'):
                formatted_result["structured_result"] = result.json_dict
            elif isinstance(result, dict):
                formatted_result["structured_result"] = result
            else:
                # 尝试从字符串中提取JSON
                import re
                json_matches = re.findall(r'\{[^{}]*\}', str(result))
                if json_matches:
                    try:
                        parsed_json = json.loads(json_matches[-1])
                        formatted_result["structured_result"] = parsed_json
                    except:
                        pass
        except Exception as e:
            formatted_result["parse_error"] = str(e)
        
        # 保存结果到文件 - 使用路径配置管理器
        try:
            from .config.path_config import get_path_str, ensure_dir
            output_dir = get_path_str("analysis_dir") or "results/analysis"
            ensure_dir("analysis_dir")
        except ImportError:
            output_dir = "results/analysis"
            os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"analysis_result_{stock_code}_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(formatted_result, f, ensure_ascii=False, indent=2)
            formatted_result["output_file"] = output_file
            
            # 自动生成MD报告
            self._auto_generate_md_report(output_file, stock_code, mode, formatted_result)
            
        except Exception as e:
            formatted_result["save_error"] = str(e)
        
        return formatted_result

    def _format_smart_coordinator_result(self, result: Dict[str, Any], stock_code: str, mode: str) -> Dict[str, Any]:
        """格式化智能协调器分析结果"""

        formatted_result = {
            "stock_code": stock_code,
            "analysis_mode": f"{mode}_smart_coordinator",
            "analysis_time": datetime.now().isoformat(),
            "status": "completed",
            "architecture": "cache_driven_smart_coordination"
        }

        # 包含智能协调器的原始结果
        formatted_result["smart_coordinator_result"] = result

        # 提取关键信息
        if "investment_recommendation" in result:
            formatted_result["structured_result"] = {
                "investment_recommendation": result["investment_recommendation"].get("action", "N/A"),
                "confidence_score": result["investment_recommendation"].get("confidence", 0),
                "reasoning": result["investment_recommendation"].get("reasoning", "N/A")
            }

        # 提取性能统计
        if "performance_stats" in result:
            stats = result["performance_stats"]
            formatted_result["performance_optimization"] = {
                "preload_time": stats.get("preload_time", 0),
                "parallel_analysis_time": stats.get("parallel_analysis_time", 0),
                "aggregation_time": stats.get("aggregation_time", 0),
                "cache_hits": stats.get("cache_hits", 0),
                "api_calls_saved": stats.get("api_calls_saved", 0),
                "total_time": stats.get("total_time", 0)
            }

        # 保存结果到文件
        try:
            from .config.path_config import get_path_str, ensure_dir
            output_dir = get_path_str("analysis_dir") or "results/analysis"
            ensure_dir("analysis_dir")
        except ImportError:
            output_dir = "results/analysis"
            os.makedirs(output_dir, exist_ok=True)

        output_file = os.path.join(output_dir, f"smart_analysis_{stock_code}_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(formatted_result, f, ensure_ascii=False, indent=2)
            formatted_result["output_file"] = output_file

            # 自动生成MD报告
            self._auto_generate_md_report(output_file, stock_code, f"{mode}_smart", formatted_result)

        except Exception as e:
            formatted_result["save_error"] = str(e)

        return formatted_result

    def _auto_generate_md_report(self, json_file_path: str, stock_code: str, mode: str, formatted_result: Dict[str, Any]):
        """
        自动生成MD报告
        
        Args:
            json_file_path: JSON文件路径
            stock_code: 股票代码
            mode: 分析模式
            formatted_result: 格式化的结果数据
        """
        if not MD_REPORT_AVAILABLE:
            logger.warning(f"[WARNING] MD报告转换器不可用，跳过 {stock_code} 的报告生成")
            return
        
        try:
            logger.info(f"[AUTO-MD] 开始为股票 {stock_code} ({mode}模式) 自动生成投资分析报告")
            
            # 创建转换器实例
            converter = AnalysisReportConverter()
            
            # 生成MD报告 - 使用路径配置管理器
            try:
                from .config.path_config import get_path_str, ensure_dir
                output_dir = get_path_str("reports_dir") or "results/reports"
                ensure_dir("reports_dir")
            except ImportError:
                output_dir = "results/reports"
            
            md_report_path = converter.convert_json_to_md(
                json_file_path=json_file_path,
                output_dir=output_dir
            )
            
            # 记录成功信息
            logger.info(f"[AUTO-MD] 自动报告生成成功: {md_report_path}")
            formatted_result["md_report"] = md_report_path
            
            # 可选：记录到通信日志
            if self.logger:
                try:
                    self.logger.log_communication(
                        "auto_reporter", 
                        "user",
                        f"已为 {stock_code} 自动生成投资分析报告",
                        f"MD报告: {md_report_path}"
                    )
                except TypeError:
                    # 兼容不同版本的日志接口
                    pass
            
            print(f"[AUTO-MD] 投资分析报告已自动生成: {md_report_path}")
            
        except Exception as e:
            # 确保MD报告生成失败不影响主流程
            error_msg = f"自动MD报告生成失败: {e}"
            logger.warning(f"[AUTO-MD] {error_msg}")
            formatted_result["md_report_error"] = error_msg
            
            # 不抛出异常，确保主分析流程不受影响
    
    # ==================== 批量处理优化方法 ====================
    
    async def analyze_stocks_batch(self, 
                                 stock_codes: List[str], 
                                 analysis_depth: str = "comprehensive",
                                 enable_optimization: bool = True) -> Dict[str, Any]:
        """
        批量股票分析 - 集成优化的并行处理系统
        
        Args:
            stock_codes: 股票代码列表
            analysis_depth: 分析深度 (quick/standard/comprehensive/fundamental)
            enable_optimization: 是否启用批量优化
            
        Returns:
            批量分析结果
        """
        logger.info(f"[CREW_BATCH] 开始批量分析 {len(stock_codes)} 只股票，深度: {analysis_depth}")
        
        try:
            if enable_optimization and len(stock_codes) > 1:
                # 使用优化的批量处理系统
                from .performance.batch_integration import get_batch_integrator
                
                integrator = get_batch_integrator()
                result = await integrator.analyze_stocks_batch_optimized(
                    stock_codes=stock_codes,
                    analysis_depth=analysis_depth,
                    enable_parallel=True
                )
                
                logger.info(f"[CREW_BATCH] 优化批量分析完成 - 成功率: {result.get('performance', {}).get('success_rate', 0):.1%}")
                return result
            else:
                # 传统逐个分析方式
                return await self._traditional_batch_analysis(stock_codes, analysis_depth)
                
        except Exception as e:
            logger.error(f"[CREW_BATCH] 批量分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _traditional_batch_analysis(self, stock_codes: List[str], analysis_depth: str) -> Dict[str, Any]:
        """传统的逐个股票分析方式"""
        results = []
        failed = []
        start_time = time.time()
        
        for i, code in enumerate(stock_codes, 1):
            try:
                logger.info(f"[CREW_BATCH] 传统分析 {i}/{len(stock_codes)}: {code}")
                
                # 根据分析深度选择方法
                if analysis_depth in ["quick", "basic"]:
                    # 使用并行数据获取的快速分析
                    result = self.analyze_stock_parallel(code)
                else:
                    # 使用标准CrewAI分析
                    result = self.run({'stock_code': code})
                
                results.append({
                    "stock_code": code,
                    "success": True,
                    "result": result,
                    "analysis_time": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"[CREW_BATCH] 股票 {code} 分析失败: {e}")
                failed.append({
                    "stock_code": code,
                    "error": str(e)
                })
        
        total_time = time.time() - start_time
        
        return {
            "success": True,
            "method": "traditional_sequential",
            "summary": {
                "total_stocks": len(stock_codes),
                "successful_analyses": len(results),
                "failed_analyses": len(failed),
                "success_rate": len(results) / len(stock_codes) if stock_codes else 0,
                "total_time_seconds": total_time,
                "avg_time_per_stock": total_time / max(len(stock_codes), 1)
            },
            "detailed_results": results,
            "failed_analyses": failed,
            "timestamp": datetime.now().isoformat()
        }
    
    def batch_quick_analysis(self, stock_codes: List[str]) -> Dict[str, Any]:
        """
        同步版本的快速批量分析
        适用于需要同步调用的场景
        """
        try:
            import asyncio
            
            # 如果已在事件循环中，使用不同的方法
            try:
                loop = asyncio.get_running_loop()
                # 在已有事件循环中，使用传统方式
                # 使用参数配置管理器获取超时时间
                try:
                    from .config.params_config import get_param_int
                    timeout = get_param_int("crew_task_timeout", 300)
                except ImportError:
                    timeout = 300
                
                return asyncio.run_coroutine_threadsafe(
                    self.analyze_stocks_batch(stock_codes, "quick", True), 
                    loop
                ).result(timeout=timeout)
                
            except RuntimeError:
                # 没有运行的事件循环，直接运行
                return asyncio.run(self.analyze_stocks_batch(stock_codes, "quick", True))
            
        except Exception as e:
            logger.error(f"[CREW_BATCH] 同步批量分析失败: {e}")
            # 降级到传统方式
            return self._sync_traditional_batch(stock_codes)
    
    def _sync_traditional_batch(self, stock_codes: List[str]) -> Dict[str, Any]:
        """同步版本的传统批量分析"""
        results = []
        failed = []
        start_time = time.time()
        
        for i, code in enumerate(stock_codes, 1):
            try:
                logger.info(f"[CREW_BATCH] 同步分析 {i}/{len(stock_codes)}: {code}")
                
                # 使用现有的并行分析方法
                result = self.analyze_stock_parallel(code)
                
                results.append({
                    "stock_code": code,
                    "success": True,
                    "result": result
                })
                
            except Exception as e:
                logger.error(f"[CREW_BATCH] 同步分析失败 {code}: {e}")
                failed.append({
                    "stock_code": code,
                    "error": str(e)
                })
        
        total_time = time.time() - start_time
        
        return {
            "success": True,
            "method": "sync_traditional",
            "summary": {
                "total_stocks": len(stock_codes),
                "successful_analyses": len(results),
                "success_rate": len(results) / len(stock_codes) if stock_codes else 0,
                "total_time_seconds": total_time
            },
            "results": results,
            "failed": failed
        }
    
    def get_batch_processing_status(self) -> Dict[str, Any]:
        """获取批量处理能力状态"""
        try:
            from .performance.batch_integration import get_batch_integrator
            
            integrator = get_batch_integrator()
            processor = integrator.batch_processor
            
            return {
                "optimization_available": True,
                "current_concurrency": processor.concurrency_controller.current_concurrency,
                "max_concurrency": processor.concurrency_controller.max_concurrency,
                "system_resources": processor.concurrency_controller.get_system_resources().__dict__,
                "performance_history": len(processor.concurrency_controller.performance_history),
                "optimization_features": [
                    "智能并发控制",
                    "自适应任务调度",
                    "系统资源监控",
                    "故障自动重试",
                    "实时进度跟踪"
                ]
            }
            
        except ImportError:
            return {
                "optimization_available": False,
                "fallback_method": "traditional_sequential",
                "message": "批量优化系统未安装，将使用传统方式"
            }

    def _enhance_llm_with_retry(self, original_llm):
        """为LLM添加响应验证和重试机制"""
        try:
            from .llm.llm_response_enhancer import get_llm_response_enhancer

            # 获取全局LLM响应增强器
            enhancer = get_llm_response_enhancer()

            # 创建增强的LLM包装器
            class EnhancedLLMWrapper:
                def __init__(self, llm, enhancer):
                    self.llm = llm
                    self.enhancer = enhancer
                    # 复制原始LLM的所有属性
                    for attr in dir(llm):
                        if not attr.startswith('_') and not hasattr(self, attr):
                            setattr(self, attr, getattr(llm, attr))

                def __call__(self, *args, **kwargs):
                    """增强的LLM调用"""
                    return self.enhancer.enhance_llm_call(
                        lambda msgs, **kw: self.llm(*args, **kwargs),
                        args[0] if args else "",
                        **kwargs
                    )

                def __getattr__(self, name):
                    """代理属性访问到原始LLM"""
                    return getattr(self.llm, name)

            return EnhancedLLMWrapper(original_llm, enhancer)

        except Exception as e:
            print(f"⚠️ LLM响应增强器集成失败: {e}，使用原始LLM")
            return original_llm


class AShareInvestmentCrew:
    """
    A股智能投资决策系统 - CrewAI多智能体协作核心

    该类整合了市场监控、基本面分析、技术分析、风险管理、策略制定和投资决策六个专业智能体，
    通过协作方式为A股投资提供全面的决策支持。

    主要功能：
    - 实时市场数据监控和分析
    - 多维度股票基本面分析
    - 技术指标分析和趋势预测
    - 风险评估和管理建议
    - 投资策略制定和优化
    - 最终投资决策建议
    """

    # 在类级别初始化工具，确保@agent装饰器可以访问
    try:
        from .tools.unified_data_collector import UnifiedDataCollectorTool, FastDataCollectorTool
        from .tools.financial_tools import FinancialIndicatorsTool, CashFlowAnalysisTool, IndustryComparisonTool
        from .tools.technical_analysis_tools import TechnicalIndicatorsTool, PatternRecognitionTool
        from .tools.risk_tools import VaRCalculatorTool, PledgeRiskTool, DelistingRiskTool
        from .tools.notification_tools import WeChatWorkNotificationTool, DingTalkNotificationTool, RiskAlertTool, NotificationManagerTool
        from .tools.auxiliary_tools import IndustryComparisonTool as AuxIndustryComparisonTool

        # 统一数据收集工具
        unified_tools = [
            UnifiedDataCollectorTool(),
            FastDataCollectorTool()
        ]

        # 核心市场工具
        core_market_tools = [
            TencentMarketToolWrapper(),  # 使用腾讯API的实时市场数据工具
            NorthBoundFlowTool(),
            SectorFlowTool(),
            LimitUpStocksTool(),
            DragonTigerListTool()
        ]

        # 财务分析工具
        financial_tools = [
            FinancialIndicatorsTool(),
            CashFlowAnalysisTool(),
            IndustryComparisonTool()
        ]

        # 技术分析工具
        technical_tools = [
            TechnicalIndicatorsTool(),
            PatternRecognitionTool()
        ]

        # 风险管理工具
        risk_tools = [
            VaRCalculatorTool(),
            PledgeRiskTool(),
            DelistingRiskTool()
        ]

        # 通知工具
        notification_tools = [
            WeChatWorkNotificationTool(),
            DingTalkNotificationTool(),
            RiskAlertTool(),
            NotificationManagerTool()
        ]

        # 辅助工具
        auxiliary_tools = [
            AuxIndustryComparisonTool()
        ]

    except ImportError as e:
        # 如果导入失败，使用空列表避免AttributeError
        unified_tools = []
        core_market_tools = []
        financial_tools = []
        technical_tools = []
        risk_tools = []
        notification_tools = []
        auxiliary_tools = []
        print(f"⚠️ 工具初始化失败: {e}，使用空工具列表")

    def __init__(self):
        """初始化A股投资决策系统"""
        # 加载配置文件
        self._load_configs()

        # 初始化LLM配置
        self.llm = self._setup_llm()
        self.setup_tools()

    def _load_configs(self):
        """加载YAML配置文件"""
        import yaml
        import os

        # 构建配置文件路径
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config')

        # 加载agents配置
        agents_config_path = os.path.join(config_dir, 'agents.yaml')
        try:
            with open(agents_config_path, 'r', encoding='utf-8') as f:
                self.agents_config = yaml.safe_load(f)
        except Exception as e:
            print(f"⚠️ 加载agents配置失败: {e}")
            self.agents_config = {}

        # 加载tasks配置
        tasks_config_path = os.path.join(config_dir, 'tasks.yaml')
        try:
            with open(tasks_config_path, 'r', encoding='utf-8') as f:
                self.tasks_config = yaml.safe_load(f)
        except Exception as e:
            print(f"⚠️ 加载tasks配置失败: {e}")
            self.tasks_config = {}

    def _setup_llm(self):
        """设置LLM配置"""
        # 使用LLM配置管理器，返回LLM对象而非字符串
        from .llm.simple_config_manager import get_crewai_llm_object, simple_llm_manager

        # 检查是否为SMART模式
        if simple_llm_manager.is_smart_mode():
            quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
            if not quiet_mode:
                logger.info("[SMART_MODE] 检测到智能团队模式，将为不同角色使用优化模型")

            # 导入智能团队配置
            from .llm.smart_team_config import smart_team_config

            # 在SMART模式下，存储智能团队配置管理器
            self.smart_team_config = smart_team_config
            self.is_smart_mode = True

            # 返回默认LLM对象作为fallback
            return get_crewai_llm_object()
        else:
            # 统一模式
            self.smart_team_config = None
            self.is_smart_mode = False
            llm_object = get_crewai_llm_object()
            return llm_object

    def _get_agent_llm(self, role_name: str):
        """根据角色获取对应的LLM对象"""
        # 简化版本：直接返回统一LLM
        llm = self.llm

        # 添加LLM响应增强功能 - 重新启用以解决LLM空响应问题
        if not hasattr(llm, '_is_response_enhanced'):
            llm = self._enhance_llm_with_retry(llm)
            llm._is_response_enhanced = True
            quiet_mode = os.getenv('QUIET_MODE', 'false').lower() == 'true'
            if not quiet_mode:
                print(f"✅ {role_name} Agent已启用LLM响应增强")

        return llm

    def _enhance_llm_with_retry(self, original_llm):
        """为LLM添加响应验证和重试机制"""
        try:
            from .llm.llm_response_enhancer import get_llm_response_enhancer

            # 获取全局LLM响应增强器
            enhancer = get_llm_response_enhancer()

            # 创建增强的LLM包装器
            class EnhancedLLMWrapper:
                def __init__(self, llm, enhancer):
                    self.llm = llm
                    self.enhancer = enhancer
                    # 复制原始LLM的所有属性
                    for attr in dir(llm):
                        if not attr.startswith('_') and not hasattr(self, attr):
                            setattr(self, attr, getattr(llm, attr))

                def __call__(self, *args, **kwargs):
                    """增强的LLM调用"""
                    return self.enhancer.enhance_llm_call(
                        lambda msgs, **kw: self.llm(*args, **kwargs),
                        args[0] if args else "",
                        **kwargs
                    )

                def __getattr__(self, name):
                    """代理属性访问到原始LLM"""
                    return getattr(self.llm, name)

            return EnhancedLLMWrapper(original_llm, enhancer)

        except Exception as e:
            print(f"⚠️ LLM响应增强器集成失败: {e}，使用原始LLM")
            return original_llm

    def setup_tools(self):
        """设置工具集合 - 专业化分工，减少工具调用次数"""
        from .tools.unified_data_collector import UnifiedDataCollectorTool, FastDataCollectorTool

        # 统一数据收集工具 - 减少重复工具调用的核心工具
        self.unified_tools = [
            TencentMarketToolWrapper(),  # 腾讯实时市场数据工具 - 优先使用
            UnifiedDataCollectorTool(),  # 作为备用数据源
            FastDataCollectorTool()     # 快速数据获取
        ]

        # 核心市场数据工具 - 减少重复调用
        self.core_market_tools = [
            TencentMarketToolWrapper(),  # 使用腾讯API的实时市场数据工具
            NorthBoundFlowTool(),
            SectorFlowTool()
        ]

        # 专业财务分析工具
        self.financial_tools = [
            FinancialIndicatorsTool(),
            CashFlowAnalysisTool()
        ]

        # 专业风险管理工具
        self.risk_tools = [
            VaRCalculatorTool(),
            PledgeRiskTool(),
            DelistingRiskTool()
        ]

        # 专业技术分析工具
        self.technical_tools = [
            HistoricalDataTool(),
            BacktestTool()
        ]

        # 精简通知工具
        self.notification_tools = [
            RiskAlertTool(),
            NotificationManagerTool()
        ]

        # 辅助工具 - 仅在必要时使用
        self.auxiliary_tools = [
            LimitUpStocksTool(),
            DragonTigerListTool(),
            IndustryComparisonTool()
        ]

        # 合并所有工具
        self.all_tools = (
            self.unified_tools +
            self.core_market_tools +
            self.financial_tools +
            self.risk_tools +
            self.technical_tools +
            self.notification_tools +
            self.auxiliary_tools
        )
    
    @agent
    def market_monitor(self) -> Agent:
        """市场监控专家Agent - 专注核心市场数据收集"""
        return Agent(
            role="市场监控专家",
            goal="高效收集股票实时行情、资金流向等核心市场数据，避免重复调用",
            backstory="我是一名高效的市场监控专家，专门负责收集最核心的实时市场数据。我只使用必要的工具，确保数据获取的效率和准确性。",
            tools=self.core_market_tools,  # 只使用核心市场工具
            verbose=True,
            allow_delegation=False,
            max_iter=3,  # 限制最大迭代次数
            llm=self._get_agent_llm('market_monitor')  # 添加LLM配置
        )
    
    @agent
    def fundamental_analyst(self) -> Agent:
        """基本面分析专家Agent - 专注财务数据分析"""
        return Agent(
            role="基本面分析专家",
            goal="高效分析股票的基本面情况，优先使用统一数据收集工具",
            backstory="我是一名高效的基本面分析师，专门使用统一数据工具快速获取财务数据，避免重复调用。我能够从财务数据中挖掘出有价值的投资线索。",
            tools=self.unified_tools + self.financial_tools,  # 优先使用统一工具
            verbose=True,
            allow_delegation=False,
            max_iter=4,  # 限制迭代次数
            llm=self._get_agent_llm('fundamental_analyst')  # 添加LLM配置
        )
    
    @agent
    def technical_analyst(self) -> Agent:
        """技术分析专家Agent - 专注技术指标分析"""
        return Agent(
            role="技术分析专家",
            goal="高效分析技术指标，优先使用统一数据中的技术数据",
            backstory="我是一名高效的技术分析师，专门使用统一数据工具获取技术指标，避免重复计算。我能够快速判断股票的技术面强弱。",
            tools=self.unified_tools + self.technical_tools,  # 优先使用统一工具
            verbose=True,
            allow_delegation=False,
            max_iter=4,  # 限制迭代次数
            llm=self._get_agent_llm('technical_analyst')  # 添加LLM配置
        )
    
    @agent
    def risk_manager(self) -> Agent:
        """风险管理专家Agent - 专注风险评估"""
        return Agent(
            role="风险管理专家",
            goal="高效评估投资风险，优先使用统一数据中的风险数据",
            backstory="我是一名高效的风险管理师，专门使用统一数据工具快速获取风险评估数据。我能够帮助投资者有效控制风险。",
            tools=self.unified_tools + self.risk_tools,  # 优先使用统一工具
            verbose=True,
            allow_delegation=False,
            max_iter=4,  # 限制迭代次数
            llm=self._get_agent_llm('risk_manager')  # 添加LLM配置
        )
    
    @agent
    def strategy_developer(self) -> Agent:
        """策略制定专家Agent - 综合策略制定"""
        return Agent(
            role="策略制定专家",
            goal="高效制定投资策略，优先使用已有分析结果",
            backstory="我是一名高效的投资策略专家，专门整合其他Agent的分析结果，制定可执行的投资策略。我避免重复调用工具。",
            tools=self.unified_tools + self.auxiliary_tools,  # 仅使用统一工具和辅助工具
            verbose=True,
            allow_delegation=False,
            max_iter=5,  # 限制迭代次数
            llm=self._get_agent_llm('strategy_developer')  # 添加LLM配置
        )
    
    @agent
    def investment_advisor(self) -> Agent:
        """投资决策专家Agent - 最终决策制定"""
        return Agent(
            role="投资决策专家",
            goal="基于所有分析结果做出最终决策，避免重复数据获取",
            backstory="我是一名高效的投资决策专家，专门综合其他Agent的分析结果，做出最终的投资建议。我不重复调用数据工具。",
            tools=self.notification_tools + self.auxiliary_tools,  # 仅使用通知和辅助工具
            verbose=True,
            allow_delegation=False,
            max_iter=3,  # 限制迭代次数
            llm=self._get_agent_llm('investment_advisor')  # 添加LLM配置
        )
    
    @task
    def market_monitoring_task(self) -> Task:
        """市场监控任务"""
        return Task(
            description="实时监控指定股票的价格变动和市场动态，获取最新的股价、成交量、北向资金流入等关键信息。使用当前真实时间和准确的数据源。",
            expected_output="详细的市场数据报告，包括股票基本信息、价格变动、成交情况和市场情绪。",
            agent=self.market_monitor()
        )
    
    @task
    def fundamental_analysis_task(self) -> Task:
        """基本面分析任务"""
        return Task(
            description="深入分析股票的基本面情况，包括财务指标、盈利能力、成长性、偿债能力等。使用真实的财务数据和行业比较。",
            expected_output="全面的基本面分析报告，包括财务健康状况、估值水平和投资价值评估。",
            agent=self.fundamental_analyst(),
            context=[self.market_monitoring_task()]
        )
    
    @task
    def technical_analysis_task(self) -> Task:
        """技术分析任务"""
        return Task(
            description="运用技术指标和图表分析，评估股票的技术面强弱，预测价格走势和关键支撑位、压力位。",
            expected_output="技术分析报告，包括技术指标解读、趋势判断和买卖信号。",
            agent=self.technical_analyst(),
            context=[self.market_monitoring_task()]
        )
    
    @task
    def risk_assessment_task(self) -> Task:
        """风险评估任务"""
        return Task(
            description="全面评估投资风险，包括市场风险、信用风险、流动性风险等，提供风险控制建议。",
            expected_output="风险评估报告，包括风险等级、可能损失和风险缓释措施。",
            agent=self.risk_manager(),
            context=[self.market_monitoring_task(), self.fundamental_analysis_task()]
        )
    
    @task
    def strategy_development_task(self) -> Task:
        """策略制定任务"""
        return Task(
            description="综合市场监控、基本面分析、技术分析和风险评估结果，制定个性化的投资策略。",
            expected_output="投资策略报告，包括具体的买入、持有和卖出建议。",
            agent=self.strategy_developer(),
            context=[
                self.market_monitoring_task(),
                self.fundamental_analysis_task(), 
                self.technical_analysis_task(),
                self.risk_assessment_task()
            ]
        )
    
    @task
    def investment_decision_task(self) -> Task:
        """投资决策任务"""
        return Task(
            description="基于所有前置分析结果，做出最终的投资决策，并提供具体的操作指导。",
            expected_output="最终投资决策报告，包括明确的投资建议、目标价位和止损策略。",
            agent=self.investment_advisor(),
            context=[
                self.market_monitoring_task(),
                self.fundamental_analysis_task(),
                self.technical_analysis_task(), 
                self.risk_assessment_task(),
                self.strategy_development_task()
            ]
        )
    
    @crew
    def crew(self) -> Crew:
        """创建A股投资决策Crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            max_execution_time=get_timeout_seconds('portfolio_manager'),  # 🔥 优先使用portfolio_manager的超时设置
            step_callback=self._step_callback if hasattr(self, '_step_callback') else None
        )
    
    def _step_callback(self, step):
        """步骤回调函数，用于监控执行进度"""
        try:
            if hasattr(step, 'agent') and hasattr(step, 'task'):
                logger.info(f"[CREW] Agent {step.agent.role} 正在执行任务: {step.task.description[:50]}...")
        except Exception as e:
            logger.debug(f"[CREW] 步骤回调错误: {e}")
    
    def analyze_stock(self, stock_code: str, **kwargs) -> dict:
        """
        分析指定股票
        
        Args:
            stock_code: 股票代码
            **kwargs: 其他参数
            
        Returns:
            分析结果字典
        """
        try:
            logger.info(f"[ANALYSIS] 开始分析股票: {stock_code}")
            
            # 准备输入数据
            inputs = {
                'stock_code': stock_code,
                'current_date': datetime.now().strftime('%Y-%m-%d'),
                **kwargs
            }
            
            # 执行分析
            result = self.crew().kickoff(inputs=inputs)
            
            logger.info(f"[ANALYSIS] 股票 {stock_code} 分析完成")
            return result
            
        except Exception as e:
            logger.error(f"[ANALYSIS] 股票分析失败: {e}")
            raise


    def print_tool_usage_stats(self):
        """打印工具使用统计信息"""
        try:
            stats = self.tool_limiter.get_statistics()
            print("\n" + "="*60)
            print("📊 工具调用统计信息")
            print("="*60)

            print(f"总调用次数: {stats['total_calls']}")
            print(f"成功率: {stats['success_rate']:.1f}%")
            print(f"平均耗时: {stats['average_duration']:.2f}秒")

            if stats['calls_by_agent']:
                print("\n📈 各Agent调用统计:")
                for agent, data in stats['calls_by_agent'].items():
                    success_rate = (data['success'] / data['count'] * 100) if data['count'] > 0 else 0
                    avg_duration = (data['duration'] / data['count']) if data['count'] > 0 else 0
                    print(f"  {agent}: {data['count']}次调用, 成功率{success_rate:.1f}%, 平均{avg_duration:.2f}秒")

            if stats['calls_by_tool']:
                print("\n🔧 各工具调用统计:")
                for tool, data in stats['calls_by_tool'].items():
                    success_rate = (data['success'] / data['count'] * 100) if data['count'] > 0 else 0
                    print(f"  {tool}: {data['count']}次调用, 成功率{success_rate:.1f}%")

            # 显示优化建议
            suggestions = self.tool_limiter.get_optimization_suggestions()
            if suggestions:
                print("\n💡 优化建议:")
                for i, suggestion in enumerate(suggestions, 1):
                    print(f"  {i}. {suggestion}")

            print("="*60)
        except Exception as e:
            print(f"⚠️ 无法获取工具使用统计: {str(e)}")


# 为了向后兼容，创建别名
AShareInvestmentCrew = AShareInvestmentCrew
