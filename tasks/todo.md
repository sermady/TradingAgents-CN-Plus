# 数据源配置优化计划

> **状态**: ✅ 已完成 (2026-02-03)
> 
> **完成报告**: [data_source_config_completion_report.md](./data_source_config_completion_report.md)

---

## 需求重述

用户希望优化数据源配置，实现以下目标：

1. **实时行情**: 仅使用 AKShare（不使用 Tushare）
2. **历史数据 & 财务数据**: 使用 Tushare
3. **同步时机**: 仅在收盘后同步，交易时段不进行实时同步

---

## 当前配置分析

### 1. 实时行情相关配置

| 配置项 | 当前值 | 说明 |
|--------|--------|------|
| `QUOTES_INGEST_ENABLED` | `true` | 实时行情入库服务（每360秒） |
| `QUOTES_INGEST_INTERVAL_SECONDS` | `360` | 入库间隔 |
| `REALTIME_QUOTE_ENABLED` | `true` | 实时行情获取总开关 |
| `REALTIME_QUOTE_TUSHARE_ENABLED` | `true` | Tushare 作为实时行情备选 |
| `REALTIME_QUOTE_AKSHARE_PRIORITY` | `1` | AKShare 优先级（1=优先） |
| `REALTIME_QUOTE_TUSHARE_PRIORITY` | `2` | Tushare 优先级（2=备选） |

### 2. 调度任务配置

**Tushare 调度任务**:
- `tushare_quotes_sync`: 实时行情同步（交易时间每5分钟）- **需要禁用**
- `tushare_historical_sync`: 历史数据同步（工作日16点）- **保留**
- `tushare_financial_sync`: 财务数据同步（周日凌晨3点）- **保留**
- `tushare_hourly_bulk_sync`: 每小时批量实时行情同步 - **需要禁用**

**AKShare 调度任务**:
- `akshare_quotes_sync`: 实时行情同步（9:30和15:00）- **需要禁用**
- `akshare_historical_sync`: 历史数据同步（工作日17点）- **保留但需确认是否重复**
- `akshare_financial_sync`: 财务数据同步（周日凌晨4点）- **保留但需确认是否重复**

**通用调度任务**:
- `quotes_ingestion_service`: 实时行情入库服务（每360秒）- **需要禁用**

### 3. 实时行情获取逻辑

当前实时行情获取优先级（`data_source_manager.py:1486-1493`）:
1. AKShare (priority=1)
2. Tushare (priority=2, 如果启用)

需要修改配置确保：
- AKShare 优先级保持为 1
- Tushare 完全禁用（`REALTIME_QUOTE_TUSHARE_ENABLED=false`）

---

## 实施步骤

### Phase 1: 禁用实时同步调度任务

**目标**: 停止所有交易时段的实时数据同步

#### 1.1 修改 `.env` 或 `.env.docker` 配置

```bash
# 禁用实时行情入库服务
QUOTES_INGEST_ENABLED=false

# 禁用 Tushare 实时行情同步
TUSHARE_QUOTES_SYNC_ENABLED=false

# 禁用 Tushare 每小时批量同步
TUSHARE_HOURLY_BULK_SYNC_ENABLED=false

# 禁用 AKShare 实时行情同步
AKSHARE_QUOTES_SYNC_ENABLED=false
```

#### 1.2 确认调度任务状态

修改后以下任务应该处于暂停状态：
- `quotes_ingestion_service`
- `tushare_quotes_sync`
- `tushare_hourly_bulk_sync`
- `akshare_quotes_sync`

### Phase 2: 配置实时行情仅使用 AKShare

**目标**: 确保分析时获取实时行情只使用 AKShare

#### 2.1 修改环境变量配置

```bash
# 实时行情配置 - 仅使用 AKShare
REALTIME_QUOTE_ENABLED=true
REALTIME_QUOTE_TUSHARE_ENABLED=false
REALTIME_QUOTE_AKSHARE_PRIORITY=1
REALTIME_QUOTE_TUSHARE_PRIORITY=2
```

#### 2.2 验证代码逻辑

检查 `data_source_manager.py:1486-1493` 确保：
- 当 `tushare_enabled=false` 时，Tushare 不会被加入数据源列表
- AKShare 保持优先级 1

### Phase 3: 配置盘后同步任务

**目标**: 确保历史数据和财务数据只在收盘后同步

#### 3.1 当前盘后同步任务配置

**Tushare**（推荐作为主要数据源）:
- 历史数据: `0 16 * * 1-5`（工作日16点）- 已配置为盘后
- 财务数据: `0 3 * * 0`（周日凌晨3点）- 已配置为非交易时间

**AKShare**（作为备选）:
- 历史数据: `0 17 * * 1-5`（工作日17点）- 已配置为盘后
- 财务数据: `0 4 * * 0`（周日凌晨4点）- 已配置为非交易时间

#### 3.2 确认配置

```bash
# Tushare 盘后同步（主数据源）
TUSHARE_HISTORICAL_SYNC_ENABLED=true
TUSHARE_HISTORICAL_SYNC_CRON="0 16 * * 1-5"
TUSHARE_FINANCIAL_SYNC_ENABLED=true
TUSHARE_FINANCIAL_SYNC_CRON="0 3 * * 0"

# AKShare 盘后同步（备选，可选禁用避免重复）
AKSHARE_HISTORICAL_SYNC_ENABLED=false  # 可选：禁用，使用 Tushare 即可
AKSHARE_FINANCIAL_SYNC_ENABLED=false   # 可选：禁用，使用 Tushare 即可
```

### Phase 4: 验证和测试

#### 4.1 配置验证清单

- [x] `QUOTES_INGEST_ENABLED=false` ✅
- [x] `TUSHARE_QUOTES_SYNC_ENABLED=false` ✅
- [x] `TUSHARE_HOURLY_BULK_SYNC_ENABLED=false` ✅
- [x] `AKSHARE_QUOTES_SYNC_ENABLED=false` ✅
- [x] `REALTIME_QUOTE_TUSHARE_ENABLED=false` ✅
- [x] `REALTIME_QUOTE_AKSHARE_PRIORITY=1` ✅
- [x] `TUSHARE_HISTORICAL_SYNC_ENABLED=true` ✅
- [x] `TUSHARE_FINANCIAL_SYNC_ENABLED=true` ✅

#### 4.2 功能测试

1. **实时行情测试**: 在交易时段运行分析，确认只使用 AKShare
2. **盘后同步测试**: 确认16点后 Tushare 历史数据同步正常执行
3. **财务数据测试**: 确认周日 Tushare 财务数据同步正常执行

---

## 需要修改的文件

### 配置文件

| 文件 | 修改内容 |
|------|----------|
| `.env` 或 `.env.docker` | 更新上述所有配置项 |

### 代码文件（如需修改默认值）

| 文件 | 修改内容 |
|------|----------|
| `app/core/config.py:169` | 考虑将 `QUOTES_INGEST_ENABLED` 默认改为 `false` |
| `app/core/config.py:206` | 考虑将 `REALTIME_QUOTE_TUSHARE_ENABLED` 默认改为 `false` |

---

## 配置变更汇总

### 最终推荐的 `.env` 配置

```bash
# ============================================
# 实时行情配置 - 仅使用 AKShare
# ============================================
# 禁用实时行情入库服务（交易时段不自动同步）
QUOTES_INGEST_ENABLED=false

# 实时行情获取配置
REALTIME_QUOTE_ENABLED=true
REALTIME_QUOTE_TUSHARE_ENABLED=false
REALTIME_QUOTE_AKSHARE_PRIORITY=1
REALTIME_QUOTE_TUSHARE_PRIORITY=2
REALTIME_QUOTE_MAX_RETRIES=3
REALTIME_QUOTE_RETRY_DELAY=1.0

# ============================================
# Tushare 配置 - 仅用于历史/财务数据
# ============================================
TUSHARE_TOKEN=your_token_here
TUSHARE_ENABLED=true
TUSHARE_UNIFIED_ENABLED=true

# 禁用 Tushare 实时行情同步
TUSHARE_QUOTES_SYNC_ENABLED=false
TUSHARE_HOURLY_BULK_SYNC_ENABLED=false

# 启用 Tushare 盘后同步
TUSHARE_HISTORICAL_SYNC_ENABLED=true
TUSHARE_HISTORICAL_SYNC_CRON="0 16 * * 1-5"
TUSHARE_FINANCIAL_SYNC_ENABLED=true
TUSHARE_FINANCIAL_SYNC_CRON="0 3 * * 0"

# 基础信息同步（低频，可保留）
TUSHARE_BASIC_INFO_SYNC_ENABLED=true
TUSHARE_BASIC_INFO_SYNC_CRON="0 2 * * *"

# ============================================
# AKShare 配置 - 仅用于实时行情
# ============================================
AKSHARE_UNIFIED_ENABLED=true

# 禁用 AKShare 定时同步（避免与 Tushare 重复）
AKSHARE_QUOTES_SYNC_ENABLED=false
AKSHARE_HISTORICAL_SYNC_ENABLED=false
AKSHARE_FINANCIAL_SYNC_ENABLED=false

# 基础信息同步（可选，如 Tushare 已启用可禁用）
AKSHARE_BASIC_INFO_SYNC_ENABLED=false
```

---

## 预期效果

1. **交易时段**: 不进行任何自动数据同步
2. **分析时实时行情**: 仅使用 AKShare 获取
3. **收盘后（16:00）**: Tushare 自动同步历史数据
4. **周日（03:00）**: Tushare 自动同步财务数据
5. **数据一致性**: 历史/财务数据以 Tushare 为主，实时数据以 AKShare 为主

---

## 回滚方案

如需恢复原有配置，将以下配置改回：

```bash
QUOTES_INGEST_ENABLED=true
TUSHARE_QUOTES_SYNC_ENABLED=true
AKSHARE_QUOTES_SYNC_ENABLED=true
REALTIME_QUOTE_TUSHARE_ENABLED=true
```

---

## 注意事项

1. **数据覆盖**: Tushare 和 AKShare 的历史数据可能存在细微差异，统一使用 Tushare 作为主要历史数据源
2. **实时行情限制**: AKShare 实时行情有频率限制，大量股票分析时可能触发限流
3. **积分消耗**: Tushare 实时行情接口需要积分，禁用后可节省积分用于历史/财务数据
4. **重启生效**: 修改 `.env` 后需要重启应用才能生效
