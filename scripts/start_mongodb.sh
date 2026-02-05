#!/bin/bash
# TradingAgents-CN MongoDB 启动脚本
# 用于评估数据源模块时启动 MongoDB 服务

echo "🚀 TradingAgents-CN MongoDB 启动脚本"
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装或未启动"
    echo "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✅ Docker 已安装"
echo ""

# 检查 MongoDB 容器是否运行
if docker ps | grep -q tradingagents-mongodb; then
    echo "✅ MongoDB 容器已运行"
    echo "端口: localhost:27017"
    echo ""
    echo "如需停止 MongoDB，请运行:"
    echo "  docker stop tradingagents-mongodb"
    echo ""
    exit 0
fi

echo "🐳 启动 MongoDB 容器..."
echo ""

# 启动 MongoDB 容器
docker run -d \
  --name tradingagents-mongodb \
  --restart unless-stopped \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=tradingagents123 \
  -e MONGO_INITDB_DATABASE=tradingagents \
  mongo:8.0

if [ $? -ne 0 ]; then
    echo "❌ MongoDB 容器启动失败"
    exit 1
fi

echo ""
echo "✅ MongoDB 容器启动成功！"
echo ""
echo "连接信息:"
echo "  主机: localhost"
echo "  端口: 27017"
echo "  用户名: admin"
echo "  密码: tradingagents123"
echo "  数据库: tradingagents"
echo ""
echo "连接字符串 (MongoDB Compass):"
echo "  mongodb://admin:tradingagents123@localhost:27017/?authSource=admin"
echo ""
echo "测试连接:"
python -c "from pymongo import MongoClient; client = MongoClient('mongodb://admin:tradingagents123@localhost:27017/?authSource=admin'); print('✅ MongoDB 连接成功!' if client.admin.command('ping') else '❌ 连接失败')"
echo ""
echo "如需停止 MongoDB，请运行:"
echo "  docker stop tradingagents-mongodb"
echo ""
