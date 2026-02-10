# TradingAgents-CN 项目技能库

**生成时间**: 2026-02-07
**用途**: 记录本次开发会话中的可复用模式，避免重复犯错

## 技能列表

### 1. [Python启动错误排查](python-startup-errors.md)
**适用场景**: Python应用启动失败、导入错误、属性错误

**关键要点**:
- 确保 `logger = logging.getLogger(__name__)` 定义在模块顶部
- 使用绝对导入路径 `from app.core.module` 而非相对导入
- 构造函数中立即赋值所有实例属性

**触发时机**:
- 修改文件顶部导入语句后
- 重构代码移动文件位置后
- 添加新的类参数后

---

### 2. [TypeScript/Python文件混合错误预防](ts-py-mixup-prevention.md)
**适用场景**: 混合使用Python和TypeScript的项目

**关键要点**:
- Python文件使用 `# -*- coding: utf-8 -*-`
- TypeScript文件不使用Python编码声明
- 全局替换时要格外小心

**快速检查**:
```bash
grep -r "# -*- coding:" frontend/src --include="*.ts" --include="*.tsx"
```

---

### 3. [WebSocket连接问题排查](websocket-troubleshooting.md)
**适用场景**: WebSocket连接断开、1006错误、实时通知失败

**关键要点**:
- 开发环境使用query string传递token: `?token=xxx`
- 生产环境使用subprotocol: `Sec-WebSocket-Protocol: token.xxx`
- WebSocket生命周期只在App.vue中管理

**禁止操作**:
- 不要在HeaderActions.vue中调用 `disconnect()`
- 不要在非App.vue组件中初始化WebSocket

---

### 4. [DashScope文本长度限制处理](dashscope-text-limit-handling.md)
**适用场景**: 使用DashScope API（通义千问）时的文本截断和提炼

**分层策略**:
- < 8000字符：直接使用
- 8000-20000字符：智能截断
- > 20000字符：LLM提炼关键信息

**关键常量**:
```python
DASHSCOPE_MAX_LENGTH = 8000  # API硬性限制
LLM_EXTRACTION_THRESHOLD = 20000  # 使用LLM提炼的阈值
```

---

### 5. [浮点数精度测试断言](float-precision-testing.md)
**适用场景**: Python单元测试中涉及浮点数的断言

**禁止**:
```python
# ❌ 错误
assert result == 0.75
```

**正确做法**:
```python
# ✅ 正确
assert abs(result - 0.75) < 0.01
assert math.isclose(result, 0.75, abs_tol=0.01)
assert result == pytest.approx(0.75, abs=0.01)
```

**容忍度标准**:
- 置信度(0-1): 0.01
- 价格(元): 0.01
- 百分比(%): 0.1

---

### 6. [数据质量检查模式](data-quality-checks.md)
**适用场景**: 财务数据验证、报告一致性检查、AI输出验证

**常见陷阱**:
1. **PE_TTM计算错误**: 必须使用TTM净利润，不是单季度
2. **成交量单位混淆**: 统一使用"手"（1手=100股）
3. **价格数据矛盾**: 各报告中的当前价格应该一致

**验证清单**:
- [ ] AI报告中有明确的计算公式说明
- [ ] 成交量单位标注为"手"
- [ ] 各分析师报告的价格数据一致
- [ ] 同比增长率数据完整

---

### 7. [WebSocket完整模式指南](websocket-patterns.md) ⭐ NEW
**适用场景**: 基于20+次WebSocket提交的系统化解决方案

**涵盖内容**:
- 1006错误根因分析
- 双模式Token传递实现
- 生命周期管理最佳实践
- 重连并发控制
- 后端双模式Token解析

**代码示例**:
```typescript
// 开发环境
wsUrl = `ws://localhost:8000/api/ws/notifications?token=${token}`;

// 生产环境  
wsUrl = `wss://api.example.com/api/ws/notifications`;
protocols = [`token.${token}`];
```

---

### 8. [数据源配置与Token管理](data-source-configuration.md) ⭐ NEW
**适用场景**: Tushare/AKShare/BaoStock配置管理

**关键要点**:
- Token读取优先级: .env > 数据库
- 数据源启用控制: 环境变量开关
- 单例模式避免重复初始化
- 降级策略实现

**配置示例**:
```bash
TUSHARE_ENABLED=true
AKSHARE_UNIFIED_ENABLED=true
BAOSTOCK_UNIFIED_ENABLED=false
HISTORICAL_DATA_SOURCE_PRIORITY=tushare,akshare,baostock
```

---

### 9. [并发与异步编程模式](concurrency-async-patterns.md) ⭐ NEW
**适用场景**: asyncio、threading.Lock、事件循环冲突

**关键决策表**:
| 场景 | 锁类型 | 原因 |
|------|--------|------|
| 纯同步 | threading.Lock | 标准选择 |
| 纯异步 | asyncio.Lock | 不阻塞事件循环 |
| 混合 | 两者都用 | 分别保护 |

**禁止**:
```python
# ❌ 在async函数中使用threading.Lock
async def get_data():
    with lock:  # 阻塞整个事件循环！
        data = await fetch_data()
```

---

### 10. [数据单位与财务计算规范](data-unit-standards.md) ⭐ NEW
**适用场景**: 成交量单位、财务指标计算、PE_TTM口径

**标准规范**:
- 成交量: 统一使用"手"（1手=100股）
- 财务数据: 统一使用"亿元"
- PE_TTM: 总市值 / TTM净利润（不是单季度！）

**数据源单位对照**:
| 数据源 | 成交量 | 成交额 |
|--------|--------|--------|
| Tushare | 手 | 元 |
| AKShare | 手 | 元 |
| BaoStock | 股→需转换 | 元 |

---

### 11. [数据源字段名映射不匹配问题](data-source-field-mapping.md) ⭐⭐ NEW
**适用场景**: 报告中指标显示 N/A、多数据源字段名不一致

**常见字段映射**:
| 中文名称 | Tushare 字段 | 通用字段名 |
|---------|-------------|-----------|
| 营收同比增速 | `or_yoy` | `revenue_yoy` |
| 净利润同比增速 | `q_profit_yoy` | `net_income_yoy` |
| 筹资性现金流 | `n_cashflow_fin_act` | `financing_cashflow` |

**修复方案**: 添加多字段名映射支持，优先使用 Tushare 字段名

---

### 12. [数据源网络连接问题诊断](network-diagnostics.md) ⭐⭐ NEW
**适用场景**: ConnectionResetError、DNS 解析失败、多数据源同步失败

**诊断步骤**:
1. 基础网络检查 (ping/nslookup)
2. Python 诊断脚本测试
3. Token 有效性验证
4. 启用备选数据源 (Baostock)

**快速修复**:
```bash
# 启用 Baostock 备选
BAOSTOCK_UNIFIED_ENABLED=true
```

---

## 快速参考

### 启动检查流程
```bash
# 1. 语法检查
python -m py_compile app/main.py

# 2. 导入检查
python -c "from app.main import app"

# 3. 运行单元测试
python -m pytest tests/unit/ -v
```

### 提交前检查清单
- [ ] 没有Python编码声明在TypeScript文件中
- [ ] 所有浮点数测试使用误差容忍比较
- [ ] logger已定义
- [ ] 类构造函数初始化所有属性
- [ ] 导入路径使用绝对路径
- [ ] 异步方法使用asyncio.Lock
- [ ] 数据源字段名与API返回字段名一致
- [ ] 添加了字段映射的备选方案

### 常见错误快速修复

#### Error: name 'logger' is not defined
```python
# 添加到文件顶部
import logging
logger = logging.getLogger(__name__)
```

#### Error: cannot import name 'X' from 'core.module'
```python
# 改为绝对导入
from app.core.module import X
```

#### AssertionError: assert 0.7500000000000001 == 0.75
```python
# 改为误差容忍比较
assert abs(result - expected) < 0.01
```

#### WebSocket 1006错误
```typescript
// 开发环境使用query string
const wsUrl = `ws://localhost:8000/api/ws/notifications?token=${token}`;
```

---

## 技能分类索引

### 按问题类型
- **启动错误**: #1, #2
- **WebSocket问题**: #3, #7
- **数据/API问题**: #4, #8, #10, #11, #12
- **测试问题**: #5
- **并发问题**: #9
- **数据质量**: #6, #10
- **网络连接**: #12
- **字段映射**: #11

### 按技术栈
- **Python**: #1, #4, #5, #6, #8, #9, #10, #11, #12
- **TypeScript/Vue**: #2, #3, #7
- **配置管理**: #8, #12
- **测试**: #5
- **网络诊断**: #12

---

## 更新记录

### 2026-02-07 (第一批)
- 初始版本，包含6个技能文件
  - python-startup-errors.md
  - ts-py-mixup-prevention.md
  - websocket-troubleshooting.md
  - dashscope-text-limit-handling.md
  - float-precision-testing.md
  - data-quality-checks.md

### 2026-02-07 (第二批) ⭐
- 从完整git历史中提取4个新技能
  - websocket-patterns.md (基于20+次提交)
  - data-source-configuration.md (基于15+次提交)
  - concurrency-async-patterns.md (基于10+次提交)
  - data-unit-standards.md (基于20+次提交)

### 2026-02-10 (第三批) ⭐⭐
- 基于最近提交记录新增2个技能
  - data-source-field-mapping.md (字段名映射不匹配)
  - network-diagnostics.md (数据源网络连接诊断)
- 更新 known-issues.md 添加新的问题记录

---

## 如何使用

1. **遇到问题时**: 先查看对应的技能文件
2. **开发新功能前**: 阅读相关技能避免踩坑
3. **代码审查时**: 对照技能检查清单
4. **新成员入职**: 作为项目知识库学习
5. **持续改进**: 遇到新问题及时补充到技能库

---

## 贡献指南

发现新的可复用模式？请按以下格式添加：

```markdown
### X. [技能名称](文件名.md)
**适用场景**: 

**关键要点**:
- 要点1
- 要点2

**代码示例**:
```python
# 示例代码
```
```

**原则**:
- 一个技能解决一类问题
- 包含具体的代码示例
- 提供检查清单
- 说明触发条件
