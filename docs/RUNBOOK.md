# 运维部署手册

**生成日期**: 2026-02-18
**来源**: package.json, pyproject.toml, .env.example

---

## 目录

1. [部署程序](#部署程序)
2. [监控和告警](#监控和告警)
3. [常见问题和修复](#常见问题和修复)
4. [回滚程序](#回滚程序)
5. [备份和恢复](#备份和恢复)
6. [性能优化](#性能优化)

---

## 部署程序

### 系统要求

| 组件 | 最低配置 | 推荐配置 |
|-----|---------|---------|
| CPU | 4核 | 8核+ |
| 内存 | 8GB | 16GB+ |
| 磁盘 | 50GB SSD | 100GB+ SSD |
| 网络 | 10Mbps | 100Mbps+ |

### Docker 部署 (推荐)

```bash
# 1. 构建并启动服务
docker-compose up -d --build

# 2. 查看日志
docker-compose logs -f

# 3. 停止服务
docker-compose down

# 4. 重启服务
docker-compose restart
```

### 本地部署

#### 后端部署

```bash
# 1. 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 2. 启动服务
python -m app

# 或使用 uvicorn 直接启动
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### 前端部署

```bash
cd frontend

# 安装依赖
yarn install

# 开发模式
yarn dev

# 生产构建
yarn build

# 预览生产构建
yarn preview
```

### 生产环境配置

```env
# 生产环境必须修改
JWT_SECRET=your-random-secret-key-min-32-chars
CSRF_SECRET=your-random-csrf-secret
DEBUG=false
LOG_LEVEL=INFO

# 数据库连接池
MONGODB_MAX_CONNECTIONS=100
REDIS_MAX_CONNECTIONS=50
```

---

## 监控和告警

### 健康检查端点

| 端点 | 说明 | 预期响应 |
|-----|------|---------|
| `GET /health` | 服务健康状态 | `{"status": "ok"}` |
| `GET /api/health/db` | 数据库连接 | `{"mongodb": true, "redis": true}` |

### 关键指标监控

```bash
# 系统资源监控
watch -n 5 'df -h && free -h'

# Docker 容器监控
docker stats

# MongoDB 监控
mongostat --host localhost:27017

# Redis 监控
redis-cli INFO stats
```

### 日志监控

```bash
# 后端日志
tail -f backend.log

# Docker 日志
docker-compose logs -f --tail=100

# 按级别过滤日志
grep "ERROR" backend.log
grep "WARNING" backend.log
```

### 告警规则

| 指标 | 阈值 | 级别 |
|-----|------|------|
| CPU 使用率 | > 80% | 警告 |
| 内存使用率 | > 85% | 警告 |
| 磁盘使用率 | > 90% | 严重 |
| API 响应时间 | > 5s | 警告 |
| 错误率 | > 5% | 严重 |
| MongoDB 连接失败 | 任何失败 | 严重 |
| Redis 连接失败 | 任何失败 | 严重 |

---

## 常见问题和修复

### 1. 数据库连接问题

**症状**:
```
ERROR: Cannot connect to MongoDB
ERROR: Redis connection refused
```

**修复**:
```bash
# 检查服务状态
sudo systemctl status mongod
sudo systemctl status redis

# 重启服务
sudo systemctl restart mongod
sudo systemctl restart redis

# 检查端口监听
netstat -tlnp | grep 27017
netstat -tlnp | grep 6379
```

### 2. API 密钥失效

**症状**:
```
ERROR: Tushare API error: 权限不足
ERROR: DeepSeek API error: 401 Unauthorized
```

**修复**:
1. 检查 `.env` 中的 API 密钥
2. 验证密钥余额和有效期
3. 更新密钥并重启服务

### 3. 内存不足

**症状**:
```
ERROR: MemoryError
ERROR: Killed process (OOM)
```

**修复**:
```bash
# 增加交换空间
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 限制 Worker 数量
uvicorn app.main:app --workers 2  # 减少 worker
```

### 4. 磁盘空间不足

**症状**:
```
ERROR: No space left on device
WARNING: Disk usage > 90%
```

**修复**:
```bash
# 清理日志
find logs/ -name "*.log" -mtime +7 -delete

# 清理缓存
find cache/ -type f -mtime +3 -delete

# 清理 Docker
docker system prune -a

# 扩容磁盘
# (云服务器控制台操作)
```

### 5. 前端构建失败

**症状**:
```
ERROR: Build failed
ERROR: Out of memory
```

**修复**:
```bash
cd frontend

# 清理并重新安装
rm -rf node_modules dist
yarn install
yarn build

# 增加 Node 内存
export NODE_OPTIONS="--max-old-space-size=4096"
yarn build
```

### 6. 数据源同步失败

**症状**:
```
ERROR: Failed to sync stock data
ERROR: Tushare API limit exceeded
```

**修复**:
```bash
# 检查 API 限制
python scripts/validation/check_system_status.py

# 手动触发同步
python scripts/import/import_a_stocks_unified.py --data-source akshare

# 检查网络连接
curl -I https://api.tushare.pro
```

---

## 回滚程序

### Docker 部署回滚

```bash
# 1. 查看历史版本
docker-compose ps
docker images

# 2. 回滚到上一个版本
docker-compose down
docker-compose up -d --build --no-deps

# 3. 使用特定镜像版本
docker-compose down
docker pull tradingagents:previous-version
docker-compose up -d
```

### 代码回滚

```bash
# 查看提交历史
git log --oneline -10

# 回滚到上一个版本
git revert HEAD

# 或强制回滚到特定提交
git reset --hard <commit-hash>
git push origin main --force

# 重启服务
docker-compose restart
```

### 数据库回滚

```bash
# 从备份恢复 MongoDB
mongorestore --host localhost:27017 --db tradingagents backup/mongodb/

# 从备份恢复 Redis
redis-cli FLUSHDB
cat backup/redis/dump.rdb > /var/lib/redis/dump.rdb
systemctl restart redis
```

---

## 备份和恢复

### 自动备份脚本

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# 备份 MongoDB
mongodump --host localhost:27017 --db tradingagents --out $BACKUP_DIR/mongodb

# 备份 Redis
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb $BACKUP_DIR/redis/

# 备份配置文件
cp .env $BACKUP_DIR/
cp -r config/ $BACKUP_DIR/

# 压缩
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR

# 清理旧备份 (保留30天)
find /backup -name "*.tar.gz" -mtime +30 -delete
```

### 手动备份

```bash
# MongoDB
mongodump --host localhost:27017 --db tradingagents --out backup/mongodb/

# Redis
redis-cli SAVE
cp /var/lib/redis/dump.rdb backup/redis/
```

### 数据恢复

```bash
# MongoDB
mongorestore --host localhost:27017 --db tradingagents backup/mongodb/tradingagents/

# Redis
systemctl stop redis
cp backup/redis/dump.rdb /var/lib/redis/
systemctl start redis
```

---

## 性能优化

### 数据库优化

```bash
# MongoDB 索引优化
db.stock_daily_quotes.createIndex({"symbol": 1, "trade_date": -1})
db.stock_basic_info.createIndex({"code": 1})
db.stock_financial_data.createIndex({"code": 1, "report_period": -1})

# Redis 内存优化
redis-cli CONFIG SET maxmemory 2gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### 应用优化

```python
# uvicorn 配置优化
workers = 4  # CPU核心数 * 2 + 1
max_requests = 1000
max_requests_jitter = 50
timeout_keep_alive = 5
```

### 缓存策略

```python
# 启用多级缓存
TA_USE_APP_CACHE=true
TA_CACHE_BACKEND=redis

# 缓存过期时间
CACHE_TTL_SHORT=300      # 5分钟
CACHE_TTL_MEDIUM=3600    # 1小时
CACHE_TTL_LONG=86400     # 1天
```

---

## 安全检查清单

部署前必须检查:

- [ ] 修改默认 JWT_SECRET (至少32字符随机字符串)
- [ ] 修改默认 CSRF_SECRET
- [ ] 禁用 DEBUG 模式
- [ ] 配置 HTTPS
- [ ] 设置防火墙规则
- [ ] 启用日志轮转
- [ ] 配置监控告警
- [ ] 创建备份任务
- [ ] 更新所有默认密码

---

## 紧急联系

| 角色 | 联系方式 |
|-----|---------|
| 运维负责人 | - |
| 开发团队 | - |
| 数据库管理员 | - |

---

## 相关文档

- [CONTRIBUTING.md](./CONTRIBUTING.md) - 开发贡献指南
- [CLAUDE.md](../CLAUDE.md) - AI 助手指引
- [部署清单](./deployment_checklist_security_fixes.md) - 安全修复部署清单

---

**最后更新**: 2026-02-18
