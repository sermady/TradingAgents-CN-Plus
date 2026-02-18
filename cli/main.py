# -*- coding: utf-8 -*-
"""
TradingAgents CLI - 多智能体大语言模型金融交易框架主入口
Multi-Agent LLM Financial Trading Framework CLI Entry Point

此文件为 CLI 主入口，所有实现已拆分到子模块：
- cli/buffer.py - 消息缓冲区管理
- cli/ui.py - UI 组件和布局
- cli/selections.py - 用户选择函数
- cli/analysis.py - 分析运行和报告
- cli/commands.py - Typer 命令

向后兼容说明：
所有原有导入路径保持不变，此模块导出所有公共API
"""

# 标准库导入

# 第三方库导入
from dotenv import load_dotenv
from rich.console import Console

# 加载环境变量
load_dotenv()

# 从子模块导入所有公共API，保持向后兼容
from cli.buffer import MessageBuffer, DEFAULT_MESSAGE_BUFFER_SIZE
from cli.ui import (
    CLIUserInterface,
    setup_cli_logging,
    create_layout,
    update_display,
    ui,
)

# 设置CLI日志配置
setup_cli_logging()

# 全局对象
console = Console()
message_buffer = MessageBuffer()

# 导出公共接口
__all__ = [
    # 主类和函数
    "CLIUserInterface",
    "MessageBuffer",
    "setup_cli_logging",
    "create_layout",
    "update_display",
    # 全局实例
    "ui",
    "console",
    "message_buffer",
    # 常量
    "DEFAULT_MESSAGE_BUFFER_SIZE",
]

# 注意：实际的Typer命令将在后续步骤中从 cli/commands.py 导入
# 此文件仅作为模块入口点
