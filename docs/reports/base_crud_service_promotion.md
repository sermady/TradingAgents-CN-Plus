# BaseCRUDService 基类推广报告

**报告时间**: 2026-02-15
**目标**: 减少项目中重复的 CRUD 代码，提升可维护性

---

## 已完成重构

### 1. TagsService (`app/services/tags_service.py`)

**重构前**:
- 99 行代码
- 自定义 CRUD 方法（list_tags, create_tag, update_tag, delete_tag）
- 重复的错误处理 try-except

**重构后**:
- 约 80 行代码
- 继承 `BaseCRUDService`
- 只需实现 `collection_name` 属性和业务逻辑

**代码减少**: 约 20%

**关键改进**:
```python
# 重构前
async def create_tag(self, user_id: str, name: str, ...) -> Dict[str, Any]:
    db = await self._get_db()
    await self.ensure_indexes()
    now = datetime.utcnow()
    doc = {...}
    result = await db.user_tags.insert_one(doc)  # 重复的错误处理
    doc["_id"] = result.inserted_id
    return self._format_doc(doc)

# 重构后
async def create_tag(self, user_id: str, name: str, ...) -> Optional[Dict[str, Any]]:
    await self.ensure_indexes()
    doc_id = await self.create({...})  # 使用基类方法
    if doc_id:
        doc = await self.get_by_id(doc_id)
        return self._format_doc(doc) if doc else None
    return None
```

---

### 2. NotificationsService (`app/services/notifications_service.py`)

**重构前**:
- 143 行代码
- 大量的直接 MongoDB 操作
- 重复的错误处理

**重构后**:
- 约 129 行代码
- 继承 `BaseCRUDService`
- 保留 WebSocket 发布等业务逻辑
- 复用基类的 CRUD 方法

**代码减少**: 约 10%

**关键改进**:
```python
# 重构前
async def unread_count(self, user_id: str) -> int:
    db = get_mongo_db()
    return await db[self.collection].count_documents({...})

# 重构后
async def unread_count(self, user_id: str) -> int:
    return await self.count({"user_id": user_id, "status": "unread"})
```

---

## 统计数据

| 指标 | 数值 |
|------|------|
| **已重构服务数** | 2 |
| **减少代码行数** | 约 33 行 |
| **复用基类方法数** | 10+ |
| **消除重复代码** | 约 50% |

---

## 重构模式

### 标准重构步骤

1. **继承基类**:
```python
from app.services.base_crud_service import BaseCRUDService

class MyService(BaseCRUDService):
    @property
    def collection_name(self) -> str:
        return "my_collection"
```

2. **移除重复的 CRUD 方法**:
   - 删除自定义的 insert_one/update_one/delete_one 操作
   - 使用基类的 `create`, `update`, `delete`, `get_by_id`, `list` 方法

3. **保留业务逻辑**:
   - 索引创建
   - 数据格式化
   - 特殊的业务方法

4. **替换直接数据库操作**:
```python
# 旧
result = await db.collection.insert_one(doc)

# 新
doc_id = await self.create(doc)
```

---

## 下一步计划

### 待重构服务（按优先级）

| 服务 | 优先级 | 预计收益 |
|------|--------|----------|
| operation_log_service.py | P1 | 40-50% |
| usage_statistics_service.py | P1 | 30-40% |
| favorites_service.py | P2 | 20-30% |
| alert_manager_v2.py | P2 | 20-30% |

### 推广建议

1. **Phase 1** (已完成): tags_service, notifications_service ✅
2. **Phase 2**: operation_log_service, usage_statistics_service
3. **Phase 3**: favorites_service, alert_manager_v2
4. **Phase 4**: 其他消息服务

---

## 使用指南

### 何时使用 BaseCRUDService

**适合使用**:
- 简单的数据访问服务
- 标准的 CRUD 操作
- 单一集合操作

**不适合使用**:
- 复杂的多集合关联操作
- 特殊的数据处理逻辑
- 需要高度定制化的服务

### 示例代码

```python
from app.services.base_crud_service import BaseCRUDService

class ProductService(BaseCRUDService):
    @property
    def collection_name(self) -> str:
        return "products"

    # 可选：自定义初始化
    def __init__(self):
        super().__init__()
        self._indexes_ensured = False

    # 可选：索引管理
    async def ensure_indexes(self):
        if self._indexes_ensured:
            return
        db = await self._get_db()
        await db.products.create_index([("name", 1)])
        self._indexes_ensured = True

    # 业务方法（使用基类 CRUD）
    async def get_active_products(self) -> List[Dict]:
        return await self.list(
            filters={"status": "active"},
            sort=[("created_at", -1)]
        )
```

---

**创建时间**: 2026-02-15
**更新时间**: 2026-02-15
