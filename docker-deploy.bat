@echo off
echo ========================================
echo Comic Web - Docker 一键部署
echo ========================================
echo.

REM 检查 Docker 是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Docker 未安装或未启动
    echo 请先安装 Docker Desktop: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM 检查 Docker Compose 是否可用
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Docker Compose 未安装
    pause
    exit /b 1
)

echo [信息] Docker 环境检查通过
echo.

REM 停止并删除旧容器
echo [步骤 1/4] 清理旧容器...
docker-compose down
echo.

REM 构建镜像
echo [步骤 2/4] 构建 Docker 镜像...
docker-compose build
if errorlevel 1 (
    echo [错误] 镜像构建失败
    pause
    exit /b 1
)
echo.

REM 启动服务
echo [步骤 3/4] 启动服务...
docker-compose up -d
if errorlevel 1 (
    echo [错误] 服务启动失败
    pause
    exit /b 1
)
echo.

REM 显示容器状态
echo [步骤 4/4] 检查服务状态...
timeout /t 3 /nobreak >nul
docker-compose ps
echo.

echo ========================================
echo 部署完成！
echo ========================================
echo.
echo 服务访问地址:
echo   前端页面: http://localhost
echo   后端 API: http://localhost:8000
echo   API 文档: http://localhost:8000/docs
echo.
echo 常用命令:
echo   查看日志: docker-compose logs -f
echo   停止服务: docker-compose stop
echo   重启服务: docker-compose restart
echo   删除容器: docker-compose down
echo.
pause
