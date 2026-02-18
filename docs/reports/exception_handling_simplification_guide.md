# 异常处理简化指南

**创建时间**: 2026-02-19
**目的**: 简化路由文件中的通用异常处理，提高全局处理器利用率

---

## 全局异常处理器

项目已配置全局异常处理器（`app/core/exceptions.py`），会自动处理：
- `Exception` - 通用异常
- `HTTPException` - HTTP异常
- `ValidationError` - Pydantic验证错误
- `ValueError` - 值错误
- `TypeError` - 类型错误

全局处理器会：
1. 自动记录日志
2. 返回标准错误格式

---

## 可简化的模式

### 模式1：通用异常捕获和HTTPException重抛

**❌ 原始代码**（可简化）:
```python
try:
    result = await service.do_something()
    return {"success": True, "data": result}
except Exception as e:
    logger.error(f"❌ 操作失败: {e}")
    raise HTTPException(status_code=400, detail=str(e))
```

**✅ 简化后**:
```python
result = await service.do_something()
return {"success": True, "data": result}
# 异常由全局处理器自动捕获和记录
```

**说明**:
- 删除try-except块
- 全局处理器会记录日志并返回标准格式
- 减少约5-8行代码

---

### 模式2：返回自定义错误格式

**❌ 原始代码**（可简化）:
```python
try:
    result = await service.do_something()
    return {"success": True, "data": result}
except Exception as e:
    logger.error(f"❌ 操作失败: {e}")
    return {
        "success": False,
        "data": None,
        "message": f"操作失败: {str(e)}"
    }
```

**✅ 简化后**:
```python
result = await service.do_something()
return {"success": True, "data": result}
# 全局处理器返回相同格式
```

**说明**:
- 全局处理器返回的格式与自定义格式一致
- 可安全删除try-except块

---

### 模式3：嵌套的异常处理

**❌ 原始代码**:
```python
try:
    # 外层业务逻辑
    result1 = await service.step1()

    try:
        # 内层特定逻辑
        result2 = specific_operation(result1)
    except SpecificError as e:
        # 特定错误处理 - 保留
        logger.warning(f"特定错误: {e}")
        result2 = default_value

    result = process(result2)
    return {"success": True, "data": result}
except Exception as e:
    logger.error(f"❌ 操作失败: {e}")
    raise HTTPException(status_code=400, detail=str(e))
```

**✅ 简化后**:
```python
# 外层业务逻辑
result1 = await service.step1()

try:
    # 内层特定逻辑 - 保留此try-except
    result2 = specific_operation(result1)
except SpecificError as e:
    # 特定错误处理
    logger.warning(f"特定错误: {e}")
    result2 = default_value

result = process(result2)
return {"success": True, "data": result}
# 外层异常由全局处理器处理
```

**说明**:
- 保留业务逻辑特定的异常处理
- 只删除通用的"包装"try-except

---

## 需要保留的模式

### 模式A：需要特定HTTP状态码

**✅ 保留**:
```python
try:
    result = await service.check_permission()
    if not result:
        raise HTTPException(
            status_code=403,
            detail="权限不足"
        )
except HTTPException:
    # 重新抛出HTTP异常
    raise
except Exception as e:
    logger.error(f"❌ 权限检查失败: {e}")
    raise HTTPException(status_code=403, detail="权限验证失败")
```

### 模式B：需要优雅降级

**✅ 保留**:
```python
try:
    result = await primary_service.get_data()
except Exception as e:
    logger.warning(f"⚠️ 主服务失败，使用备用服务: {e}")
    try:
        result = await fallback_service.get_data()
    except Exception:
        result = get_cached_data()  # 最后的兜底
```

### 模式C：需要事务回滚

**✅ 保留**:
```python
try:
    async with database.transaction():
        await step1()
        await step2()
        await step3()
except Exception as e:
    logger.error(f"❌ 事务失败，已回滚: {e}")
    raise HTTPException(status_code=500, detail="操作失败")
```

---

## 简化步骤

1. **识别可简化的端点**
   - 查找包含 `except Exception as e:` 的端点
   - 检查是否只是记录日志和重抛异常

2. **删除try-except块**
   - 删除 `try:` 行
   - 删除 `except Exception as e:` 块
   - 保留业务逻辑代码

3. **验证功能**
   - 确保端点仍能正常工作
   - 测试错误情况是否正确处理

4. **提交代码**
   - 每个文件单独提交
   - 使用清晰的提交消息

---

## 预期收益

- **代码减少**: 约800-1200行
- **全局处理器利用率**: 从3%提升到70%
- **可维护性**: 更清晰的代码结构
- **一致性**: 统一的错误处理格式

---

## 示例文件

| 文件 | try块数 | 预计减少行数 | 优先级 |
|------|---------|--------------|--------|
| config/llm_config.py | 13 | ~60 | 🔴 高 |
| config/datasource_config.py | 14 | ~65 | 🔴 高 |
| config/system_config.py | 14 | ~65 | 🔴 高 |
| analysis.py | 28 | ~200 | 🟡 中 |
| scheduler.py | 16 | ~80 | 🟡 中 |

---

**最后更新**: 2026-02-19
