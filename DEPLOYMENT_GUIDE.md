# 增强功能部署指南

## 📋 部署前检查清单

- [ ] 所有新模块文件已创建
- [ ] .env 配置已更新
- [ ] 测试脚本运行通过
- [ ] 备份当前配置

---

## 🚀 快速开始

### 步骤 1: 验证文件

```bash
# 检查所有新模块是否存在
ls -la tradingagents/graph/parallel_analysts_v2.py
ls -la tradingagents/cache/llm_cache_enhanced.py
ls -la app/core/redis_client_enhanced.py
ls -la app/services/progress/tracker_enhanced.py
ls -la app/services/enhancements_integration.py
```

### 步骤 2: 运行测试

```bash
# 运行集成测试
python scripts/test_enhancements.py
```

预期输出：
```
============================================================
Enhancements Integration Test
============================================================

Test 1: Enhancements Config Module
  [OK] Config module imported

Test 2: Enhanced Parallel Executor
  [OK] Parallel executor imported

Test 3: Enhanced LLM Cache
  [OK] Cache read/write test passed

Test 4: Enhanced Progress Tracker
  [OK] Progress tracker created
  Steps: 20

Test 5: Graph Module Exports
  [OK] Graph exports working

============================================================
All tests completed!
============================================================
```

### 步骤 3: 启用增强功能

编辑 `.env` 文件，启用需要的功能：

```bash
# ===== 增强功能配置 =====

# 启用增强型并行执行
ENABLE_ENHANCED_PARALLEL_EXECUTION=true

# 启用增强型LLM缓存
ENABLE_ENHANCED_LLM_CACHE=true
LLM_CACHE_BACKEND=redis  # 或 memory, file

# 启用增强型Redis客户端
ENABLE_ENHANCED_REDIS_CLIENT=true

# 启用增强型进度跟踪
ENABLE_ENHANCED_PROGRESS_TRACKER=true

# 超时配置
ANALYST_TIMEOUT_SECONDS=180
ANALYST_ALLOW_PARTIAL_FAILURE=true
```

### 步骤 4: 重启应用

```bash
# Docker部署
docker-compose restart

# 本地开发
python -m app
```

---

## ⚙️ 配置详解

### 功能开关

| 环境变量 | 说明 | 默认值 | 建议 |
|---------|------|--------|------|
| `ENABLE_ENHANCED_PARALLEL_EXECUTION` | 增强型并行执行 | false | 建议启用 |
| `ENABLE_ENHANCED_LLM_CACHE` | 增强型LLM缓存 | false | 建议启用 |
| `ENABLE_ENHANCED_REDIS_CLIENT` | 增强型Redis客户端 | false | 建议启用 |
| `ENABLE_ENHANCED_PROGRESS_TRACKER` | 增强型进度跟踪 | false | 建议启用 |

### 超时配置

| 环境变量 | 说明 | 默认值 | 建议 |
|---------|------|--------|------|
| `ANALYST_TIMEOUT_SECONDS` | 分析师超时(秒) | 180 | 120-300 |
| `ANALYST_ALLOW_PARTIAL_FAILURE` | 允许部分失败 | true | true |

### 缓存配置

| 环境变量 | 说明 | 可选值 | 默认值 |
|---------|------|--------|--------|
| `LLM_CACHE_BACKEND` | 缓存后端 | memory/redis/file | memory |
| `LLM_CACHE_MAX_SIZE` | 最大缓存数 | - | 10000 |
| `LLM_CACHE_DEFAULT_TTL` | 默认TTL(秒) | - | 3600 |

### Redis配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `REDIS_MAX_RETRIES` | 连接重试次数 | 3 |
| `REDIS_RETRY_DELAY` | 初始重试延迟(秒) | 1.0 |

---

## 🧪 渐进式启用建议

建议按以下顺序逐步启用功能：

### 第一阶段：LLM缓存

```bash
ENABLE_ENHANCED_LLM_CACHE=true
LLM_CACHE_BACKEND=memory  # 先使用内存测试
```

**验证：**
- 观察缓存命中率
- 检查API调用次数是否减少

### 第二阶段：进度跟踪

```bash
ENABLE_ENHANCED_PROGRESS_TRACKER=true
```

**验证：**
- 查看进度更新是否更细粒度
- 检查时间预估是否更准确

### 第三阶段：Redis客户端

```bash
ENABLE_ENHANCED_REDIS_CLIENT=true
```

**验证：**
- 检查Redis连接是否更稳定
- 查看连接统计信息

### 第四阶段：并行执行

```bash
ENABLE_ENHANCED_PARALLEL_EXECUTION=true
```

**验证：**
- 测试分析师超时功能
- 验证部分失败模式

---

## 📊 监控指标

### 缓存统计

```python
from tradingagents.cache.llm_cache_enhanced import get_cache_stats

stats = get_cache_stats()
print(f"缓存命中率: {stats['hit_rate']}")
print(f"缓存大小: {stats['size']}")
```

### Redis连接统计

```python
from app.core.redis_client_enhanced import get_connection_stats

stats = get_connection_stats()
print(f"连接尝试: {stats['connection_attempts']}")
print(f"连接失败: {stats['connection_failures']}")
print(f"重连次数: {stats['reconnect_count']}")
```

### 增强功能状态

```python
from app.services.enhancements_integration import get_enhancements_status

status = get_enhancements_status()
print(status)
```

---

## 🔧 故障排除

### 问题1: 模块导入失败

**症状：**
```
ModuleNotFoundError: No module named 'tradingagents.cache.llm_cache_enhanced'
```

**解决：**
1. 检查文件是否存在
2. 确认项目根目录在 Python 路径中
3. 重新运行测试脚本

### 问题2: Redis连接失败

**症状：**
```
Redis连接失败，回退到文件存储
```

**解决：**
1. 检查Redis服务是否运行
2. 检查 `.env` 中的 Redis 配置
3. 系统会自动回退到文件存储，不影响功能

### 问题3: 超时设置不生效

**症状：**
分析师执行超过设置的超时时间

**解决：**
1. 确认 `ENABLE_ENHANCED_PARALLEL_EXECUTION=true`
2. 检查 `ANALYST_TIMEOUT_SECONDS` 值
3. 查看日志确认使用的是增强型执行器

### 问题4: 进度不更新

**症状：**
进度条长时间不变化

**解决：**
1. 确认 `ENABLE_ENHANCED_PROGRESS_TRACKER=true`
2. 检查 Redis/文件存储是否可用
3. 查看日志中的进度更新消息

---

## 🔄 回滚方案

如需禁用所有增强功能：

```bash
# 编辑 .env 文件
ENABLE_ENHANCED_PARALLEL_EXECUTION=false
ENABLE_ENHANCED_LLM_CACHE=false
ENABLE_ENHANCED_REDIS_CLIENT=false
ENABLE_ENHANCED_PROGRESS_TRACKER=false

# 重启应用
docker-compose restart
```

系统将自动回退到原始版本的功能模块。

---

## 📈 性能对比

启用增强功能后的预期性能提升：

| 指标 | 原始版本 | 增强版本 | 提升 |
|------|---------|---------|------|
| 分析速度 | 基准 | +30-50% | 并行优化 |
| API调用 | 基准 | -20-40% | 缓存命中 |
| Redis稳定性 | 基准 | +显著 | 重试机制 |
| 进度精度 | 基准 | +显著 | 细粒度跟踪 |

---

## 📝 更新日志

### v1.1.0 (2026-02-12)
- 新增增强型并行执行器
- 新增增强型LLM缓存
- 新增增强型Redis客户端
- 新增增强型进度跟踪器
- 新增功能配置集成模块

---

## 💡 最佳实践

1. **从小规模开始**：先在一台服务器上测试
2. **监控指标**：关注缓存命中率和错误率
3. **逐步启用**：一次启用一个功能，观察稳定后再启用下一个
4. **保留日志**：初期启用详细日志，便于排查问题
5. **备份配置**：修改 `.env` 前备份原始配置

---

## 📞 支持

如有问题，请检查：
1. `IMPROVEMENTS_SUMMARY.md` - 功能详细说明
2. `scripts/test_enhancements.py` - 运行测试
3. 应用日志 - 查看详细错误信息

---

**部署日期**: 2026-02-12
**版本**: v1.1.0
**作者**: Claude
