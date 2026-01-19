# TradingAgents-CN MongoDB 升级脚本
# 从 MongoDB 4.4 升级到 MongoDB 8.0
# 版本: v1.0.0-preview

# 注意：MongoDB 不支持跨多个大版本直接升级
# 但由于我们的数据量通常不大，我们采用导出-重建-导入的方式

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🔄 MongoDB 升级脚本 (4.4 → 8.0)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 获取脚本所在目录并切换到项目根目录
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot
Write-Host "📂 项目目录: $projectRoot" -ForegroundColor Gray
Write-Host ""

# 检查 Docker 是否运行
Write-Host "🔍 检查 Docker 环境..." -ForegroundColor Yellow
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
} catch {
    try {
        docker compose version | Out-Null
        $composeCmd = "docker compose"
    } catch {
        Write-Host "❌ docker-compose 未安装" -ForegroundColor Red
        exit 1
    }
}
Write-Host "✅ 使用: $composeCmd" -ForegroundColor Green

# 检查当前 MongoDB 版本
Write-Host ""
Write-Host "🔍 检查当前 MongoDB 状态..." -ForegroundColor Yellow

$mongoRunning = docker ps --filter "name=tradingagents-mongodb" --format "{{.Names}}" 2>$null
$currentImage = docker inspect tradingagents-mongodb --format "{{.Config.Image}}" 2>$null

if ($mongoRunning) {
    Write-Host "✅ MongoDB 容器正在运行" -ForegroundColor Green
    Write-Host "   当前镜像: $currentImage" -ForegroundColor Gray
} else {
    Write-Host "⚠️ MongoDB 容器未运行" -ForegroundColor Yellow
}

# 创建备份目录
$backupDir = Join-Path $projectRoot "backups"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupPath = Join-Path $backupDir "mongodb_backup_$timestamp"

if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
}
New-Item -ItemType Directory -Path $backupPath -Force | Out-Null

Write-Host ""
Write-Host "📦 备份目录: $backupPath" -ForegroundColor Cyan

# 确认升级
Write-Host ""
Write-Host "⚠️  警告：此操作将升级 MongoDB 从 4.4 到 8.0" -ForegroundColor Yellow
Write-Host "   升级过程会:" -ForegroundColor Yellow
Write-Host "   1. 导出现有数据" -ForegroundColor Gray
Write-Host "   2. 停止并删除旧容器" -ForegroundColor Gray
Write-Host "   3. 删除旧数据卷" -ForegroundColor Gray
Write-Host "   4. 启动新版本 MongoDB 8.0" -ForegroundColor Gray
Write-Host "   5. 导入备份数据" -ForegroundColor Gray
Write-Host ""

$confirm = Read-Host "是否继续升级？(输入 'yes' 确认)"
if ($confirm -ne "yes") {
    Write-Host "❌ 升级已取消" -ForegroundColor Red
    exit 0
}

Write-Host ""
Write-Host "🚀 开始升级..." -ForegroundColor Green

# Step 1: 导出数据
Write-Host ""
Write-Host "[1/5] 📤 导出 MongoDB 数据..." -ForegroundColor Yellow

if ($mongoRunning) {
    # 使用 mongodump 导出数据
    $dumpResult = docker exec tradingagents-mongodb mongodump --username admin --password tradingagents123 --authenticationDatabase admin --out /dump 2>&1

    if ($LASTEXITCODE -eq 0) {
        # 将导出的数据复制到宿主机
        docker cp tradingagents-mongodb:/dump $backupPath
        Write-Host "✅ 数据导出成功" -ForegroundColor Green

        # 显示导出的数据库
        $databases = Get-ChildItem "$backupPath\dump" -Directory -ErrorAction SilentlyContinue
        if ($databases) {
            Write-Host "   导出的数据库:" -ForegroundColor Gray
            foreach ($db in $databases) {
                $collections = Get-ChildItem $db.FullName -File -Filter "*.bson" -ErrorAction SilentlyContinue
                $collCount = if ($collections) { $collections.Count } else { 0 }
                Write-Host "   - $($db.Name): $collCount 个集合" -ForegroundColor Gray
            }
        }
    } else {
        Write-Host "⚠️ 数据导出失败，可能是空数据库" -ForegroundColor Yellow
        Write-Host "   继续升级（将创建全新数据库）..." -ForegroundColor Gray
    }
} else {
    Write-Host "⚠️ MongoDB 未运行，跳过数据导出" -ForegroundColor Yellow
}

# Step 2: 停止所有服务
Write-Host ""
Write-Host "[2/5] 🛑 停止所有服务..." -ForegroundColor Yellow

if ($composeCmd -eq "docker compose") {
    docker compose down --remove-orphans
} else {
    docker-compose down --remove-orphans
}
Write-Host "✅ 服务已停止" -ForegroundColor Green

# Step 3: 删除旧的 MongoDB 数据卷
Write-Host ""
Write-Host "[3/5] 🗑️ 删除旧的 MongoDB 数据卷..." -ForegroundColor Yellow

$volumeExists = docker volume ls --filter "name=tradingagents_mongodb_data" --format "{{.Name}}" 2>$null
if ($volumeExists) {
    docker volume rm tradingagents_mongodb_data -f 2>$null
    Write-Host "✅ 旧数据卷已删除" -ForegroundColor Green
} else {
    Write-Host "⚠️ 数据卷不存在，跳过" -ForegroundColor Yellow
}

# Step 4: 启动新版本 MongoDB 8.0
Write-Host ""
Write-Host "[4/5] 🚀 启动 MongoDB 8.0..." -ForegroundColor Yellow

if ($composeCmd -eq "docker compose") {
    docker compose up -d mongodb
} else {
    docker-compose up -d mongodb
}

# 等待 MongoDB 启动
Write-Host "   等待 MongoDB 启动..." -ForegroundColor Gray
$maxWait = 60
$waited = 0
$interval = 5

while ($waited -lt $maxWait) {
    Start-Sleep -Seconds $interval
    $waited += $interval

    $health = docker inspect tradingagents-mongodb --format "{{.State.Health.Status}}" 2>$null
    if ($health -eq "healthy") {
        Write-Host "✅ MongoDB 8.0 启动成功" -ForegroundColor Green
        break
    }
    Write-Host "   等待中... ($waited 秒)" -ForegroundColor Gray
}

if ($waited -ge $maxWait) {
    Write-Host "⚠️ MongoDB 启动超时，请检查日志" -ForegroundColor Yellow
}

# 验证版本
$newVersion = docker exec tradingagents-mongodb mongosh --eval "db.version()" --quiet 2>$null
Write-Host "   当前版本: MongoDB $newVersion" -ForegroundColor Cyan

# Step 5: 导入备份数据
Write-Host ""
Write-Host "[5/5] 📥 导入备份数据..." -ForegroundColor Yellow

$dumpDir = Join-Path $backupPath "dump"
if (Test-Path $dumpDir) {
    # 将备份数据复制回容器
    docker cp $dumpDir tradingagents-mongodb:/restore

    # 使用 mongorestore 导入数据
    $restoreResult = docker exec tradingagents-mongodb mongorestore --username admin --password tradingagents123 --authenticationDatabase admin /restore 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ 数据导入成功" -ForegroundColor Green
    } else {
        Write-Host "⚠️ 数据导入可能有警告，请检查" -ForegroundColor Yellow
        Write-Host $restoreResult -ForegroundColor Gray
    }

    # 清理容器内的临时文件
    docker exec tradingagents-mongodb rm -rf /restore /dump 2>$null
} else {
    Write-Host "⚠️ 没有备份数据需要导入" -ForegroundColor Yellow
}

# 启动其他服务
Write-Host ""
Write-Host "🚀 启动其他服务..." -ForegroundColor Yellow

if ($composeCmd -eq "docker compose") {
    docker compose up -d
} else {
    docker-compose up -d
}

# 等待所有服务启动
Write-Host "   等待服务启动..." -ForegroundColor Gray
Start-Sleep -Seconds 10

# 显示最终状态
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "🎉 MongoDB 升级完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# 显示容器状态
Write-Host "📋 容器状态:" -ForegroundColor Cyan
if ($composeCmd -eq "docker compose") {
    docker compose ps
} else {
    docker-compose ps
}

Write-Host ""
Write-Host "📦 备份位置: $backupPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "🌐 访问地址:" -ForegroundColor Cyan
Write-Host "   前端界面: http://localhost:3000" -ForegroundColor White
Write-Host "   后端API:  http://localhost:8000" -ForegroundColor White
Write-Host "   API文档:  http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "💡 如果遇到问题，可以从备份恢复:" -ForegroundColor Yellow
Write-Host "   备份目录: $backupPath" -ForegroundColor Gray
Write-Host ""
