# TradingAgents-CN Docker 启动脚本 (PowerShell版本)
# 前后端分离架构 (FastAPI + Vue3)
# 版本: v1.0.0-preview

$ErrorActionPreference = "Stop"

Write-Host "🚀 TradingAgents-CN Docker 启动" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host "架构: FastAPI 后端 + Vue3 前端" -ForegroundColor Cyan
Write-Host ""

# 检查Docker是否运行
Write-Host "🔍 检查Docker环境..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "✅ Docker运行正常" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker未运行，请先启动Docker Desktop" -ForegroundColor Red
    exit 1
}

# 检查docker-compose是否可用
$composeCmd = "docker-compose"
try {
    docker-compose --version | Out-Null
    Write-Host "✅ 使用: docker-compose" -ForegroundColor Green
} catch {
    try {
        docker compose version | Out-Null
        $composeCmd = "docker compose"
        Write-Host "✅ 使用: docker compose" -ForegroundColor Green
    } catch {
        Write-Host "❌ docker-compose未安装或不可用" -ForegroundColor Red
        exit 1
    }
}

# 创建必要的目录
Write-Host ""
Write-Host "📁 创建必要目录..." -ForegroundColor Yellow
$directories = @("logs", "data", "config")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "   📁 创建目录: $dir" -ForegroundColor Gray
    }
}
Write-Host "✅ 目录准备完成" -ForegroundColor Green

# 创建.gitkeep文件
$gitkeepFile = "logs\.gitkeep"
if (-not (Test-Path $gitkeepFile)) {
    New-Item -ItemType File -Path $gitkeepFile -Force | Out-Null
}

# 检查.env文件
Write-Host ""
Write-Host "🔧 检查配置文件..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "⚠️ .env文件不存在" -ForegroundColor Yellow
    if (Test-Path ".env.docker") {
        Copy-Item ".env.docker" ".env"
        Write-Host "📋 已复制.env.docker到.env" -ForegroundColor Cyan
        Write-Host "✅ 已使用Docker默认配置" -ForegroundColor Green
    } elseif (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "📋 已复制.env.example到.env" -ForegroundColor Cyan
        Write-Host "⚠️ 请编辑.env文件配置API密钥" -ForegroundColor Yellow
    } else {
        Write-Host "❌ 找不到配置模板文件" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ .env文件存在" -ForegroundColor Green
}

# 显示当前配置
Write-Host ""
Write-Host "📋 当前配置:" -ForegroundColor Cyan
Write-Host "   项目目录: $(Get-Location)" -ForegroundColor Gray
Write-Host "   日志目录: $(Join-Path (Get-Location) 'logs')" -ForegroundColor Gray
Write-Host "   数据目录: $(Join-Path (Get-Location) 'data')" -ForegroundColor Gray
Write-Host "   配置文件: .env" -ForegroundColor Gray

# 停止可能存在的旧容器
Write-Host ""
Write-Host "🧹 清理旧容器..." -ForegroundColor Yellow
if ($composeCmd -eq "docker compose") {
    docker compose down --remove-orphans 2>$null
} else {
    docker-compose down --remove-orphans 2>$null
}

# 启动Docker容器
Write-Host ""
Write-Host "🐳 启动Docker容器..." -ForegroundColor Yellow
if ($composeCmd -eq "docker compose") {
    docker compose up -d
} else {
    docker-compose up -d
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker容器启动失败" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Docker容器启动成功" -ForegroundColor Green

# 检查启动状态
Write-Host ""
Write-Host "📊 容器状态:" -ForegroundColor Yellow
if ($composeCmd -eq "docker compose") {
    docker compose ps
} else {
    docker-compose ps
}

# 等待服务启动
Write-Host ""
Write-Host "⏳ 等待服务启动..." -ForegroundColor Yellow

$maxWait = 120
$waitInterval = 5
$waited = 0

# 等待后端服务
Write-Host -NoNewline "等待后端服务 (backend:8000)"
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
    Write-Host "⚠️ 后端服务启动超时，可能还在初始化中..." -ForegroundColor Yellow
}

# 等待前端服务
$waited = 0
Write-Host -NoNewline "等待前端服务 (frontend:3000)"
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
    Write-Host "⚠️ 前端服务启动超时，可能还在初始化中..." -ForegroundColor Yellow
}

# 检查数据库服务
Write-Host ""
Write-Host "🗄️ 检查数据库服务..." -ForegroundColor Yellow

$mongoCheck = docker exec tradingagents-mongodb mongosh --eval "db.runCommand('ping')" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ MongoDB 运行正常" -ForegroundColor Green
} else {
    Write-Host "⚠️ MongoDB 可能还在启动中" -ForegroundColor Yellow
}

$redisCheck = docker exec tradingagents-redis redis-cli -a tradingagents123 ping 2>$null
if ($redisCheck -eq "PONG") {
    Write-Host "✅ Redis 运行正常" -ForegroundColor Green
} else {
    Write-Host "⚠️ Redis 可能还在启动中" -ForegroundColor Yellow
}

# 检查是否有日志文件生成
Write-Host ""
Write-Host "📄 检查日志文件..." -ForegroundColor Yellow
$logFiles = Get-ChildItem "logs\*.log" -ErrorAction SilentlyContinue
if ($logFiles) {
    Write-Host "✅ 找到日志文件:" -ForegroundColor Green
    foreach ($file in $logFiles) {
        $size = [math]::Round($file.Length / 1KB, 2)
        Write-Host "   📄 $($file.Name) ($size KB)" -ForegroundColor Gray
    }
} else {
    Write-Host "⏳ 日志文件还未生成，请稍等..." -ForegroundColor Yellow
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
Write-Host "📋 日志查看:" -ForegroundColor Cyan
Write-Host "   应用日志: Get-Content logs\tradingagents.log -Wait" -ForegroundColor Gray
Write-Host "   后端日志: $composeCmd logs -f backend" -ForegroundColor Gray
Write-Host "   前端日志: $composeCmd logs -f frontend" -ForegroundColor Gray
Write-Host "   全部日志: $composeCmd logs -f" -ForegroundColor Gray
Write-Host ""
Write-Host "💡 常用命令:" -ForegroundColor Cyan
Write-Host "   查看状态: $composeCmd ps" -ForegroundColor Gray
Write-Host "   停止服务: $composeCmd down" -ForegroundColor Gray
Write-Host "   重启后端: $composeCmd restart backend" -ForegroundColor Gray
Write-Host "   重启前端: $composeCmd restart frontend" -ForegroundColor Gray
Write-Host "   重建服务: $composeCmd up -d --build" -ForegroundColor Gray
Write-Host ""
Write-Host "🔧 管理界面 (需启用management profile):" -ForegroundColor Cyan
Write-Host "   启用方式: $composeCmd --profile management up -d" -ForegroundColor Gray
Write-Host "   Redis管理: http://localhost:8081" -ForegroundColor Gray
Write-Host "   Mongo管理: http://localhost:8082" -ForegroundColor Gray
Write-Host ""
