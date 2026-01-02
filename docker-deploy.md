# Docker部署指南

## 部署版本选择

### 🚀 快速版本（推荐用于快速体验）
- **文件**: `Dockerfile` + `docker-compose.yml`
- **特点**: 不包含Chrome，镜像小，启动快
- **功能**: 支持Web界面、API采集、数据管理
- **限制**: 无法使用自动登录和完整浏览器采集

### 🔧 完整版本（推荐用于生产环境）
- **文件**: `Dockerfile.full` + `docker-compose.full.yml`
- **特点**: 包含Chrome和Playwright，功能完整
- **功能**: 支持所有功能，包括自动登录和浏览器采集
- **限制**: 镜像较大，启动稍慢

## 快速开始

### 方式1: 快速版本部署

```bash
# 使用docker-compose一键部署
docker-compose up -d

# 或者手动构建
docker build -t pharma-price-discovery .
docker run -d -p 5001:5001 -v $(pwd)/data:/app/data --name pharma-app pharma-price-discovery
```

### 方式2: 完整版本部署

```bash
# 使用完整版docker-compose
docker-compose -f docker-compose.full.yml up -d

# 或者手动构建
docker build -f Dockerfile.full -t pharma-price-discovery-full .
docker run -d -p 5001:5001 -v $(pwd)/data:/app/data --name pharma-app-full pharma-price-discovery-full
```

### 方式3: 一键部署脚本

```bash
# 快速版本
./deploy.sh

# 完整版本
./deploy.sh full
```

## 功能对比

| 功能 | 快速版本 | 完整版本 |
|------|----------|----------|
| Web界面 | ✅ | ✅ |
| API采集 | ✅ | ✅ |
| 数据管理 | ✅ | ✅ |
| 价格比较 | ✅ | ✅ |
| 监控告警 | ✅ | ✅ |
| 自动登录 | ❌ | ✅ |
| 浏览器采集 | ❌ | ✅ |
| 完整数据采集 | ❌ | ✅ |
| 镜像大小 | ~500MB | ~2GB |
| 启动时间 | ~30秒 | ~60秒 |

## 访问应用

- 应用地址: http://localhost:5001
- 健康检查: http://localhost:5001/

## 部署选项

### 选项1: SQLite数据库（推荐用于开发和小规模部署）

```bash
# 创建数据目录
mkdir -p data logs

# 启动服务
docker-compose up -d
```

### 选项2: PostgreSQL数据库（推荐用于生产环境）

1. 修改 `docker-compose.yml`，取消PostgreSQL相关注释
2. 更新环境变量:

```yaml
environment:
  - DATABASE_URL=postgresql://pharma_user:pharma_password@postgres:5432/pharma_prices
```

3. 启动服务:

```bash
docker-compose up -d
```

## 环境变量配置

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `FLASK_ENV` | production | Flask运行环境 |
| `SECRET_KEY` | your-secret-key-change-this | Flask密钥（生产环境必须修改） |
| `DATABASE_URL` | sqlite:///data/pharma_prices.db | 数据库连接URL |

## 数据持久化

- SQLite数据库文件: `./data/pharma_prices.db`
- 应用日志: `./logs/`
- 爬虫缓存: `./data/.scrapy/`

## 常用命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f pharma-app

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 进入容器
docker-compose exec pharma-app bash

# 备份数据库
docker-compose exec pharma-app cp /app/data/pharma_prices.db /app/data/backup_$(date +%Y%m%d_%H%M%S).db
```

## 生产环境部署建议

### 1. 安全配置

```bash
# 生成强密钥
export SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')

# 更新docker-compose.yml中的SECRET_KEY
```

### 2. 反向代理（Nginx）

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. 监控和日志

```bash
# 设置日志轮转
echo "*/5 * * * * docker-compose exec pharma-app find /app/logs -name '*.log' -size +100M -delete" | crontab -

# 监控容器健康状态
docker-compose exec pharma-app curl -f http://localhost:5001/ || echo "应用异常"
```

### 4. 备份策略

```bash
#!/bin/bash
# backup.sh - 数据备份脚本
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec pharma-app cp /app/data/pharma_prices.db /app/data/backup_$DATE.db
# 保留最近7天的备份
find ./data -name "backup_*.db" -mtime +7 -delete
```

## 故障排除

### 1. 容器启动失败

```bash
# 查看详细日志
docker-compose logs pharma-app

# 检查端口占用
lsof -i :5001
```

### 2. 数据库连接问题

```bash
# 检查数据库文件权限
ls -la data/

# 重新初始化数据库
docker-compose exec pharma-app python -c "from app import create_app; from app.models import db; app = create_app(); app.app_context().push(); db.create_all()"
```

### 3. 爬虫功能异常

```bash
# 检查Chrome浏览器安装
docker-compose exec pharma-app google-chrome --version

# 测试Selenium功能
docker-compose exec pharma-app python -c "from selenium import webdriver; from selenium.webdriver.chrome.options import Options; options = Options(); options.add_argument('--headless'); driver = webdriver.Chrome(options=options); print('Selenium工作正常')"
```

## 更新部署

```bash
# 拉取最新代码
git pull

# 重新构建镜像
docker-compose build

# 重启服务
docker-compose up -d
```