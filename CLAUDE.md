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

### Multi-Agent Execution Flow

```
START
  |
  v
[Analyst Team] (4 agents, serial execution)
  |- Market Analyst - Technical indicators (MA, RSI, MACD, BOLL)
  |- Social Analyst - Sentiment analysis
  |- News Analyst - News interpretation
  '- Fundamentals Analyst - Financial data (with forced tool calls)
  |
  v
[Investment Debate Team] (3 rounds = 6 exchanges)
  |- Bull Researcher - Bullish arguments
  |- Bear Researcher - Bearish arguments
  '- Research Manager -> Investment plan
  |
  v
[Trading Decision]
  '- Trader -> Trading plan + Target price (validated)
  |
  v
[Risk Management Debate Team] (2 rounds = 6 exchanges)
  |- Risky Analyst - Aggressive risk assessment
  |- Safe Analyst - Conservative risk assessment
  |- Neutral Analyst - Neutral risk assessment
  '- Risk Manager -> Final decision
  |
  v
END (Complete report generated)
```

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

**LLM Provider Selection Guide**:
| Provider | Model | Cost | VPN Required | Best For |
|----------|-------|------|--------------|----------|
| DashScope | qwen-turbo | Low (CNY0.002/1K) | No | Daily use, China users |
| DeepSeek | deepseek-chat | Very Low (CNY0.0014/1K) | No | Cost optimization |
| Google AI | gemini-2.5-flash | Medium ($0.00025/1K) | Recommended | Speed + Quality balance |
| Google AI | gemini-2.5-pro | Higher ($0.00125/1K) | Recommended | Complex analysis |
| OpenAI | gpt-4o-mini | High ($0.0015/1K) | Required | International users |
| Anthropic | claude-3-sonnet | Medium | Required | Complex reasoning |
| Ollama | local models | Free | No | Privacy, offline use |

**Hybrid Mode Strategy**:
```python
# Quick analysis with cheap model
quick_think_llm = "qwen-turbo"  # Low cost, fast

# Deep decisions with powerful model
deep_think_llm = "gemini-2.5-pro"  # High quality, strong reasoning
```

**Data Sources** (`tradingagents/dataflows/`):
- `providers/china/` - Tushare, AkShare, Baostock for A-shares
- `providers/us/` - FinnHub, Alpha Vantage, yfinance for US stocks
- `providers/hk/` - Hong Kong stock providers
- `data_source_manager.py` - Intelligent source switching with fallback

**Data Source Priority**:
| Market | Priority Order | Notes |
|--------|---------------|-------|
| A-shares | MongoDB cache -> Tushare -> AkShare -> Baostock | Smart fallback |
| US stocks | yfinance -> Alpha Vantage -> Finnhub | By availability |
| HK stocks | AkShare -> Yahoo Finance -> Finnhub | Multi-source |

**Data Source Comparison**:
| Source | Cost | API Key | Quality | Stability |
|--------|------|---------|---------|-----------|
| Tushare | Points | Required | Best | High |
| AkShare | Free | Not required | Good | Medium |
| Baostock | Free | Not required | Good | High |
| yfinance | Free | Not required | Good | Medium |

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
| 2025-01-12 | `agents/analysts/fundamentals_analyst.py` | Complex monolithic function (692 lines) | Refactored: 2 -> 33 functions, main function 590 -> 88 lines (-85%), nesting 5 -> 3 levels |

### Key Design Highlights

**1. Forced Tool Call Mechanism** (fundamentals_analyst.py):
```python
# Prevents LLM from fabricating data - must have actual tool results
if has_tool_result:
    return use_existing_analysis()
# Force tool call to get real data
return execute_force_tool_call()
```

**2. Trading Decision Validation** (trader.py):
```python
def validate_trading_decision(content, currency_symbol, company_name):
    # Validates: recommendation, target price, currency, confidence, risk score
    # Rejects evasive responses like "cannot determine"
```

**3. Memory-Enhanced Learning**:
- All agents retrieve 5 historical memories for similar situations
- Enables learning from past mistakes and successes

### Critical Files Reference

| Category | File | Lines | Purpose |
|----------|------|-------|---------|
| Orchestration | `graph/trading_graph.py` | 1398 | Main LangGraph orchestration |
| Flow Control | `graph/conditional_logic.py` | 243 | Debate round conditions |
| Fundamentals | `agents/analysts/fundamentals_analyst.py` | 1158 | Refactored, 33 functions |
| Trading | `agents/trader/trader.py` | 227 | Decision + validation |
| Risk | `agents/managers/risk_manager.py` | 164 | Final decision maker |
| Data Sources | `dataflows/data_source_manager.py` | - | Smart source switching |
| Config | `default_config.py` | - | Debate rounds, LLM settings |
