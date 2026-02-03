# 数据源配置优化完成报告

## 优化目标

实现以下数据源策略：
- **实时行情**: 仅使用 AKShare（不使用 Tushare）
- **历史数据 & 财务数据**: 使用 Tushare（高质量数据）
- **同步时机**: 仅在收盘后同步，交易时段不进行实时同步

## 修改的文件

### 1. `.env` (本地环境)
状态: ✅ 已正确配置，无需修改

关键配置确认：
```bash
# 实时行情配置 - 仅使用 AKShare
REALTIME_QUOTE_ENABLED=true
REALTIME_QUOTE_TUSHARE_ENABLED=false
REALTIME_QUOTE_AKSHARE_PRIORITY=1

# 禁用实时同步
QUOTES_INGEST_ENABLED=false
TUSHARE_QUOTES_SYNC_ENABLED=false
TUSHARE_HOURLY_BULK_SYNC_ENABLED=false
AKSHARE_QUOTES_SYNC_ENABLED=false

# 启用盘后同步
TUSHARE_HISTORICAL_SYNC_ENABLED=true
TUSHARE_FINANCIAL_SYNC_ENABLED=true
```

### 2. `.env.docker` (Docker 环境)
状态: ✅ 已修改

修改内容：
```bash
# 新增实时行情配置
REALTIME_QUOTE_ENABLED=true
REALTIME_QUOTE_TUSHARE_ENABLED=false
REALTIME_QUOTE_AKSHARE_PRIORITY=1
REALTIME_QUOTE_TUSHARE_PRIORITY=2

# 修改实时行情入库配置
QUOTES_INGEST_ENABLED=false  # 原为 true
QUOTES_INGEST_INTERVAL_SECONDS=3600  # 原为 360
```

### 3. `app/core/config.py` (默认配置)
状态: ✅ 已修改

修改内容：
- `AKSHARE_QUOTES_SYNC_ENABLED`: default=True → default=False
- `AKSHARE_HISTORICAL_SYNC_ENABLED`: default=True → default=False
- `AKSHARE_FINANCIAL_SYNC_ENABLED`: default=True → default=False
- `BAOSTOCK_UNIFIED_ENABLED`: default=True → default=False
- `BAOSTOCK_BASIC_INFO_SYNC_ENABLED`: default=True → default=False
- `BAOSTOCK_DAILY_QUOTES_SYNC_ENABLED`: default=True → default=False
- `BAOSTOCK_HISTORICAL_SYNC_ENABLED`: default=True → default=False
- `BAOSTOCK_STATUS_CHECK_ENABLED`: default=True → default=False

## 配置验证结果

所有配置项验证通过：

| 配置项 | 预期值 | 实际值 | 状态 |
|--------|--------|--------|------|
| QUOTES_INGEST_ENABLED | false | false | ✅ |
| TUSHARE_QUOTES_SYNC_ENABLED | false | false | ✅ |
| TUSHARE_HOURLY_BULK_SYNC_ENABLED | false | false | ✅ |
| AKSHARE_QUOTES_SYNC_ENABLED | false | false | ✅ |
| REALTIME_QUOTE_ENABLED | true | true | ✅ |
| REALTIME_QUOTE_TUSHARE_ENABLED | false | false | ✅ |
| REALTIME_QUOTE_AKSHARE_PRIORITY | 1 | 1 | ✅ |
| TUSHARE_HISTORICAL_SYNC_ENABLED | true | true | ✅ |
| TUSHARE_FINANCIAL_SYNC_ENABLED | true | true | ✅ |
| BAOSTOCK_UNIFIED_ENABLED | false | false | ✅ |

## 预期行为

### 交易时段（工作日 9:30-15:30）
- ❌ 不进行自动数据同步
- ✅ 分析时按需使用 AKShare 获取实时行情

### 收盘后（工作日 16:00）
- ✅ Tushare 自动同步历史数据
- 数据质量高，用于后续分析

### 周日（凌晨 3:00）
- ✅ Tushare 自动同步财务数据
- 包括财报、PE/PB 等指标

### 数据源优先级
```
实时行情: AKShare (priority=1) → Tushare disabled
历史数据: Tushare → AKShare (fallback)
财务数据: Tushare → AKShare (fallback)
```

## 节省的 Tushare 积分

禁用以下实时行情功能后，可节省大量积分：
- rt_k 接口（实时行情）: 200元/月（付费接口）
- 每分钟/每小时同步: 节省 API 调用次数

## 注意事项

1. **AKShare 频率限制**: 实时行情有频率限制，大量股票分析时可能触发限流
2. **重启生效**: 修改配置后需要重启应用才能生效
3. **Docker 用户**: 确保 `.env.docker` 配置正确，并重新构建镜像

## 回滚方案

如需恢复原有配置，将以下配置改回：

```bash
# .env 或 .env.docker
QUOTES_INGEST_ENABLED=true
TUSHARE_QUOTES_SYNC_ENABLED=true
AKSHARE_QUOTES_SYNC_ENABLED=true
REALTIME_QUOTE_TUSHARE_ENABLED=true
```

## 验证脚本

已创建验证脚本：`scripts/verify_data_source_config.py`

运行方式：
```bash
python scripts/verify_data_source_config.py
```

---

**完成日期**: 2026-02-03
**配置版本**: v1.0
