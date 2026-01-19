@echo off
chcp 65001 >nul
REM TradingAgents-CN Docker 服务停止脚本
REM 前后端分离架构 (FastAPI + Vue3)
REM 版本: v1.0.0-preview

echo ========================================
echo 🛑 TradingAgents-CN Docker 服务停止
echo ========================================
echo.

REM 获取脚本所在目录并切换到项目根目录
cd /d "%~dp0..\.."
echo 📂 项目目录: %CD%
echo.

REM 检查docker-compose
set COMPOSE_CMD=docker-compose
docker-compose version >nul 2>&1
if %errorlevel% neq 0 (
    docker compose version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] ❌ docker-compose未安装
        pause
        exit /b 1
    )
    set COMPOSE_CMD=docker compose
)
echo [OK] ✅ 使用: %COMPOSE_CMD%
echo.

REM 显示当前运行的容器
echo 📋 当前运行的容器:
%COMPOSE_CMD% ps
echo.

REM 停止服务
echo 🛑 停止所有服务...

REM 检查是否需要停止管理工具
if "%1"=="--all" goto stop_all
if "%1"=="-a" goto stop_all

%COMPOSE_CMD% down --remove-orphans
goto check_result

:stop_all
echo 📊 包含管理工具 ^(Redis Commander, Mongo Express^)
%COMPOSE_CMD% --profile management down --remove-orphans

:check_result
if %errorlevel% equ 0 (
    echo [OK] ✅ 服务停止成功
) else (
    echo [WARN] ⚠️ 部分服务可能已经停止
)

echo.

REM 检查剩余容器
echo 📋 检查剩余容器...
for /f "tokens=*" %%i in ('docker ps --filter "name=tradingagents-" --format "{{.Names}}" 2^>nul') do (
    set REMAINING=%%i
)

if not defined REMAINING (
    echo [OK] ✅ 所有 TradingAgents 容器已停止
) else (
    echo [WARN] ⚠️ 以下容器仍在运行:
    docker ps --filter "name=tradingagents-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo.
    echo 💡 手动停止: docker stop [容器名]
)

echo.
echo ========================================
echo ✅ 停止操作完成
echo ========================================
echo.
echo 💡 提示:
echo    - 数据已保存在 Docker 卷中，下次启动时会自动恢复
echo    - 重新启动: %COMPOSE_CMD% up -d
echo.
echo 🧹 如需完全清理数据:
echo    删除数据卷: docker volume rm tradingagents_mongodb_data tradingagents_redis_data
echo    删除镜像:   docker rmi tradingagents-backend:v1.0.0-preview tradingagents-frontend:v1.0.0-preview
echo    完全清理:   %COMPOSE_CMD% down -v --rmi all
echo.

pause
