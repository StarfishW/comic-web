#!/bin/bash

echo "========================================"
echo "Comic Web - Docker 一键部署"
echo "========================================"
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "[错误] Docker 未安装或未启动"
    echo "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# 检查 Docker Compose 是否可用
if ! command -v docker-compose &> /dev/null; then
    echo "[错误] Docker Compose 未安装"
    exit 1
fi

echo "[信息] Docker 环境检查通过"
echo ""

# 停止并删除旧容器
echo "[步骤 1/4] 清理旧容器..."
docker-compose down
echo ""

# 构建镜像
echo "[步骤 2/4] 构建 Docker 镜像..."
docker-compose build
if [ $? -ne 0 ]; then
    echo "[错误] 镜像构建失败"
    exit 1
fi
echo ""

# 启动服务
echo "[步骤 3/4] 启动服务..."
docker-compose up -d
if [ $? -ne 0 ]; then
    echo "[错误] 服务启动失败"
    exit 1
fi
echo ""

# 显示容器状态
echo "[步骤 4/4] 检查服务状态..."
sleep 3
docker-compose ps
echo ""

echo "========================================"
echo "部署完成！"
echo "========================================"
echo ""
echo "服务访问地址:"
echo "  前端页面: http://localhost"
echo "  后端 API: http://localhost:8000"
echo "  API 文档: http://localhost:8000/docs"
echo ""
echo "常用命令:"
echo "  查看日志: docker-compose logs -f"
echo "  停止服务: docker-compose stop"
echo "  重启服务: docker-compose restart"
echo "  删除容器: docker-compose down"
echo ""
