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
| Tushare 每小时批量实时行情同步 | 2026-01-30 | 🟢 已实现 |  |
| 实时行情数据源分离 | 2026-01-29 | 🟢 已修复 |  |
| 成交量单位统一为"手" | 2026-01-30 | 🔴 需清理 | 所有数据源适配器 |
| 分析日期传递 Bug | 2026-01-29 | 🔴 已修复 |  |
| 实时行情判断逻辑修复 | 2026-01-30 | 🔴 已修复 |  |

### 常见调试命令



**查看完整问题列表和解决方案** → [skills/learned/known-issues.md](./skills/learned/known-issues.md)

---

#### 1. 报告生成方式

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
