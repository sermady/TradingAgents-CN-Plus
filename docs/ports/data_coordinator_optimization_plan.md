# data_coordinator.py 结构重组方案

**文件**: tradingagents/graph/data_coordinator.py
**行数**: 1300行
**方法数**: 25个
**拆分风险**: 🔴高（高耦合，建议不拆分）

---

## 优化策略：结构重组（不拆分文件）

### 1. 添加注释分组

将 DataCoordinator 类的方法按功能分组，添加清晰的章节注释：

```python
class DataCoordinator:
    def __init__(self):
        # ... 初始化代码 ...

    # ===== 缓存管理 =====
    def _get_cache_key(self, symbol: str, data_type: str, date: str) -> str:
        """生成缓存键"""
        ...

    def _get_cached_data(self, key: str) -> Optional[str]:
        """获取缓存数据"""
        ...

    def _set_cached_data(self, key: str, data: str):
        """设置缓存数据"""
        ...

    # ===== 数据解析 =====
    def _parse_market_data(self, data_str: str) -> Dict[str, Any]:
        """解析市场数据字符串为结构化数据"""
        ...

    def _parse_fundamentals_data(self, data_str: str) -> Dict[str, Any]:
        """解析基本面数据字符串为结构化数据"""
        ...
```

### 2. 提取常量到独立模块

创建 `tradingagents/graph/data_coordinator_constants.py`:

```python
# -*- coding: utf-8 -*-
"""数据协调器常量"""

# 数据源优先级
DATA_SOURCE_PRIORITY = ["tushare", "baostock", "akshare"]

# 数据类型映射
DATA_TYPES = {
    "market": {
        "name": "市场数据",
        "validator": "price",
        "weight": 0.20,
    },
    "financial": {
        "name": "基本面数据",
        "validator": "fundamentals",
        "weight": 0.20,
    },
}

# 数据源超时配置（秒）
SOURCE_TIMEOUT = {
    "tushare": 10,
    "baostock": 15,
    "akshare": 15,
}

# 默认缓存TTL（秒）
DEFAULT_CACHE_TTL = 300  # 5分钟
ANALYSIS_CACHE_TTL = 300  # 5分钟
```

### 3. 提取数据解析方法到独立模块

创建 `tradingagents/graph/data_parsers.py`:

```python
# -*- coding: utf-8 -*-
"""数据解析器"""

import re
from typing import Dict, Any

def parse_market_data(data_str: str) -> Dict[str, Any]:
    """解析市场数据字符串为结构化数据"""
    result = {}
    patterns = {
        "current_price": r"最新价[：:]\s*(\d+\.?\d*)",
        # ... 更多模式
    }

    for key, pattern in patterns.items():
        matches = re.findall(pattern, data_str)
        if matches:
            try:
                result[key] = float(matches[0])
            except (ValueError, TypeError):
                result[key] = matches[0]

    return result
```

---

## 实施建议

由于该文件的高耦合性和复杂度，建议：
1. ✅ **优先采用注释分组**（低风险，立即提升可读性）
2. ⚠️ **提取常量和解析器可延后**（需要更多测试）
3. ✅ **不建议拆分文件**（风险太高）

---

**计划制定时间**: 2026-02-15
