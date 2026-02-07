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

### Backend (FastAPI)

```bash
# Start backend server
python -m app

# Install dependencies
pip install -e .

# Using uv (faster)
uv pip install -e .
```

### Frontend (Vue 3)

```bash
cd frontend

# Development server
npm run dev

# Production build
npm run build

# Code linting
npm run lint

# Code formatting
npm run format

# Type checking
npm run type-check
```

### Docker Deployment

```bash
# Windows
scripts\docker\start_docker_services.bat

# Or using docker-compose directly
docker-compose up -d
```

### Testing

```bash
# Run all tests
python -m pytest

# Run unit tests only (fast, no external dependencies)
python -m pytest -m unit -v

# Run integration tests (requires database/API)
python -m pytest -m integration -v

# Run specific test file
python -m pytest tests/unit/test_data_manager.py -v

# Run single test
python -m pytest tests/unit/test_data_manager.py::TestDataManager::test_get_data -v

# Run with coverage
python -m pytest --cov=tradingagents --cov=app --cov-report=term-missing

# Run slow tests
python -m pytest -m slow -v

# Run tests requiring database
python -m pytest -m requires_db -v
```

### Code Quality

```bash
# Ruff linting (if configured)
ruff check .
ruff check . --fix

# Ruff formatting
ruff format .

# Black formatting
black .

# Import sorting
isort .
```

### Data Import

```bash
# Using Baostock (free)
python scripts/import/import_a_stocks_unified.py --data-source baostock

# Using Tushare (requires token)
python scripts/import/import_a_stocks_unified.py --data-source tushare

# Auto-select best available source
python scripts/import/import_a_stocks_unified.py --data-source auto
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
详细问题记录和调试指南已迁移至：**[skills/learned/known-issues.md](./skills/learned/known-issues.md)**

### 关键问题速查

| 问题 | 日期 | 状态 | 位置 |
|------|------|------|------|
| Tushare 每小时批量实时行情同步 | 2026-01-30 | 🟢 已实现 | `app/worker/tushare_sync_service.py` |
| 实时行情数据源分离 | 2026-01-29 | 🟢 已修复 | `data_source_manager.py:1441-1560` |
| 成交量单位统一为"手" | 2026-01-30 | 🔴 需清理 | 所有数据源适配器 |
| 分析日期传递 Bug | 2026-01-29 | 🔴 已修复 | `trading_graph.py:988-993` |
| 实时行情判断逻辑修复 | 2026-01-30 | 🔴 已修复 | `market_time.py:216` |

### 常见调试命令

```bash
# 检查 MongoDB 中的成交量数据
python -c "from app.core.database import get_database; db=get_database(); doc=db.historical_data.find_one({'symbol': '600765'}); print(f'Volume: {doc.get(\"volume\", 0):,.0f}')"

# 验证实时行情数据源
python test_realtime_quote.py
```

**查看完整问题列表和解决方案** → [skills/learned/known-issues.md](./skills/learned/known-issues.md)

---

## 系统架构深度解析

### 完整数据流概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户交互层 (Web/Frontend)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  单股分析页面 │  │  批量分析页面 │  │  分析历史页面 │  │  实时通知中心 │     │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API/WebSocket 层 (FastAPI)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Analysis API │  │  SSE Stream  │  │  WebSocket   │  │ Queue Service│     │
│  │  /api/analysis│  │ /api/stream  │  │  /api/ws/*   │  │ /api/queue   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         多智能体分析引擎 (LangGraph)                          │
│                                                                              │
│  ┌─────────────────┐    ┌─────────────────────────────────────────────────┐ │
│  │  Data Coordinator│───▶│         分析师团队 (并行执行)                     │ │
│  │    (数据协调器)   │    │  ┌─────────┐┌─────────┐┌─────────┐┌─────────┐ │ │
│  └─────────────────┘    │  │ Market  ││Social   ││  News   ││Fundamen-│ │ │
│                         │  │ Analyst ││Media    ││ Analyst ││tals     │ │ │
│  ┌─────────────────┐    │  │         ││Analyst  ││         ││Analyst  │ │ │
│  │  研究员辩论机制  │    │  └─────────┘└─────────┘└─────────┘└─────────┘ │ │
│  │ ┌─────┐ ┌─────┐ │    │           ┌─────────┐                           │ │
│  │ │Bull │↔│Bear │ │    │           │ China   │                           │ │
│  │ │Res. │ │Res. │ │    │           │ Market  │                           │ │
│  │ └─────┘ └─────┘ │    │           │ Analyst │                           │ │
│  │      ↓          │    │           └─────────┘                           │ │
│  │  Research Mgr   │    └─────────────────────────────────────────────────┘ │ │
│  └─────────────────┘                          │                             │ │
│           │                                   ▼                             │ │
│           ▼                    ┌─────────────────────────┐                  │ │
│  ┌─────────────────┐           │        Trader           │                  │ │
│  │  风险管理辩论    │           │    (交易员制定计划)      │                  │ │
│  │ ┌─────┐┌──────┐ │           └─────────────────────────┘                  │ │
│  │ │Risky││ Safe │ │                      │                                  │ │
│  │ │     ││      │ │                      ▼                                  │ │
│  │ └─────┘└──────┘ │           ┌─────────────────────────┐                  │ │
│  │ ┌─────────────┐ │           │    Risk Debate (3-way)  │                  │ │
│  │ │   Neutral   │ │           │  ┌─────┐┌──────┐┌──────┐│                  │ │
│  │ └─────────────┘ │           │  │Risky││ Safe ││Neutral│                  │ │
│  │        ↓        │           │  └─────┘└──────┘└──────┘│                  │ │
│  │   Risk Manager  │           └─────────────────────────┘                  │ │
│  └─────────────────┘                      │                                  │ │
│                                           ▼                                  │ │
│                              ┌─────────────────────────┐                     │ │
│                              │    Final Decision       │                     │ │
│                              │    (最终交易决策)        │                     │ │
│                              └─────────────────────────┘                     │ │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据层 (Data Layer)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   MongoDB    │  │    Redis     │  │  Tushare API │  │  AKShare API │     │
│  │  (持久化存储) │  │  (缓存/队列)  │  │  (数据源1)   │  │  (数据源2)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐                                                           │
│  │ BaoStock API │                                                           │
│  │  (数据源3)   │                                                           │
│  └──────────────┘                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 第一阶段：股票信息获取

#### 1. 数据源管理架构

**核心组件**：
| 组件 | 文件路径 | 职责 |
|------|----------|------|
| 数据源管理器 | `tradingagents/dataflows/data_source_manager.py` | 统一接口，智能降级 |
| Tushare提供器 | `tradingagents/dataflows/providers/china/tushare.py` | 高质量数据，需积分 |
| AKShare提供器 | `tradingagents/dataflows/providers/china/akshare.py` | 免费开源，爬虫获取 |
| BaoStock提供器 | `tradingagents/dataflows/providers/china/baostock.py` | 免费开源，数据稳定 |

#### 2. 数据源优先级与降级策略

```python
# tradingagents/dataflows/data_source_manager.py:106-160
# 默认优先级：Tushare > AKShare > BaoStock
env_priority = os.getenv(
    "HISTORICAL_DATA_SOURCE_PRIORITY", "tushare,akshare,baostock"
)
```

**优先级策略**：
1. **Tushare** - 数据质量最高，需要积分
2. **AKShare** - 免费开源，基于爬虫
3. **BaoStock** - 免费开源，数据稳定

#### 3. 实时行情获取逻辑

```python
# tradingagents/dataflows/data_source_manager.py:1453-1517
def get_realtime_quote(self, symbol: str) -> Optional[Dict]:
    """
    获取实时行情数据 - 只使用外部API，不使用MongoDB缓存
    """
```

**实时行情优先级**：
- AKShare 优先级: 1 (优先)
- Tushare 优先级: 2 (备选)

#### 4. 市场时间智能判断

```python
# tradingagents/utils/market_time.py:216-295
def should_use_realtime_quote(symbol, analysis_date, check_time):
    """
    智能判断是否使用实时行情
    - 历史日期（<今天）：绝对不使用实时行情
    - 今天 + 盘中：使用实时行情
    - 今天 + 盘前/盘后：不使用实时行情
    """
    if analysis_date < today:
        return False, "⚡ 历史分析，使用历史收盘价"

    if is_trading:
        return True, "⚡ 盘中分析，使用实时行情"
    elif "盘前" in status:
        return False, "⚡ 盘前分析，使用昨日收盘价"
    elif "盘后" in status:
        return False, "📊 盘后分析，使用今日收盘价"
```

**场景覆盖**：

| 分析日期 | 当前时间 | 是否使用实时行情 | 说明 |
|---------|---------|----------------|------|
| 2024-06-01 (历史) | 任意 | 否 | 使用历史数据 |
| 今天 | 08:00 (盘前) | 否 | 使用昨日收盘价 |
| 今天 | 10:00 (盘中) | 是 | 使用实时行情 |
| 今天 | 16:00 (盘后) | 否 | 使用今日收盘价 |

#### 5. 数据标准化

**成交量单位统一**：
- **统一标准**: 全部使用 **"手"** 单位（1手=100股）
- **成交额**: 全部使用 **"元"** 单位

```python
# tradingagents/dataflows/standardizers/data_standardizer.py:32-83
@staticmethod
def standardize_volume(volume: Any, unit: Optional[str] = None) -> Dict[str, Any]:
    """标准化成交量到"手"（2026-01-30统一单位）"""
    if unit == "shares":
        volume_in_lots = volume / DataStandardizer.SHARES_PER_LOT
```

---

### 第二阶段：多智能体分析

#### 1. 分析师团队

| 分析师 | 文件路径 | 职责 | 输出 |
|--------|----------|------|------|
| 市场分析师 | `tradingagents/agents/analysts/market_analyst.py` | 技术分析（MA/MACD/RSI/布林带） | `market_report` |
| 基本面分析师 | `tradingagents/agents/analysts/fundamentals_analyst.py` | 财务分析（PE/PB/ROE/现金流） | `fundamentals_report` |
| 新闻分析师 | `tradingagents/agents/analysts/news_analyst.py` | 消息面分析（新闻/政策/公告） | `news_report` |
| 中国市场分析师 | `tradingagents/agents/analysts/china_market_analyst.py` | A股特色（涨跌停/换手率/量比） | `china_market_report` |
| 社交媒体分析师 | `tradingagents/agents/analysts/social_media_analyst.py` | 情绪分析（散户情绪/热度） | `sentiment_report` |

**分析师提示词设计模式**：

```python
# 以市场分析师为例
system_message = f"""你是一位专业的股票技术分析师。
请基于以下**真实市场数据**对 {company_name} ({ticker}) 进行详细的技术分析。

=== 数据信息 ===
- 数据来源: {market_source}
- 数据日期: {current_date}（历史数据）
{metadata_info}

=== 市场数据 ===
{market_data}
================

**分析要求（必须严格遵守）：**
1. **数据来源**：必须严格基于上述提供的市场数据进行分析，绝对禁止编造数据。
2. **技术指标**：分析移动平均线（MA）、MACD、RSI、布林带等指标。
3. **成交量**：分析量价配合情况（成交量单位为"手"，1手=100股）。
4. **投资建议**：给出明确的买入/持有/卖出建议。
"""
```

#### 2. 研究员辩论机制

**辩论流程**：
```
Bull Researcher (看涨) ↔ Bear Researcher (看跌)
           ↓
    Research Manager (研究经理)
           ↓
      Investment Plan (投资计划)
```

**关键代码**：

```python
# tradingagents/graph/conditional_logic.py:202-243
def should_continue_debate(self, state: AgentState) -> str:
    """Determine if debate should continue."""
    current_count = state["investment_debate_state"]["count"]
    max_count = 2 * self.max_debate_rounds

    if current_count >= max_count:
        return "Research Manager"

    next_speaker = "Bear Researcher" if current_speaker.startswith("Bull") else "Bull Researcher"
    return next_speaker
```

**研究员职责**：

| 研究员 | 文件路径 | 职责 |
|--------|----------|------|
| 看涨研究员 | `tradingagents/agents/researchers/bull_researcher.py` | 构建看涨案例，反驳看跌论点 |
| 看跌研究员 | `tradingagents/agents/researchers/bear_researcher.py` | 构建看跌案例，反驳看涨论点 |
| 研究经理 | `tradingagents/agents/managers/research_manager.py` | 评估辩论，做出投资决策 |

#### 3. 交易员决策

**交易员职责**：
- 基于所有分析师报告和辩论结果
- 提供具体的投资建议（买入/持有/卖出）
- **强制要求**: 必须提供具体的目标价位
- 给出置信度和风险评分

```python
# tradingagents/agents/trader/trader.py:14-160
def extract_trading_decision(content: str, current_price: float = None) -> dict:
    result = {
        "recommendation": "未知",  # 买入/持有/卖出
        "target_price": None,
        "target_price_range": None,
        "confidence": None,  # 置信度
        "risk_score": None,  # 风险评分
        "current_price": None,
        "stop_loss": None,  # 止损位
        "position_suggestion": None,  # 仓位建议
        "time_horizon": None,  # 时间窗口
        "entry_strategy": None,  # 建仓策略
        "warnings": [],
    }
```

#### 4. 风险管理辩论

**三种风险分析师**：

| 类型 | 文件路径 | 职责 |
|------|----------|------|
| 激进分析师 | `tradingagents/agents/risk_mgmt/aggresive_debator.py` | 关注上涨空间和增长潜力 |
| 保守分析师 | `tradingagents/agents/risk_mgmt/conservative_debator.py` | 关注风险缓解和资产保护 |
| 中性分析师 | `tradingagents/agents/risk_mgmt/neutral_debator.py` | 提供平衡视角 |

**风险辩论流程**：
```
Trader (交易计划)
  ↓
Risky Analyst (激进) → Safe Analyst (保守) → Neutral Analyst (中性)
                          ↓
                   Risk Manager (最终决策)
                          ↓
              Final Trade Decision (最终交易决策)
```

---

### 第三阶段：工作流编排

#### 1. LangGraph 状态定义

```python
# tradingagents/agents/utils/agent_states.py
class AgentState(MessagesState):
    # 基础信息
    company_of_interest: str  # 股票代码
    trade_date: str  # 分析日期

    # 中央数据存储 (由DataCoordinator预取)
    market_data: str  # 原始市场数据
    financial_data: str  # 原始财务数据
    news_data: str  # 原始新闻数据
    sentiment_data: str  # 原始情绪数据

    # 分析师报告
    market_report: str
    fundamentals_report: str
    news_report: str
    china_market_report: str
    sentiment_report: str

    # 研究团队辩论状态
    investment_debate_state: InvestDebateState
    investment_plan: str  # 投资计划
    trader_investment_plan: str  # 交易员计划

    # 风险管理团队辩论状态
    risk_debate_state: RiskDebateState
    final_trade_decision: str  # 最终交易决策
```

#### 2. 完整工作流

```
START
  │
  ▼
┌─────────────────┐
│  Data Coordinator │  ← 预加载所有数据
│   (数据协调器)    │
└─────────────────┘
  │
  ├─────────────────┬─────────────────┬─────────────────┐
  ▼                 ▼                 ▼                 ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Market   │  │ Social   │  │ News     │  │Fundamentals│ │ China    │
│ Analyst  │  │ Analyst  │  │ Analyst  │  │ Analyst   │  │ Analyst  │
│ (并行)   │  │ (并行)   │  │ (并行)   │  │ (并行)    │  │ (并行)   │
└──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘
  │              │              │              │              │
  └──────────────┴──────────────┴──────────────┴──────────────┘
  │
  ▼
┌─────────────────┐     ┌─────────────────┐
│ Bull Researcher │ ↔️  │ Bear Researcher │
│  (多头观点)      │     │  (空头观点)      │
└─────────────────┘     └─────────────────┘
  │
  ▼
┌─────────────────┐
│ Research Manager│  ← 综合决策，生成投资计划
│  (研究经理)      │
└─────────────────┘
  │
  ▼
┌─────────────────┐
│     Trader      │  ← 制定交易计划
│   (交易员)      │
└─────────────────┘
  │
  ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Risky Analyst  │ ↔️  │  Safe Analyst   │ ↔️  │ Neutral Analyst │
│   (激进)        │     │   (保守)        │     │   (中性)        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
  │
  ▼
┌─────────────────┐
│   Risk Manager  │  ← 最终交易决策
│  (风险管理员)    │
└─────────────────┘
  │
  ▼
 END
```

#### 3. 主图执行流程

```python
# tradingagents/graph/trading_graph.py:967-1184
def propagate(self, company_name, trade_date, progress_callback=None, task_id=None):
    """Run the trading agents graph for a company on a specific date."""

    # 同步日期到全局配置
    if trade_date is not None:
        Toolkit._config["trade_date"] = str(trade_date)
        Toolkit._config["analysis_date"] = str(trade_date)

    # 创建初始状态
    init_agent_state = self.propagator.create_initial_state(company_name, trade_date)

    # 执行图工作流
    for chunk in self.graph.stream(init_agent_state, **args):
        # 记录节点执行时间
        for node_name in chunk.keys():
            if not node_name.startswith("__"):
                # 记录节点执行时间...

        # 发送进度更新
        if progress_callback:
            self._send_progress_update(chunk, progress_callback)

    # 处理最终决策
    decision = self.process_signal(final_state["final_trade_decision"], company_name)

    return final_state, decision
```

---

### 第四阶段：报告生成

#### 1. 报告生成器

**核心文件**：
| 文件 | 功能 |
|------|------|
| `tradingagents/templates/report_templates.py` | 统一报告模板定义 |
| `app/utils/report_exporter.py` | 后端报告导出工具 |
| `web/utils/report_exporter.py` | Web端报告导出工具 |

**支持的报告格式**：

| 格式 | 方法 | 依赖 |
|------|------|------|
| Markdown | `generate_markdown_report()` | 无 |
| Word | `generate_docx_report()` | pypandoc + pandoc |
| PDF | `generate_pdf_report()` | pdfkit + wkhtmltopdf |

#### 2. 报告验证系统

```python
# tradingagents/utils/report_validator.py:37-98
class ReportValidator:
    """报告一致性校验器"""

    REQUIRED_FIELDS = {
        "final_trade_decision": ["recommendation", "target_price", "confidence"],
        "fundamentals_report": ["pe_ratio", "current_price"],
        "technical_report": ["current_price", "volume"],
        "sentiment_report": ["sentiment_score"],
    }

    def validate_all_reports(self, reports: Dict[str, str], stock_code: str, company_name: str):
        # 1. 检查必填字段
        self._check_required_fields(reports)
        # 2. 检测投资建议矛盾
        self._check_recommendation_conflicts(reports)
        # 3. 检查价格数据一致性
        self._check_price_consistency(reports)
        # 4. 检查成交量数据一致性
        self._check_volume_consistency(reports)
```

#### 3. 最终决策结构

```python
{
    "recommendation": "买入",  # 买入/持有/卖出
    "target_price": 15.50,
    "target_price_range": "14.00-16.00",
    "confidence": 0.75,  # 0-1
    "risk_score": 0.6,   # 0-1，越高风险越大
    "current_price": 12.30,
    "stop_loss": 11.30,  # 止损位
    "position_suggestion": "中等仓位 (40-60%)",
    "time_horizon": "1-3个月",
    "entry_strategy": "分批建仓，首次30%，回调加仓",
    "warnings": ["宏观经济不确定性", "行业竞争加剧"]
}
```

---

### 第五阶段：Web界面与API

#### 1. 后端API

**核心端点**：
```python
# app/routers/analysis.py
POST   /api/analysis/single           # 提交单股分析任务
POST   /api/analysis/batch            # 提交批量分析任务
GET    /api/analysis/tasks/{id}/status # 获取任务状态
GET    /api/analysis/tasks/{id}/result # 获取分析结果
GET    /api/analysis/tasks            # 获取用户任务列表
POST   /api/analysis/tasks/{id}/cancel # 取消任务
```

#### 2. WebSocket实时通知

```python
# app/routers/websocket_notifications.py
WS /api/ws/notifications              # 用户通知通道
WS /api/ws/tasks/{task_id}            # 任务进度通道
```

**消息格式**：
```json
{
    "type": "notification",
    "data": {
        "id": "...",
        "title": "分析完成",
        "content": "股票 000001 分析已完成",
        "status": "unread",
        "created_at": "2025-10-23T12:00:00"
    }
}
```

#### 3. 任务队列系统

```python
# app/services/queue_service.py
class QueueService:
    def __init__(self, redis: Redis):
        self.user_concurrent_limit = 3      # 用户并发限制
        self.global_concurrent_limit = 3    # 全局并发限制
        self.visibility_timeout = 300       # 5分钟可见性超时
```

---

### 完整数据流总结

```
用户输入股票代码和分析日期
        ↓
┌─────────────────┐
│  1. 数据获取层   │
│  - 根据日期判断实时/历史数据 │
│  - 多数据源智能降级 (Tushare→AKShare→BaoStock) │
│  - 数据标准化（成交量统一为"手"） │
└─────────────────┘
        ↓
┌─────────────────┐
│  2. 数据协调器   │
│  - 预加载所有数据到state │
│  - 为分析师准备数据 │
└─────────────────┘
        ↓
┌─────────────────┐
│  3. 分析师团队   │
│  - 5个分析师并行执行 │
│  - 各自生成专业报告 │
└─────────────────┘
        ↓
┌─────────────────┐
│  4. 研究员辩论   │
│  - Bull vs Bear 辩论 │
│  - 研究经理综合决策 │
│  - 生成投资计划 │
└─────────────────┘
        ↓
┌─────────────────┐
│  5. 交易员决策   │
│  - 基于所有报告制定交易计划 │
│  - 提取结构化决策信息 │
│  - 计算止损位、仓位建议 │
└─────────────────┘
        ↓
┌─────────────────┐
│  6. 风险管理辩论 │
│  - Risky/Safe/Neutral 三方辩论 │
│  - 风险管理员最终决策 │
│  - 生成最终交易决策 │
└─────────────────┘
        ↓
┌─────────────────┐
│  7. 报告生成     │
│  - 验证报告一致性 │
│  - 生成Markdown/PDF/Word报告 │
│  - 保存到MongoDB │
└─────────────────┘
        ↓
┌─────────────────┐
│  8. 前端展示     │
│  - WebSocket实时推送进度 │
│  - 展示分析报告 │
│  - 支持报告下载 │
└─────────────────┘
```

---

**最后更新**: 2026-02-03
**版本**: 1.3.0
**配套文档**: [SKILLS.md](./skills/SKILLS.md)
