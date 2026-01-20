# Docker 脚本目录

TradingAgents-CN Docker 容器管理脚本

## 架构说明

项目采用前后端分离架构：
- **后端**: FastAPI (端口 8000)
- **前端**: Vue3 + Nginx (端口 3000)
- **数据库**: MongoDB (端口 27017)
- **缓存**: Redis (端口 6379)

## 脚本列表

| 脚本 | 说明 |
|------|------|
| `start_docker_services.sh` | Linux/Mac 启动脚本 |
| `start_docker_services.bat` | Windows 启动脚本 |
| `stop_docker_services.sh` | Linux/Mac 停止脚本 |
| `stop_docker_services.bat` | Windows 停止脚本 |
| `check_docker_health.sh` | Linux/Mac 健康检查脚本 |
| `check_docker_health.bat` | Windows 健康检查脚本 |
| `docker-compose-start.bat` | Windows Docker Compose 快速启动 |
| `mongo-init.js` | MongoDB 初始化脚本 |

## 快速开始

### Linux / macOS

```bash
# 进入项目根目录
cd /path/to/TradingAgents-CN

# 启动服务
./scripts/docker/start_docker_services.sh

# 启动服务（包含管理工具）
./scripts/docker/start_docker_services.sh --with-management

# 停止服务
./scripts/docker/stop_docker_services.sh

# 健康检查
./scripts/docker/check_docker_health.sh
```

### Windows

```powershell
# 进入项目根目录
cd C:\path\to\TradingAgents-CN

# 启动服务
.\scripts\docker\start_docker_services.bat

# 启动服务（包含管理工具）
.\scripts\docker\start_docker_services.bat --with-management

# 停止服务
.\scripts\docker\stop_docker_services.bat

# 健康检查
.\scripts\docker\check_docker_health.bat
```

## 访问地址

启动成功后，可通过以下地址访问：

| 服务 | 地址 |
|------|------|
| 前端界面 | http://localhost:3000 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |
| MongoDB | mongodb://localhost:27017 |
| Redis | redis://localhost:6379 |

### 管理工具（可选）

使用 `--with-management` 或 `-m` 参数启动时可用：

| 服务 | 地址 | 账号/密码 |
|------|------|-----------|
| Redis Commander | http://localhost:8081 | - |
| Mongo Express | http://localhost:8082 | admin / tradingagents123 |

## 常用命令

```bash
# 查看容器状态
docker-compose ps

# 查看所有日志
docker-compose logs -f

# 查看后端日志
docker-compose logs -f backend

# 查看前端日志
docker-compose logs -f frontend

# 重启后端服务
docker-compose restart backend

# 重建并启动
docker-compose up -d --build

# 停止并删除容器
docker-compose down

# 完全清理（包括数据卷和镜像）
docker-compose down -v --rmi all
```

## 数据持久化

数据存储在 Docker 卷中，容器删除后数据仍会保留：

- `tradingagents_mongodb_data`: MongoDB 数据
- `tradingagents_redis_data`: Redis 数据

清理数据卷：
```bash
docker volume rm tradingagents_mongodb_data tradingagents_redis_data
```

## 故障排查

### 端口被占用

检查端口占用情况：
```bash
# Linux/Mac
lsof -i :3000
lsof -i :8000

# Windows
netstat -ano | findstr :3000
netstat -ano | findstr :8000
```

### 容器启动失败

查看详细日志：
```bash
docker-compose logs backend
docker-compose logs frontend
docker-compose logs mongodb
docker-compose logs redis
```

### 数据库连接失败

确保 MongoDB 和 Redis 容器正常运行：
```bash
docker-compose ps mongodb redis
```

## 相关文档

- [项目 README](../../README.md)
- [Docker 部署指南](../../docs/deployment/docker/)
- [环境配置说明](../../docs/deployment/v1.0.0-source-installation.md)