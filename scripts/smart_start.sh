#!/bin/bash
# TradingAgents-CN 智能Docker启动脚本 (Linux/Mac Bash版本)
# 前后端分离架构 (FastAPI + Vue3)
# 版本: v1.0.0-preview
#
# 功能：自动判断是否需要重新构建Docker镜像
# 使用：chmod +x scripts/smart_start.sh && ./scripts/smart_start.sh
#
# 判断逻辑：
# 1. 检查是否存在 tradingagents-backend 和 tradingagents-frontend 镜像
# 2. 如果镜像不存在 -> 执行构建启动
# 3. 如果镜像存在但代码有变化 -> 执行构建启动
# 4. 如果镜像存在且代码无变化 -> 快速启动

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo "========================================"
echo -e "${CYAN}🚀 TradingAgents-CN Docker 智能启动脚本${NC}"
echo "========================================"
echo "架构: FastAPI 后端 + Vue3 前端"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 切换到项目根目录
cd "$PROJECT_ROOT"
echo -e "${CYAN}📂 项目目录: $PROJECT_ROOT${NC}"
echo ""

# 检查 docker-compose
COMPOSE_CMD=""
if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
elif docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    echo -e "${RED}❌ docker-compose 未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 使用: $COMPOSE_CMD${NC}"

# 创建必要的目录
mkdir -p logs data config

# 检查.env文件
if [ ! -f ".env" ]; then
    if [ -f ".env.docker" ]; then
        cp .env.docker .env
        echo -e "${GREEN}✅ 已使用 Docker 默认配置${NC}"
    elif [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}⚠️ 请编辑 .env 文件配置 API 密钥${NC}"
    fi
fi

# 检查镜像是否存在
BACKEND_EXISTS=false
FRONTEND_EXISTS=false

if docker images | grep -q "tradingagents-backend"; then
    BACKEND_EXISTS=true
    echo -e "${GREEN}✅ 发现后端镜像${NC}"
else
    echo -e "${YELLOW}⚠️ 后端镜像不存在${NC}"
fi

if docker images | grep -q "tradingagents-frontend"; then
    FRONTEND_EXISTS=true
    echo -e "${GREEN}✅ 发现前端镜像${NC}"
else
    echo -e "${YELLOW}⚠️ 前端镜像不存在${NC}"
fi

# 判断是否需要构建
NEED_BUILD=false

if [ "$BACKEND_EXISTS" = false ] || [ "$FRONTEND_EXISTS" = false ]; then
    NEED_BUILD=true
    echo -e "${CYAN}🏗️ 首次运行或镜像缺失，需要构建${NC}"
else
    # 检查代码是否有变化（排除文档和脚本）
    if git rev-parse --git-dir > /dev/null 2>&1; then
        if ! git diff --quiet HEAD~1 HEAD -- . ':!*.md' ':!docs/' ':!scripts/' 2>/dev/null; then
            NEED_BUILD=true
            echo -e "${CYAN}🔄 检测到代码变化，需要重新构建${NC}"
        else
            echo -e "${GREEN}📦 代码无变化，使用快速启动${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️ 非 Git 仓库，跳过变化检测${NC}"
    fi
fi

# 停止可能存在的旧容器
echo ""
echo -e "${YELLOW}🧹 清理旧容器...${NC}"
$COMPOSE_CMD down --remove-orphans 2>/dev/null || true

# 启动服务
echo ""
if [ "$NEED_BUILD" = true ]; then
    echo -e "${YELLOW}🏗️ 构建并启动服务...${NC}"
    $COMPOSE_CMD up -d --build
else
    echo -e "${YELLOW}🚀 快速启动服务...${NC}"
    $COMPOSE_CMD up -d
fi

# 等待服务启动
echo ""
echo -e "${YELLOW}⏳ 等待服务启动...${NC}"

MAX_WAIT=90
WAIT_INTERVAL=5
WAITED=0

# 等待后端
echo -n "等待后端服务"
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8000/api/health >/dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}✅ 后端服务已就绪${NC}"
        break
    fi
    echo -n "."
    sleep $WAIT_INTERVAL
    WAITED=$((WAITED + WAIT_INTERVAL))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo ""
    echo -e "${YELLOW}⚠️ 后端服务启动超时${NC}"
fi

# 等待前端
WAITED=0
echo -n "等待前端服务"
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}✅ 前端服务已就绪${NC}"
        break
    fi
    echo -n "."
    sleep $WAIT_INTERVAL
    WAITED=$((WAITED + WAIT_INTERVAL))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo ""
    echo -e "${YELLOW}⚠️ 前端服务启动超时${NC}"
fi

# 显示容器状态
echo ""
echo -e "${YELLOW}📋 容器状态:${NC}"
$COMPOSE_CMD ps

# 显示访问信息
echo ""
echo "========================================"
echo -e "${GREEN}🎉 启动完成！${NC}"
echo "========================================"
echo ""
echo -e "${CYAN}🌐 访问地址:${NC}"
echo "   前端界面: http://localhost:3000"
echo "   后端API:  http://localhost:8000"
echo "   API文档:  http://localhost:8000/docs"
echo ""
echo -e "${CYAN}🗄️ 数据库:${NC}"
echo "   MongoDB:  mongodb://localhost:27017"
echo "   Redis:    redis://localhost:6379"
echo ""
echo -e "${CYAN}📋 常用命令:${NC}"
echo "   查看日志: $COMPOSE_CMD logs -f"
echo "   停止服务: $COMPOSE_CMD down"
echo "   重启服务: $COMPOSE_CMD restart"
echo ""
