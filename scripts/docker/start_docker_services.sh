#!/bin/bash
# TradingAgents-CN Docker 服务启动脚本
# 前后端分离架构 (FastAPI + Vue3)
# 版本: v1.0.0-preview

set -e

echo "========================================"
echo "🐳 TradingAgents-CN Docker 服务启动"
echo "========================================"
echo "架构: FastAPI 后端 + Vue3 前端"
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

# 检查Docker是否运行
echo -e "${YELLOW}🔍 检查Docker服务状态...${NC}"
if ! docker version >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker未运行或未安装，请先启动Docker${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker服务正常${NC}"

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

# 创建必要的目录
echo ""
echo -e "${YELLOW}📁 创建必要目录...${NC}"
mkdir -p logs data config
echo -e "${GREEN}✅ 目录准备完成${NC}"

# 检查.env文件
echo ""
echo -e "${YELLOW}🔧 检查配置文件...${NC}"
if [ ! -f ".env" ]; then
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

# 停止可能存在的旧容器
echo ""
echo -e "${YELLOW}🧹 清理旧容器...${NC}"
$COMPOSE_CMD down --remove-orphans 2>/dev/null || true

# 启动服务
echo ""
echo -e "${YELLOW}🚀 启动Docker服务...${NC}"

# 检查是否需要启动管理工具
if [ "$1" == "--with-management" ] || [ "$1" == "-m" ]; then
    echo -e "${CYAN}📊 包含管理工具 (Redis Commander, Mongo Express)${NC}"
    $COMPOSE_CMD --profile management up -d
else
    $COMPOSE_CMD up -d
fi

# 等待服务启动
echo ""
echo -e "${YELLOW}⏳ 等待服务启动...${NC}"
sleep 5

# 显示容器状态
echo ""
echo -e "${YELLOW}📋 服务状态:${NC}"
$COMPOSE_CMD ps

# 等待后端健康检查
echo ""
echo -e "${YELLOW}🔍 检查服务健康状态...${NC}"

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
    echo -e "${YELLOW}⚠️ 后端服务启动超时，请检查日志${NC}"
fi

# 检查前端
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
    echo -e "${YELLOW}⚠️ 前端服务启动超时，请检查日志${NC}"
fi

# 显示访问信息
echo ""
echo "========================================"
echo -e "${GREEN}🎉 Docker服务启动完成！${NC}"
echo "========================================"
echo ""
echo -e "${CYAN}🌐 访问地址:${NC}"
echo "   前端界面: http://localhost:3000"
echo "   后端API:  http://localhost:8000"
echo "   API文档:  http://localhost:8000/docs"
echo ""
echo -e "${CYAN}🗄️ 数据库:${NC}"
echo "   MongoDB:  mongodb://admin:tradingagents123@localhost:27017/tradingagents"
echo "   Redis:    redis://:tradingagents123@localhost:6379"
echo ""

if [ "$1" == "--with-management" ] || [ "$1" == "-m" ]; then
    echo -e "${CYAN}🔧 管理界面:${NC}"
    echo "   Redis Commander: http://localhost:8081"
    echo "   Mongo Express:   http://localhost:8082 (用户: admin, 密码: tradingagents123)"
    echo ""
fi

echo -e "${CYAN}📋 常用命令:${NC}"
echo "   查看状态:   $COMPOSE_CMD ps"
echo "   查看日志:   $COMPOSE_CMD logs -f"
echo "   后端日志:   $COMPOSE_CMD logs -f backend"
echo "   前端日志:   $COMPOSE_CMD logs -f frontend"
echo "   停止服务:   $COMPOSE_CMD down"
echo "   重启后端:   $COMPOSE_CMD restart backend"
echo "   重建服务:   $COMPOSE_CMD up -d --build"
echo ""
echo -e "${CYAN}💡 提示:${NC}"
echo "   - 首次启动可能需要几分钟来初始化数据库"
echo "   - 使用 '$COMPOSE_CMD logs -f' 查看实时日志"
echo "   - 数据将持久化保存在 Docker 卷中"
echo "   - 启用管理工具: $0 --with-management"
echo ""
