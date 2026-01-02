#!/bin/bash

# 医药价格发现系统 Docker部署脚本

set -e

# 检查参数
FULL_VERSION=false
if [ "$1" = "full" ]; then
    FULL_VERSION=true
    echo "🚀 开始部署医药价格发现系统（完整版）..."
    COMPOSE_FILE="docker-compose.full.yml"
    DOCKERFILE="Dockerfile.full"
else
    echo "🚀 开始部署医药价格发现系统（快速版）..."
    COMPOSE_FILE="docker-compose.yml"
    DOCKERFILE="Dockerfile"
fi

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 创建必要的目录
echo "📁 创建数据目录..."
mkdir -p data logs

# 设置权限
chmod 755 data logs

# 生成密钥（如果不存在）
if [ ! -f .env ]; then
    echo "🔐 生成配置文件..."
    SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))' 2>/dev/null || openssl rand -hex 32)
    cat > .env << EOF
SECRET_KEY=$SECRET_KEY
FLASK_ENV=production
DATABASE_URL=sqlite:///data/pharma_prices.db
EOF
    echo "✅ 配置文件已生成: .env"
fi

# 构建和启动服务
echo "🔨 构建Docker镜像..."
if [ "$FULL_VERSION" = true ]; then
    echo "   使用完整版Dockerfile（包含Chrome和Playwright）"
    docker-compose -f $COMPOSE_FILE build
else
    echo "   使用快速版Dockerfile（不包含Chrome）"
    docker-compose -f $COMPOSE_FILE build
fi

echo "🚀 启动服务..."
docker-compose -f $COMPOSE_FILE up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 15

# 健康检查
if curl -f http://localhost:5001/ > /dev/null 2>&1; then
    echo "✅ 部署成功！"
    echo ""
    echo "🌐 访问地址: http://localhost:5001"
    if [ "$FULL_VERSION" = true ]; then
        echo "🔧 版本: 完整版（支持自动登录和浏览器采集）"
    else
        echo "🚀 版本: 快速版（基础功能）"
    fi
    echo "📊 查看状态: docker-compose -f $COMPOSE_FILE ps"
    echo "📝 查看日志: docker-compose -f $COMPOSE_FILE logs -f"
    echo "🛑 停止服务: docker-compose -f $COMPOSE_FILE down"
else
    echo "❌ 服务启动失败，请检查日志:"
    docker-compose -f $COMPOSE_FILE logs
    exit 1
fi