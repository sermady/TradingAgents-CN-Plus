# error_handler 装饰器推广报告 - Phase 1

**报告时间**: 2026-02-15
**目标**: 减少项目中重复的错误处理代码，提升可维护性

---

## 已完成重构

### StockDataService (`app/services/stock_data_service.py`)

**重构前**:
- 404 行代码
- 5 个方法使用重复的手动 try-except 错误处理
- 每个方法约 10-15 行的重复错误处理代码

**重构后**:
- 389 行代码
- 使用 error_handler 装饰器统一错误处理
- 更清晰的业务逻辑代码

**代码减少**: 约 15 行（净减少），消除约 50 行重复错误处理代码

**应用装饰器**:

| 方法 | 装饰器 | 原返回值 |
|------|--------|----------|
| `get_stock_basic_info` | `@async_handle_errors_none` | `Optional[StockBasicInfoExtended]` |
| `get_market_quotes` | `@async_handle_errors_none` | `Optional[MarketQuotesExtended]` |
| `get_stock_list` | `@async_handle_errors_empty_list` | `List[StockBasicInfoExtended]` |
| `update_stock_basic_info` | `@async_handle_errors_false` | `bool` |
| `update_market_quotes` | `@async_handle_errors_false` | `bool` |

**关键改进**:

```python
# 重构前
async def get_stock_basic_info(self, symbol: str, ...) -> Optional[...]:
    try:
        db = get_mongo_db()
        # 业务逻辑...
        return StockBasicInfoExtended(**standardized_doc)
    except Exception as e:
        logger.error(f"获取股票基础信息失败 symbol={symbol}, source={source}: {e}")
        return None

# 重构后
@async_handle_errors_none(error_message="获取股票基础信息失败")
async def get_stock_basic_info(self, symbol: str, ...) -> Optional[...]:
    db = get_mongo_db()
    # 业务逻辑...
    return StockBasicInfoExtended(**standardized_doc)
```

---

## 统计数据

| 指标 | Phase 1 |
|------|---------|
| **已重构服务数** | 1 |
| **重构方法数** | 5 |
| **减少代码行数** | 约 15 行（净减少） |
| **消除重复错误处理** | 约 50 行 |
| **测试通过率** | 4/4 ✅ |

---

## 使用的装饰器

### 导入
```python
from app.utils.error_handler import (
    async_handle_errors_none,
    async_handle_errors_empty_list,
    async_handle_errors_false,
)
```

### 装饰器说明

| 装饰器 | 用途 | 异常时返回 |
|--------|------|-----------|
| `@async_handle_errors_none` | 查询单个对象 | `None` |
| `@async_handle_errors_empty_list` | 查询列表 | `[]` |
| `@async_handle_errors_false` | 更新/删除操作 | `False` |
| `@async_handle_errors_empty_dict` | 查询字典 | `{}` |
| `@async_handle_errors_zero` | 计数操作 | `0` |

---

## 重构模式

### 标准重构步骤

1. **导入装饰器**:
```python
from app.utils.error_handler import async_handle_errors_none, async_handle_errors_false
```

2. **应用装饰器**:
```python
@async_handle_errors_none(error_message="自定义错误消息")
async def get_data(self, id: str) -> Optional[Data]:
    # 业务逻辑...
    return data
```

3. **移除 try-except 块**:
   - 删除 `try:` 和 `except Exception as e:` 行
   - 删除错误日志记录代码
   - 删除 `return None/False/[]` 等默认返回值

### 注意事项

1. **保留业务逻辑中的 try-except**: 如果需要特殊错误处理，保留原有的 try-except
2. **错误消息**: 使用 `error_message` 参数提供上下文信息
3. **日志级别**: 可以使用 `log_level` 参数调整日志级别（默认为 "error"）

---

## 下一步计划

### 待重构服务（按优先级）

| 服务 | 优先级 | 预计方法数 | 预计收益 |
|------|--------|-----------|----------|
| scheduler_service.py | P1 | 5-8 个 | ~30 行 |
| metrics_collector.py | P1 | 4-6 个 | ~25 行 |
| quotes_ingestion_service.py | P2 | 3-5 个 | ~20 行 |
| data_sync_manager.py | P2 | 4-6 个 | ~25 行 |

### 总体目标

- 推广 error_handler 装饰器到 10+ 个服务
- 减少约 200 行重复错误处理代码
- 将使用率从 11 个文件提升到 30+ 个文件

---

## 使用指南

### 何时使用 error_handler 装饰器

**适合使用**:
- 简单的数据访问方法
- 标准 CRUD 操作
- 需要统一的错误日志记录

**不适合使用**:
- 需要特殊错误处理逻辑的方法
- 需要自定义错误转换的方法
- 已经使用其他错误处理模式的方法

### 示例代码

```python
from app.utils.error_handler import async_handle_errors_none, async_handle_errors_empty_list

class MyService:
    @async_handle_errors_none(error_message="获取数据失败")
    async def get_by_id(self, id: str) -> Optional[MyModel]:
        db = await self._get_db()
        doc = await db.collection.find_one({"_id": id})
        return MyModel(**doc) if doc else None

    @async_handle_errors_empty_list(error_message="查询列表失败")
    async def list_items(self, filters: dict) -> List[MyModel]:
        db = await self._get_db()
        cursor = db.collection.find(filters)
        docs = await cursor.to_list(length=None)
        return [MyModel(**doc) for doc in docs]
```

---

**创建时间**: 2026-02-15
**更新时间**: 2026-02-15
**完成时间**: 2026-02-15
