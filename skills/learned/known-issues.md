# -*- coding: utf-8 -*-
"""
已知问题与调试指南

记录项目中的关键问题、修复方案和调试技巧
来源: 原 CLAUDE.md "Known Issues & Debugging Guide" 章节
"""

## 目录

1. [Tushare 每小时批量实时行情同步](#tushare-每小时批量实时行情同步)
2. [实时行情数据源分离](#实时行情数据源分离)
3. [成交量单位统一](#成交量单位统一)
4. [数据质量评分隐藏](#数据质量评分隐藏)
5. [分析日期传递 Bug](#分析日期传递-bug)
6. [Tushare ts_code 格式修复](#tushare-ts_code-格式修复)
7. [LSP 类型错误修复](#lsp-类型错误修复)
8. [数据源增强与修复批次](#数据源增强与修复批次)
9. [Tushare 新接口集成](#tushare-新接口集成)
10. [实时行情判断逻辑修复](#实时行情判断逻辑修复)
11. [增速字段解析修复](#增速字段解析修复)
12. [数据源网络连接问题](#数据源网络连接问题)
13. [PS_TTM 和股息率字段缺失问题](#ps_ttm-和股息率字段缺失问题)

---

## Tushare 每小时批量实时行情同步

**日期**: 2026-01-30
**状态**: 🟢 已实现

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

---

## 实时行情数据源分离

**日期**: 2026-01-29
**状态**: 🟢 已修复

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

## 成交量单位统一

**日期**: 2026-01-30
**状态**: 🔴 已修复（需数据清理）

**统一标准**:
- **成交量**: 全部使用 **"手"** 单位（1手=100股）
- **成交额**: 全部使用 **"元"** 单位

**背景问题**:
- Tushare/AKShare 返回"手"，但代码转换为"股"
- BaoStock 返回"股"，代码未转换
- 导致 MongoDB 中混合格式，AI 分析时数值混乱

**修复内容**:
1. **Tushare** (`tushare.py`): 移除 `* 100` 转换，保持"手"
2. **AKShare** (`akshare.py`): 移除 `* 100` 转换，保持"手"
3. **BaoStock** (`baostock.py`): 添加 `/ 100` 转换，从"股"转为"手"
4. **App 适配器**: tushare_adapter.py, akshare_adapter.py 同步修改

**数据清理步骤**:
```bash
# 1. 清理 MongoDB 中错误单位的数据
python scripts/clear_volume_data.py

# 2. 重新导入数据（使用修复后的代码）
python scripts/import/import_a_stocks_unified.py --data-source tushare

# 3. 验证成交量单位是否正确
python scripts/test_volume_unit.py
```

**单位确认**:
| 数据类型 | 数据源 | 单位 | 状态 |
|---------|--------|------|------|
| 历史数据 | Tushare/AKShare/BaoStock | 手 | ✅ |
| 实时行情 | 新浪/东方财富 | 手 | ✅ |
| MongoDB存储 | App层 | 手 | ✅ |
| 报告显示 | 所有分析师 | 手 | ✅ |
| 成交额 | 所有数据源 | 元 | ✅ |

---

## 数据质量评分隐藏

**日期**: 2026-01-29
**状态**: 🟢 已实现

**修改目标**: 从 AI 提示词中移除数据质量评分，减少干扰

**修改内容**:
- `market_analyst.py`, `fundamentals_analyst.py`, `news_analyst.py`, `china_market_analyst.py`
- 从提示词中移除 "数据质量评分: 0%" 等内容
- 保留数据来源和成交量单位等必要元数据
- 数据质量问题仍记录到日志 (`logger.warning`)

**原因**: 经常出现 0% 评分反而让 AI 质疑数据可靠性

---

## 分析日期传递 Bug

**日期**: 2026-01-29
**状态**: 🔴 已修复

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

## Tushare ts_code 格式修复

**日期**: 2026-01-30
**状态**: 🟢 已修复

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

## LSP 类型错误修复

**日期**: 2026-01-30
**状态**: 🟢 已修复

**批量修复多个文件的类型注解问题**:

1. **Tushare** (`tushare.py`): 修复 `Optional[str]` 类型错误
2. **AKShare** (`akshare.py`): 修复 `Optional[str]` 类型错误
3. **BaoStock** (`baostock.py`): 修复 `Optional[str]` 类型错误
4. **Enum 映射**: 修复 Enum 映射和 Optional 参数类型错误

**修复原则**:
- 明确区分 `str` 和 `Optional[str]` 的使用场景
- 函数参数默认值为 None 时必须标注 `Optional[str]`
- 返回值可能为 None 时必须使用 `Optional[str]`

---

## 数据源增强与修复批次

**日期**: 2026-01-29
**状态**: 🟢 已完成

**第一批修复**: 解决 DataFrame 歧义和 tuple 类型错误
- 修复 AKShare 返回值解包问题
- 统一返回数据结构

**第二批修复**: Tushare 和 AKShare 数据源增强
- 增加错误重试机制
- 优化数据缓存策略

**第三批修复**: BaoStock 异步 + MongoDB 兜底
- 添加异步连接检查，避免重复登录
- MongoDB 作为数据获取失败时的兜底方案

---

## Tushare 新接口集成

**日期**: 2026-01-29
**状态**: 🟢 已实现

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

## 实时行情判断逻辑修复

**日期**: 2026-01-30
**状态**: 🔴 已修复

**问题现象**: 用户指定分析历史日期（如 2024-06-01）时，系统错误地使用了当前实时行情

**根本原因**:
```python
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
| 今天 | 08:00 (盘前) | ⚠️ 可能失败 | ✅ 使用昨日收盘价 |
| 今天 | 10:00 (盘中) | ✅ 正确 | ✅ 使用实时行情 |
| 今天 | 16:00 (盘后) | ⚠️ 可能不完整 | ✅ 使用今日收盘价 |

**修改文件**:
1. `tradingagents/utils/market_time.py:216` - 添加 analysis_date 参数
2. `tradingagents/dataflows/data_source_manager.py:1815` - 传入 analysis_date
3. `tradingagents/utils/market_time.py:336,363,380` - 更新调用点

**报告标注**:
- ⚡ 盘中分析 - 使用实时行情
- ⚡ 盘前分析 - 使用昨日收盘价
- 📊 盘后分析 - 使用今日收盘价
- ⚡ 历史分析 - 使用历史收盘价

---

## 增速字段解析修复

**日期**: 2026-02-10
**状态**: 🟢 已修复

**问题现象**: 分析报告中 **筹资性现金流净额**、**营收同比增速**、**净利润同比增速** 显示为 **N/A**

**根本原因**: 数据源字段名与代码中使用的字段名不匹配

```python
# Tushare 返回的字段名
tushare_data = {
    "or_yoy": 15.5,          # 营收同比增速
    "q_profit_yoy": 20.3,    # 净利润同比增速
    "n_cashflow_fin_act": -50000000,  # 筹资性现金流净额
}

# 代码中查找的字段名（错误）
code_lookup = {
    "revenue_yoy": None,      # ❌ 找不到
    "net_income_yoy": None,   # ❌ 找不到
}
```

**修复方案**:

```python
# 在 _parse_financial_data_with_stock_info() 中添加多字段名映射
revenue_yoy = (
    financial_data.get("or_yoy")  # Tushare 字段名
    or financial_data.get("revenue_yoy")
    or financial_data.get("oper_rev_yoy")
    or (stock_info.get("or_yoy") if stock_info else None)
)

net_income_yoy = (
    financial_data.get("q_profit_yoy")  # Tushare 字段名
    or financial_data.get("net_income_yoy")
    or financial_data.get("n_income_yoy")
    or (stock_info.get("q_profit_yoy") if stock_info else None)
)
```

**相关技能**: [数据源字段名映射不匹配问题](data-source-field-mapping.md)

---

## 数据源网络连接问题

**日期**: 2026-02-10
**状态**: 🟢 已诊断

**问题现象**: 
```
Tushare: ConnectionResetError(10054, '远程主机强迫关闭了一个现有的连接。')
AKShare: NameResolutionError: Failed to resolve 'query.sse.com.cn'
RuntimeError: All data sources failed to provide stock list
```

**诊断结果**:
- 网络连接测试：✅ 正常
- DNS 解析：✅ 正常
- Tushare API：✅ 可连接（响应 5s）

**根本原因**: 
- Tushare 服务器临时不稳定或 Token 被限流
- 应用程序层问题，非网络问题

**解决方案**:

1. **检查 Token 有效性**:
```python
python -c "
import tushare as ts
import os
from dotenv import load_dotenv
load_dotenv('app/.env')
token = os.getenv('TUSHARE_TOKEN')
ts.set_token(token)
pro = ts.pro_api()
df = pro.stock_basic(limit=5)
print(f'✅ Token 有效，获取到 {len(df)} 条数据')
"
```

2. **启用 Baostock 作为备选**:
```bash
# 在 .env 中添加
BAOSTOCK_UNIFIED_ENABLED=true
```

3. **等待后重试**:
- ConnectionResetError 通常是服务器临时问题
- 建议等待 10-15 分钟后重试

**相关技能**: [数据源网络连接问题诊断](network-diagnostics.md)

**诊断脚本**: `diagnose_network.py`

---

## PS_TTM 和股息率字段缺失问题

**日期**: 2026-02-12
**状态**: 🟢 已修复

**问题现象**: 
基本面分析报告中显示 **"PS_TTM数据缺失"** 和 **"股息率数据不可用"**，但 Tushare API 实际提供了这些数据。

**根本原因**: 
`_get_valuation_indicators()` 方法只返回了部分字段，遗漏了 `ps_ttm`、`dv_ratio`、`dv_ttm` 等新添加的字段。

```python
# 修复前 - 字段不完整
def _get_valuation_indicators(self, symbol: str) -> Dict:
    return {
        "pe": result.get("pe"),
        "pb": result.get("pb"),
        "pe_ttm": result.get("pe_ttm"),
        "total_mv": result.get("total_mv"),
        "circ_mv": result.get("circ_mv"),
        # ❌ 缺少 ps_ttm, dv_ratio, dv_ttm, total_share, float_share
    }
```

**修复方案**:

```python
# 修复后 - 完整字段
def _get_valuation_indicators(self, symbol: str) -> Dict:
    return {
        "pe": result.get("pe"),
        "pb": result.get("pb"),
        "pe_ttm": result.get("pe_ttm"),
        "ps": result.get("ps"),
        "ps_ttm": result.get("ps_ttm"),  # ✅ 新增
        "total_mv": result.get("total_mv"),
        "circ_mv": result.get("circ_mv"),
        "dv_ratio": result.get("dv_ratio"),  # ✅ 新增
        "dv_ttm": result.get("dv_ttm"),  # ✅ 新增
        "total_share": result.get("total_share"),  # ✅ 新增
        "float_share": result.get("float_share"),  # ✅ 新增
    }
```

**新增字段说明**:

| 字段名 | 中文名 | 数据源 | 用途 |
|--------|--------|--------|------|
| `ps_ttm` | 市销率TTM | Tushare daily_basic | 估值分析优先指标 |
| `dv_ratio` | 股息率 | Tushare daily_basic | 当前分红收益率 |
| `dv_ttm` | 股息率TTM | Tushare daily_basic | 近12个月分红收益率 |
| `total_share` | 总股本 | Tushare daily_basic | 公司股本结构 |
| `float_share` | 流通股本 | Tushare daily_basic | 流通股数量 |

**修改文件**:
1. `tradingagents/dataflows/data_source_manager.py:3887-3915` - 更新 `_get_valuation_indicators()`
2. `tradingagents/dataflows/providers/china/tushare.py:535` - 添加字段获取
3. `tradingagents/dataflows/schemas/stock_basic_schema.py` - 添加字段定义
4. `tradingagents/dataflows/cache/app_adapter.py` - 添加缓存映射
5. `tradingagents/agents/utils/agent_utils.py` - 添加报告显示

**验证方法**:
```python
# 检查 MongoDB 中的字段
python -c "
from app.core.database import get_database
db = get_database()
doc = db.stock_basic_info.find_one({'ts_code': '000001.SZ'})
if doc:
    print(f'ps_ttm: {doc.get(\"ps_ttm\")}')
    print(f'dv_ttm: {doc.get(\"dv_ttm\")}')
    print(f'total_share: {doc.get(\"total_share\")}')
"
```

**相关技能**: [数据源字段名映射不匹配问题](data-source-field-mapping.md)

---

## 调试技巧

### 检查 MongoDB 中的成交量数据
```bash
python -c "
from app.core.database import get_database
db = get_database()
doc = db.historical_data.find_one({'symbol': '600765'})
if doc:
    print(f\"Volume: {doc.get('volume', 0):,.0f}\")
    print(f\"预期: 如果>1,000,000则是'股'（错误），<100,000则是'手'（正确）\")
"
```

### 验证实时行情数据源
```bash
python test_realtime_quote.py
# 预期输出: source: tushare_sina_realtime 或 source: sina_realtime
```

### 检查日期传递
```python
# 在工具函数中添加调试日志
from tradingagents.agents.utils.agent_utils import Toolkit
print(f"Trade date from config: {Toolkit._config.get('trade_date')}")
```
