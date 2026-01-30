#!/bin/bash
# ================================================================
# XMMCG CompetitionPhase Status Auto-Update Script (Linux/Debian)
# 自动更新比赛阶段状态
# ================================================================

set -e  # 遇到错误立即退出

# 项目路径配置（根据实际部署路径修改）
PROJECT_ROOT="/opt/xmmcg"
BACKEND_DIR="${PROJECT_ROOT}/backend/xmmcg"
VENV_PATH="${PROJECT_ROOT}/.venv"
LOG_DIR="/var/log/xmmcg"
LOG_FILE="${LOG_DIR}/phase_update.log"

# 创建日志目录（如果不存在）
mkdir -p "${LOG_DIR}"

# 记录开始时间
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting phase status update..." >> "${LOG_FILE}"

# 激活虚拟环境
if [ -f "${VENV_PATH}/bin/activate" ]; then
    source "${VENV_PATH}/bin/activate"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Virtual environment not found at ${VENV_PATH}" >> "${LOG_FILE}"
    exit 1
fi

# 切换到项目目录
cd "${BACKEND_DIR}"

# 执行更新命令
python manage.py update_phase_status >> "${LOG_FILE}" 2>&1

# 记录完成状态
if [ $? -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Phase status update completed successfully." >> "${LOG_FILE}"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Phase status update failed!" >> "${LOG_FILE}"
    exit 1
fi

echo "" >> "${LOG_FILE}"

# 停用虚拟环境
deactivate
