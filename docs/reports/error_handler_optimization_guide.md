# error_handler装饰器推广指南

本文档说明如何使用error_handler装饰器优化代码，减少重复的错误处理模式。

## 问题分析

项目中存在大量重复的try-except模式：

```python
# ❌ 原始模式（重复）
async def create_rule(self, rule: AlertRule) -> Optional[str]:
    try:
        db = await self._get_db()
        now = datetime.now().isoformat()
        rule_data = {...}
        result = await db[self._rules_collection].insert_one(rule_data)
        rule.id = str(result.inserted_id)
        return rule.id
    except Exception as e:
        logger.error(f"❌ 创建规则失败: {e}")
        return None
```

## 解决方案

使用error_handler装饰器（已存在于`app/utils/error_handler.py`）：

```python
# ✅ 优化模式（使用装饰器）
from app.utils.error_handler import async_handle_errors_none

@async_handle_errors_none(error_message="创建规则失败")
async def create_rule(self, rule: AlertRule) -> Optional[str]:
    db = await self._get_db()
    now = datetime.now().isoformat()
    rule_data = {...}
    result = await db[self._rules_collection].insert_one(rule_data)
    rule.id = str(result.inserted_id)
    return rule.id
```

## 装饰器类型

### 返回None的装饰器

适用于查询、获取等可能返回空值的操作：

```python
from app.utils.error_handler import async_handle_errors_none

@async_handle_errors_none(error_message="操作失败")
async def get_data(self) -> Optional[Dict]:
    # 逻辑代码
    return data
```

### 返回False的装饰器

适用于创建、更新、删除等布尔操作：

```python
from app.utils.error_handler import async_handle_errors_false

@async_handle_errors_false(error_message="操作失败")
async def create_item(self, data: Dict) -> bool:
    # 逻辑代码
    return True
```

### 返回空列表的装饰器

适用于列表查询：

```python
from app.utils.error_handler import async_handle_errors_empty_list

@async_handle_errors_empty_list(error_message="查询失败")
async def list_items(self) -> List[Dict]:
    # 逻辑代码
    return items
```

### 自定义返回值

```python
from app.utils.error_handler import async_handle_errors

@async_handle_errors(
    default_return=0,
    log_level="warning",
    error_message="计数失败"
)
async def count_items(self) -> int:
    # 逻辑代码
    return count
```

## 推广收益估算

基于app/services目录分析：
- 71个文件有try-except模式
- 333处logger.error调用

假设每个文件平均减少30行重复代码：
- 10个文件 × 30行 = 300行减少

## 实施步骤

### 阶段1：高优先级文件（1-2天）
1. alert_manager.py - 5个错误处理
2. favorites_service.py - 15个错误处理
3. auth_service.py - 10个错误处理
4. quotes_service.py - 20个错误处理

### 阶段2：中优先级文件（2-3天）
1. config_service.py
2. notifications_service.py
3. foreign_stock_service.py
4. 其他服务文件

### 阶段3：验证（1天）
1. 语法检查所有文件
2. 功能测试
3. 更新文档

## 注意事项

1. **保持API兼容性**：装饰器不应改变函数签名
2. **错误消息清晰**：提供具体的错误上下文
3. **日志级别适当**：根据严重性选择debug/info/warning/error
4. **测试充分**：每个优化的函数都需要测试

## 示例对比

### 原始代码（30行）
```python
async def create_rule(self, rule: AlertRule) -> Optional[str]:
    try:
        if not self._initialized:
            await self.initialize()

        db = await self._get_db()
        now = datetime.now().isoformat()
        rule_data = {
            "name": rule.name,
            # ... 更多字段
            "created_at": now,
        }

        result = await db[self._rules_collection].insert_one(rule_data)
        rule.id = str(result.inserted_id)
        rule.created_at = now

        if rule.enabled and rule.id:
            self._active_rules[rule.id] = rule

        return rule.id
    except Exception as e:
        logger.error(f"❌ 创建规则失败: {e}")
        return None
```

### 优化后代码（15行）
```python
from app.utils.error_handler import async_handle_errors_none

@async_handle_errors_none(error_message="创建规则失败")
async def create_rule(self, rule: AlertRule) -> Optional[str]:
    if not self._initialized:
        await self.initialize()

    db = await self._get_db()
    now = datetime.now().isoformat()
    rule_data = {
        "name": rule.name,
        # ... 更多字段
        "created_at": now,
    }

    result = await db[self._rules_collection].insert_one(rule_data)
    rule.id = str(result.inserted_id)
    rule.created_at = now

    if rule.enabled and rule.id:
        self._active_rules[rule.id] = rule

    return rule.id
```

**减少：15行（50%）**
