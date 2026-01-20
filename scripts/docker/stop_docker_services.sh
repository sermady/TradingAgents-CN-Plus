#!/bin/bash
# TradingAgents-CN Docker 服务停止脚本
# 前后端分离架构 (FastAPI + Vue3)
# 版本: v1.0.0-preview

echo "========================================"
echo "🛑 TradingAgents-CN Docker 服务停止"
echo "========================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 切换到项目根目录
cd "$PROJECT_ROOT"
echo -e "${CYAN}📂 项目目录: $PROJECT_ROOT${NC}"
echo ""

# 检查docker-compose
COMPOSE_CMD=""
if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
elif docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    echo -e "${RED}❌ docker-compose未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 使用: $COMPOSE_CMD${NC}"
echo ""

# 显示当前运行的容器
echo -e "${YELLOW}📋 当前运行的容器:${NC}"
$COMPOSE_CMD ps
echo ""

# 停止服务
echo -e "${YELLOW}🛑 停止所有服务...${NC}"

# 检查是否需要停止管理工具
if [ "$1" == "--all" ] || [ "$1" == "-a" ]; then
    echo -e "${CYAN}📊 包含管理工具 (Redis Commander, Mongo Express)${NC}"
    $COMPOSE_CMD --profile management down --remove-orphans
else
    $COMPOSE_CMD down --remove-orphans
fi

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 服务停止成功${NC}"
else
    echo -e "${YELLOW}⚠️ 部分服务可能已经停止${NC}"
fi

echo ""

# 检查剩余容器
echo -e "${YELLOW}📋 检查剩余容器...${NC}"
REMAINING=$(docker ps --filter "name=tradingagents-" --format "{{.Names}}" 2>/dev/null)
if [ -z "$REMAINING" ]; then
    echo -e "${GREEN}✅ 所有 TradingAgents 容器已停止${NC}"
else
    echo -e "${YELLOW}⚠️ 以下容器仍在运行:${NC}"
    docker ps --filter "name=tradingagents-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    echo -e "${CYAN}💡 手动停止: docker stop $REMAINING${NC}"
fi

echo ""
echo "========================================"
echo -e "${GREEN}✅ 停止操作完成${NC}"
echo "========================================"
echo ""
echo -e "${CYAN}💡 提示:${NC}"
echo "   - 数据已保存在 Docker 卷中，下次启动时会自动恢复"
echo "   - 重新启动: $COMPOSE_CMD up -d"
echo ""
echo -e "${CYAN}🧹 如需完全清理数据:${NC}"
echo "   删除数据卷: docker volume rm tradingagents_mongodb_data tradingagents_redis_data"
echo "   删除镜像:   docker rmi tradingagents-backend:v1.0.0-preview tradingagents-frontend:v1.0.0-preview"
echo "   完全清理:   $COMPOSE_CMD down -v --rmi all"
echo ""
