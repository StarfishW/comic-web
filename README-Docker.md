# Docker 部署指南

## 前置要求

- Docker Engine 20.10+
- Docker Compose 2.0+
- 已克隆本仓库（含子模块）

## 快速开始

```bash
# 1. 初始化 jmcomic 子模块（首次克隆必须执行）
git submodule update --init

# 2. 构建镜像并后台启动
docker compose up --build -d
```

启动后访问：

| 服务 | 地址 |
|------|------|
| 前端页面 | http://localhost:90 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |

## 服务说明

### backend

| 项目 | 内容 |
|------|------|
| 镜像基础 | python:3.11-slim |
| 端口 | 8000 |
| 框架 | FastAPI + uvicorn |
| 缓存路径 | `/app/backend/chapter_cache`（命名卷 `comic_cache` 持久化） |

### frontend

| 项目 | 内容 |
|------|------|
| 构建基础 | node:22-alpine（多阶段构建） |
| 运行基础 | nginx:alpine |
| 端口 | 90（容器内 80） |
| API 代理 | Nginx 将 `/api/*` 反代到 `backend:8000` |

## 数据持久化

漫画缓存存储在 Docker 命名卷 `comic_cache` 中，容器重启或 `docker compose down` 后数据不会丢失。

```bash
# 查看卷占用
docker volume inspect comic_cache

# 停止服务但保留缓存
docker compose down

# 停止服务并清空缓存（谨慎）
docker compose down -v
```

## 常用命令

```bash
# 查看运行状态
docker compose ps

# 查看实时日志
docker compose logs -f
docker compose logs -f backend
docker compose logs -f frontend

# 停止服务
docker compose stop

# 重新构建（代码更新后）
docker compose up --build -d
```

## 自定义端口

编辑 `docker-compose.yml` 中的 `ports` 字段：

```yaml
services:
  frontend:
    ports:
      - "8080:80"    # 前端改为 8080
  backend:
    ports:
      - "8888:8000"  # 后端改为 8888
```

## 故障排查

**构建失败 / jmcomic 相关报错**

```bash
git submodule update --init
docker compose build --no-cache
```

**前端无法请求后端**

检查 `frontend/nginx.conf` 中 `proxy_pass` 是否为 `http://backend:8000`，两个服务需在同一 Docker 网络（`comic-network`）中。

**清理重来**

```bash
docker compose down --rmi all -v
docker compose up --build -d
```

## 项目结构

```
comic-web/
├── docker-compose.yml       # Compose 配置（生产模式）
├── .dockerignore
├── backend/
│   ├── Dockerfile
│   ├── main.py              # FastAPI 入口，缓存目录 ./chapter_cache
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile           # 多阶段构建：Node 编译 → Nginx 服务
│   ├── nginx.conf           # SPA 路由 + /api 反代
│   └── src/
└── jmcomic/                 # git submodule
```
