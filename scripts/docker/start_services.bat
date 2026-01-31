@echo off
chcp 65001

:: 启动 Docker 容器脚本
:: MongoDB + Redis 一键启动

echo =====================================================
echo    TradingAgents-CN Docker 服务启动脚本
echo =====================================================
echo.

:: 检查 Docker 是否运行
docker info >nul 2>&1
if errorlevel 1 (
    echo [错误] Docker 没有运行，请先启动 Docker Desktop
    echo.
    pause
    exit /b 1
)

:: 停止并删除现有容器（如果存在）
echo [1/4] 清理现有容器...
docker stop mongo redis 2>nul
docker rm mongo redis 2>nul

:: 创建数据卷
echo [2/4] 创建数据卷...
docker volume create mongo_data 2>nul
docker volume create redis_data 2>nul

:: 启动 MongoDB
echo [3/4] 启动 MongoDB...
docker run -d --name mongo \
    -p 27017:27017 \
    -v mongo_data:/data/db \
    -e MONGO_INITDB_ROOT_USERNAME=admin \
    -e MONGO_INITDB_ROOT_PASSWORD=admin123 \
    --restart unless-stopped \
    mongo:6.0

if errorlevel 1 (
    echo [错误] MongoDB 启动失败
    pause
    exit /b 1
)
echo ✅ MongoDB 启动成功 (端口: 27017)

:: 启动 Redis
echo [4/4] 启动 Redis...
docker run -d --name redis \
    -p 6379:6379 \
    -v redis_data:/data \
    --restart unless-stopped \
    redis:7-alpine

if errorlevel 1 (
    echo [错误] Redis 启动失败
    pause
    exit /b 1
)
echo ✅ Redis 启动成功 (端口: 6379)

echo.
echo =====================================================
echo    服务启动完成！
echo =====================================================
echo.
echo MongoDB:
echo   - 地址: localhost:27017
echo   - 用户名: admin
echo   - 密码: admin123
echo   - 管理界面: http://localhost:27017 (需安装 MongoDB Compass)
echo.
echo Redis:
echo   - 地址: localhost:6379
echo   - 无密码（开发环境）
echo   - 管理界面: 使用 Redis Insight 或 redis-cli
echo.
echo 测试连接:
echo   docker exec mongo mongosh --eval "db.adminCommand('ping')"
echo   docker exec redis redis-cli ping
echo.
echo 停止服务:
echo   docker stop mongo redis
echo.
echo 查看日志:
echo   docker logs -f mongo
echo   docker logs -f redis
echo.
pause
