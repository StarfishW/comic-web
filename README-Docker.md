# Comic Web - Docker 部署指南

本项目支持使用 Docker 和 Docker Compose 进行一键部署。

## 前置要求

- Docker Engine 20.10+
- Docker Compose 2.0+

## 快速开始

### 1. 启动所有服务

在项目根目录下运行：

```bash
docker-compose up -d
```

这将会：
- 构建后端 API 服务（Python FastAPI）
- 构建前端 Web 服务（Vue 3 + Nginx）
- 启动两个服务并建立网络连接

### 2. 访问应用

- **前端页面**: http://localhost
- **后端 API**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs

### 3. 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看后端日志
docker-compose logs -f backend

# 查看前端日志
docker-compose logs -f frontend
```

### 4. 停止服务

```bash
# 停止服务
docker-compose stop

# 停止并删除容器
docker-compose down

# 停止并删除容器及卷
docker-compose down -v
```

## 服务配置

### 后端服务 (backend)

- **端口**: 8000
- **技术栈**: Python 3.11 + FastAPI + jmcomic
- **热重载**: 支持（开发模式下代码修改会自动重载）

### 前端服务 (frontend)

- **端口**: 80
- **技术栈**: Node.js 22 + Vue 3 + Vite + Nginx
- **反向代理**: Nginx 自动将 `/api` 请求代理到后端服务

## 开发模式

如果需要在开发模式下运行并实时查看代码变更：

```bash
# 构建镜像
docker-compose build

# 启动服务（前台运行，显示日志）
docker-compose up

# 重新构建并启动
docker-compose up --build
```

## 生产环境部署

生产环境建议：

1. 修改 `docker-compose.yml` 中的端口映射
2. 配置环境变量（如数据库连接、API 密钥等）
3. 使用 Nginx 反向代理并配置 SSL 证书
4. 配置持久化存储卷

### 自定义端口

编辑 `docker-compose.yml`：

```yaml
services:
  frontend:
    ports:
      - "8080:80"  # 将前端改为 8080 端口
  backend:
    ports:
      - "8888:8000"  # 将后端改为 8888 端口
```

## 故障排查

### 容器无法启动

```bash
# 查看容器状态
docker-compose ps

# 查看详细日志
docker-compose logs backend
docker-compose logs frontend
```

### 前端无法连接后端

检查 `frontend/nginx.conf` 中的代理配置，确保 `proxy_pass` 指向正确的后端服务名称。

### 重新构建镜像

```bash
# 清理旧镜像
docker-compose down --rmi all

# 重新构建
docker-compose build --no-cache

# 启动
docker-compose up -d
```

## 项目结构

```
comic-web/
├── docker-compose.yml       # Docker Compose 配置
├── .dockerignore           # Docker 忽略文件
├── backend/
│   ├── Dockerfile          # 后端 Docker 镜像配置
│   ├── main.py            # FastAPI 应用入口
│   └── requirements.txt   # Python 依赖
├── frontend/
│   ├── Dockerfile         # 前端 Docker 镜像配置
│   ├── nginx.conf        # Nginx 配置
│   ├── package.json      # Node.js 依赖
│   └── src/              # Vue 源码
└── jmcomic/              # jmcomic Python 包
```

## 更多帮助

如有问题，请查看：
- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- 项目 API 文档：http://localhost:8000/docs
