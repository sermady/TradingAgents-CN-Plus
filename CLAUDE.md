# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working on TradingAgents-CN.

## Quick Links

- **完整开发规范**: [SKILLS.md](./skills/SKILLS.md)
- **README**: [README.md](./README.md)
- **pytest配置**: [pytest.ini](./pytest.ini)

## Core Rules

### 1. Always use Chinese
**注意**: 请使用中文回答用户的所有问题和交流。

### 2. File Creation Rules
See **skills/SKILLS.md > Section 2** for complete file location and naming rules.

### 3. Encoding Standards
See **skills/SKILLS.md > Section 3** for encoding requirements.

### 4. Testing Standards
See **skills/SKILLS.md > Section 4** for testing patterns and pytest markers.

### 5. Data Sources
See **skills/SKILLS.md > Section 5** for data source development guidelines.

### 6. Git Conventions
See **skills/SKILLS.md > Section 6** for commit message format.

## Development Commands

```bash
# Backend (FastAPI)
python -m app

# Frontend (Vue 3)
cd frontend && npm run dev

# Docker Deployment
scripts\docker\start_docker_services.bat

# Run Tests
python -m pytest tests/unit/ -v

# Data Import
python scripts/import/import_a_stocks_unified.py --data-source baostock
```

## Architecture Overview

TradingAgents-CN = FastAPI + Vue 3 + MongoDB/Redis + LangGraph Multi-Agent System

**Data Sources**: Tushare → Baostock → AkShare (auto-fallback)

**Multi-Agent System**:
- Analysts: Market, News, Social, Fundamentals, China
- Researchers: Bull/Bear (debate mechanism)
- Risk Management: Aggressive/Conservative/Neutral
- Trader: Final trading decision

See **skills/SKILLS.md > Section 1** for detailed architecture diagrams.

## License Information

| Component | License | Commercial Use |
|-----------|---------|----------------|
| `tradingagents/` | Apache 2.0 | Free with attribution |
| `app/` | Proprietary | Contact: hsliup@163.com |
| `frontend/` | Proprietary | Contact: hsliup@163.com |

**Personal/Learning Use**: All functionality can be used freely.

## Known Issues & Debugging Guide

### 🟢 实时行情数据源分离 (2026-01-29)

**修改目标**: 分析股票时优先从 MongoDB 读取历史数据，实时行情时直接调用外部 API

**修改内容**:
1. **`tradingagents/dataflows/data_source_manager.py:1441-1560`**
   - 重构 `get_realtime_quote()` 方法，移除 MongoDB 备选逻辑
   - 实现 `get_tushare_realtime_quote()` 方法，使用 Tushare Sina 接口获取实时行情
   - 新增 `_update_price_cache()` 辅助方法

**新的数据获取策略**:
```
历史数据: MongoDB → Tushare → AKShare → BaoStock (缓存优先)
实时行情: AKShare → Tushare → None (只使用外部API)
```

**实时行情优先级**:
1. **AKShare** (新浪/东方财富) - 秒级实时数据，优先尝试
2. **Tushare** (新浪财经) - 无需高级权限，自动降级
3. **None** - 所有外部API失败时返回 None，不使用 MongoDB 缓存

**测试验证**:
```bash
# 验证实时行情只使用外部API
python test_realtime_quote.py
# 预期输出: source: tushare_sina_realtime 或 source: sina_realtime
```

---

### 🔴 分析日期传递 Bug (已修复)

**问题现象**: 分析师使用系统时间而非前端指定的分析日期（如 2024年 vs 2026-01-29）

**根本原因**: 日期传递链断裂
```
前端 → propagate() → state["trade_date"] ✅
                     ↓
              Toolkit._config ❌ (未同步)
                     ↓
              工具函数 Fallback → datetime.now()
```

**涉及文件**:
- `tradingagents/graph/trading_graph.py:988-993`
- `tradingagents/graph/propagation.py:30`

**修复方案**: 在 `propagate()` 开头同步日期到全局配置
```python
from tradingagents.agents.utils.agent_utils import Toolkit
Toolkit._config["trade_date"] = str(trade_date)
Toolkit._config["analysis_date"] = str(trade_date)
```

**预防措施**:
1. 所有涉及日期的工具函数，优先从 `Toolkit._config` 获取
2. Fallback 逻辑应先检查 `Toolkit._config` 再使用 `datetime.now()`
3. 新增工具时需验证日期传递链完整性

