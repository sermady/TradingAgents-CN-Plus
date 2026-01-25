# 实时行情缓存机制

本文档描述实时行情数据的多层缓存架构设计。

## 概述

实时行情数据具有高频访问、低延迟要求的特点。通过多层缓存策略，显著降低API调用频率，提升系统响应速度。

## 缓存架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      实时行情缓存架构                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐      │
│   │  应用层缓存   │     │  模块级缓存   │     │  外部API    │      │
│   │  (5min TTL) │     │  (15-30s)   │     │            │      │
│   └─────────────┘     └─────────────┘     └─────────────┘      │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            │                                    │
│                     价格一致性保证                               │
│              (PriceCacheCoordinator)                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 缓存层级

### 1. 模块级缓存（内存）

#### Tushare 批量缓存（30秒TTL）

| 属性 | 值 |
|------|-----|
| 缓存变量 | `BATCH_QUOTES_CACHE` |
| TTL | 30秒 |
| 用途 | 批量获取全市场行情 |
| 线程安全 | `threading.Lock` |

**缓存结构：**
```python
{
    "data": {
        "000001": {"code": "000001", "close": 10.5, "pct_chg": 1.2, ...},
        "000002": {"code": "000002", "close": 20.3, "pct_chg": -0.5, ...},
        ...
    },
    "timestamp": datetime(2026, 1, 25, 19, 30, 0),
    "lock": <threading.Lock>
}
```

**API函数：**
- `_get_cached_batch_quotes()` - 获取缓存
- `_set_cached_batch_quotes(data)` - 设置缓存
- `_invalidate_batch_cache()` - 使缓存失效

#### AkShare 单股票缓存（15秒TTL）

| 属性 | 值 |
|------|-----|
| 缓存变量 | `AKSHARE_QUOTES_CACHE` |
| TTL | 15秒 |
| 用途 | 单只股票实时行情 |
| 线程安全 | `threading.Lock` |

**缓存结构：**
```python
{
    "000001": {
        "data": {"code": "000001", "close": 10.5, ...},
        "timestamp": datetime(2026, 1, 25, 19, 30, 0)
    },
    "000002": {...},
    ...
}
```

**API函数：**
- `_get_akshare_cached_quote(code)` - 获取单只股票缓存
- `_set_akshare_cached_quote(code, data)` - 设置单只股票缓存
- `_clear_all_akshare_cache()` - 清空所有缓存（测试用）

### 2. Provider 状态查询

```python
# TushareProvider
status = provider.get_batch_cache_status()
# 返回: {"cached": bool, "count": int, "ttl_seconds": int}

# AKShareProvider
status = provider.get_akshare_cache_status()
# 返回: {"cached_count": int, "ttl_seconds": int}
```

## 性能对比

| 场景 | 无缓存 | 有缓存 | 提升 |
|------|-------|-------|------|
| 全市场行情（5000+股票） | 5000次API调用 | 1次API调用 | 5000x |
| 单股票连续查询 | N次API调用 | 1次API调用 | Nx |
| 多分析师同时查询 | N×M次API调用 | 1次API调用 | N×M×x |

## TTL选择依据

### Tushare 批量缓存：30秒

- **rt_k** API成本高，一次调用返回全部股票
- 30秒内多次查询复用同一结果
- 平衡实时性与API调用成本

### AkShare 单股票缓存：15秒

- **单股票API**成本低，但可单独调用
- 15秒足够覆盖一次分析流程
- 更快响应数据更新

## 线程安全

所有缓存操作使用 `threading.Lock` 保证线程安全：

```python
with AKSHARE_CACHE_LOCK:
    AKSHARE_QUOTES_CACHE[code] = {"data": data, "timestamp": datetime.now()}
```

## 缓存失效策略

1. **TTL超时**：自动失效，下次查询重新获取
2. **手动失效**：`_invalidate_batch_cache()` / `_clear_all_akshare_cache()`
3. **写时失效**：数据写入后立即失效缓存

## 与价格一致性系统集成

`PriceCacheCoordinator` 确保同一分析报告中所有分析师使用相同价格：

```python
class PriceCacheCoordinator:
    def __init__(self):
        self._cache = {}  # {ticker: {price_info, timestamp}}
    
    def get_price(self, ticker: str) -> Optional[Dict]:
        # 内部使用 Provider 的缓存机制
```

## 监控指标

### 缓存状态查询

```python
from tradingagents.dataflows.providers.china.tushare import TushareProvider
from tradingagents.dataflows.providers.china.akshare import AKShareProvider

tushare_status = TushareProvider().get_batch_cache_status()
akshare_status = AKShareProvider().get_akshare_cache_status()
```

### 日志输出

缓存操作会输出INFO级别日志：
```
2026-01-25 19:30:00 | tushare.py | INFO | 已获取批量行情数据，缓存5002条记录
2026-01-25 19:30:15 | akshare.py | INFO | AKShare缓存状态: 5条记录, TTL 15秒
```

## 系统集成

### 实时行情获取优先级

```python
# optimized_china_data.py 中的调用链
1. market_quotes (MongoDB)           # 第一优先级
2. Tushare rt_k (批量缓存30s)        # 第二优先级
3. AKShare (单股票缓存15s)           # 第三优先级
```

### Tushare 批量缓存集成

```python
# TushareProvider.get_realtime_price_from_batch()
cached = _get_cached_batch_quotes()      # 检查缓存
if cached and code6 in cached:
    return cached[code6].get("close")    # 返回缓存价格

batch = await get_realtime_quotes_batch()  # 重新获取
_set_cached_batch_quotes(batch)            # 设置缓存
```

### AkShare 单股票缓存集成

```python
# AKShareProvider.get_stock_quotes_cached()
cached = _get_akshare_cached_quote(code)  # 检查缓存
if cached:
    return cached

result = await get_stock_quotes(code)      # 重新获取
_set_akshare_cached_quote(code, result)   # 设置缓存
return result
```

**修复说明**：`get_stock_quotes_cached` 现在会在获取数据后自动设置缓存，确保后续相同股票的查询能命中缓存。

## 最佳实践

1. **分析流程启动前**：不清空缓存，确保数据一致性
2. **强制刷新**：设置 `force_refresh=True` 参数
3. **批量查询优先**：使用Tushare批量API而非多次单股票查询
4. **监控缓存命中率**：过低说明TTL可能需要调整

## 测试

```bash
# 运行缓存机制单元测试
python -m pytest tests/unit/dataflows/test_realtime_quotes.py -v

# 测试结果
# 8 passed in 8.36s
```
