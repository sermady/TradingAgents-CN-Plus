#!/bin/bash
# TradingAgents-CN Docker 健康检查脚本
# 前后端分离架构 (FastAPI + Vue3)
# 版本: v1.0.0-preview

echo "========================================"
echo "🔍 TradingAgents-CN Docker 健康检查"
echo "========================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 统计
PASSED=0
FAILED=0
WARNINGS=0

# 检查函数
check_pass() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}❌ $1${NC}"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠️ $1${NC}"
    ((WARNINGS++))
}

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 切换到项目根目录
cd "$PROJECT_ROOT"
echo -e "${CYAN}📂 项目目录: $PROJECT_ROOT${NC}"
echo ""

# 1. 检查 Docker 环境
echo -e "${CYAN}[1/6] 检查 Docker 环境${NC}"
echo "----------------------------------------"

if docker version >/dev/null 2>&1; then
    DOCKER_VERSION=$(docker version --format '{{.Server.Version}}' 2>/dev/null)
    check_pass "Docker 运行正常 (版本: $DOCKER_VERSION)"
else
    check_fail "Docker 未运行或未安装"
fi

# 检查 docker-compose
COMPOSE_CMD=""
if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
    COMPOSE_VERSION=$(docker-compose version --short 2>/dev/null)
    check_pass "docker-compose 可用 (版本: $COMPOSE_VERSION)"
elif docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
    COMPOSE_VERSION=$(docker compose version --short 2>/dev/null)
    check_pass "docker compose 可用 (版本: $COMPOSE_VERSION)"
else
    check_fail "docker-compose 未安装"
fi

echo ""

# 2. 检查容器状态
echo -e "${CYAN}[2/6] 检查容器状态${NC}"
echo "----------------------------------------"

# 定义需要检查的容器
CONTAINERS=("tradingagents-backend" "tradingagents-frontend" "tradingagents-mongodb" "tradingagents-redis")

for container in "${CONTAINERS[@]}"; do
    STATUS=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null)
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null)

    if [ "$STATUS" == "running" ]; then
        if [ -n "$HEALTH" ] && [ "$HEALTH" != "<no value>" ]; then
            if [ "$HEALTH" == "healthy" ]; then
                check_pass "$container: 运行中 (健康)"
            elif [ "$HEALTH" == "starting" ]; then
                check_warn "$container: 运行中 (健康检查中)"
            else
                check_warn "$container: 运行中 (状态: $HEALTH)"
            fi
        else
            check_pass "$container: 运行中"
        fi
    elif [ "$STATUS" == "exited" ]; then
        check_fail "$container: 已停止"
    elif [ -z "$STATUS" ]; then
        check_fail "$container: 未创建"
    else
        check_warn "$container: $STATUS"
    fi
done

echo ""

# 3. 检查端口
echo -e "${CYAN}[3/6] 检查服务端口${NC}"
echo "----------------------------------------"

check_port() {
    local port=$1
    local service=$2

    if nc -z localhost "$port" 2>/dev/null || (echo >/dev/tcp/localhost/"$port") 2>/dev/null; then
        check_pass "端口 $port ($service): 可访问"
        return 0
    else
        check_fail "端口 $port ($service): 不可访问"
        return 1
    fi
}

# 使用 curl 检查（更通用）
check_port_curl() {
    local port=$1
    local service=$2
    local path=${3:-""}

    if curl -s --connect-timeout 3 "http://localhost:$port$path" >/dev/null 2>&1; then
        check_pass "端口 $port ($service): 可访问"
        return 0
    else
        check_fail "端口 $port ($service): 不可访问"
        return 1
    fi
}

check_port_curl 3000 "前端" "/"
check_port_curl 8000 "后端API" "/api/health"
check_port_curl 27017 "MongoDB" "" || true  # MongoDB 不响应 HTTP
check_port_curl 6379 "Redis" "" || true     # Redis 不响应 HTTP

echo ""

# 4. 检查 API 健康状态
echo -e "${CYAN}[4/6] 检查 API 健康状态${NC}"
echo "----------------------------------------"

# 后端健康检查
HEALTH_RESPONSE=$(curl -s --connect-timeout 5 "http://localhost:8000/api/health" 2>/dev/null)
if [ -n "$HEALTH_RESPONSE" ]; then
    STATUS=$(echo "$HEALTH_RESPONSE" | grep -o '"status"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4)
    if [ "$STATUS" == "healthy" ] || [ "$STATUS" == "ok" ]; then
        check_pass "后端 API 健康检查通过"
    else
        check_warn "后端 API 返回状态: $STATUS"
    fi
else
    check_fail "后端 API 无响应"
fi

# 前端健康检查
FRONTEND_RESPONSE=$(curl -s --connect-timeout 5 -o /dev/null -w "%{http_code}" "http://localhost:3000" 2>/dev/null)
if [ "$FRONTEND_RESPONSE" == "200" ]; then
    check_pass "前端服务健康检查通过"
else
    check_fail "前端服务返回状态码: $FRONTEND_RESPONSE"
fi

echo ""

# 5. 检查数据库连接
echo -e "${CYAN}[5/6] 检查数据库连接${NC}"
echo "----------------------------------------"

# MongoDB 检查
MONGO_PING=$(docker exec tradingagents-mongodb mongo --eval "db.adminCommand('ping')" -u admin -p tradingagents123 --authenticationDatabase admin --quiet 2>/dev/null)
if echo "$MONGO_PING" | grep -q '"ok".*1'; then
    check_pass "MongoDB 连接正常"
else
    # 尝试 mongosh
    MONGO_PING=$(docker exec tradingagents-mongodb mongosh --eval "db.adminCommand('ping')" -u admin -p tradingagents123 --authenticationDatabase admin --quiet 2>/dev/null)
    if echo "$MONGO_PING" | grep -q '"ok".*1'; then
        check_pass "MongoDB 连接正常"
    else
        check_fail "MongoDB 连接失败"
    fi
fi

# Redis 检查
REDIS_PING=$(docker exec tradingagents-redis redis-cli -a tradingagents123 ping 2>/dev/null)
if [ "$REDIS_PING" == "PONG" ]; then
    check_pass "Redis 连接正常"
else
    check_fail "Redis 连接失败"
fi

echo ""

# 6. 检查资源使用
echo -e "${CYAN}[6/6] 检查资源使用${NC}"
echo "----------------------------------------"

echo "容器资源使用情况:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
    tradingagents-backend tradingagents-frontend tradingagents-mongodb tradingagents-redis 2>/dev/null || \
    echo "无法获取资源使用信息"

echo ""

# 总结
echo "========================================"
echo -e "${CYAN}📊 检查结果总结${NC}"
echo "========================================"
echo ""
echo -e "通过: ${GREEN}$PASSED${NC}"
echo -e "失败: ${RED}$FAILED${NC}"
echo -e "警告: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 所有检查通过！服务运行正常。${NC}"
    echo ""
    echo -e "${CYAN}🌐 访问地址:${NC}"
    echo "   前端界面: http://localhost:3000"
    echo "   后端API:  http://localhost:8000"
    echo "   API文档:  http://localhost:8000/docs"
    EXIT_CODE=0
elif [ $FAILED -le 2 ]; then
    echo -e "${YELLOW}⚠️ 部分服务可能存在问题，请检查上述失败项。${NC}"
    EXIT_CODE=1
else
    echo -e "${RED}❌ 多个服务存在问题，请检查 Docker 容器状态。${NC}"
    echo ""
    echo -e "${CYAN}💡 故障排查建议:${NC}"
    echo "   1. 查看容器日志: docker-compose logs -f"
    echo "   2. 重启服务: docker-compose restart"
    echo "   3. 重建服务: docker-compose up -d --build"
    EXIT_CODE=2
fi

echo ""
exit $EXIT_CODE
