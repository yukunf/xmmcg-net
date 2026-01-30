#!/bin/bash
# ================================================================
# XMMCG 路径更新和日志目录设置脚本
# 用于从 /var/www/xmmcg-net 迁移到 /opt/xmmcg
# ================================================================

set -e

echo "=========================================="
echo "  XMMCG 路径更新脚本"
echo "=========================================="

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 请使用 sudo 运行此脚本"
    exit 1
fi

# 创建必要的日志目录
echo "📁 创建日志目录..."
mkdir -p /var/log/xmmcg
chown www-data:www-data /var/log/xmmcg
chmod 755 /var/log/xmmcg

# 如果存在旧的日志文件，迁移过来
OLD_LOG_DIR="/var/www/xmmcg-net/logs"
NEW_LOG_DIR="/var/log/xmmcg"

if [ -d "$OLD_LOG_DIR" ]; then
    echo "📦 迁移旧日志文件..."
    cp -r "$OLD_LOG_DIR"/* "$NEW_LOG_DIR/" 2>/dev/null || true
    chown -R www-data:www-data "$NEW_LOG_DIR"
    echo "✅ 日志文件迁移完成"
fi

# 更新 systemd 服务（如果存在）
if [ -f "/etc/systemd/system/xmmcg-phase-update.service" ]; then
    echo "🔄 更新 systemd 服务..."
    systemctl stop xmmcg-phase-update.service 2>/dev/null || true
    systemctl stop xmmcg-phase-update.timer 2>/dev/null || true
    
    # 复制新的服务文件
    cp /opt/xmmcg/scripts/systemd/xmmcg-phase-update.service /etc/systemd/system/
    cp /opt/xmmcg/scripts/systemd/xmmcg-phase-update.timer /etc/systemd/system/
    
    # 重新加载 systemd
    systemctl daemon-reload
    
    # 启用并启动服务
    systemctl enable xmmcg-phase-update.timer
    systemctl start xmmcg-phase-update.timer
    
    echo "✅ systemd 服务更新完成"
fi

# 检查 crontab 是否需要更新
echo "⚠️  请注意：如果你使用了 crontab 定时任务，请手动更新："
echo "   crontab -e"
echo "   参考文件：/opt/xmmcg/scripts/crontab.example"

# 检查 nginx 配置
echo "⚠️  请检查 nginx 配置是否需要更新："
echo "   - 静态文件应该在 /var/www/xmmcg/"
echo "   - 代码库在 /opt/xmmcg/"

echo ""
echo "✅ 路径更新完成！"
echo ""
echo "📋 接下来的步骤："
echo "1. 检查并更新 nginx 配置文件"
echo "2. 更新 crontab（如果使用）"
echo "3. 重新启动相关服务"
echo "4. 验证定时任务是否正常工作"