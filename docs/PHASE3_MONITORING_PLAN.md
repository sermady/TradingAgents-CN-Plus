# TradingAgents-CN 阶段3监控调优计划

> **计划版本**: v1.0.0
> **创建日期**: 2026-01-19
> **预计耗时**: 持续进行
> **风险等级**: 低
> **优先级**: 建议（持续改进）

---

## 🎯 阶段3目标

建立完善的性能监控和持续调优体系，确保系统长期稳定运行。

### 核心目标

1. **实时监控**: 监控关键性能指标
2. **问题预警**: 及时发现性能下降
3. **数据分析**: 收集和分析性能数据
4. **持续优化**: 基于数据驱动优化

---

## 📊 监控指标体系

### 1. 应用层指标

#### API性能指标

| 指标 | 目标值 | 告警阈值 | 说明 |
|------|--------|---------|------|
| **API平均响应时间** | <0.3秒 | >0.5秒 | 所有API端点 |
| **API P95响应时间** | <0.5秒 | >1.0秒 | 95%请求 |
| **API P99响应时间** | <1.0秒 | >2.0秒 | 99%请求 |
| **API错误率** | <0.1% | >1% | 5xx错误 |
| **API QPS** | - | >100 | 每秒请求数 |

#### 健康检查指标

| 指标 | 目标值 | 告警阈值 | 说明 |
|------|--------|---------|------|
| **健康检查响应时间** | <0.1秒 | >0.3秒 | /api/health |
| **深度健康检查时间** | <0.5秒 | >1.0秒 | /api/health/detailed |
| **缓存命中率** | >70% | <50% | 缓存效果 |

---

### 2. 基础设施指标

#### 容器资源指标

| 指标 | 正常范围 | 告警阈值 | 说明 |
|------|---------|---------|------|
| **CPU使用率** | <70% | >90% | 持续5分钟 |
| **内存使用率** | <80% | >95% | Backend容器 |
| **网络I/O** | <100MB/s | >500MB/s | 持续5分钟 |
| **磁盘I/O** | <50MB/s | >200MB/s | 持续5分钟 |

#### 数据库指标

| 指标 | 正常范围 | 告警阈值 | 说明 |
|------|---------|---------|------|
| **MongoDB连接数** | <40 | >45 | 最大50 |
| **Redis连接数** | <50 | >90 | 最大100 |
| **MongoDB查询延迟** | <50ms | >200ms | P95 |
| **Redis命令延迟** | <10ms | >50ms | P95 |
| **缓存命中率** | >60% | <40% | Redis缓存 |

---

### 3. 业务指标

| 指标 | 说明 | 数据源 |
|------|------|--------|
| **活跃用户数** | 日活用户数 | MongoDB |
| **分析任务数** | 每日分析任务 | MongoDB |
| **平均分析时间** | 单次分析耗时 | 日志 |
| **任务失败率** | 分析失败比例 | 日志 |
| **数据同步状态** | 数据源同步情况 | 日志 |

---

## 🔧 监控实施方案

### 方案1: 使用Prometheus + Grafana（推荐）⭐⭐⭐⭐⭐

**优点**:
- 功能强大，社区活跃
- 丰富的可视化面板
- 灵活的告警规则
- 开源免费

**缺点**:
- 学习曲线较陡
- 需要额外部署监控服务

**实施步骤**:

#### 1.1 添加Prometheus监控端点

**文件**: `app/routers/metrics.py` (新建)

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response
import time

# 定义指标
api_request_count = Counter(
    'api_request_count',
    'API请求总数',
    ['method', 'endpoint', 'status']
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API请求耗时',
    ['method', 'endpoint']
)

api_request_duration.observe(duration)

active_connections = Gauge(
    'active_connections',
    '当前活跃连接数'
)

cache_hits = Counter(
    'cache_hits_total',
    '缓存命中次数',
    ['cache_type']
)

@router.get("/metrics")
async def metrics():
    """Prometheus监控端点"""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )
```

#### 1.2 集成到FastAPI

```python
# app/main.py
from prometheus_client import Counter
import time

@app.middleware("http")
async def monitor_middleware(request: Request, call_next):
    """监控中间件"""
    start_time = time.time()
    
    # 执行请求
    response = await call_next(request)
    
    # 记录指标
    duration = time.time() - start_time
    api_request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    api_request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    return response
```

#### 1.3 部署Prometheus

**文件**: `docker-compose.yml`

```yaml
  prometheus:
    image: prom/prometheus:latest
    container_name: tradingagents-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - tradingagents-network
    profiles:
      - monitoring
```

**配置文件**: `monitoring/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'tradingagents'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
```

#### 1.4 部署Grafana

**文件**: `docker-compose.yml`

```yaml
  grafana:
    image: grafana/grafana:latest
    container_name: tradingagents-grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana-dashboards:/etc/grafana/provisioning/dashboards
    networks:
      - tradingagents-network
    depends_on:
      - prometheus
    profiles:
      - monitoring
```

#### 1.5 导入仪表板

**推荐仪表板**:
- FastAPI Dashboard (ID: 14369)
- MongoDB Dashboard (ID: 2573)
- Redis Dashboard (ID: 11835)

**自定义仪表板**:
- 创建TradingAgents-CN专用仪表板
- 包含所有关键指标
- 设置告警规则

---

### 方案2: 使用内置日志监控（简单）⭐⭐⭐

**优点**:
- 无需额外部署
- 实施简单
- 成本低

**缺点**:
- 功能有限
- 可视化差
- 需要手动分析

**实施步骤**:

#### 2.1 添加性能日志

**文件**: `app/middleware/logging_middleware.py`

```python
import time
import logging

logger = logging.getLogger(__name__)

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """性能日志中间件"""
    start_time = time.time()
    
    # 执行请求
    response = await call_next(request)
    
    # 计算耗时
    duration = time.time() - start_time
    
    # 记录慢请求
    if duration > 1.0:
        logger.warning(
            f"Slow request: {request.method} {request.url.path} "
            f"took {duration:.3f}s"
        )
    
    # 记录所有请求
    logger.info(
        f"{request.method} {request.url.path} "
        f"{response.status_code} {duration:.3f}s"
    )
    
    return response
```

#### 2.2 定期分析日志

```bash
# 查看慢请求
grep "Slow request" logs/tradingagents.log | tail -20

# 统计API响应时间
grep "took" logs/tradingagents.log | \
  awk '{print $NF}' | \
  sort -n | \
  uniq -c

# 查看错误率
grep " 5" logs/tradingagents.log | wc -l
```

---

### 方案3: 使用APM工具（付费）⭐⭐⭐⭐

**推荐工具**:
- **Sentry**: 错误监控和性能追踪
- **Datadog**: 全栈监控（付费）
- **New Relic**: 应用性能监控（付费）

**Sentry集成示例**:

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,  # 10%采样
    environment="production"
)
```

---

## 📈 数据收集和分析

### 数据收集策略

#### 短期数据（实时）

- 保存时间: 7天
- 粒度: 15秒
- 用途: 实时监控和告警

#### 中期数据（趋势）

- 保存时间: 90天
- 粒度: 1小时
- 用途: 趋势分析和容量规划

#### 长期数据（历史）

- 保存时间: 1年
- 粒度: 1天
- 用途: 历史对比和年度报告

---

### 性能基线建立

#### 步骤1: 收集基线数据

在系统正常运行期间收集7天数据：

- API平均响应时间
- API P95/P99响应时间
- 资源使用率
- 错误率

#### 步骤2: 确定基线值

计算各项指标的平均值和分位数：

```
基线响应时间 = P50值
正常范围 = [P25, P75]
告警阈值 = P99
```

#### 步骤3: 设置告警规则

基于基线值设置告警：

```python
# 伪代码
if current_response_time > baseline_p99 * 1.5:
    trigger_alert("响应时间异常")
```

---

## ⚠️ 告警规则配置

### 告警级别

| 级别 | 说明 | 响应时间 | 通知方式 |
|------|------|---------|---------|
| **P0 - 严重** | 服务不可用 | 立即 | 电话+短信+邮件 |
| **P1 - 高** | 性能严重下降 | 15分钟内 | 邮件+IM |
| **P2 - 中** | 性能轻微下降 | 1小时内 | 邮件 |
| **P3 - 低** | 指标异常 | 1天内 | 日志记录 |

### 告警规则示例

#### 规则1: API响应时间过高

```yaml
# prometheus/alerts.yml
- alert: HighAPILatency
  expr: api_request_duration_seconds{quantile="0.95"} > 1.0
  for: 5m
  labels:
    severity: P1
  annotations:
    summary: "API响应时间过高"
    description: "P95响应时间超过1秒，当前值: {{ $value }}秒"
```

#### 规则2: 错误率过高

```yaml
- alert: HighErrorRate
  expr: rate(api_request_count{status=~"5.."}[5m]) > 0.01
  for: 5m
  labels:
    severity: P0
  annotations:
    summary: "API错误率过高"
    description: "5xx错误率超过1%，当前值: {{ $value }}%"
```

#### 规则3: 容器资源不足

```yaml
- alert: ContainerHighCPU
  expr: rate(container_cpu_usage_seconds_total{name="backend"}[5m]) > 0.8
  for: 10m
  labels:
    severity: P2
  annotations:
    summary: "Backend容器CPU使用率过高"
    description: "CPU使用率超过80%，当前值: {{ $value }}%"
```

---

## 🔄 持续优化流程

### 优化循环

```
监控数据 → 问题识别 → 根因分析 → 优化实施 → 效果验证 → 监控数据
   ↑                                                           ↓
   └─────────────────────── 持续改进 ←──────────────────────────┘
```

### 优化案例

#### 案例1: 发现慢查询

**监控数据发现**:
- `/api/analysis/start` 响应时间 > 5秒
- MongoDB查询耗时 > 3秒

**根因分析**:
- 缺少索引
- 查询返回大量数据

**优化实施**:
- 添加索引
- 分页返回数据

**效果验证**:
- 响应时间: 5秒 → 0.8秒
- 查询时间: 3秒 → 0.3秒

#### 案例2: 发现内存泄漏

**监控数据发现**:
- Backend容器内存使用持续增长
- 7天后从200MB增长到2GB

**根因分析**:
- 连接池未正确释放
- 缓存无限增长

**优化实施**:
- 修复连接池释放逻辑
- 添加缓存大小限制

**效果验证**:
- 内存使用稳定在300MB
- 无泄漏现象

---

## 📊 性能报告

### 日报（自动生成）

**内容**:
- 今日API平均响应时间
- 今日API请求总数
- 今日错误率
- 今日资源使用峰值
- Top 10慢请求

### 周报（自动生成）

**内容**:
- 本周性能趋势图
- 本周告警统计
- 本周性能优化成果
- 下周优化建议

### 月报（人工分析）

**内容**:
- 月度性能总结
- 性能改进前后对比
- 容量规划建议
- 技术债务清单

---

## 🛠️ 实施时间表

### 第1周: 监控基础设施部署

- [ ] 部署Prometheus
- [ ] 部署Grafana
- [ ] 配置监控端点
- [ ] 导入仪表板

### 第2周: 告警规则配置

- [ ] 定义告警规则
- [ ] 配置告警通知
- [ ] 测试告警功能
- [ ] 调整阈值

### 第3-4周: 数据收集和基线建立

- [ ] 收集7天基线数据
- [ ] 计算基线值
- [ ] 设置告警阈值
- [ ] 编写监控文档

### 持续: 优化和改进

- [ ] 每周审查监控数据
- [ ] 分析性能瓶颈
- [ ] 实施优化措施
- [ ] 验证优化效果

---

## 📝 文档和培训

### 监控文档

- [ ] 监控系统架构文档
- [ ] 监控指标定义文档
- [ ] 告警处理手册
- [ ] 性能优化指南

### 团队培训

- [ ] 监控系统使用培训
- [ ] 告警处理流程培训
- [ ] 性能优化最佳实践分享

---

## 🎯 总结

**阶段3监控调优**是一个持续改进的过程，建议：

1. **先建立监控**: 确保可观测性
2. **收集基线数据**: 了解正常状态
3. **设置合理告警**: 及时发现问题
4. **持续优化**: 基于数据驱动决策

**预期收益**:
- 问题发现时间: 从小时级降到分钟级
- 问题解决效率: 提升50%
- 系统稳定性: 提升30%
- 用户满意度: 显著提升

---

**文档版本**: v1.0.0
**创建日期**: 2026-01-19
**维护者**: Droid AI Assistant
