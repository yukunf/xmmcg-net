@echo off
REM Django 用户管理系统 - 启动脚本

echo.
echo ================================
echo Django 用户管理后端启动脚本
echo ================================
echo.

REM 检查是否在正确的目录
if not exist "manage.py" (
    echo 错误: 请在 backend/xmmcg 目录下运行此脚本
    pause
    exit /b 1
)

REM 检查虚拟环境
if not exist "..\..\\.venv\Scripts\activate.bat" (
    echo 错误: 虚拟环境不存在
    echo 请先创建虚拟环境并安装依赖
    pause
    exit /b 1
)

echo 激活虚拟环境...
call ..\..\\.venv\Scripts\activate.bat

echo 安装依赖...
pip install -q -r requirements.txt

echo.
echo 执行数据库迁移...
python manage.py migrate --noinput

echo.
echo ================================
echo 启动 Django 开发服务器
echo ================================
echo.
echo 服务器地址: http://localhost:8000
echo API 基础 URL: http://localhost:8000/api/users
echo Django Admin: http://localhost:8000/admin
echo.
echo 按 Ctrl+C 停止服务器
echo.

python manage.py runserver

pause
