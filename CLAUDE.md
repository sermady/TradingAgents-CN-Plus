# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TradingAgents-CN is a Chinese-enhanced multi-agent LLM financial trading decision framework. It provides complete A股/HK/美股 analysis capabilities with full Chinese localization. The project uses a FastAPI + Vue 3 architecture with MongoDB + Redis dual-database support.

**注意**: 请使用中文回答用户的所有问题和交流。

### Core Technology Stack

**Backend (FastAPI)**:
- FastAPI with Uvicorn server
- MongoDB for persistent storage
- Redis for caching
- LangGraph for multi-agent orchestration
- Multiple LLM provider support (OpenAI, Google AI, DashScope, DeepSeek, etc.)

**Frontend (Vue 3)**:
- Vue 3 + Vite
- Element Plus UI components
- Pinia state management
- TypeScript support

**Multi-Agent System**:
- Market Analyst, Social Media Analyst, News Analyst, Fundamentals Analyst
- Bull/Bear Researchers for debate mechanism
- Risk Management, Trading execution

### Data Sources

**China A-Stock** (three-source unified management with auto-fallback):
- Tushare (highest quality, requires token)
- Baostock (free, stable)
- AkShare (multi-source aggregation, fallback option)

**Hong Kong/US Stocks**:
- AkShare, Yahoo Finance, FinnHub

## Development Commands

### Running the Application

**Docker Deployment (Recommended)**:
```bash
# Windows
scripts\docker\start_docker_services.bat

# Linux/Mac
chmod +x scripts/docker/start_docker_services.sh && ./scripts/docker/start_docker_services.sh

# Smart start (auto-detects if build needed)
# Windows
powershell -ExecutionPolicy Bypass -File scripts\smart_start.ps1

# Linux/Mac
chmod +x scripts/smart_start.sh && ./scripts/smart_start.sh

# With management tools (Redis Commander, Mongo Express)
docker-compose --profile management up -d
```

**Local Development**:
```bash
# Backend (FastAPI)
python -m app
# or
python app/__main__.py

# Frontend (Vue 3 - development mode)
cd frontend
npm run dev

# Frontend (build for production)
cd frontend
npm run build

# Frontend (preview production build)
cd frontend
npm run preview
```

### Data Import

**Unified Data Importer (supports three data sources)**:
```bash
# Baostock (free, open source)
python scripts/import/import_a_stocks_unified.py --data-source baostock

# Tushare (requires token)
python scripts/import/import_a_stocks_unified.py --data-source tushare

# AkShare (original)
python scripts/import/import_a_stocks_unified.py --data-source akshare

# Mixed mode (auto-fallback: Tushare → Baostock → AkShare)
python scripts/import/import_a_stocks_unified.py --data-source mixed

# Auto-select best source
python scripts/import/import_a_stocks_unified.py --data-source auto

# Interactive selection
python scripts/import/import_a_stocks_unified.py --interactive

# Limited import for testing
python scripts/import/import_a_stocks_unified.py --data-source baostock --limit 10 --delay 1.0
```

### Testing and Validation

```bash
# Data source integration tests
python scripts/test/test_data_sources.py

# Import system tests
python scripts/test/test_import_system.py

# Performance benchmarking
python scripts/test/test_performance_benchmark.py

# System status check
python scripts/validation/check_system_status.py

# Data integrity validation
python scripts/validation/validate_data_integrity.py

# Health check
python scripts/maintenance/health_check.py

# Final status check
python scripts/maintenance/final_status_check.py
```

### Build and Dependencies

```bash
# Install all dependencies
pip install -e .

# Using uv (faster)
uv pip install -e .

# Frontend dependencies
cd frontend && npm install
```

## Architecture Overview

### Multi-Agent Graph System

The core analysis logic uses LangGraph to orchestrate multiple specialized agents:

**TradingGraph** (`tradingagents/graph/trading_graph.py`):
- Main orchestration layer using LangGraph
- Supports multiple LLM providers through unified interface
- Implements progressive analysis (1-5 levels of depth)
- Manages agent states and debate flow

**Agent Types**:
1. **Analysts** (`tradingagents/agents/analysts/`):
   - Market Analyst: Technical indicators and price trends
   - News Analyst: News sentiment analysis
   - Social Media Analyst: Social media sentiment
   - Fundamentals Analyst: Financial metrics (PE, PB, ROE, etc.)
   - China Market Analyst: A股 specific analysis

2. **Researchers** (`tradingagents/agents/researchers/`):
   - Bull Researcher: Bullish investment arguments
   - Bear Researcher: Bearish investment arguments
   - Debate mechanism for balanced decision-making

3. **Risk Management** (`tradingagents/agents/risk_mgmt/`):
   - Aggressive Debator, Conservative Debator, Neutral Debator
   - Risk assessment and position sizing

4. **Trader** (`tradingagents/agents/trader/`):
   - Final trading decision based on all inputs

5. **Managers** (`tradingagents/agents/managers/`):
   - Research Manager: Coordinates analysis workflow
   - Risk Manager: Manages risk assessment

**Agent Tools** (`tradingagents/agents/utils/agent_utils.py`):
- LangChain `@tool` decorator for function calling
- Available tools: `get_reddit_news`, `get_finnhub_news`, `get_economic_calendar`, etc.
- Tool logging via `log_tool_call` decorator
- Google tool handler for Gemini function calling

### Data Flow Architecture

**Data Source Management**:
- `tradingagents/dataflows/providers/base_provider.py`: Unified interface for all data sources
- `tradingagents/dataflows/providers/china/`: A股 data providers (Tushare, Baostock, AkShare)
- `tradingagents/dataflows/providers/hk/`: Hong Kong stock providers
- `tradingagents/dataflows/providers/us/`: US stock providers

**Multi-Source Fallback Strategy**:
```
Priority 1: Tushare (highest data quality)
Priority 2: Baostock (free, stable)
Priority 3: AkShare (fallback option)
```

**Data Source Adapters** (`app/services/data_sources/`):
- `manager.py`: `DataSourceManager` - unified data source interface
- `tushare_adapter.py`: Tushare adapter with permission detection
- `akshare_adapter.py`: AKShare adapter supporting multiple APIs (eastmoney, sina)
- Real-time quotes with automatic fallback
- Historical data with multi-source support

**Caching System**:
- MongoDB cache for persistent storage
- Redis cache for high-performance access
- File-based cache as fallback
- Adaptive cache selection based on availability

**Real-time Quotes System**:
- `app/services/quotes_ingestion_service.py`: Real-time quotes ingestion and backfill
- `app/services/quotes_service.py`: Quotes query and management
- `market_quotes` collection: MongoDB storage for real-time market data
- Auto-detects Tushare permission (free vs premium users)
- Rotation strategy: Tushare → AKShare Eastmoney → AKShare Sina
- Trading hours: 9:30-15:30 (with 30min post-close buffer)
- Auto-backfill from historical data on startup

**Price Cache System**:
- `tradingagents/utils/price_cache.py`: Unified price caching for analysts
- Ensures price consistency across all analysts in a report
- 5-minute TTL with automatic expiration

### LLM Adapter System

**LLM Provider Support** (`tradingagents/llm_adapters/`):
- OpenAI-compatible base adapter
- Google AI (Gemini) adapter
- DashScope (Alibaba Qwen) adapter
- DeepSeek adapter
- Custom OpenAI-compatible endpoint support

**Configuration Management**:
- Database-backed LLM provider configuration
- Runtime model selection
- Model capability management (vision, function calling, etc.)
- Token usage tracking

### FastAPI Backend Structure

**Main Application** (`app/main.py`):
- FastAPI app initialization
- CORS and middleware setup
- Router registration
- Lifespan management (startup/shutdown)
- Background task scheduling

**Core Components**:
- `app/core/`: Configuration, database, logging
- `app/routers/`: API route handlers (30+ modules)
- `app/services/`: Business logic services
- `app/models/`: Pydantic models
- `app/schemas/`: Request/response schemas
- `app/middleware/`: Custom middleware (auth, logging, rate limiting)

**Key API Routes** (`app/routers/`):
- `analysis.py`: Stock analysis endpoints
- `auth_db.py`: Authentication endpoints
- `stocks.py`: Stock data queries
- `screening.py`: Stock screening
- `favorites.py`: User favorites
- `reports.py`: Analysis reports
- `queue.py`: Task queue management (legacy, use `/tasks`)
- `sse.py`: Server-Sent Events for real-time updates
- `notifications.py`: Notification management
- `scheduler.py`: Scheduled task management
- `config.py`: Runtime configuration
- `health.py`: Health check endpoint

**Key Services**:
- Analysis Service: Multi-agent analysis orchestration
- Database Service: MongoDB operations
- Cache Service: Redis caching layer
- Config Service: Runtime configuration management
- Auth Service: JWT-based authentication
- Notification Service: SSE + WebSocket notifications
- Progress Manager: Analysis progress tracking (app/services/progress_manager.py)
- Billing Service: Token usage and cost calculation (app/services/billing_service.py)

### Vue 3 Frontend Structure

**Main Entry** (`frontend/src/main.ts`):
- Vue app initialization with Pinia
- Element Plus UI library (Chinese locale)
- Router setup
- Global components registration

**Key Modules**:
- `api/`: HTTP API clients (auto-generated types)
- `components/`: Reusable Vue components
- `stores/`: Pinia state management (`app.ts`, `auth.ts`, `notifications.ts`)
- `types/`: TypeScript type definitions
- `utils/`: Utility functions
- `router/`: Vue Router configuration with NProgress

**Key Features**:
- Authentication with JWT tokens
- Real-time notifications via SSE
- Analysis progress tracking
- Multi-language support (Chinese optimized)
- Responsive design with Element Plus

**Main Routes**:
- `/dashboard`: Dashboard home
- `/analysis`: Single/Batch analysis
- `/screening`: Stock screening
- `/favorites`: User favorites
- `/tasks`: Task center (previously `/queue`)
- `/reports`: Analysis reports
- `/settings`: System settings
- `/learning`: Learning center (public)
- `/about`: About page (public)

## File Creation Rules

**IMPORTANT**: Never create files in the project root directory unless explicitly allowed!

| File Type | Location | Pattern | Example |
|-----------|----------|---------|---------|
| Data import scripts | `scripts/import/` | `import_<function>.py` | `import_realtime_data.py` |
| Unit tests | `tests/unit/` | `test_<feature>.py` | `test_trading_logic.py` |
| Integration tests | `tests/integration/` | `test_<feature>_integration.py` | `test_api_analysis.py` |
| Validation scripts | `scripts/validation/` | `validate_<target>.py` | `validate_model_accuracy.py` |
| Maintenance scripts | `scripts/maintenance/` | `<action>_<object>.py` | `cleanup_old_data.py` |
| Database scripts | `scripts/database/` | `<operation>_<database>.py` | `migrate_mongodb.py` |
| Core business logic | `tradingagents/` | By module | `tradingagents/agents/new_agent.py` |
| Backend services | `app/services/` | `<service>_service.py` | `app/services/billing_service.py` |
| Backend API routes | `app/routers/` | `<feature>.py` | `app/routers/new_feature.py` |
| Frontend components | `frontend/src/components/` | `<ComponentName>.vue` | `StockAnalysis.vue` |
| Frontend API clients | `frontend/src/api/` | `<feature>.ts` | `newApi.ts` |
| Log files | `logs/` | `<module>_<date>.log` | `trading_2024-01-15.log` |
| Report documents | `docs/reports/` | `<type>_report_<date>.md` | `performance_20240115.md` |
| Service classes | `app/services/` | `<service>_service.py` | `progress_manager.py`, `billing_service.py` |
| Technical docs | `docs/` | `<topic>.md` | `docs/architecture/new_feature.md` |
| Analysis results | `results/` | `<type>_<code>_<date>/` | `results/analysis_000001_20240115/` |
| Config files | `config/` | `<module>.json/.yaml` | `config/trading_params.yaml` |
| Data files | `data/` | By type in subdirs | `data/stocks/` |
| Export files | `exports/` | `<content>_<date>.<format>` | `exports/portfolio_20240115.xlsx` |
| Temp files | `temp/` | `temp_<function>_<random>.ext` | `temp/test_data_abc123.json` |

**Allowed root files**: `main.py`, `start_web.py`, `pyproject.toml`, `requirements.txt`, `.env`, `.gitignore`, `docker-compose.yml`, `README.md`, `LICENSE`, `CHANGELOG.md`, `CLAUDE.md`, Dockerfiles

## Encoding Standards

**CRITICAL**: All Python files MUST use UTF-8 encoding and declare it at the top:

```python
# -*- coding: utf-8 -*-
```

**File Operations**:
```python
# ✅ Correct: Explicit UTF-8 encoding
with open('data.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# ✅ JSON files
import json
with open('config.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
```

**Network Requests**:
```python
import requests

# ✅ Correct: Force UTF-8 encoding
response = requests.get('http://api.example.com/data')
response.encoding = 'utf-8'
text = response.text
```

## Key Configuration

### Environment Variables (.env)

**Database Configuration**:
- `MONGODB_HOST`, `MONGODB_PORT`, `MONGODB_DATABASE`
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`

**LLM API Keys**:
- `DASHSCOPE_API_KEY`: Alibaba DashScope (Qwen models)
- `GOOGLE_API_KEY`: Google AI (Gemini models)
- `DEEPSEEK_API_KEY`: DeepSeek models
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`: OpenAI/Anthropic models

**Data Source Keys**:
- `TUSHARE_TOKEN`: Tushare data source (required for A股 data)
- `FINNHUB_API_KEY`: FinnHub for US stocks

**Server Configuration**:
- `HOST`, `PORT`, `DEBUG`: Server host, port, debug mode
- `ALLOWED_ORIGINS`: CORS allowed origins

**Quotes Ingestion**:
- `QUOTES_INGEST_ENABLED`: Enable real-time quotes ingestion
- `QUOTES_INGEST_INTERVAL_SECONDS`: Collection interval (default: 360s/6min)
- `QUOTES_ROTATION_ENABLED`: Enable API rotation (Tushare → AKShare)
- `QUOTES_TUSHARE_HOURLY_LIMIT`: Tushare hourly call limit (default: 2)
- `QUOTES_AUTO_DETECT_TUSHARE_PERMISSION`: Auto-detect Tushare permission level

**Tushare Configuration**:
- `TUSHARE_ENABLED`: Enable Tushare data source
- `TUSHARE_TIER`: Account tier (free/basic/standard/premium/vip)
- `TUSHARE_INIT_HISTORICAL_DAYS`: Initial historical data days (default: 365)
- `TUSHARE_INIT_AUTO_START`: Auto-initialize data on startup

**Proxy Configuration** (for accessing Chinese data sources):
- `HTTP_PROXY`, `HTTPS_PROXY`: Proxy settings
- `NO_PROXY`: Domains to bypass proxy (eastmoney.com, sina.com.cn, tushare.pro, etc.)

### Database Connection
- **MongoDB**: Used for persistent storage (stock data, analysis reports, user data)
- **Redis**: Used for high-performance caching and session management

### API Configuration
The FastAPI backend runs on:
- Default port: 8000
- API docs: http://localhost:8000/docs (when DEBUG=True)
- Health check: http://localhost:8000/api/health

The Vue 3 frontend runs on:
- Development: http://localhost:5173 (Vite dev server)
- Production: http://localhost:3000 (Nginx in Docker)

## Git Commit Convention

Follow semantic commit format:

```bash
# Feature addition
git commit -m "feat: add Baostock data source support"

# Bug fix
git commit -m "fix: resolve encoding issue in unified importer"

# Performance optimization
git commit -m "perf: optimize data source switching performance"

# Documentation
git commit -m "docs: update Baostock integration guide"

# Testing
git commit -m "test: add Baostock integration tests"

# Build
git commit -m "build: update dependency versions"

# Refactoring
git commit -m "refactor: restructure data flow architecture"
```

## Development Best Practices

### Code Quality
1. **UTF-8 Encoding**: All new files must use UTF-8 encoding
2. **Error Handling**: Implement comprehensive exception handling and logging
3. **Testing**: Write test scripts for new functionality
4. **Documentation**: Update relevant docs when changing code

### Testing Standards

**pytest 配置** (`pytest.ini`):
- 自动忽略 `tests/legacy/`, `tests/0.1.14/`, `scripts/test/` 目录
- 支持 asyncio 自动模式 (`asyncio_mode = auto`)
- 定义的测试标记: `unit`, `integration`, `slow`, `requires_auth`, `requires_db`

1. **Test Directory Structure**:
   - `tests/unit/` - Unit tests (fast, no external dependencies)
   - `tests/integration/` - Integration tests (requires database/API)
   - `tests/legacy/` - Legacy test scripts (ignored by pytest, for reference only)
   - `tests/debug/` - 临时调试脚本（调试完成后删除）

2. **Test File Naming**:
   - Unit tests: `test_<feature>.py`
   - Integration tests: `test_<feature>_integration.py`

3. **pytest Requirements**:
   - All tests must use `pytest` framework
   - Use `pytest.mark` decorators for marks (`@pytest.mark.unit`, `@pytest.mark.integration`)
   - Add `pytest.ini` configuration for proper test discovery
   - Avoid creating standalone test scripts outside `tests/` directory

4. **Forbidden Practices**:
   - ❌ Creating `test_*.py` in project root
   - ❌ Creating standalone test scripts without pytest structure
   - ❌ Creating `debug_*.py` or `*_fix.py` scripts anywhere in the project
   - ❌ Leaving debug scripts in project root or `tests/`
   - ❌ Mixing test scripts with production code

5. **Temporary Debugging**:
   - For temporary debugging, use `temp/` directory
   - Name files with `temp_<purpose>_<random>.ext` pattern
   - Delete immediately after debugging is complete
   - Never commit temporary debug files to repository

6. **Running Tests**:
   ```bash
   # Run all unit tests
   python -m pytest tests/unit/ -v

   # Run with coverage
   python -m pytest tests/unit/ --cov=tradingagents --cov-report=term-missing

   # Skip slow tests
   python -m pytest -m "not slow"

   # Run only integration tests
   python -m pytest -m integration

   # Run with verbose output
   python -m pytest -v --tb=short
   ```

### Data Source Development
1. **Unified Interface**: All data sources must implement `BaseStockDataProvider`
2. **Error Fallback**: Support automatic switching to backup data sources
3. **Caching Strategy**: Use MongoDB/Redis caching appropriately
4. **Performance Optimization**: Support batch processing and delay control

### Avoid Reinventing the Wheel
```python
# ✅ Correct: Extend existing framework
from tradingagents.dataflows.providers.base_provider import BaseStockDataProvider

class CustomProvider(BaseStockDataProvider):
    """Extend base provider functionality"""
    pass

# ❌ Wrong: Reimplement core functionality
class MyOwnDataProvider:  # Don't do this
    """Completely custom data provider"""
    pass
```

## Troubleshooting

### Common Issues

**Encoding Problems**:
```bash
# Check system encoding
python -c "import sys; print(f'System encoding: {sys.stdout.encoding}')"

# Check data source availability
python -c "from tradingagents.dataflows.providers.base_provider import get_data_source_manager; mgr = get_data_source_manager(); print(f'Available sources: {[s.value for s in mgr.available_sources]}')"
```

**Database Connection**:
```bash
# MongoDB connection check
python -c "import pymongo; client = pymongo.MongoClient('mongodb://localhost:27017/'); print('MongoDB OK') if client.admin.command('ping') else print('MongoDB Failed')"

# Redis connection check
python -c "import redis; r = redis.Redis(host='localhost', port=6379); print('Redis OK') if r.ping() else print('Redis Failed')"
```

### Log Locations
- Application logs: `logs/` directory
- Docker logs: `docker-compose logs -f [service]`
- Frontend dev server logs: Console output

## License Information

This project uses a **mixed license** model:

**Apache 2.0 (Open Source)**:
- Applies to all files except `app/` and `frontend/`
- Free for commercial use with attribution
- See LICENSE file for details

**Proprietary (Commercial License Required)**:
- `app/` (FastAPI backend)
- `frontend/` (Vue 3 frontend)
- Commercial use requires separate licensing
- Contact: hsliup@163.com

**Personal/Learning Use**: All functionality can be used freely
**Commercial Application**: Contact for proprietary component licensing
