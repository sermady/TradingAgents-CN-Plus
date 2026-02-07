# -*- coding: utf-8 -*-
"""
技术指标测试配置

避免模块导入时的副作用
"""
import os
import sys

# 设置测试环境变量
os.environ["TESTING"] = "true"
os.environ["MONGODB_URI"] = "mongodb://localhost:27017/tradingagents_test"

# 抑制日志输出
import logging
logging.disable(logging.CRITICAL)

# 确保项目根目录在 Python 路径中
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
