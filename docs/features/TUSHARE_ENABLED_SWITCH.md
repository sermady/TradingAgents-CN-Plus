# TUSHARE_ENABLED 开关功能说明

## 📋 功能概述

新增 `TUSHARE_ENABLED` 环境变量开关，允许用户在 `.env` 文件中快速禁用Tushare数据源，无需删除或注释Token配置。

## 🎯 使用场景

1. **临时禁用Tushare**：当Tushare API出现问题时，快速切换到其他数据源（AKShare、BaoStock）
2. **成本控制**：Tushare免费用户有调用频率限制，禁用可以避免不必要的API调用
3. **测试验证**：在测试环境下禁用付费数据源，使用免费数据源
4. **网络问题**：当Tushare服务无法访问时，快速切换到备用数据源

## 🔧 配置方法

### 1. 在 `.env` 文件中配置

```bash
# 禁用Tushare
TUSHARE_ENABLED=false

# 启用Tushare（默认）
TUSHARE_ENABLED=true
```

### 2. 支持的值格式

**启用Tushare**（以下所有值都会启用）:
- `true`, `True`, `TRUE`
- `1`
- `yes`, `Yes`, `YES`
- `on`, `On`, `ON`
- 默认值（如果未设置此变量）

**禁用Tushare**（以下所有值都会禁用）:
- `false`, `False`, `FALSE`
- `0`
- `no`, `No`, `NO`
- `off`, `Off`, `OFF`
- 空值

### 3. 数据源降级优先级

当Tushare被禁用时，系统会自动降级到以下数据源：

```
MongoDB缓存 → AKShare → BaoStock → TDX
```

## 📊 行为说明

### TUSHARE_ENABLED=false 时的行为

```python
# 1. 创建Tushare提供器
provider = TushareProvider()

# 2. 尝试连接
provider.connect_sync()

# 结果：
# ✅ 日志: "⏸️ [Tushare] TUSHARE_ENABLED=false，跳过Tushare数据源"
# ✅ connected = False
# ✅ 不调用任何Tushare API
# ✅ 自动降级到AKShare等其他数据源
```

### TUSHARE_ENABLED=true 时的行为

```python
# 1. 创建Tushare提供器
provider = TushareProvider()

# 2. 尝试连接
provider.connect_sync()

# 结果：
# ✅ 尝试从数据库读取Token
# ✅ 尝试从.env读取Token
# ✅ 调用stock_basic API测试连接
# ✅ 如果连接成功，connected = True
# ❌ 如果连接失败，降级到其他数据源
```

## 🧪 测试验证

运行测试脚本验证功能：

```bash
python scripts/test_tushare_enabled_switch.py
```

测试内容：
1. 测试 TUSHARE_ENABLED=false 时的跳过行为
2. 测试 TUSHARE_ENABLED=true 时的连接尝试
3. 测试各种值格式的大小写不敏感

## 🔍 日志输出

### 禁用时的日志

```
⏸️ [Tushare] TUSHARE_ENABLED=false，跳过Tushare数据源
```

### 启用时的日志

```
🔍 [步骤1] 开始从数据库读取 Tushare Token...
✅ [步骤1] 数据库中找到 Token (长度: 32)
🔍 [步骤2] 读取 .env 中的 Token...
⚠️ [步骤2] .env 中未找到 Token
🔄 [步骤3] 尝试使用数据库中的 Tushare Token (超时: 10秒)...
🔄 [步骤3.1] 调用 stock_basic API 测试连接...
✅ [步骤3.1] API 调用成功，返回数据: 1 条
✅ [步骤3.2] Tushare连接成功 (Token来源: 数据库)
```

## 💡 最佳实践

### 1. 生产环境配置

```bash
# 推荐：启用Tushare作为主要数据源
TUSHARE_ENABLED=true
TUSHARE_TOKEN=your_valid_token_here

# 同时配置AKShare作为备用
DEFAULT_CHINA_DATA_SOURCE=akshare
```

### 2. 测试环境配置

```bash
# 测试环境：禁用Tushare，使用免费数据源
TUSHARE_ENABLED=false
DEFAULT_CHINA_DATA_SOURCE=akshare
```

### 3. 网络问题时的临时处理

当Tushare服务不稳定时：

```bash
# 方案1: 快速禁用
TUSHARE_ENABLED=false

# 方案2: 调整数据源优先级
DEFAULT_CHINA_DATA_SOURCE=akshare
```

### 4. 成本控制

Tushare免费用户有调用频率限制：

```bash
# 日常使用：启用Tushare
TUSHARE_ENABLED=true

# 频繁调用时：禁用Tushare，使用AKShare
TUSHARE_ENABLED=false
```

## 📝 相关配置

其他数据源也有类似的开关：

```bash
# DeepSeek模型开关
DEEPSEEK_ENABLED=false

# AKShare统一数据同步开关
AKSHARE_UNIFIED_ENABLED=true

# BaoStock统一数据同步开关
BAOSTOCK_UNIFIED_ENABLED=true
```

## 🐛 故障排除

### 问题1: 修改.env后仍然使用Tushare

**原因**: 环境变量未重新加载

**解决**:
```bash
# 重启服务
docker-compose restart

# 或重新运行应用
python -m app.main
```

### 问题2: 禁用后数据获取失败

**原因**: 其他数据源未正确配置

**解决**:
1. 检查 `DEFAULT_CHINA_DATA_SOURCE` 设置
2. 确保AKShare或BaoStock可用
3. 查看日志中的降级信息

### 问题3: 日志中没有看到跳过信息

**原因**: 代码未使用最新版本

**解决**:
```bash
# 确保代码已更新
git pull

# 重新构建Docker镜像
docker-compose build

# 重启服务
docker-compose up -d
```

## 📚 相关文档

- [数据源配置指南](../../docs/configuration/data-sources-guide.md)
- [环境变量配置](../../.env.example)
- [数据源管理器](../../tradingagents/dataflows/data_source_manager.py)

## 🔄 版本历史

- **v1.0.0-preview**: 新增 `TUSHARE_ENABLED` 开关功能
- 支持大小写不敏感的布尔值
- 支持多种值格式（true/false, 1/0, yes/no, on/off）

---

**更新日期**: 2025-01-18
**作者**: TradingAgents-CN 开发团队
