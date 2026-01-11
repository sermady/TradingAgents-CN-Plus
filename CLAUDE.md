# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Run Commands

### Docker Deployment (Recommended)
```bash
# First time or after code changes
docker-compose up -d --build

# Daily startup (image exists)
docker-compose up -d

# Smart start (auto-detect if build needed)
# Windows
powershell -ExecutionPolicy Bypass -File scripts\smart_start.ps1
# Linux/Mac
./scripts/smart_start.sh
```

### Local Development
```bash
# Install dependencies
pip install -e .

# Start FastAPI backend
cd app && python main.py
# Or use uvicorn
uvicorn app.main:app --reload --port 8000

# Start Vue frontend
cd frontend && yarn install && yarn dev
```

### Testing
Tests are standalone scripts in `scripts/` directory:
```bash
python scripts/test_<feature>.py           # Run specific test
python scripts/check_<component>.py        # Check component status
python scripts/diagnose_<issue>.py         # Diagnose issues
```

## Architecture Overview

### Core Components

**Multi-Agent Trading Framework** (`tradingagents/`):
- `graph/trading_graph.py` - Main orchestration using LangGraph, coordinates all agents
- `agents/analysts/` - Market, fundamentals, news, social media analysts
- `agents/researchers/` - Bull/bear researchers for investment debate
- `agents/trader/` - Final trading decision maker
- `agents/risk_mgmt/` - Conservative/aggressive/neutral risk debaters

**FastAPI Backend** (`app/`):
- RESTful API with JWT authentication
- `routers/` - API endpoints for analysis, stocks, users, config
- `services/` - Business logic layer
- `worker/` - Background task processing

**Vue 3 Frontend** (`frontend/`):
- Element Plus UI framework
- `views/` - Page components
- `stores/` - Pinia state management
- `api/` - Backend API clients

### Data Flow

**LLM Providers** (`tradingagents/llm_adapters/`):
- Google AI (Gemini), DashScope (Qwen), DeepSeek, OpenAI, Anthropic
- Unified interface via `create_llm_by_provider()` in trading_graph.py

**Data Sources** (`tradingagents/dataflows/`):
- `providers/china/` - Tushare, AkShare, Baostock for A-shares
- `providers/us/` - FinnHub, Alpha Vantage, yfinance for US stocks
- `providers/hk/` - Hong Kong stock providers
- `data_source_manager.py` - Intelligent source switching with fallback

**Caching** (`tradingagents/dataflows/cache/`):
- MongoDB for persistent storage
- Redis for high-speed caching
- Adaptive multi-layer caching strategy

### Key Patterns

- **Debate Mechanism**: Bull vs bear researchers debate before trading decisions
- **Research Depth**: 1-5 levels from quick to comprehensive analysis
- **Automatic Fallback**: Data sources degrade gracefully (Tushare -> Baostock -> AkShare)
- **SSE + WebSocket**: Real-time progress tracking for long-running analyses

## Configuration

Environment variables in `.env`:
- LLM API keys: `GOOGLE_API_KEY`, `DASHSCOPE_API_KEY`, `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`
- Data sources: `TUSHARE_TOKEN`, `FINNHUB_API_KEY`
- Database: `MONGODB_URL`, `REDIS_URL`

## File Conventions

- Python encoding: Always use UTF-8 with `# -*- coding: utf-8 -*-` header
- File operations: Always specify `encoding='utf-8'`
- Scripts go in `scripts/` subdirectories, not project root
- Logs in `logs/`, results in `results/`, exports in `exports/`

## Multi-Agent Accuracy Improvements

### Debate Configuration
The multi-agent debate mechanism has been optimized for better decision quality:

```python
# tradingagents/default_config.py
"max_debate_rounds": 3,        # Bull vs Bear: 6 exchanges (was 1 round = 2 exchanges)
"max_risk_discuss_rounds": 2,  # Risk debate: 6 exchanges (was 1 round = 3 exchanges)
```

### Bug Fixes Applied
| Date | File | Issue | Fix |
|------|------|-------|-----|
| 2025-01-12 | `agents/managers/risk_manager.py:18` | Wrong report fetched | Changed `state["news_report"]` to `state["fundamentals_report"]` |
| 2025-01-12 | `default_config.py` | Insufficient debate rounds | Increased from 1 to 3 (bull/bear) and 1 to 2 (risk) |
| 2025-01-12 | `agents/trader/trader.py` | No target price validation | Added `validate_trading_decision()` function with checks for target price, currency, confidence |
| 2025-01-12 | `agents/analysts/fundamentals_analyst.py` | Tool call bypass | Fixed logic: only skip tool call when `has_tool_result=True`, not when only `has_analysis_content=True` |
| 2025-01-12 | Multiple agents | Insufficient memory retrieval | Increased `n_matches` from 2 to 5 in bull/bear researchers, research/risk managers, trader |
