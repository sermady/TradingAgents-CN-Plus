# -*- coding: utf-8 -*-
"""Agent 工具模块 - 向后兼容入口

该文件已重构，所有工具函数已拆分到 toolkit/ 子模块中。
为了保持向后兼容性，保留此文件作为入口点。

新结构：
- tradingagents/agents/utils/toolkit/
  - __init__.py       # 主入口，导出 Toolkit 类
  - base_toolkit.py   # Toolkit 门面类
  - news_tools.py     # 新闻获取工具
  - stock_data_tools.py  # 股票数据工具
  - technical_tools.py   # 技术指标工具
  - fundamentals_tools.py # 基本面数据工具
  - unified_tools.py     # 统一接口工具
- tradingagents/agents/utils/message_utils.py  # 消息清理工具

使用方式：
    from tradingagents.agents.utils.agent_utils import Toolkit, create_msg_delete
    # 或
    from tradingagents.agents.utils.toolkit import Toolkit
    from tradingagents.agents.utils.message_utils import create_msg_delete
"""

# 从新的子模块导入，保持向后兼容
from tradingagents.agents.utils.toolkit import Toolkit
from tradingagents.agents.utils.message_utils import create_msg_delete

__all__ = ["Toolkit", "create_msg_delete"]
