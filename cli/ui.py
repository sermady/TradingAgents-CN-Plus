# -*- coding: utf-8 -*-
"""CLI用户界面组件"""

import logging
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from rich.spinner import Spinner
from rich.markdown import Markdown

from tradingagents.utils.logging_manager import get_logger

# 常量定义
DEFAULT_MAX_TOOL_ARGS_LENGTH = 100
DEFAULT_MAX_CONTENT_LENGTH = 200
DEFAULT_MAX_DISPLAY_MESSAGES = 12
DEFAULT_API_KEY_DISPLAY_LENGTH = 12

# 初始化日志系统
logger = get_logger("cli")


def setup_cli_logging() -> None:
    """
    CLI模式下的日志配置：移除控制台输出，保持界面清爽
    Configure logging for CLI mode: remove console output to keep interface clean
    """
    from tradingagents.utils.logging_manager import get_logger_manager

    logger_manager = get_logger_manager()

    # 获取根日志器
    root_logger = logging.getLogger()

    # 移除所有控制台处理器，只保留文件日志
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and hasattr(handler, 'stream'):
            if handler.stream.name in ['<stderr>', '<stdout>']:
                root_logger.removeHandler(handler)

    # 同时移除tradingagents日志器的控制台处理器
    tradingagents_logger = logging.getLogger('tradingagents')
    for handler in tradingagents_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and hasattr(handler, 'stream'):
            if handler.stream.name in ['<stderr>', '<stdout>']:
                tradingagents_logger.removeHandler(handler)

    # 记录CLI启动日志（只写入文件）
    logger.debug("🚀 CLI模式启动，控制台日志已禁用，保持界面清爽")


class CLIUserInterface:
    """CLI用户界面管理器：处理用户显示和进度提示
    CLI User Interface Manager: handles user display and progress messages
    """

    def __init__(self):
        self.console = Console()
        self.logger = get_logger("cli")

    def show_user_message(self, message: str, style: str = "") -> None:
        """显示用户消息
        Display user message

        Args:
            message: 消息内容
            style: Rich 样式标签（可选）
        """
        if style:
            self.console.print(f"[{style}]{message}[/{style}]")
        else:
            self.console.print(message)

    def show_progress(self, message: str) -> None:
        """显示进度信息
        Display progress message

        Args:
            message: 进度消息
        """
        self.console.print(f"🔄 {message}")
        # 同时记录到日志文件
        self.logger.info(f"进度: {message}")

    def show_success(self, message: str) -> None:
        """显示成功信息
        Display success message

        Args:
            message: 成功消息
        """
        self.console.print(f"[green]✅ {message}[/green]")
        self.logger.info(f"成功: {message}")

    def show_error(self, message: str) -> None:
        """显示错误信息
        Display error message

        Args:
            message: 错误消息
        """
        self.console.print(f"[red]❌ {message}[/red]")
        self.logger.error(f"错误: {message}")

    def show_warning(self, message: str) -> None:
        """显示警告信息
        Display warning message

        Args:
            message: 警告消息
        """
        self.console.print(f"[yellow]⚠️ {message}[/yellow]")
        self.logger.warning(f"警告: {message}")

    def show_step_header(self, step_num: int, title: str) -> None:
        """显示步骤标题
        Display step header

        Args:
            step_num: 步骤编号
            title: 步骤标题
        """
        self.console.print(f"\n[bold cyan]步骤 {step_num}: {title}[/bold cyan]")
        self.console.print("─" * 60)

    def show_data_info(self, data_type: str, symbol: str, details: str = "") -> None:
        """显示数据获取信息
        Display data fetch information

        Args:
            data_type: 数据类型
            symbol: 股票代码
            details: 详细信息（可选）
        """
        if details:
            self.console.print(f"📊 {data_type}: {symbol} - {details}")
        else:
            self.console.print(f"📊 {data_type}: {symbol}")


def create_layout() -> Layout:
    """
    创建CLI界面的布局结构
    Create layout structure for CLI interface

    Returns:
        Layout: Rich Layout对象
    """
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main"),
        Layout(name="footer", size=3),
    )
    layout["main"].split_column(
        Layout(name="upper", ratio=3),
        Layout(name="analysis", ratio=5)
    )
    layout["upper"].split_row(
        Layout(name="progress", ratio=2),
        Layout(name="messages", ratio=3)
    )
    return layout


def update_display(layout: Layout, message_buffer, spinner_text: str = None) -> None:
    """
    更新CLI界面显示内容
    Update CLI interface display content

    Args:
        layout: Rich Layout对象
        message_buffer: MessageBuffer对象
        spinner_text: 可选的spinner文本
    """
    # Header with welcome message
    layout["header"].update(
        Panel(
            "[bold green]Welcome to TradingAgents CLI[/bold green]\n"
            "[dim]© [Tauric Research](https://github.com/TauricResearch)[/dim]",
            title="Welcome to TradingAgents",
            border_style="green",
            padding=(1, 2),
            expand=True,
        )
    )

    # Progress panel showing agent status
    progress_table = Table(
        show_header=True,
        header_style="bold magenta",
        show_footer=False,
        box=box.SIMPLE_HEAD,  # Use simple header with horizontal lines
        title=None,  # Remove redundant Progress title
        padding=(0, 2),  # Add horizontal padding
        expand=True,  # Make table expand to fill available space
    )
    progress_table.add_column("Team", style="cyan", justify="center", width=20)
    progress_table.add_column("Agent", style="green", justify="center", width=20)
    progress_table.add_column("Status", style="yellow", justify="center", width=20)

    # Group agents by team
    teams = {
        "Analyst Team": [
            "Market Analyst",
            "Social Analyst",
            "News Analyst",
            "Fundamentals Analyst",
        ],
        "Research Team": ["Bull Researcher", "Bear Researcher", "Research Manager"],
        "Trading Team": ["Trader"],
        "Risk Management": ["Risky Analyst", "Neutral Analyst", "Safe Analyst"],
        "Portfolio Management": ["Portfolio Manager"],
    }

    for team, agents in teams.items():
        # Add first agent with team name
        first_agent = agents[0]
        status = message_buffer.agent_status[first_agent]
        if status == "in_progress":
            spinner = Spinner(
                "dots", text="[blue]in_progress[/blue]", style="bold cyan"
            )
            status_cell = spinner
        else:
            status_color = {
                "pending": "yellow",
                "completed": "green",
                "error": "red",
            }.get(status, "white")
            status_cell = f"[{status_color}]{status}[/{status_color}]"
        progress_table.add_row(team, first_agent, status_cell)

        # Add remaining agents in team
        for agent in agents[1:]:
            status = message_buffer.agent_status[agent]
            if status == "in_progress":
                spinner = Spinner(
                    "dots", text="[blue]in_progress[/blue]", style="bold cyan"
                )
                status_cell = spinner
            else:
                status_color = {
                    "pending": "yellow",
                    "completed": "green",
                    "error": "red",
                }.get(status, "white")
                status_cell = f"[{status_color}]{status}[/{status_color}]"
            progress_table.add_row("", agent, status_cell)

        # Add horizontal line after each team
        progress_table.add_row("─" * 20, "─" * 20, "─" * 20, style="dim")

    layout["progress"].update(
        Panel(progress_table, title="Progress", border_style="cyan", padding=(1, 2))
    )

    # Messages panel showing recent messages and tool calls
    messages_table = Table(
        show_header=True,
        header_style="bold magenta",
        show_footer=False,
        expand=True,  # Make table expand to fill available space
        box=box.MINIMAL,  # Use minimal box style for a lighter look
        show_lines=True,  # Keep horizontal lines
        padding=(0, 1),  # Add some padding between columns
    )
    messages_table.add_column("Time", style="cyan", width=8, justify="center")
    messages_table.add_column("Type", style="green", width=10, justify="center")
    messages_table.add_column(
        "Content", style="white", no_wrap=False, ratio=1
    )  # Make content column expand

    # Combine tool calls and messages
    all_messages = []

    # Add tool calls
    for timestamp, tool_name, args in message_buffer.tool_calls:
        # Truncate tool call args if too long
        if isinstance(args, str) and len(args) > DEFAULT_MAX_TOOL_ARGS_LENGTH:
            args = args[:97] + "..."
        all_messages.append((timestamp, "Tool", f"{tool_name}: {args}"))

    # Add regular messages
    for timestamp, msg_type, content in message_buffer.messages:
        # Convert content to string if it's not already
        content_str = content
        if isinstance(content, list):
            # Handle list of content blocks (Anthropic format)
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get('type') == 'text':
                        text_parts.append(item.get('text', ''))
                    elif item.get('type') == 'tool_use':
                        text_parts.append(f"[Tool: {item.get('name', 'unknown')}]")
                else:
                    text_parts.append(str(item))
            content_str = ' '.join(text_parts)
        elif not isinstance(content_str, str):
            content_str = str(content)

        # Truncate message content if too long
        if len(content_str) > DEFAULT_MAX_CONTENT_LENGTH:
            content_str = content_str[:197] + "..."
        all_messages.append((timestamp, msg_type, content_str))

    # Sort by timestamp
    all_messages.sort(key=lambda x: x[0])

    # Calculate how many messages we can show based on available space
    # Start with a reasonable number and adjust based on content length
    max_messages = DEFAULT_MAX_DISPLAY_MESSAGES

    # Get last N messages that will fit in panel
    recent_messages = all_messages[-max_messages:]

    # Add messages to table
    for timestamp, msg_type, content in recent_messages:
        # Format content with word wrapping
        wrapped_content = Text(content, overflow="fold")
        messages_table.add_row(timestamp, msg_type, wrapped_content)

    if spinner_text:
        messages_table.add_row("", "Spinner", spinner_text)

    # Add a footer to indicate if messages were truncated
    if len(all_messages) > max_messages:
        messages_table.footer = (
            f"[dim]Showing last {max_messages} of {len(all_messages)} messages[/dim]"
        )

    layout["messages"].update(
        Panel(
            messages_table,
            title="Messages & Tools",
            border_style="blue",
            padding=(1, 2),
        )
    )

    # Analysis panel showing current report
    if message_buffer.current_report:
        layout["analysis"].update(
            Panel(
                Markdown(message_buffer.current_report),
                title="Current Report",
                border_style="green",
                padding=(1, 2),
            )
        )
    else:
        layout["analysis"].update(
            Panel(
                "[italic]Waiting for analysis report...[/italic]",
                title="Current Report",
                border_style="green",
                padding=(1, 2),
            )
        )

    # Footer with statistics
    tool_calls_count = len(message_buffer.tool_calls)
    llm_calls_count = sum(
        1 for _, msg_type, _ in message_buffer.messages if msg_type == "Reasoning"
    )
    reports_count = sum(
        1 for content in message_buffer.report_sections.values() if content is not None
    )

    stats_table = Table(show_header=False, box=None, padding=(0, 2), expand=True)
    stats_table.add_column("Stats", justify="center")
    stats_table.add_row(
        f"Tool Calls: {tool_calls_count} | LLM Calls: {llm_calls_count} | Generated Reports: {reports_count}"
    )

    layout["footer"].update(Panel(stats_table, border_style="grey50"))


# 创建全局UI管理器
ui = CLIUserInterface()
