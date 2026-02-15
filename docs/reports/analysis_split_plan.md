# analysis.py 拆分方案

## 当前状态
- **文件**: app/routers/analysis.py
- **行数**: 1386行
- **函数数**: 26个
- **平均复杂度**: 6（高）
- **拆分风险**: 🟡 中

## 拆分策略

### 目标
1. **保持API兼容性** - 所有端点路径不变
2. **提升可维护性** - 按功能模块分组
3. **减少主文件** - 目标~300行
4. **清晰的依赖关系** - 避免循环依赖

## 拆分方案

```
app/routers/analysis/
├── __init__.py              # 统一导出，保持API兼容性
├── routes.py                # 路由定义（~200行）
├── schemas.py               # 请求/响应模型（~150行）
├── task_service.py          # 任务管理逻辑（~300行）
├── status_service.py         # 任务状态查询（~200行）
├── dependencies.py          # 依赖管理（~100行）
└── validators.py            # 验证逻辑（~150行）
```

### 模块职责

#### routes.py (~200行)
```python
from fastapi import APIRouter

from app.routers.analysis.task_service import get_task_service
from app.routers.analysis.schemas import (
    SingleAnalysisRequest,
    BatchAnalysisRequest,
    TaskStatusResponse
)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

# 端点1: POST /single
@router.post("/single", response_model=Dict[str, Any])
async def submit_single_analysis(
    request: SingleAnalysisRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """提交单股分析任务"""
    task_service = get_task_service()
    return await task_service.submit_single_task(request, user)

# 端点2: POST /batch
@router.post("/batch", response_model=Dict[str, Any])
async def submit_batch_analysis(
    request: BatchAnalysisRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """提交批量分析任务"""
    task_service = get_task_service()
    return await task_service.submit_batch_tasks(request, user)

# 更多端点...
```

#### task_service.py (~300行)
```python
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from app.services.queue_service import get_queue_service
from app.services.analysis_service import get_analysis_service

logger = logging.getLogger(__name__)

class TaskService:
    """任务管理服务 - 提取自analysis.py的任务管理逻辑"""

    def __init__(self):
        self.queue_service = get_queue_service()
        self.analysis_service = get_analysis_service()

    async def submit_single_task(
        self,
        request: SingleAnalysisRequest,
        user: dict
    ) -> Dict[str, Any]:
        """提交单股分析任务（从原代码迁移）"""
        try:
            # 原有的逻辑...
            task_id = await self.queue_service.enqueue_analysis(...)

            return {
                "success": True,
                "task_id": task_id,
                "message": "分析任务已提交"
            }
        except Exception as e:
            logger.error(f"提交任务失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # 更多方法...
```

#### schemas.py (~150行)
```python
from pydantic import BaseModel, Field
from typing import Optional, List

class SingleAnalysisRequest(BaseModel):
    """单股分析请求"""
    symbol: str = Field(..., description="股票代码")
    analysis_date: Optional[str] = Field(None, description="分析日期")
    research_depth: int = Field(1, ge=1, le=5, description="研究深度")
    # ... 更多字段

class BatchAnalysisRequest(BaseModel):
    """批量分析请求"""
    symbols: List[str] = Field(..., description="股票代码列表")
    analysis_date: Optional[str] = Field(None, description="分析日期")
    research_depth: int = Field(1, ge=1, le=5, description="研究深度")

class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str
    progress: float
    message: Optional[str]
    created_at: datetime
    updated_at: datetime
    # ... 更多字段
```

#### status_service.py (~200行)
```python
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from app.core.database import get_mongo_db

logger = logging.getLogger(__name__)

class StatusService:
    """任务状态查询服务"""

    async def get_task_status(
        self,
        task_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """获取任务状态（从原代码迁移）"""
        try:
            db = get_mongo_db()
            task = await db.analysis_tasks.find_one({"task_id": task_id})

            if not task:
                return None

            return {
                "task_id": task_id,
                "status": task.get("status", "unknown"),
                "progress": task.get("progress", 0),
                "created_at": task.get("created_at"),
                "updated_at": task.get("updated_at")
            }
        except Exception as e:
            logger.error(f"查询任务状态失败: {e}")
            return None
```

#### validators.py (~150行)
```python
from typing import Optional, List
from pydantic import BaseModel, validator

def validate_stock_code(symbol: str) -> Optional[str]:
    """验证股票代码"""
    if not symbol:
        return "股票代码不能为空"

    # A股代码：6位数字
    if len(symbol) == 6 and symbol.isdigit():
        return None

    return None

def validate_analysis_date(date: Optional[str]) -> Optional[str]:
    """验证分析日期"""
    if not date:
        return None

    # 验证日期格式 YYYY-MM-DD
    # ...

    return None
```

#### dependencies.py (~100行)
```python
"""
依赖管理 - 统一导入，避免循环依赖
"""

from app.services.queue_service import QueueService
from app.services.analysis_service import AnalysisService
# ... 其他依赖

# 服务实例缓存（延迟初始化）
_queue_service: Optional[QueueService] = None
_analysis_service: Optional[AnalysisService] = None

def get_queue_service() -> QueueService:
    """获取队列服务实例"""
    global _queue_service
    if _queue_service is None:
        from app.services.queue_service import QueueService
        _queue_service = QueueService()
    return _queue_service

def get_analysis_service() -> AnalysisService:
    """获取分析服务实例"""
    global _analysis_service
    if _analysis_service is None:
        from app.services.analysis_service import AnalysisService
        _analysis_service = AnalysisService()
    return _analysis_service
```

#### __init__.py (~50行)
```python
"""
统一导出 - 保持API兼容性
"""

from app.routers.analysis.routes import router
from app.routers.analysis.task_service import get_task_service
from app.routers.analysis.status_service import get_status_service

__all__ = ['router', 'get_task_service', 'get_status_service']
```

## API兼容性保证

### 导出兼容
```python
# 原有代码（在app.py或其他地方）：
from app.routers.analysis import submit_single_analysis

# 拆分后仍然可用：
from app.routers.analysis import submit_single_analysis  # ✅ 兼容
```

### 端点路径不变
```python
# 原有：
POST /api/analysis/single

# 拆分后：
POST /api/analysis/single  # ✅ 路径相同
```

## 拆分步骤

### 第一阶段：创建模块结构（不替换原文件）
1. 创建 app/routers/analysis/ 目录
2. 创建各模块文件（从原代码复制并调整）
3. 在__init__.py中导出统一接口
4. 测试API兼容性
5. 验证功能正常

### 第二阶段：更新导入（如果第一阶段成功）
1. 更新app/routers/__init__.py
2. 更新app/main.py
3. 删除或注释原analysis.py的重复部分

## 风险控制

### 代码验证
- [ ] 所有模块可正常导入
- [ ] API端点路径不变
- [ ] 功能测试通过（至少核心功能）
- [ ] 性能无明显下降

### 预期收益
- **代码减少**: 主文件减少~1100行（从1386行→~300行）
- **可读性**: 显著提升（模块化，职责清晰）
- **可维护性**: 显著提升（独立模块，易于修改）

## 注意事项

1. **复制策略**: 从原文件复制相关代码，粘贴到新模块
2. **导入顺序**: dependencies.py放在最前，避免循环依赖
3. **日志保持**: 保留原有的日志语句
4. **测试充分**: 每个模块都需要独立测试
