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
