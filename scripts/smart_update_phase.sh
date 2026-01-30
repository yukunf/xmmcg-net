#!/bin/bash
# ================================================================
# 智能调整定时任务频率的脚本
# 根据距离下一个阶段切换的时间动态调整执行频率
# ================================================================

set -e

# 项目路径配置
PROJECT_ROOT="/opt/xmmcg"
BACKEND_DIR="${PROJECT_ROOT}/backend/xmmcg"
VENV_PATH="${PROJECT_ROOT}/.venv"
LOG_FILE="/var/log/xmmcg/smart_update.log"

# 激活虚拟环境
source "${VENV_PATH}/bin/activate"
cd "${BACKEND_DIR}"

# 获取下一个阶段切换的时间（秒）
# 使用 Python 脚本计算
SECONDS_TO_NEXT=$(python << EOF
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xmmcg.settings')
django.setup()

from django.utils import timezone
from songs.models import CompetitionPhase

now = timezone.now()

# 查找最近的阶段切换时间点
upcoming_starts = CompetitionPhase.objects.filter(
    is_active=True,
    start_time__gt=now
).order_by('start_time').first()

upcoming_ends = CompetitionPhase.objects.filter(
    is_active=True,
    end_time__gt=now
).order_by('end_time').first()

# 找出最近的切换时间
times = []
if upcoming_starts:
    times.append(upcoming_starts.start_time)
if upcoming_ends:
    times.append(upcoming_ends.end_time)

if times:
    next_change = min(times)
    delta = (next_change - now).total_seconds()
    print(int(delta))
else:
    # 如果没有即将到来的切换，返回一个大值
    print(86400)  # 24小时
EOF
)

# 记录日志
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Next phase change in ${SECONDS_TO_NEXT} seconds" >> "${LOG_FILE}"

# 根据时间决定是否执行
# 如果距离切换不到 2 小时（7200秒），强制执行
# 否则，只在整点执行
CURRENT_MINUTE=$(date +%M)

if [ "${SECONDS_TO_NEXT}" -lt 7200 ]; then
    # 距离切换不到 2 小时，每次都执行
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Executing update (approaching phase change)" >> "${LOG_FILE}"
    ${PROJECT_ROOT}/scripts/update_phase_linux.sh
elif [ "${CURRENT_MINUTE}" = "00" ]; then
    # 平时只在整点执行
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Executing update (hourly schedule)" >> "${LOG_FILE}"
    ${PROJECT_ROOT}/scripts/update_phase_linux.sh
else
    # 跳过本次执行
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Skipping update (not scheduled)" >> "${LOG_FILE}"
fi

deactivate
