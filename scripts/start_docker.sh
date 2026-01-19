#!/bin/bash
# TradingAgents-CN Docker 启动脚本
# 前后端分离架构 (FastAPI + Vue3)
# 版本: v1.0.0-preview

set -e

echo "🚀 TradingAgents-CN Docker 启动"
echo "================================"
echo "架构: FastAPI 后端 + Vue3 前端"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 检查Docker是否运行
echo -e "${YELLOW}🔍 检查Docker环境...${NC}"
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker未运行，请先启动Docker${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker运行正常${NC}"

# 检查docker-compose是否可用
if ! command -v docker-compose >/dev/null 2>&1; then
    # 尝试使用 docker compose (新版本)
    if ! docker compose version >/dev/null 2>&1; then
        echo -e "${RED}❌ docker-compose未安装${NC}"
        exit 1
    fi
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi
echo -e "${GREEN}✅ 使用: $COMPOSE_CMD${NC}"

# 创建必要的目录
echo ""
echo -e "${YELLOW}📁 创建必要目录...${NC}"
mkdir -p logs data config
chmod 755 logs data config 2>/dev/null || true
echo -e "${GREEN}✅ 目录准备完成${NC}"

# 检查.env文件
echo ""
echo -e "${YELLOW}🔧 检查配置文件...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️ .env文件不存在${NC}"
    if [ -f ".env.docker" ]; then
        echo -e "${CYAN}📋 复制.env.docker到.env${NC}"
        cp .env.docker .env
        echo -e "${GREEN}✅ 已使用Docker默认配置${NC}"
    elif [ -f ".env.example" ]; then
        echo -e "${CYAN}📋 复制.env.example到.env${NC}"
        cp .env.example .env
        echo -e "${YELLOW}⚠️ 请编辑.env文件配置API密钥${NC}"
    else
        echo -e "${RED}❌ 找不到配置模板文件${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ .env文件存在${NC}"
fi

# 显示当前配置
echo ""
echo -e "${CYAN}📋 当前配置:${NC}"
echo "   项目目录: $(pwd)"
echo "   日志目录: $(pwd)/logs"
echo "   数据目录: $(pwd)/data"
echo "   配置文件: .env"

# 停止可能存在的旧容器
echo ""
echo -e "${YELLOW}🧹 清理旧容器...${NC}"
$COMPOSE_CMD down --remove-orphans 2>/dev/null || true

# 启动Docker容器
echo ""
echo -e "${YELLOW}🐳 启动Docker容器...${NC}"
$COMPOSE_CMD up -d

# 检查启动状态
echo ""
echo -e "${YELLOW}📊 容器状态:${NC}"
$COMPOSE_CMD ps

# 等待服务启动
echo ""
echo -e "${YELLOW}⏳ 等待服务启动...${NC}"

# 等待后端服务
MAX_WAIT=120
WAIT_INTERVAL=5
WAITED=0

echo -n "等待后端服务 (backend:8000)"
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
    echo -e "${YELLOW}⚠️ 后端服务启动超时，可能还在初始化中...${NC}"
fi

# 等待前端服务
WAITED=0
echo -n "等待前端服务 (frontend:3000)"
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
    echo -e "${YELLOW}⚠️ 前端服务启动超时，可能还在初始化中...${NC}"
fi

# 检查数据库服务
echo ""
echo -e "${YELLOW}🗄️ 检查数据库服务...${NC}"
if docker exec tradingagents-mongodb mongosh --eval "db.runCommand('ping')" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ MongoDB 运行正常${NC}"
else
    echo -e "${YELLOW}⚠️ MongoDB 可能还在启动中${NC}"
fi

if docker exec tradingagents-redis redis-cli -a tradingagents123 ping >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis 运行正常${NC}"
else
    echo -e "${YELLOW}⚠️ Redis 可能还在启动中${NC}"
fi

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
echo -e "${CYAN}📋 日志查看:${NC}"
echo "   应用日志: tail -f logs/tradingagents.log"
echo "   后端日志: $COMPOSE_CMD logs -f backend"
echo "   前端日志: $COMPOSE_CMD logs -f frontend"
echo "   全部日志: $COMPOSE_CMD logs -f"
echo ""
echo -e "${CYAN}💡 常用命令:${NC}"
echo "   查看状态: $COMPOSE_CMD ps"
echo "   停止服务: $COMPOSE_CMD down"
echo "   重启后端: $COMPOSE_CMD restart backend"
echo "   重启前端: $COMPOSE_CMD restart frontend"
echo "   重建服务: $COMPOSE_CMD up -d --build"
echo ""
echo -e "${CYAN}🔧 管理界面 (需启用management profile):${NC}"
echo "   启用方式: $COMPOSE_CMD --profile management up -d"
echo "   Redis管理: http://localhost:8081"
echo "   Mongo管理: http://localhost:8082"
echo ""
