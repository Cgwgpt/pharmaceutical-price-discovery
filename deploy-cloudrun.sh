#!/bin/bash

# Google Cloud Run部署脚本

set -e

# 配置变量
PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"asia-east1"}
SERVICE_NAME="pharmaceutical-price-discovery"

echo "开始部署到Google Cloud Run..."
echo "项目ID: $PROJECT_ID"
echo "区域: $REGION"
echo "服务名: $SERVICE_NAME"

# 检查是否已登录gcloud
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "请先登录Google Cloud: gcloud auth login"
    exit 1
fi

# 设置项目
gcloud config set project $PROJECT_ID

# 启用必要的API
echo "启用必要的API..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# 构建并推送镜像
echo "构建Docker镜像..."
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"
docker build -f Dockerfile.cloudrun -t $IMAGE_NAME .

echo "推送镜像到Container Registry..."
docker push $IMAGE_NAME

# 部署到Cloud Run
echo "部署到Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 900 \
    --concurrency 10 \
    --max-instances 5 \
    --set-env-vars "FLASK_ENV=production,DATABASE_URL=sqlite:///tmp/pharma_prices.db"

# 获取服务URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo "部署完成！"
echo "服务URL: $SERVICE_URL"
echo ""
echo "测试命令:"
echo "curl $SERVICE_URL"