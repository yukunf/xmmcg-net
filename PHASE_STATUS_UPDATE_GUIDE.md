# CompetitionPhase 自动更新 is_active 状态 - 部署指南

## 📋 概述

为了确保 `CompetitionPhase` 的 `is_active` 字段能够根据时间自动更新，我们提供了一个 Django management command 和多种定时执行方案。

---

## 🚀 使用方式

### 1. 手动执行命令

```bash
# 进入项目目录
cd backend/xmmcg

# 激活虚拟环境（如果使用）
source venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows

# 执行更新命令
python manage.py update_phase_status

# 干运行模式（只查看不修改）
python manage.py update_phase_status --dry-run
```

### 2. 命令输出示例

```
✓ 已激活: 第一轮竞标 (phase_key: bidding)
✓ 已停用: 歌曲提交期 (phase_key: music_submit)
============================================================
✓ 成功更新 2 个阶段
激活: 1 个
停用: 1 个

当前活跃阶段:
  • 第一轮竞标 (bidding)
============================================================
```

---

## ⏰ 定时任务配置

### 方案 A：Windows 任务计划程序（推荐）

1. **打开任务计划程序**
   - 按 `Win + R`，输入 `taskschd.msc`

2. **创建基本任务**
   - 右键点击"任务计划程序库" → "创建基本任务"
   - 名称：`XMMCG Phase Status Update`
   - 描述：`自动更新比赛阶段状态`

3. **设置触发器**
   - 选择：每天
   - 开始时间：00:00（午夜）
   - 重复间隔：每 1 小时

4. **设置操作**
   - 操作：启动程序
   - 程序/脚本：`C:\Users\fengy\xmmcg-net\.venv\Scripts\python.exe`
   - 添加参数：`manage.py update_phase_status`
   - 起始于：`C:\Users\fengy\xmmcg-net\backend\xmmcg`

5. **高级设置**
   - ✅ 如果任务失败，每隔 1 分钟重试
   - ✅ 最多重试 3 次

### 方案 B：批处理脚本 + 任务计划程序

创建 `update_phase.bat`：

```batch
@echo off
cd /d C:\Users\fengy\xmmcg-net\backend\xmmcg
call C:\Users\fengy\xmmcg-net\.venv\Scripts\activate.bat
python manage.py update_phase_status >> C:\Users\fengy\xmmcg-net\logs\phase_update.log 2>&1
```

然后在任务计划程序中执行此批处理文件。

### 方案 C：Celery 定时任务（生产环境推荐）

1. **安装 Celery 和 Redis**

```bash
pip install celery redis
```

2. **创建 Celery 配置** (`xmmcg/celery.py`)

```python
from celery import Celery
from celery.schedules import crontab
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'xmmcg.settings')

app = Celery('xmmcg')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# 定时任务配置
app.conf.beat_schedule = {
    'update-phase-status-every-hour': {
        'task': 'songs.tasks.update_phase_status',
        'schedule': crontab(minute=0),  # 每小时整点执行
    },
}
```

3. **创建任务** (`songs/tasks.py`)

```python
from celery import shared_task
from django.core.management import call_command

@shared_task
def update_phase_status():
    """定时更新 CompetitionPhase 状态"""
    call_command('update_phase_status')
```

4. **启动 Celery Worker 和 Beat**

```bash
# 启动 worker
celery -A xmmcg worker -l info

# 启动 beat（定时任务调度器）
celery -A xmmcg beat -l info
```

---

## 🔧 推荐执行频率

| 场景 | 频率建议 | 说明 |
|------|---------|------|
| 开发环境 | 每 5 分钟 | 便于测试 |
| 测试环境 | 每 30 分钟 | 平衡及时性和资源 |
| 生产环境 | 每 1 小时 | 足够及时且不占用资源 |
| 重要阶段转换前 | 每 1 分钟 | 确保准时切换 |

---

## ✅ 验证定时任务是否生效

1. **查看日志**
   - 检查任务计划程序的历史记录
   - 查看 Django 日志输出

2. **手动测试**
   ```bash
   # 设置一个即将到期的阶段
   # 等待定时任务执行
   # 检查 is_active 是否自动更新
   ```

3. **数据库检查**
   ```sql
   SELECT name, phase_key, is_active, start_time, end_time 
   FROM songs_competitionphase 
   ORDER BY start_time;
   ```

---

## 📝 注意事项

1. **时区问题**
   - 确保 Django 的 `TIME_ZONE` 设置正确
   - Windows 任务计划程序使用系统本地时间

2. **权限问题**
   - 确保任务以有足够权限的用户身份运行
   - Python 虚拟环境路径需要正确

3. **日志记录**
   - 建议将输出重定向到日志文件
   - 定期清理旧日志

4. **失败重试**
   - 任务失败时应有重试机制
   - 重要阶段切换前应收到通知

---

## 🛠️ 故障排查

### 问题：任务没有执行

**检查清单：**
- [ ] 任务计划程序中任务是否启用
- [ ] Python 路径是否正确
- [ ] 工作目录是否正确
- [ ] 虚拟环境是否激活

### 问题：执行失败

**检查清单：**
- [ ] 查看错误日志
- [ ] 手动运行命令确认
- [ ] 检查数据库连接
- [ ] 检查文件权限

### 问题：is_active 没有更新

**检查清单：**
- [ ] 时区设置是否正确
- [ ] 阶段时间配置是否正确
- [ ] 使用 `--dry-run` 测试

---

## 📚 相关文档

- [Django Management Commands](https://docs.djangoproject.com/en/stable/howto/custom-management-commands/)
- [Windows Task Scheduler](https://docs.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-start-page)
- [Celery Documentation](https://docs.celeryproject.org/)

---

## 🎯 快速开始（Windows）

```powershell
# 1. 测试命令是否正常
cd C:\Users\fengy\xmmcg-net\backend\xmmcg
.venv\Scripts\activate
python manage.py update_phase_status --dry-run

# 2. 创建批处理文件
# 保存为 C:\Users\fengy\xmmcg-net\scripts\update_phase.bat

# 3. 设置 Windows 任务计划（使用管理员权限）
schtasks /create /tn "XMMCG-PhaseUpdate" /tr "C:\Users\fengy\xmmcg-net\scripts\update_phase.bat" /sc hourly /st 00:00

# 4. 验证任务已创建
schtasks /query /tn "XMMCG-PhaseUpdate"

# 5. 手动运行测试
schtasks /run /tn "XMMCG-PhaseUpdate"
```
