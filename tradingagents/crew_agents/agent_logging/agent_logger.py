# -*- coding: utf-8 -*-
"""
增强型Agent间通信日志系统
提供详细的Agent执行过程、任务传递、数据流向的日志打印功能
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from functools import wraps
from dataclasses import dataclass, asdict
from pathlib import Path
import inspect

# 颜色输出支持
try:
    from colorama import Fore, Back, Style, init
    init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    # 定义空的颜色类
    class DummyColor:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
    Fore = Back = Style = DummyColor()

# 设置UTF-8编码
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

@dataclass
class AgentLogEntry:
    """Agent日志条目"""
    timestamp: str
    agent_name: str
    task_name: str
    action_type: str  # START, PROGRESS, COMPLETE, ERROR, COMMUNICATION
    message: str
    data: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    memory_usage: Optional[int] = None
    token_usage: Optional[Dict[str, int]] = None
    error_details: Optional[str] = None

@dataclass
class TaskFlowEntry:
    """任务流转日志条目"""
    timestamp: str
    from_agent: str
    to_agent: str
    task_name: str
    data_summary: str
    data_size: int
    flow_type: str  # INPUT, OUTPUT, CONTEXT_PASSING

class AgentLogger:
    """增强型Agent日志器"""
    
    def __init__(self, log_dir: str = "logs", enable_file_logging: bool = True, 
                 enable_console: bool = True, log_level: str = "INFO"):
        self.log_dir = Path(log_dir)
        self.enable_file_logging = enable_file_logging
        self.enable_console = enable_console
        self.log_level = log_level
        
        # 创建日志目录
        if self.enable_file_logging:
            self.log_dir.mkdir(exist_ok=True)
        
        # 当前会话信息
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_start_time = time.time()
        
        # 日志存储
        self.agent_logs: List[AgentLogEntry] = []
        self.task_flows: List[TaskFlowEntry] = []
        
        # 当前执行状态
        self.current_executions: Dict[str, Dict[str, Any]] = {}
        
        # 统计信息
        self.agent_stats: Dict[str, Dict[str, Any]] = {}
        
        try:
            print(f"{Fore.CYAN}[SYSTEM] Agent日志系统已启动 - 会话ID: {self.session_id}{Style.RESET_ALL}")
        except UnicodeEncodeError:
            print(f"{Fore.CYAN}Agent Logging System Started - Session ID: {self.session_id}{Style.RESET_ALL}")
    
    def _get_color_by_agent(self, agent_name: str) -> str:
        """根据Agent名称获取专属颜色"""
        if not COLORAMA_AVAILABLE:
            return ""
        
        color_map = {
            'market_monitor': Fore.GREEN,
            'financial_analyst': Fore.BLUE,
            'technical_analyst': Fore.MAGENTA,
            'risk_manager': Fore.RED,
            'strategy_analyst': Fore.YELLOW,
            'portfolio_manager': Fore.CYAN
        }
        return color_map.get(agent_name, Fore.WHITE)
    
    def _format_timestamp(self) -> str:
        """格式化时间戳"""
        return datetime.now().strftime('%H:%M:%S.%f')[:-3]
    
    def _format_data_summary(self, data: Any) -> str:
        """格式化数据摘要"""
        if data is None:
            return "无数据"
        
        if isinstance(data, dict):
            keys = list(data.keys())[:5]  # 只显示前5个键
            summary = f"Dict({len(data)}键): {keys}"
            if len(data) > 5:
                summary += "..."
            return summary
        elif isinstance(data, list):
            return f"List({len(data)}项)"
        elif isinstance(data, str):
            return f"String({len(data)}字符): {data[:50]}..." if len(data) > 50 else f"String: {data}"
        else:
            return f"{type(data).__name__}: {str(data)[:50]}"
    
    def _calculate_data_size(self, data: Any) -> int:
        """计算数据大小（字节）"""
        try:
            return len(json.dumps(data, ensure_ascii=False)) if data else 0
        except:
            return len(str(data)) if data else 0
    
    def log_agent_start(self, agent_name: str, task_name: str, inputs: Dict[str, Any] = None):
        """记录Agent开始执行"""
        timestamp = self._format_timestamp()
        color = self._get_color_by_agent(agent_name)
        
        # 记录开始时间
        execution_key = f"{agent_name}_{task_name}"
        self.current_executions[execution_key] = {
            'start_time': time.time(),
            'agent_name': agent_name,
            'task_name': task_name
        }
        
        # 创建日志条目
        log_entry = AgentLogEntry(
            timestamp=timestamp,
            agent_name=agent_name,
            task_name=task_name,
            action_type="START",
            message=f"开始执行任务",
            data=inputs
        )
        self.agent_logs.append(log_entry)
        
        # 控制台输出
        if self.enable_console:
            input_summary = self._format_data_summary(inputs) if inputs else "无输入数据"
            print(f"{color}[START] [{timestamp}] {agent_name.upper()} 开始执行 -> {task_name}")
            print(f"{color}   [INPUT] 输入数据: {input_summary}{Style.RESET_ALL}")
            if inputs:
                print(f"{color}   [DETAIL] 详细输入: {json.dumps(inputs, ensure_ascii=False, indent=2)[:200]}...{Style.RESET_ALL}")
    
    def log_agent_progress(self, agent_name: str, task_name: str, message: str, 
                          progress_data: Dict[str, Any] = None):
        """记录Agent执行进度"""
        timestamp = self._format_timestamp()
        color = self._get_color_by_agent(agent_name)
        
        log_entry = AgentLogEntry(
            timestamp=timestamp,
            agent_name=agent_name,
            task_name=task_name,
            action_type="PROGRESS",
            message=message,
            data=progress_data
        )
        self.agent_logs.append(log_entry)
        
        if self.enable_console:
            print(f"{color}[PROGRESS] [{timestamp}] {agent_name.upper()} 进度更新 -> {message}{Style.RESET_ALL}")
            if progress_data:
                print(f"{color}   [DATA] 进度数据: {self._format_data_summary(progress_data)}{Style.RESET_ALL}")
    
    def log_agent_complete(self, agent_name: str, task_name: str, outputs: Dict[str, Any] = None,
                          success: bool = True):
        """记录Agent完成执行"""
        timestamp = self._format_timestamp()
        color = self._get_color_by_agent(agent_name)
        
        # 计算执行时间
        execution_key = f"{agent_name}_{task_name}"
        execution_time = None
        if execution_key in self.current_executions:
            start_time = self.current_executions[execution_key]['start_time']
            execution_time = time.time() - start_time
            del self.current_executions[execution_key]
        
        # 更新统计信息
        if agent_name not in self.agent_stats:
            self.agent_stats[agent_name] = {'total_tasks': 0, 'total_time': 0.0, 'success_count': 0}
        
        self.agent_stats[agent_name]['total_tasks'] += 1
        if execution_time:
            self.agent_stats[agent_name]['total_time'] += execution_time
        if success:
            self.agent_stats[agent_name]['success_count'] += 1
        
        # 创建日志条目
        log_entry = AgentLogEntry(
            timestamp=timestamp,
            agent_name=agent_name,
            task_name=task_name,
            action_type="COMPLETE",
            message="任务执行完成" if success else "任务执行失败",
            data=outputs,
            execution_time=execution_time
        )
        self.agent_logs.append(log_entry)
        
        # 控制台输出
        if self.enable_console:
            status_icon = "[SUCCESS]" if success else "[FAILED]"
            time_str = f"({execution_time:.2f}s)" if execution_time else ""
            output_summary = self._format_data_summary(outputs) if outputs else "无输出数据"
            
            print(f"{color}{status_icon} [{timestamp}] {agent_name.upper()} 任务完成 {time_str}")
            print(f"{color}   [OUTPUT] 输出数据: {output_summary}{Style.RESET_ALL}")
            if outputs:
                print(f"{color}   [DETAIL] 详细输出: {json.dumps(outputs, ensure_ascii=False, indent=2)[:200]}...{Style.RESET_ALL}")
    
    def log_agent_error(self, agent_name: str, task_name: str, error: Exception, 
                       context: Dict[str, Any] = None):
        """记录Agent执行错误"""
        timestamp = self._format_timestamp()
        
        log_entry = AgentLogEntry(
            timestamp=timestamp,
            agent_name=agent_name,
            task_name=task_name,
            action_type="ERROR",
            message=f"执行错误: {str(error)}",
            data=context,
            error_details=f"{type(error).__name__}: {str(error)}"
        )
        self.agent_logs.append(log_entry)
        
        if self.enable_console:
            print(f"{Fore.RED}[FAILED] [{timestamp}] {agent_name.upper()} 执行错误")
            print(f"{Fore.RED}   [ERROR] 错误信息: {str(error)}")
            print(f"{Fore.RED}   [INFO] 错误类型: {type(error).__name__}{Style.RESET_ALL}")
            if context:
                print(f"{Fore.RED}   [DETAIL] 上下文: {self._format_data_summary(context)}{Style.RESET_ALL}")
    
    def log_task_flow(self, from_agent: str, to_agent: str, task_name: str, 
                     data: Any, flow_type: str = "OUTPUT"):
        """记录任务间数据流转"""
        timestamp = self._format_timestamp()
        data_summary = self._format_data_summary(data)
        data_size = self._calculate_data_size(data)
        
        flow_entry = TaskFlowEntry(
            timestamp=timestamp,
            from_agent=from_agent,
            to_agent=to_agent,
            task_name=task_name,
            data_summary=data_summary,
            data_size=data_size,
            flow_type=flow_type
        )
        self.task_flows.append(flow_entry)
        
        if self.enable_console:
            from_color = self._get_color_by_agent(from_agent)
            to_color = self._get_color_by_agent(to_agent)
            size_str = f"({data_size}字节)" if data_size > 0 else ""
            
            print(f"{from_color}{from_agent.upper()}{Style.RESET_ALL} "
                  f"→ {to_color}{to_agent.upper()}{Style.RESET_ALL} "
                  f"📦 {task_name} {size_str}")
            print(f"   [DATA] 数据内容: {data_summary}")
    
    def log_communication(self, sender_agent: str, receiver_agent: str, 
                         message_type: str, content: str, data: Dict[str, Any] = None):
        """记录Agent间通信"""
        timestamp = self._format_timestamp()
        
        log_entry = AgentLogEntry(
            timestamp=timestamp,
            agent_name=sender_agent,
            task_name=f"COMMUNICATION_TO_{receiver_agent}",
            action_type="COMMUNICATION",
            message=f"{message_type}: {content}",
            data=data
        )
        self.agent_logs.append(log_entry)
        
        if self.enable_console:
            sender_color = self._get_color_by_agent(sender_agent)
            receiver_color = self._get_color_by_agent(receiver_agent)
            
            print(f"{sender_color}{sender_agent.upper()}{Style.RESET_ALL} "
                  f"💬 {receiver_color}{receiver_agent.upper()}{Style.RESET_ALL}")
            print(f"   📨 {message_type}: {content}")
            if data:
                print(f"   [INFO] 附加数据: {self._format_data_summary(data)}")
    
    def log_tool_call(self, agent_name: str, tool_name: str, tool_input: Dict[str, Any] = None,
                     context: str = "工具调用"):
        """记录工具调用 - 根据环境变量控制是否记录"""
        if not os.getenv('LOG_TOOL_REQUESTS', 'true').lower() == 'true':
            return
            
        timestamp = self._format_timestamp()
        
        log_entry = AgentLogEntry(
            timestamp=timestamp,
            agent_name=agent_name,
            task_name=f"TOOL_CALL_{tool_name}",
            action_type="TOOL_CALL",
            message=f"调用工具: {tool_name}",
            data={'tool_input': tool_input, 'context': context}
        )
        self.agent_logs.append(log_entry)
        
        if self.enable_console:
            color = self._get_color_by_agent(agent_name)
            input_summary = self._format_data_summary(tool_input) if tool_input else "无输入参数"
            
            print(f"{color}[TOOL] [{timestamp}] {agent_name.upper()} → {tool_name.upper()}")
            print(f"{color}   [INPUT] 调用参数: {input_summary}")
            print(f"{color}   📍 调用上下文: {context}{Style.RESET_ALL}")
    
    def log_tool_response(self, agent_name: str, tool_name: str, tool_output: Any = None,
                         execution_time: float = None, success: bool = True, error: Exception = None):
        """记录工具响应 - 根据环境变量控制是否记录"""
        if not os.getenv('LOG_TOOL_RESPONSES', 'true').lower() == 'true':
            return
            
        timestamp = self._format_timestamp()
        
        log_entry = AgentLogEntry(
            timestamp=timestamp,
            agent_name=agent_name,
            task_name=f"TOOL_RESPONSE_{tool_name}",
            action_type="TOOL_RESPONSE",
            message=f"工具响应: {tool_name}" + (" (成功)" if success else " (失败)"),
            data={'tool_output': tool_output, 'success': success},
            execution_time=execution_time,
            error_details=str(error) if error else None
        )
        self.agent_logs.append(log_entry)
        
        if self.enable_console:
            color = self._get_color_by_agent(agent_name)
            status_icon = "[SUCCESS]" if success else "[FAILED]"
            time_str = f"({execution_time:.2f}s)" if execution_time else ""
            output_summary = self._format_data_summary(tool_output) if tool_output else "无返回数据"
            
            print(f"{color}{status_icon} [{timestamp}] {tool_name.upper()} → {agent_name.upper()} {time_str}")
            print(f"{color}   [OUTPUT] 返回数据: {output_summary}")
            if error:
                print(f"{color}   [FAILED] 错误信息: {str(error)}")
            if os.getenv('LOG_SHOW_DATA_DETAILS', 'false').lower() == 'true' and tool_output:
                print(f"{color}   [DETAIL] 详细数据: {json.dumps(tool_output, ensure_ascii=False, indent=2)[:300]}...{Style.RESET_ALL}")
    
    def log_api_request(self, agent_name: str, api_name: str, method: str, url: str,
                       headers: Dict[str, str] = None, params: Dict[str, Any] = None,
                       body: Any = None, context: str = "API请求"):
        """记录API请求 - 根据环境变量控制是否记录"""
        if not os.getenv('LOG_API_CALLS', 'true').lower() == 'true':
            return
            
        timestamp = self._format_timestamp()
        
        # 脱敏处理：隐藏敏感信息
        safe_headers = {}
        if headers:
            for key, value in headers.items():
                if any(sensitive in key.lower() for sensitive in ['key', 'token', 'auth', 'password']):
                    safe_headers[key] = f"***{value[-4:]}" if len(value) > 4 else "***"
                else:
                    safe_headers[key] = value
        
        log_entry = AgentLogEntry(
            timestamp=timestamp,
            agent_name=agent_name,
            task_name=f"API_REQUEST_{api_name}",
            action_type="API_REQUEST",
            message=f"API请求: {method.upper()} {api_name}",
            data={
                'method': method,
                'url': url[:100] + "..." if len(url) > 100 else url,  # 截断长URL
                'headers': safe_headers,
                'params': params,
                'body_size': len(str(body)) if body else 0,
                'context': context
            }
        )
        self.agent_logs.append(log_entry)
        
        if self.enable_console:
            color = self._get_color_by_agent(agent_name)
            
            print(f"{color}🌐 [{timestamp}] {agent_name.upper()} → API调用")
            print(f"{color}   🔗 {method.upper()} {api_name}")
            print(f"{color}   📍 URL: {url[:80]}{'...' if len(url) > 80 else ''}")
            if params:
                print(f"{color}   [INFO] 参数: {self._format_data_summary(params)}")
            print(f"{color}   📍 上下文: {context}{Style.RESET_ALL}")
    
    def log_api_response(self, agent_name: str, api_name: str, status_code: int = None,
                        response_data: Any = None, execution_time: float = None,
                        success: bool = True, error: Exception = None):
        """记录API响应 - 根据环境变量控制是否记录"""
        if not os.getenv('LOG_API_CALLS', 'true').lower() == 'true':
            return
            
        timestamp = self._format_timestamp()
        
        log_entry = AgentLogEntry(
            timestamp=timestamp,
            agent_name=agent_name,
            task_name=f"API_RESPONSE_{api_name}",
            action_type="API_RESPONSE",
            message=f"API响应: {api_name}" + (f" ({status_code})" if status_code else "") + (" (成功)" if success else " (失败)"),
            data={
                'status_code': status_code,
                'response_size': len(str(response_data)) if response_data else 0,
                'success': success
            },
            execution_time=execution_time,
            error_details=str(error) if error else None
        )
        self.agent_logs.append(log_entry)
        
        if self.enable_console:
            color = self._get_color_by_agent(agent_name)
            status_icon = "[SUCCESS]" if success else "[FAILED]"
            time_str = f"({execution_time:.2f}s)" if execution_time else ""
            status_str = f"[{status_code}]" if status_code else ""
            data_size = len(str(response_data)) if response_data else 0
            
            print(f"{color}{status_icon} [{timestamp}] API响应 → {agent_name.upper()} {time_str}")
            print(f"{color}   [DATA] 状态: {api_name} {status_str}")
            print(f"{color}   📦 数据大小: {data_size}字节")
            if error:
                print(f"{color}   [FAILED] 错误信息: {str(error)}")
            if os.getenv('LOG_SHOW_DATA_DETAILS', 'false').lower() == 'true' and response_data:
                print(f"{color}   [DETAIL] 响应数据: {json.dumps(response_data, ensure_ascii=False, indent=2)[:300]}...{Style.RESET_ALL}")
    
    def log_progress_with_percentage(self, agent_name: str, task_name: str, message: str, 
                                   percentage: float = None, current_step: int = None, 
                                   total_steps: int = None, progress_data: Dict[str, Any] = None):
        """记录带百分比的实时进度显示"""
        timestamp = self._format_timestamp()
        color = self._get_color_by_agent(agent_name)
        
        # 计算百分比
        if percentage is None and current_step is not None and total_steps is not None:
            percentage = (current_step / total_steps) * 100
        
        # 创建日志条目
        log_entry = AgentLogEntry(
            timestamp=timestamp,
            agent_name=agent_name,
            task_name=task_name,
            action_type="PROGRESS_DETAILED",
            message=message,
            data={
                'percentage': percentage,
                'current_step': current_step,
                'total_steps': total_steps,
                'progress_data': progress_data
            }
        )
        self.agent_logs.append(log_entry)
        
        # 实时控制台显示
        if self.enable_console:
            # 创建进度条
            progress_bar = ""
            if percentage is not None:
                bar_length = 20
                filled_length = int(bar_length * percentage // 100)
                progress_bar = f"[{'█' * filled_length}{'░' * (bar_length - filled_length)}] {percentage:.1f}%"
            elif current_step is not None and total_steps is not None:
                progress_bar = f"[{current_step}/{total_steps}]"
            
            print(f"{color}[DATA] [{timestamp}] {agent_name.upper()} 进度: {message}")
            if progress_bar:
                print(f"{color}   {progress_bar}")
            if progress_data and os.getenv('LOG_SHOW_DATA_DETAILS', 'false').lower() == 'true':
                print(f"{color}   [INFO] 详细进度: {self._format_data_summary(progress_data)}{Style.RESET_ALL}")
    
    def log_performance_metrics(self, agent_name: str, task_name: str, execution_time: float = None,
                              memory_usage: int = None, cpu_usage: float = None, 
                              additional_metrics: Dict[str, Any] = None):
        """记录性能指标 - 根据环境变量控制是否记录"""
        if not (os.getenv('LOG_EXECUTION_TIME', 'true').lower() == 'true' or 
                os.getenv('LOG_MEMORY_USAGE', 'true').lower() == 'true'):
            return
            
        timestamp = self._format_timestamp()
        color = self._get_color_by_agent(agent_name)
        
        # 尝试获取当前内存使用情况
        if memory_usage is None:
            try:
                import psutil
                process = psutil.Process()
                memory_usage = process.memory_info().rss  # 物理内存使用，字节
            except ImportError:
                memory_usage = None
        
        log_entry = AgentLogEntry(
            timestamp=timestamp,
            agent_name=agent_name,
            task_name=task_name,
            action_type="PERFORMANCE_METRICS",
            message="性能指标更新",
            execution_time=execution_time,
            memory_usage=memory_usage,
            data={'cpu_usage': cpu_usage, 'additional_metrics': additional_metrics}
        )
        self.agent_logs.append(log_entry)
        
        if self.enable_console:
            print(f"{color}[METRICS] [{timestamp}] {agent_name.upper()} 性能指标:")
            if execution_time and os.getenv('LOG_EXECUTION_TIME', 'true').lower() == 'true':
                print(f"{color}   ⏱️  执行时间: {execution_time:.2f}秒")
            if memory_usage and os.getenv('LOG_MEMORY_USAGE', 'true').lower() == 'true':
                memory_mb = memory_usage / (1024 * 1024)
                print(f"{color}   💾 内存使用: {memory_mb:.1f}MB")
            if cpu_usage is not None:
                print(f"{color}   🖥️  CPU使用: {cpu_usage:.1f}%")
            if additional_metrics:
                for key, value in additional_metrics.items():
                    print(f"{color}   [DATA] {key}: {value}")
            print(Style.RESET_ALL)
    
    def log_retry_attempt(self, agent_name: str, task_name: str, attempt_number: int, 
                         max_attempts: int, error: Exception = None, delay_seconds: float = None,
                         retry_reason: str = None):
        """记录重试尝试 - 根据环境变量控制是否记录"""
        if not os.getenv('LOG_RETRY_ATTEMPTS', 'true').lower() == 'true':
            return
            
        timestamp = self._format_timestamp()
        color = self._get_color_by_agent(agent_name)
        
        log_entry = AgentLogEntry(
            timestamp=timestamp,
            agent_name=agent_name,
            task_name=task_name,
            action_type="RETRY_ATTEMPT",
            message=f"重试尝试 {attempt_number}/{max_attempts}" + (f": {retry_reason}" if retry_reason else ""),
            data={
                'attempt_number': attempt_number,
                'max_attempts': max_attempts,
                'delay_seconds': delay_seconds,
                'retry_reason': retry_reason
            },
            error_details=str(error) if error else None
        )
        self.agent_logs.append(log_entry)
        
        if self.enable_console:
            retry_icon = "[RETRY]" if attempt_number < max_attempts else "[WARNING]"
            print(f"{color}{retry_icon} [{timestamp}] {agent_name.upper()} 重试 {attempt_number}/{max_attempts}")
            if retry_reason:
                print(f"{color}   [DETAIL] 重试原因: {retry_reason}")
            if error:
                print(f"{color}   [FAILED] 错误: {str(error)[:100]}...")
            if delay_seconds:
                print(f"{color}   ⏳ 延迟: {delay_seconds}秒后重试")
            print(Style.RESET_ALL)
    
    def log_enhanced_error(self, agent_name: str, task_name: str, error: Exception,
                         context: Dict[str, Any] = None, stack_trace: str = None,
                         recovery_suggestion: str = None, error_category: str = None):
        """记录增强的错误详情 - 根据环境变量控制详细程度"""
        timestamp = self._format_timestamp()
        color = Fore.RED
        
        # 获取堆栈跟踪
        if stack_trace is None and os.getenv('LOG_ERROR_DETAILS', 'true').lower() == 'true':
            import traceback
            stack_trace = traceback.format_exc()
        
        log_entry = AgentLogEntry(
            timestamp=timestamp,
            agent_name=agent_name,
            task_name=task_name,
            action_type="ENHANCED_ERROR",
            message=f"详细错误报告: {str(error)}",
            data={
                'context': context,
                'error_category': error_category,
                'recovery_suggestion': recovery_suggestion,
                'stack_trace': stack_trace[:1000] if stack_trace else None  # 截断长堆栈跟踪
            },
            error_details=f"{type(error).__name__}: {str(error)}"
        )
        self.agent_logs.append(log_entry)
        
        if self.enable_console:
            print(f"{color}💥 [{timestamp}] {agent_name.upper()} 详细错误报告")
            print(f"{color}   🏷️  错误类型: {type(error).__name__}")
            print(f"{color}   📝 错误信息: {str(error)}")
            if error_category:
                print(f"{color}   🏪 错误类别: {error_category}")
            if context:
                print(f"{color}   [INFO] 错误上下文: {self._format_data_summary(context)}")
            if recovery_suggestion:
                print(f"{color}   💡 恢复建议: {recovery_suggestion}")
            if stack_trace and os.getenv('LOG_ERROR_DETAILS', 'true').lower() == 'true':
                print(f"{color}   📚 堆栈跟踪:")
                for line in stack_trace.split('\n')[:10]:  # 只显示前10行
                    if line.strip():
                        print(f"{color}     {line}")
            print(Style.RESET_ALL)
    
    def log_real_time_status(self, agent_name: str, task_name: str, status: str,
                           elapsed_time: float = None, estimated_remaining: float = None,
                           current_action: str = None):
        """记录实时状态更新 - 用于长时间运行的任务"""
        if not self.enable_console:
            return
            
        timestamp = self._format_timestamp()
        color = self._get_color_by_agent(agent_name)
        
        # 创建状态指示器
        status_icons = {
            'running': '[RETRY]',
            'waiting': '⏳',
            'processing': '⚙️',
            'connecting': '🔗',
            'downloading': '⬇️',
            'uploading': '⬆️',
            'analyzing': '[DETAIL]',
            'complete': '[SUCCESS]',
            'error': '[FAILED]'
        }
        
        status_icon = status_icons.get(status.lower(), '[DATA]')
        
        # 构建状态行
        status_line = f"{color}{status_icon} [{timestamp}] {agent_name.upper()} - {status.upper()}"
        
        if current_action:
            status_line += f" → {current_action}"
        
        if elapsed_time is not None:
            status_line += f" ({elapsed_time:.1f}s"
            if estimated_remaining is not None:
                status_line += f", ~{estimated_remaining:.1f}s剩余"
            status_line += ")"
        
        print(f"{status_line}{Style.RESET_ALL}")
    
    def print_session_summary(self):
        """打印会话总结"""
        session_duration = time.time() - self.session_start_time
        total_tasks = len(self.agent_logs)
        total_flows = len(self.task_flows)
        
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"[DATA] Agent执行会话总结 - 会话ID: {self.session_id}")
        print(f"{'='*60}{Style.RESET_ALL}")
        
        print(f"{Fore.WHITE}⏱️  会话时长: {session_duration:.2f}秒")
        print(f"[INFO] 总任务数: {total_tasks}")
        print(f"[RETRY] 数据流转: {total_flows}次{Style.RESET_ALL}")
        
        # Agent统计
        print(f"\n{Fore.YELLOW}🤖 Agent执行统计:{Style.RESET_ALL}")
        for agent_name, stats in self.agent_stats.items():
            color = self._get_color_by_agent(agent_name)
            success_rate = (stats['success_count'] / stats['total_tasks'] * 100) if stats['total_tasks'] > 0 else 0
            avg_time = (stats['total_time'] / stats['total_tasks']) if stats['total_tasks'] > 0 else 0
            
            print(f"{color}  {agent_name.upper()}:")
            print(f"    [DATA] 任务数量: {stats['total_tasks']}")
            print(f"    [SUCCESS] 成功率: {success_rate:.1f}%")
            print(f"    ⏱️  平均耗时: {avg_time:.2f}s")
            print(f"    🕒 总耗时: {stats['total_time']:.2f}s{Style.RESET_ALL}")
        
        # 任务流转统计
        if self.task_flows:
            print(f"\n{Fore.MAGENTA}[RETRY] 数据流转分析:{Style.RESET_ALL}")
            flow_stats = {}
            for flow in self.task_flows:
                key = f"{flow.from_agent} → {flow.to_agent}"
                if key not in flow_stats:
                    flow_stats[key] = {'count': 0, 'total_size': 0}
                flow_stats[key]['count'] += 1
                flow_stats[key]['total_size'] += flow.data_size
            
            for flow_path, stats in flow_stats.items():
                print(f"  {flow_path}: {stats['count']}次, {stats['total_size']}字节")
    
    def save_logs_to_file(self):
        """保存日志到文件"""
        if not self.enable_file_logging:
            return
        
        # 保存Agent日志
        agent_log_file = self.log_dir / f"agent_logs_{self.session_id}.json"
        with open(agent_log_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(log) for log in self.agent_logs], f, 
                     ensure_ascii=False, indent=2)
        
        # 保存任务流转日志
        flow_log_file = self.log_dir / f"task_flows_{self.session_id}.json"
        with open(flow_log_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(flow) for flow in self.task_flows], f, 
                     ensure_ascii=False, indent=2)
        
        # 保存会话统计
        stats_file = self.log_dir / f"session_stats_{self.session_id}.json"
        session_stats = {
            'session_id': self.session_id,
            'session_duration': time.time() - self.session_start_time,
            'total_logs': len(self.agent_logs),
            'total_flows': len(self.task_flows),
            'agent_stats': self.agent_stats
        }
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(session_stats, f, ensure_ascii=False, indent=2)
        
        print(f"{Fore.GREEN}💾 日志已保存到 {self.log_dir} 目录{Style.RESET_ALL}")


# 全局日志器实例
_global_agent_logger: Optional[AgentLogger] = None

def get_agent_logger() -> AgentLogger:
    """获取全局Agent日志器"""
    global _global_agent_logger
    if _global_agent_logger is None:
        _global_agent_logger = AgentLogger()
    return _global_agent_logger

def initialize_agent_logger(log_dir: str = "logs", enable_console: bool = True, 
                           enable_file_logging: bool = True, log_level: str = "INFO") -> AgentLogger:
    """初始化Agent日志器"""
    global _global_agent_logger
    _global_agent_logger = AgentLogger(
        log_dir=log_dir, 
        enable_console=enable_console,
        enable_file_logging=enable_file_logging,
        log_level=log_level
    )
    return _global_agent_logger

# 装饰器函数
def log_agent_execution(agent_name: str = None):
    """Agent执行日志装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_agent_logger()
            
            # 推断Agent名称
            nonlocal agent_name
            if agent_name is None:
                if hasattr(func, '__self__'):
                    agent_name = func.__self__.__class__.__name__
                else:
                    agent_name = func.__name__
            
            task_name = func.__name__
            
            try:
                # 记录开始
                logger.log_agent_start(agent_name, task_name, kwargs)
                
                # 执行函数
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # 记录完成
                logger.log_agent_complete(agent_name, task_name, 
                                        {'result': str(result)[:200]} if result else None)
                
                return result
                
            except Exception as e:
                # 记录错误
                logger.log_agent_error(agent_name, task_name, e, 
                                     {'args': str(args)[:200], 'kwargs': str(kwargs)[:200]})
                raise
        
        return wrapper
    return decorator

# 上下文管理器
class AgentExecutionContext:
    """Agent执行上下文管理器"""
    
    def __init__(self, agent_name: str, task_name: str, inputs: Dict[str, Any] = None):
        self.agent_name = agent_name
        self.task_name = task_name
        self.inputs = inputs
        self.logger = get_agent_logger()
    
    def __enter__(self):
        self.logger.log_agent_start(self.agent_name, self.task_name, self.inputs)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.logger.log_agent_complete(self.agent_name, self.task_name)
        else:
            self.logger.log_agent_error(self.agent_name, self.task_name, exc_val)
        return False
    
    def log_progress(self, message: str, data: Dict[str, Any] = None):
        """记录进度"""
        self.logger.log_agent_progress(self.agent_name, self.task_name, message, data)
    
    def log_communication(self, receiver_agent: str, message_type: str, content: str, 
                         data: Dict[str, Any] = None):
        """记录通信"""
        self.logger.log_communication(self.agent_name, receiver_agent, message_type, content, data)