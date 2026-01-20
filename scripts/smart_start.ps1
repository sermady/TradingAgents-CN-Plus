# TradingAgents-CN 智能Docker启动脚本 (PowerShell版本)
# 前后端分离架构 (FastAPI + Vue3)
# 版本: v1.0.0-preview
#
# 功能：自动判断是否需要重新构建Docker镜像
# 使用：.\scripts\smart_start.ps1
#
# 判断逻辑：
# 1. 检查是否存在 tradingagents-backend 和 tradingagents-frontend 镜像
# 2. 如果镜像不存在 -> 执行构建启动
# 3. 如果镜像存在但代码有变化 -> 执行构建启动
# 4. 如果镜像存在且代码无变化 -> 快速启动

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🚀 TradingAgents-CN Docker 智能启动脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "架构: FastAPI 后端 + Vue3 前端" -ForegroundColor Gray
Write-Host ""

# 获取脚本所在目录并切换到项目根目录
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot
Write-Host "📂 项目目录: $projectRoot" -ForegroundColor Cyan
Write-Host ""

# 检查 Docker 是否运行
try {
    docker info | Out-Null
    Write-Host "✅ Docker 运行正常" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker 未运行，请先启动 Docker Desktop" -ForegroundColor Red
    exit 1
}

# 检查 docker-compose
$composeCmd = "docker-compose"
try {
    docker-compose version | Out-Null
    Write-Host "✅ 使用: docker-compose" -ForegroundColor Green
} catch {
    try {
        docker compose version | Out-Null
        $composeCmd = "docker compose"
        Write-Host "✅ 使用: docker compose" -ForegroundColor Green
    } catch {
        Write-Host "❌ docker-compose 未安装" -ForegroundColor Red
        exit 1
    }
}

# 创建必要的目录
$directories = @("logs", "data", "config")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# 检查 .env 文件
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.docker") {
        Copy-Item ".env.docker" ".env"
        Write-Host "✅ 已使用 Docker 默认配置" -ForegroundColor Green
    } elseif (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "⚠️ 请编辑 .env 文件配置 API 密钥" -ForegroundColor Yellow
    }
}

# 检查镜像是否存在
$backendExists = $false
$frontendExists = $false

$images = docker images --format "{{.Repository}}" 2>$null
if ($images -match "tradingagents-backend") {
    $backendExists = $true
    Write-Host "✅ 发现后端镜像" -ForegroundColor Green
} else {
    Write-Host "⚠️ 后端镜像不存在" -ForegroundColor Yellow
}

if ($images -match "tradingagents-frontend") {
    $frontendExists = $true
    Write-Host "✅ 发现前端镜像" -ForegroundColor Green
} else {
    Write-Host "⚠️ 前端镜像不存在" -ForegroundColor Yellow
}

# 判断是否需要构建
$needBuild = $false

if (-not $backendExists -or -not $frontendExists) {
    $needBuild = $true
    Write-Host "🏗️ 首次运行或镜像缺失，需要构建" -ForegroundColor Cyan
} else {
    # 检查是否是 Git 仓库
    if (Test-Path ".git") {
        try {
            $gitDiff = git diff --quiet "HEAD~1" HEAD -- . ':!*.md' ':!docs/' ':!scripts/' 2>$null
            if ($LASTEXITCODE -ne 0) {
                $needBuild = $true
                Write-Host "🔄 检测到代码变化，需要重新构建" -ForegroundColor Cyan
            } else {
                Write-Host "📦 代码无变化，使用快速启动" -ForegroundColor Green
            }
        } catch {
            Write-Host "⚠️ Git 检查失败，跳过变化检测" -ForegroundColor Yellow
        }
    } else {
        Write-Host "⚠️ 非 Git 仓库，跳过变化检测" -ForegroundColor Yellow
    }
}

# 停止可能存在的旧容器
Write-Host ""
Write-Host "🧹 清理旧容器..." -ForegroundColor Yellow
if ($composeCmd -eq "docker compose") {
    docker compose down --remove-orphans 2>$null
} else {
    docker-compose down --remove-orphans 2>$null
}

# 启动服务
Write-Host ""
if ($needBuild) {
    Write-Host "🏗️ 构建并启动服务..." -ForegroundColor Yellow
    if ($composeCmd -eq "docker compose") {
        docker compose up -d --build
    } else {
        docker-compose up -d --build
    }
} else {
    Write-Host "🚀 快速启动服务..." -ForegroundColor Yellow
    if ($composeCmd -eq "docker compose") {
        docker compose up -d
    } else {
        docker-compose up -d
    }
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker 服务启动失败" -ForegroundColor Red
    exit 1
}

# 等待服务启动
Write-Host ""
Write-Host "⏳ 等待服务启动..." -ForegroundColor Yellow

$maxWait = 90
$waitInterval = 5
$waited = 0

# 等待后端
Write-Host -NoNewline "等待后端服务"
while ($waited -lt $maxWait) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 3 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host ""
            Write-Host "✅ 后端服务已就绪" -ForegroundColor Green
            break
        }
    } catch {
        # 继续等待
    }
    Write-Host -NoNewline "."
    Start-Sleep -Seconds $waitInterval
    $waited += $waitInterval
}

if ($waited -ge $maxWait) {
    Write-Host ""
    Write-Host "⚠️ 后端服务启动超时" -ForegroundColor Yellow
}

# 等待前端
$waited = 0
Write-Host -NoNewline "等待前端服务"
while ($waited -lt $maxWait) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 3 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host ""
            Write-Host "✅ 前端服务已就绪" -ForegroundColor Green
            break
        }
    } catch {
        # 继续等待
    }
    Write-Host -NoNewline "."
    Start-Sleep -Seconds $waitInterval
    $waited += $waitInterval
}

if ($waited -ge $maxWait) {
    Write-Host ""
    Write-Host "⚠️ 前端服务启动超时" -ForegroundColor Yellow
}

# 显示容器状态
Write-Host ""
Write-Host "📋 容器状态:" -ForegroundColor Yellow
if ($composeCmd -eq "docker compose") {
    docker compose ps
} else {
    docker-compose ps
}

# 显示访问信息
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "🎉 启动完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 访问地址:" -ForegroundColor Cyan
Write-Host "   前端界面: http://localhost:3000" -ForegroundColor White
Write-Host "   后端API:  http://localhost:8000" -ForegroundColor White
Write-Host "   API文档:  http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "🗄️ 数据库:" -ForegroundColor Cyan
Write-Host "   MongoDB:  mongodb://localhost:27017" -ForegroundColor Gray
Write-Host "   Redis:    redis://localhost:6379" -ForegroundColor Gray
Write-Host ""
Write-Host "📋 常用命令:" -ForegroundColor Cyan
Write-Host "   查看日志: $composeCmd logs -f" -ForegroundColor Gray
Write-Host "   停止服务: $composeCmd down" -ForegroundColor Gray
Write-Host "   重启服务: $composeCmd restart" -ForegroundColor Gray
Write-Host ""
