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

### 🟢 Tushare 每小时批量实时行情同步 (2026-01-30)

**功能**: 使用 Tushare `rt_k` 接口每小时批量同步全市场实时行情（约 5000+ 只股票）

**实现文件**:
- `app/core/config.py` - 新增配置项
- `app/worker/tushare_sync_service.py` - 新增 `run_tushare_hourly_bulk_sync()` 函数
- `app/main.py` - 调度器配置

**配置说明**:
```python
# .env 文件或配置中心
TUSHARE_HOURLY_BULK_SYNC_ENABLED=true  # 启用每小时批量同步
TUSHARE_HOURLY_BULK_SYNC_CRON="0 9-15 * * 1-5"  # 工作日9-15点每小时执行
```

**数据存储**:
- **MongoDB**: `market_quotes` 集合，持久化存储
- **Redis**: `realtime_quote:{symbol}` key，缓存10分钟

**执行逻辑**:
1. 检查是否在交易时段（工作日 9:30-15:30）
2. 使用 `rt_k` 接口一次性获取全市场数据
3. 批量写入 MongoDB 和 Redis
4. 每小时整点触发（如 10:00, 11:00...）

**适用场景**:
- 有足够 Tushare 积分（rt_k 接口需要积分）
- 需要全市场实时行情数据
- 替代原有的高频实时行情同步

---

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

### 🟢 成交量单位统一为"手" (2026-01-29)

**修改目标**: 将 Tushare/AKShare/BaoStock 的成交量单位统一为"手"(1手=100股)

**背景问题**:
- Tushare/AKShare 返回"手"，但代码转换为"股"
- BaoStock 返回"股"，代码未转换
- 导致 MongoDB 中混合格式，AI 分析时数值混乱

**修改内容**:
1. **Tushare** (`tushare.py:1789-1791, 2530-2531`): 移除 `* 100` 转换，保持"手"
2. **AKShare** (`akshare.py:944-946, 1277-1280`): 移除 `* 100` 转换，保持"手"
3. **BaoStock** (`baostock.py`): 
   - 添加 `/ 100` 转换，从"股"转为"手"
   - 成交额确认原始单位是"元"，移除错误转换
4. **App 适配器**: tushare_adapter.py, akshare_adapter.py 同步修改

**数据迁移步骤**:
```bash
# 1. 清除 MongoDB 中的旧 volume 数据
python scripts/clear_volume_data.py

# 2. 重新导入数据
python scripts/import/import_a_stocks_unified.py --data-source tushare

# 3. 验证单位
python scripts/test_volume_unit.py
```

**成交额单位确认**:
- Tushare: 原始"千元" → 转换为"元" (×1000) ✅
- AKShare: 原始"元" → 直接使用 ✅  
- BaoStock: 原始"元" → 直接使用 ✅

---

### 🟢 数据质量评分隐藏 (2026-01-29)

**修改目标**: 从 AI 提示词中移除数据质量评分，减少干扰

**修改内容**:
- `market_analyst.py`, `fundamentals_analyst.py`, `news_analyst.py`, `china_market_analyst.py`
- 从提示词中移除 "数据质量评分: 0%" 等内容
- 保留数据来源和成交量单位等必要元数据
- 数据质量问题仍记录到日志 (`logger.warning`)

**原因**: 经常出现 0% 评分反而让 AI 质疑数据可靠性

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

---

### 🟢 Tushare ts_code 格式修复 (2026-01-30)

**问题现象**: Tushare 股票信息查询时 ts_code 格式错误，导致部分接口返回空数据

**修复内容**:
- `tradingagents/dataflows/tushare.py`: 修正 ts_code 格式处理逻辑
- 确保股票代码格式统一为 `000001.SZ` 格式

**验证方法**:
```bash
# 测试Tushare股票信息查询
python -c "from tradingagents.dataflows import TushareProvider; t = TushareProvider(); print(t.get_stock_info('000001'))"
```

---

### 🟢 LSP 类型错误修复 (2026-01-30)

**批量修复多个文件的类型注解问题**:

1. **Tushare** (`tushare.py:132cf70`): 修复 `Optional[str]` 类型错误
2. **AKShare** (`akshare.py:d71fbee`): 修复 `Optional[str]` 类型错误
3. **BaoStock** (`baostock.py:cf16954`): 修复 `Optional[str]` 类型错误
4. **Enum 映射** (`1b3eff9`): 修复 Enum 映射和 Optional 参数类型错误

**修复原则**:
- 明确区分 `str` 和 `Optional[str]` 的使用场景
- 函数参数默认值为 None 时必须标注 `Optional[str]`
- 返回值可能为 None 时必须使用 `Optional[str]`

---

### 🟢 数据源增强与修复批次 (2026-01-29)

**第一批修复** (`a9e62b4`): 解决 DataFrame 歧义和 tuple 类型错误
- 修复 AKShare 返回值解包问题
- 统一返回数据结构

**第二批修复** (`f62f69f`): Tushare 和 AKShare 数据源增强
- 增加错误重试机制
- 优化数据缓存策略

**第三批修复** (`dd053ca`): BaoStock 异步 + MongoDB 兜底
- 添加异步连接检查，避免重复登录
- MongoDB 作为数据获取失败时的兜底方案

---

### 🟢 Tushare 新接口集成 (2026-01-29)

**新增3个接口，充分利用 5210 积分权限**:

1. **实时行情接口** (`sina_realtime`): 新浪财经实时数据
2. **分钟线数据** (`minute_data`): 支持 1/5/15/30/60 分钟 K 线
3. **资金流向数据** (`money_flow`): 主力资金流向追踪

**接口优先级**:
```
积分充足时: Tushare 优先 (稳定性高)
积分不足时: AKShare 兜底 (免费但有限流)
```

---

### 🔴 成交量单位修复完整版 (2026-01-30)

**问题现象**: 分析报告中成交量被放大了100倍

**根本原因**: App 层代码与数据源层不一致

```
数据源层 (tradingagents/dataflows/providers/china/*.py)
├── 已修复：统一返回"手"单位 ✅
└── 移除了 *100 转换

App 层 (app/services/*.py)
├── 未修复：仍将"手"×100转为"股"存入 MongoDB ❌
└── 导致数据不一致

结果
├── MongoDB 存储的是"股"（错误）
└── 报告显示时当成"手"（错误）
└── 用户看到放大100倍的数值
```

**修复内容**:

1. **historical_data_service.py:116-119**
   ```python
   # 修改前：将"手"×100转为"股"
   data['volume'] = data['volume'] * 100
   
   # 修改后：保持"手"单位
   # 成交量：保持"手"单位（不再转换为股）
   ```

2. **tushare_adapter.py:266, 384**
   ```python
   # 修改前：vol = vol * 100
   # 修改后：直接使用"手"单位
   ```

3. **akshare_adapter.py:478**
   ```python
   # 修改前：根据字段名判断并×100
   if "手" in volume_col or volume_col in [...]:
       vol = vol * 100
   
   # 修改后：统一使用"手"单位
   # 不再转换，AKShare 返回的已经是"手"
   ```

4. **data_source_manager.py:782**
   - 更新注释，说明 MongoDB 现在正确存储"手"单位
   - 添加修复记录和数据清理说明

**数据清理步骤**:

```bash
# 1. 清理 MongoDB 中错误单位的数据
python scripts/clear_volume_data.py

# 2. 重新导入数据（使用修复后的代码）
python scripts/import/import_a_stocks_unified.py --data-source tushare

# 3. 验证成交量单位是否正确
python scripts/test_volume_unit.py
```

**验证方法**:

```bash
# 检查 MongoDB 中的数据
python -c "
from app.core.database import get_database
db = get_database()
doc = db.historical_data.find_one({'symbol': '600765'})
if doc:
    print(f\"Volume: {doc.get('volume', 0):,.0f}\")
    print(f\"预期: 如果>1,000,000则是'股'（错误），<100,000则是'手'（正确）\")
"
```

**受影响的集合**:
- `historical_data` - 完全删除后重新导入
- `stock_daily_quotes` - 清除 volume 字段
- `realtime_quotes` - 完全删除
- `market_quotes` - 清除 volume 字段

**单位确认 (2026-01-30)**:
- Tushare: "手" ✅
- AKShare: "手" ✅
- BaoStock: "手" ✅
- MongoDB: 修复前="股"，修复后="手" ✅
- 报告显示: "手" ✅

---

### 🔴 成交量/成交额单位完全统一 (2026-01-30)

**统一标准**:
- **成交量**: 全部使用 **"手"** 单位（1手=100股）
- **成交额**: 全部使用 **"元"** 单位

**修改范围**: 覆盖所有数据源和实时行情

**1. 实时行情统一**:

```python
# data_source_manager.py

# 新浪实时行情（修改前）
volume = int(float(data[8])) * 100  # 转换为股 ❌
logger.info(f"成交量={volume:,.0f}股")

# 新浪实时行情（修改后）
volume = int(float(data[8]))  # 单位：手 ✅
logger.info(f"成交量={volume:,.0f}手")

# 东方财富实时行情（修改前）
volume_in_shares = volume_in_lots * 100  # 转换为股 ❌

# 东方财富实时行情（修改后）
volume = volume_in_lots  # 单位：手 ✅
```

**2. 数据标准化器更新**:

```python
# data_standardizer.py（修改前）
def standardize_volume(volume, unit=None):
    """标准化成交量到"股"""
    if unit == 'lots':
        return volume * 100  # 手→股 ❌

# data_standardizer.py（修改后）
def standardize_volume(volume, unit=None):
    """标准化成交量到"手"""
    if unit == 'shares':
        return volume / 100  # 股→手 ✅
```

**3. Schema 注释更新**:

```python
# stock_historical_schema.py
volume: Optional[float] = None  # 成交量（手）- 2026-01-30统一单位 ✅
amount: Optional[float] = None  # 成交额（元）- 统一单位 ✅
```

**4. 优化数据提供器**:

```python
# optimized_china_data.py
# 修改前：手→股转换
if volume_unit == "lots":
    volume_value = volume_value * 100  # ❌

# 修改后：统一为手
if volume_value > 1000000:
    volume_value = volume_value / 100  # 股→手（容错处理）✅
volume = f"{int(volume_value):,}手"
```

**单位确认 (2026-01-30 最终版)**:

| 数据类型 | 数据源 | 单位 | 状态 |
|---------|--------|------|------|
| 历史数据 | Tushare/AKShare/BaoStock | 手 | ✅ |
| 实时行情 | 新浪/东方财富 | 手 | ✅ |
| MongoDB存储 | App层 | 手 | ✅ |
| 报告显示 | 所有分析师 | 手 | ✅ |
| 成交额 | 所有数据源 | 元 | ✅ |

---

### 🔴 实时行情判断逻辑修复 (2026-01-30)

**问题现象**: 用户指定分析历史日期（如 2024-06-01）时，系统错误地使用了当前实时行情

**根本原因**: 
```
should_use_realtime_quote(symbol)  # 只传入股票代码
└── 使用 datetime.now() 判断当前时间
    └── 历史日期分析时被误判为"盘中"，使用实时行情 ❌
```

**修复方案**:
```python
# 修改前
should_use_rt, reason = MarketTimeUtils.should_use_realtime_quote(symbol)

# 修改后
should_use_rt, reason = MarketTimeUtils.should_use_realtime_quote(
    symbol, 
    analysis_date=analysis_date  # 传入用户指定的分析日期
)
```

**智能判断逻辑**:
```python
def should_use_realtime_quote(symbol, analysis_date, check_time):
    today = check_time.strftime("%Y-%m-%d")
    
    # 1. 历史日期：绝对不使用实时行情
    if analysis_date < today:
        return False, "⚡ 历史分析，使用历史收盘价"
    
    # 2. 未来日期：使用最新历史数据
    if analysis_date > today:
        return False, "📅 未来日期，使用最新历史数据"
    
    # 3. 今天：根据交易时间判断
    if 盘中:
        return True, "⚡ 盘中分析，使用实时行情"
    elif 盘前:
        return False, "⚡ 盘前分析，使用昨日收盘价"
    elif 盘后:
        return False, "📊 盘后分析，使用今日收盘价"
```

**场景覆盖**:

| 分析日期 | 当前时间 | 修复前行为 | 修复后行为 |
|---------|---------|-----------|-----------|
| 2024-06-01 (历史) | 任意 | ❌ 错误使用实时行情 | ✅ 使用历史数据 |
| 2026-01-30 (今天) | 08:00 盘前 | ⚠️ 可能失败 | ✅ 使用昨日收盘价 |
| 2026-01-30 (今天) | 10:00 盘中 | ✅ 正确 | ✅ 使用实时行情 |
| 2026-01-30 (今天) | 16:00 盘后 | ⚠️ 可能不完整 | ✅ 使用今日收盘价 |

**修改文件**:
1. `tradingagents/utils/market_time.py:216` - 添加 analysis_date 参数
2. `tradingagents/dataflows/data_source_manager.py:1815` - 传入 analysis_date
3. `tradingagents/utils/market_time.py:336,363,380` - 更新调用点

**报告标注**:
- ⚡ 盘中分析 - 使用实时行情
- ⚡ 盘前分析 - 使用昨日收盘价  
- 📊 盘后分析 - 使用今日收盘价
- ⚡ 历史分析 - 使用历史收盘价
