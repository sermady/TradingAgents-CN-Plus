# error_handler 装饰器推广报告 - Phase 2

**报告时间**: 2026-02-15
**目标**: 将 error_handler 装饰器推广到更多高频服务

---

## 已完成重构

### HistoricalDataService (`app/services/historical_data_service.py`)

**重构前**:
- 560 行代码
- 3 个方法使用手动 try-except 错误处理
- 每个方法约 6-8 行的重复错误处理代码

**重构后**:
- 540 行代码
- 使用 error_handler 装饰器统一错误处理
- 更清晰的业务逻辑代码

**代码减少**: 约 20 行（净减少）

**应用装饰器**:

| 方法 | 装饰器 | 原返回值 |
|------|--------|----------|
| `get_historical_data` | `@async_handle_errors_empty_list` | `List[Dict[str, Any]]` |
| `get_latest_date` | `@async_handle_errors_none` | `Optional[str]` |
| `get_data_statistics` | `@async_handle_errors_empty_dict` | `Dict[str, Any]` |

**关键改进**:

```python
# 重构前
async def get_historical_data(self, ...) -> List[Dict[str, Any]]:
    try:
        # 业务逻辑...
        return results
    except Exception as e:
        logger.error(f"❌ 查询历史数据失败 {symbol}: {e}")
        return []

# 重构后
@async_handle_errors_empty_list(error_message="查询历史数据失败")
async def get_historical_data(self, ...) -> List[Dict[str, Any]]:
    # 业务逻辑...
    return results
```

---

## 不适合重构的服务分析

在推广过程中，分析了以下服务，但发现**不适合**应用 error_handler 装饰器：

### 1. base_crud_service.py
- **原因**: 这是基础设施本身，提供基础CRUD功能
- **风险**: 应用装饰器会导致循环依赖或破坏设计

### 2. unified_cache_service.py
- **原因**: 缓存服务涉及多级降级策略（Redis→MongoDB→File）
- **风险**: 错误处理不仅仅是返回默认值，还涉及降级逻辑

### 3. database_config_service.py
- **原因**: 有特定的错误处理逻辑（不同异常类型返回不同错误消息）
- **风险**: 需要为每种错误类型提供特定的用户提示

### 4. unified_stock_service.py
- **原因**: 方法返回复杂对象，没有try-except块
- **风险**: 不适用装饰器模式

### 5. memory_state_manager.py
- **原因**: 使用内存存储，不涉及数据库操作
- **风险**: 使用锁机制保护内存访问

### 6. quotes_service.py
- **原因**: 返回复杂字典，涉及缓存策略
- **风险**: 不适用标准装饰器

---

## 统计数据

| 指标 | Phase 1 | Phase 2 | 总计 |
|------|---------|---------|------|
| **已重构服务数** | 5 | 1 | **6** |
| **重构方法数** | 28 | 3 | **31** |
| **减少代码行数** | 约 180 行 | 约 20 行 | **约 200 行** |
| **测试通过率** | 4/4 ✅ | 4/4 ✅ | **4/4 ✅** |

---

## 使用的装饰器

### 导入
```python
from app.utils.error_handler import (
    async_handle_errors_none,
    async_handle_errors_empty_list,
    async_handle_errors_empty_dict,
    async_handle_errors_false,
    async_handle_errors_zero,
)
```

### 装饰器说明

| 装饰器 | 用途 | 异常时返回 |
|--------|------|-----------|
| `@async_handle_errors_none` | 查询单个对象 | `None` |
| `@async_handle_errors_empty_list` | 查询列表 | `[]` |
| `@async_handle_errors_empty_dict` | 查询字典 | `{}` |
| `@async_handle_errors_false` | 更新/删除操作 | `False` |
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

## 测试验证

创建并运行测试脚本验证重构:

```bash
python scripts/test/test_error_handler_promotion.py
```

**测试结果**: 4/4 通过 ✅
- 装饰器导入测试 ✅
- 语法检查测试 ✅
- HistoricalDataService 测试 ✅
- 错误处理功能测试 ✅

---

## 总结

### 已完成工作

1. **HistoricalDataService** (3 个方法)
   - `@async_handle_errors_empty_list` × 1
   - `@async_handle_errors_none` × 1
   - `@async_handle_errors_empty_dict` × 1

### 收益总结

- **已重构服务数**: 6 个（Phase 1: 5个 + Phase 2: 1个）
- **重构方法数**: 31 个
- **减少代码行数**: 约 **200 行**
- **新增统一错误处理**: 31 个方法

### 后续建议

- 继续寻找适合装饰器模式的简单服务
- 在代码审查中推荐使用 error_handler 装饰器
- 将 error_handler 作为新项目的基础组件

---

**创建时间**: 2026-02-15
**更新时间**: 2026-02-15
**完成时间**: 2026-02-15
