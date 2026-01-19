@echo off
chcp 65001 >nul
REM TradingAgents-CN Docker 服务启动脚本
REM 前后端分离架构 (FastAPI + Vue3)
REM 版本: v1.0.0-preview

echo ========================================
echo 🐳 TradingAgents-CN Docker 服务启动
echo ========================================
echo 架构: FastAPI 后端 + Vue3 前端
echo.

REM 获取脚本所在目录并切换到项目根目录
cd /d "%~dp0..\.."
echo 📂 项目目录: %CD%
echo.

REM 检查Docker是否运行
echo 🔍 检查Docker服务状态...
docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] ❌ Docker未运行或未安装
    echo 请先启动 Docker Desktop
    pause
    exit /b 1
)
echo [OK] ✅ Docker服务正常

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

REM 创建必要的目录
echo.
echo 📁 创建必要目录...
if not exist "logs" mkdir logs
if not exist "data" mkdir data
if not exist "config" mkdir config
echo [OK] ✅ 目录准备完成

REM 检查.env文件
echo.
echo 🔧 检查配置文件...
if not exist ".env" (
    if exist ".env.docker" (
        echo 📋 复制.env.docker到.env
        copy /Y ".env.docker" ".env" >nul
        echo [OK] ✅ 已使用Docker默认配置
    ) else if exist ".env.example" (
        echo 📋 复制.env.example到.env
        copy /Y ".env.example" ".env" >nul
        echo [WARN] ⚠️ 请编辑.env文件配置API密钥
    ) else (
        echo [ERROR] ❌ 找不到配置模板文件
        pause
        exit /b 1
    )
) else (
    echo [OK] ✅ .env文件存在
)

REM 停止可能存在的旧容器
echo.
echo 🧹 清理旧容器...
%COMPOSE_CMD% down --remove-orphans >nul 2>&1

REM 启动服务
echo.
echo 🚀 启动Docker服务...

REM 检查是否需要启动管理工具
if "%1"=="--with-management" (
    echo 📊 包含管理工具 ^(Redis Commander, Mongo Express^)
    %COMPOSE_CMD% --profile management up -d
) else if "%1"=="-m" (
    echo 📊 包含管理工具 ^(Redis Commander, Mongo Express^)
    %COMPOSE_CMD% --profile management up -d
) else (
    %COMPOSE_CMD% up -d
)

if %errorlevel% neq 0 (
    echo [ERROR] ❌ Docker服务启动失败
    pause
    exit /b 1
)

REM 等待服务启动
echo.
echo ⏳ 等待服务启动...
timeout /t 5 /nobreak >nul

REM 显示容器状态
echo.
echo 📋 服务状态:
%COMPOSE_CMD% ps

REM 等待后端健康检查
echo.
echo 🔍 检查服务健康状态...
echo.
set /a MAX_WAIT=120
set /a WAIT_INTERVAL=5
set /a WAITED=0

:wait_backend
echo 等待后端服务 (backend:8000)...
curl -s http://localhost:8000/api/health >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] ✅ 后端服务已就绪
    goto check_frontend
)
if %WAITED% geq %MAX_WAIT% (
    echo [WARN] ⚠️ 后端服务启动超时，请检查日志
    goto check_frontend
)
timeout /t %WAIT_INTERVAL% /nobreak >nul
set /a WAITED=%WAITED%+%WAIT_INTERVAL%
goto wait_backend

:check_frontend
set /a WAITED=0

:wait_frontend
echo 等待前端服务 (frontend:3000)...
curl -s http://localhost:3000 >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] ✅ 前端服务已就绪
    goto show_info
)
if %WAITED% geq %MAX_WAIT% (
    echo [WARN] ⚠️ 前端服务启动超时，请检查日志
    goto show_info
)
timeout /t %WAIT_INTERVAL% /nobreak >nul
set /a WAITED=%WAITED%+%WAIT_INTERVAL%
goto wait_frontend

:show_info
REM 显示访问信息
echo.
echo ========================================
echo 🎉 Docker服务启动完成！
echo ========================================
echo.
echo 🌐 访问地址:
echo    前端界面: http://localhost:3000
echo    后端API:  http://localhost:8000
echo    API文档:  http://localhost:8000/docs
echo.
echo 🗄️ 数据库:
echo    MongoDB:  mongodb://admin:tradingagents123@localhost:27017/tradingagents
echo    Redis:    redis://:tradingagents123@localhost:6379
echo.

if "%1"=="--with-management" goto show_management
if "%1"=="-m" goto show_management
goto show_commands

:show_management
echo 🔧 管理界面:
echo    Redis Commander: http://localhost:8081
echo    Mongo Express:   http://localhost:8082 (用户: admin, 密码: tradingagents123)
echo.

:show_commands
echo 📋 常用命令:
echo    查看状态:   %COMPOSE_CMD% ps
echo    查看日志:   %COMPOSE_CMD% logs -f
echo    后端日志:   %COMPOSE_CMD% logs -f backend
echo    前端日志:   %COMPOSE_CMD% logs -f frontend
echo    停止服务:   %COMPOSE_CMD% down
echo    重启后端:   %COMPOSE_CMD% restart backend
echo    重建服务:   %COMPOSE_CMD% up -d --build
echo.
echo 💡 提示:
echo    - 首次启动可能需要几分钟来初始化数据库
echo    - 使用 '%COMPOSE_CMD% logs -f' 查看实时日志
echo    - 数据将持久化保存在 Docker 卷中
echo    - 启用管理工具: %~nx0 --with-management
echo.

pause
