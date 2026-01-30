#!/bin/bash
# ================================================================
# XMMCG Phase Update - 一键部署脚本（Debian/Ubuntu）
# ================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目路径（根据实际情况修改）
PROJECT_ROOT="/var/www/xmmcg-net"

echo -e "${BLUE}=== XMMCG Phase Update Deployment ===${NC}"
echo ""

# 检查是否在正确的目录
if [ ! -d "${PROJECT_ROOT}" ]; then
    echo -e "${RED}错误: 项目目录不存在: ${PROJECT_ROOT}${NC}"
    echo "请修改脚本中的 PROJECT_ROOT 变量"
    exit 1
fi

# 步骤 1: 设置系统时区
echo -e "${YELLOW}[1/7] 设置系统时区为 Asia/Shanghai...${NC}"
if command -v timedatectl &> /dev/null; then
    sudo timedatectl set-timezone Asia/Shanghai
    echo -e "${GREEN}✓ 时区设置完成${NC}"
    timedatectl | grep "Time zone"
else
    echo -e "${YELLOW}⚠ timedatectl 未找到，跳过时区设置${NC}"
fi
echo ""

# 步骤 2: 安装必要的系统包
echo -e "${YELLOW}[2/7] 检查必要的系统包...${NC}"
if ! command -v ntpdate &> /dev/null; then
    echo "安装 ntpdate..."
    sudo apt-get update -qq
    sudo apt-get install -y ntpdate
fi
echo -e "${GREEN}✓ 系统包检查完成${NC}"
echo ""

# 步骤 3: 同步系统时间
echo -e "${YELLOW}[3/7] 同步系统时间...${NC}"
if command -v ntpdate &> /dev/null; then
    sudo ntpdate -u ntp.ubuntu.com || echo -e "${YELLOW}⚠ 时间同步失败，继续...${NC}"
fi
echo -e "${GREEN}✓ 当前系统时间: $(date)${NC}"
echo ""

# 步骤 4: 设置脚本权限
echo -e "${YELLOW}[4/7] 设置脚本执行权限...${NC}"
chmod +x ${PROJECT_ROOT}/scripts/update_phase_linux.sh
chmod +x ${PROJECT_ROOT}/scripts/smart_update_phase.sh
echo -e "${GREEN}✓ 脚本权限设置完成${NC}"
ls -lh ${PROJECT_ROOT}/scripts/*.sh
echo ""

# 步骤 5: 创建日志目录
echo -e "${YELLOW}[5/7] 创建日志目录...${NC}"
mkdir -p ${PROJECT_ROOT}/logs
chmod 755 ${PROJECT_ROOT}/logs
echo -e "${GREEN}✓ 日志目录创建完成: ${PROJECT_ROOT}/logs${NC}"
echo ""

# 步骤 6: 测试 Django 命令
echo -e "${YELLOW}[6/7] 测试 Django 管理命令...${NC}"
if [ -f "${PROJECT_ROOT}/.venv/bin/activate" ]; then
    source ${PROJECT_ROOT}/.venv/bin/activate
    cd ${PROJECT_ROOT}/backend/xmmcg
    
    echo "执行干运行模式..."
    python manage.py update_phase_status --dry-run
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Django 命令测试成功${NC}"
    else
        echo -e "${RED}✗ Django 命令测试失败${NC}"
        exit 1
    fi
    
    deactivate
else
    echo -e "${RED}✗ 虚拟环境未找到: ${PROJECT_ROOT}/.venv${NC}"
    exit 1
fi
echo ""

# 步骤 7: 配置 Crontab
echo -e "${YELLOW}[7/7] 配置 Crontab 定时任务...${NC}"
echo ""
echo "请选择定时任务方案："
echo "  1) 智能频率（推荐）- 平时每小时，切换前每 10 分钟"
echo "  2) 固定频率 - 每小时整点"
echo "  3) 高频模式 - 每 30 分钟"
echo "  4) 跳过配置（手动配置）"
echo ""
read -p "请输入选项 [1-4]: " choice

case $choice in
    1)
        CRON_LINE="*/10 * * * * ${PROJECT_ROOT}/scripts/smart_update_phase.sh"
        echo "已选择: 智能频率模式"
        ;;
    2)
        CRON_LINE="0 * * * * ${PROJECT_ROOT}/scripts/update_phase_linux.sh"
        echo "已选择: 每小时固定模式"
        ;;
    3)
        CRON_LINE="0,30 * * * * ${PROJECT_ROOT}/scripts/update_phase_linux.sh"
        echo "已选择: 高频模式（每 30 分钟）"
        ;;
    4)
        echo "跳过 crontab 配置"
        CRON_LINE=""
        ;;
    *)
        echo "无效选项，使用默认值（智能频率）"
        CRON_LINE="*/10 * * * * ${PROJECT_ROOT}/scripts/smart_update_phase.sh"
        ;;
esac

if [ -n "$CRON_LINE" ]; then
    # 检查是否已存在相同的 cron 任务
    if crontab -l 2>/dev/null | grep -q "xmmcg-net/scripts"; then
        echo -e "${YELLOW}⚠ 检测到已存在的 crontab 任务${NC}"
        echo "当前 crontab:"
        crontab -l | grep "xmmcg-net/scripts"
        echo ""
        read -p "是否替换现有任务？[y/N]: " replace
        if [[ $replace =~ ^[Yy]$ ]]; then
            # 移除旧任务
            crontab -l 2>/dev/null | grep -v "xmmcg-net/scripts" | crontab -
            # 添加新任务
            (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
            echo -e "${GREEN}✓ Crontab 任务已替换${NC}"
        else
            echo "保持现有 crontab 配置"
        fi
    else
        # 添加新任务
        (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
        echo -e "${GREEN}✓ Crontab 任务已添加${NC}"
    fi
fi
echo ""

# 最终验证
echo -e "${BLUE}=== 部署验证 ===${NC}"
echo ""

echo -e "${GREEN}当前系统时区:${NC}"
timedatectl | grep "Time zone" || date

echo ""
echo -e "${GREEN}当前 Crontab 配置:${NC}"
crontab -l | grep "xmmcg-net" || echo "（未配置）"

echo ""
echo -e "${GREEN}脚本文件:${NC}"
ls -lh ${PROJECT_ROOT}/scripts/*.sh

echo ""
echo -e "${GREEN}日志目录:${NC}"
ls -ld ${PROJECT_ROOT}/logs

echo ""
echo -e "${BLUE}=== 部署完成! ===${NC}"
echo ""
echo -e "${GREEN}后续操作:${NC}"
echo "  1. 查看日志: tail -f ${PROJECT_ROOT}/logs/phase_update.log"
echo "  2. 手动执行测试: ${PROJECT_ROOT}/scripts/update_phase_linux.sh"
echo "  3. 验证 cron 运行: sudo tail -f /var/log/syslog | grep CRON"
echo "  4. 检查阶段状态: cd ${PROJECT_ROOT}/backend/xmmcg && python manage.py shell"
echo ""
echo -e "${YELLOW}提示: 请确保 .env 文件中的 TIME_ZONE=Asia/Shanghai${NC}"
echo ""
