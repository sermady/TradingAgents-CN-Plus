@echo off
chcp 65001 >nul
REM TradingAgents-CN Docker 健康检查脚本
REM 前后端分离架构 (FastAPI + Vue3)
REM 版本: v1.0.0-preview

echo ========================================
echo 🔍 TradingAgents-CN Docker 健康检查
echo ========================================
echo.

REM 获取脚本所在目录并切换到项目根目录
cd /d "%~dp0..\.."
echo 📂 项目目录: %CD%
echo.

REM 统计变量
set /a PASSED=0
set /a FAILED=0
set /a WARNINGS=0

REM ===================================
REM [1/6] 检查 Docker 环境
REM ===================================
echo [1/6] 检查 Docker 环境
echo ----------------------------------------

docker version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('docker version --format "{{.Server.Version}}" 2^>nul') do set DOCKER_VERSION=%%i
    echo [OK] ✅ Docker 运行正常 ^(版本: %DOCKER_VERSION%^)
    set /a PASSED+=1
) else (
    echo [FAIL] ❌ Docker 未运行或未安装
    set /a FAILED+=1
)

REM 检查 docker-compose
set COMPOSE_CMD=docker-compose
docker-compose version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('docker-compose version --short 2^>nul') do set COMPOSE_VERSION=%%i
    echo [OK] ✅ docker-compose 可用 ^(版本: %COMPOSE_VERSION%^)
    set /a PASSED+=1
) else (
    docker compose version >nul 2>&1
    if %errorlevel% equ 0 (
        set COMPOSE_CMD=docker compose
        for /f "tokens=*" %%i in ('docker compose version --short 2^>nul') do set COMPOSE_VERSION=%%i
        echo [OK] ✅ docker compose 可用 ^(版本: %COMPOSE_VERSION%^)
        set /a PASSED+=1
    ) else (
        echo [FAIL] ❌ docker-compose 未安装
        set /a FAILED+=1
    )
)

echo.

REM ===================================
REM [2/6] 检查容器状态
REM ===================================
echo [2/6] 检查容器状态
echo ----------------------------------------

REM 检查 backend 容器
for /f "tokens=*" %%i in ('docker inspect --format "{{.State.Status}}" tradingagents-backend 2^>nul') do set STATUS=%%i
if "%STATUS%"=="running" (
    echo [OK] ✅ tradingagents-backend: 运行中
    set /a PASSED+=1
) else if "%STATUS%"=="exited" (
    echo [FAIL] ❌ tradingagents-backend: 已停止
    set /a FAILED+=1
) else (
    echo [FAIL] ❌ tradingagents-backend: 未创建
    set /a FAILED+=1
)

REM 检查 frontend 容器
for /f "tokens=*" %%i in ('docker inspect --format "{{.State.Status}}" tradingagents-frontend 2^>nul') do set STATUS=%%i
if "%STATUS%"=="running" (
    echo [OK] ✅ tradingagents-frontend: 运行中
    set /a PASSED+=1
) else if "%STATUS%"=="exited" (
    echo [FAIL] ❌ tradingagents-frontend: 已停止
    set /a FAILED+=1
) else (
    echo [FAIL] ❌ tradingagents-frontend: 未创建
    set /a FAILED+=1
)

REM 检查 mongodb 容器
for /f "tokens=*" %%i in ('docker inspect --format "{{.State.Status}}" tradingagents-mongodb 2^>nul') do set STATUS=%%i
if "%STATUS%"=="running" (
    echo [OK] ✅ tradingagents-mongodb: 运行中
    set /a PASSED+=1
) else if "%STATUS%"=="exited" (
    echo [FAIL] ❌ tradingagents-mongodb: 已停止
    set /a FAILED+=1
) else (
    echo [FAIL] ❌ tradingagents-mongodb: 未创建
    set /a FAILED+=1
)

REM 检查 redis 容器
for /f "tokens=*" %%i in ('docker inspect --format "{{.State.Status}}" tradingagents-redis 2^>nul') do set STATUS=%%i
if "%STATUS%"=="running" (
    echo [OK] ✅ tradingagents-redis: 运行中
    set /a PASSED+=1
) else if "%STATUS%"=="exited" (
    echo [FAIL] ❌ tradingagents-redis: 已停止
    set /a FAILED+=1
) else (
    echo [FAIL] ❌ tradingagents-redis: 未创建
    set /a FAILED+=1
)

echo.

REM ===================================
REM [3/6] 检查服务端口
REM ===================================
echo [3/6] 检查服务端口
echo ----------------------------------------

REM 检查前端端口 3000
curl -s --connect-timeout 3 http://localhost:3000 >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] ✅ 端口 3000 ^(前端^): 可访问
    set /a PASSED+=1
) else (
    echo [FAIL] ❌ 端口 3000 ^(前端^): 不可访问
    set /a FAILED+=1
)

REM 检查后端端口 8000
curl -s --connect-timeout 3 http://localhost:8000/api/health >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] ✅ 端口 8000 ^(后端API^): 可访问
    set /a PASSED+=1
) else (
    echo [FAIL] ❌ 端口 8000 ^(后端API^): 不可访问
    set /a FAILED+=1
)

echo.

REM ===================================
REM [4/6] 检查 API 健康状态
REM ===================================
echo [4/6] 检查 API 健康状态
echo ----------------------------------------

REM 后端健康检查
for /f "tokens=*" %%i in ('curl -s --connect-timeout 5 http://localhost:8000/api/health 2^>nul') do set HEALTH_RESPONSE=%%i
if defined HEALTH_RESPONSE (
    echo %HEALTH_RESPONSE% | findstr /C:"healthy" /C:"ok" >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] ✅ 后端 API 健康检查通过
        set /a PASSED+=1
    ) else (
        echo [WARN] ⚠️ 后端 API 返回异常状态
        set /a WARNINGS+=1
    )
) else (
    echo [FAIL] ❌ 后端 API 无响应
    set /a FAILED+=1
)

REM 前端健康检查
for /f "tokens=*" %%i in ('curl -s --connect-timeout 5 -o nul -w "%%{http_code}" http://localhost:3000 2^>nul') do set HTTP_CODE=%%i
if "%HTTP_CODE%"=="200" (
    echo [OK] ✅ 前端服务健康检查通过
    set /a PASSED+=1
) else (
    echo [FAIL] ❌ 前端服务返回状态码: %HTTP_CODE%
    set /a FAILED+=1
)

echo.

REM ===================================
REM [5/6] 检查数据库连接
REM ===================================
echo [5/6] 检查数据库连接
echo ----------------------------------------

REM MongoDB 检查
docker exec tradingagents-mongodb mongo --eval "db.adminCommand('ping')" -u admin -p tradingagents123 --authenticationDatabase admin --quiet >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] ✅ MongoDB 连接正常
    set /a PASSED+=1
) else (
    echo [FAIL] ❌ MongoDB 连接失败
    set /a FAILED+=1
)

REM Redis 检查
for /f "tokens=*" %%i in ('docker exec tradingagents-redis redis-cli -a tradingagents123 ping 2^>nul') do set REDIS_PING=%%i
if "%REDIS_PING%"=="PONG" (
    echo [OK] ✅ Redis 连接正常
    set /a PASSED+=1
) else (
    echo [FAIL] ❌ Redis 连接失败
    set /a FAILED+=1
)

echo.

REM ===================================
REM [6/6] 检查资源使用
REM ===================================
echo [6/6] 检查资源使用
echo ----------------------------------------

echo 容器资源使用情况:
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" tradingagents-backend tradingagents-frontend tradingagents-mongodb tradingagents-redis 2>nul
if %errorlevel% neq 0 (
    echo 无法获取资源使用信息
)

echo.

REM ===================================
REM 总结
REM ===================================
echo ========================================
echo 📊 检查结果总结
echo ========================================
echo.
echo 通过: %PASSED%
echo 失败: %FAILED%
echo 警告: %WARNINGS%
echo.

if %FAILED% equ 0 (
    echo 🎉 所有检查通过！服务运行正常。
    echo.
    echo 🌐 访问地址:
    echo    前端界面: http://localhost:3000
    echo    后端API:  http://localhost:8000
    echo    API文档:  http://localhost:8000/docs
    set EXIT_CODE=0
) else if %FAILED% leq 2 (
    echo ⚠️ 部分服务可能存在问题，请检查上述失败项。
    set EXIT_CODE=1
) else (
    echo ❌ 多个服务存在问题，请检查 Docker 容器状态。
    echo.
    echo 💡 故障排查建议:
    echo    1. 查看容器日志: %COMPOSE_CMD% logs -f
    echo    2. 重启服务: %COMPOSE_CMD% restart
    echo    3. 重建服务: %COMPOSE_CMD% up -d --build
    set EXIT_CODE=2
)

echo.
pause
exit /b %EXIT_CODE%
